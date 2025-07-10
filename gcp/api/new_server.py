"""
A new, experimental implementation of the OSV API server logic.

This module contains functions for querying vulnerabilities from different
data sources (Datastore, GCS) and is intended for performance benchmarking
and testing of new query strategies.
"""

import concurrent.futures
import logging

from google.cloud import ndb
from google.cloud import storage
from google.protobuf import json_format
from google.protobuf import timestamp_pb2
from google.cloud.ndb import tasklets

import osv
from osv import ecosystems
from osv import vulnerability_pb2

# TODO: don't hard code these.
storage_client = storage.Client()
GCS_BUCKET = storage_client.bucket('michaelkedar-test-osv-export')
# TODO: Global ThreadPoolExecutor is kinda bad.
_GET_FROM_BUCKET_POOL = concurrent.futures.ThreadPoolExecutor(max_workers=32)


@ndb.tasklet
def query_by_version_new(
    context,
    package_name: str | None,
    ecosystem: str | None,
    version: str,
    include_details: bool = True
) -> list[vulnerability_pb2.Vulnerability]:
  """
  Queries for vulnerabilities by package and version using a new data model.

  This function is designed to test a new query path that may use different
  data sources (like GCS) for fetching vulnerability details.

  Args:
    context: The QueryContext for the current request.
    package_name: The name of the package.
    ecosystem: The package's ecosystem.
    version: The version of the package to query for.
    include_details: Whether to return full or minimal vulnerability details.

  Returns:
    A list of Vulnerability protos.
  """
  # TODO: This and AffectedVersions do not handle some unqualified ecosystems,
  # e.g., 'Debian' (instead of 'Debian:11').
  # TODO: This does not support querying Git tags.

  if not package_name:
    return []

  query = osv.AffectedVersions.query(osv.AffectedVersions.name == package_name)
  if ecosystem:
    query = query.filter(osv.AffectedVersions.ecosystem == ecosystem)
  query = query.order(osv.AffectedVersions.bug_id)

  bugs = []
  # In case a package matches multiple times for the same bug, we only need to
  # process it once. Since results are ordered by bug_id, we only need to
  # track the last matched ID.
  # TODO: If this gets paginated, it might return the same vuln multiple times.
  last_matched_id = ''

  context.query_counter += 1
  if context.should_skip_query():
    return bugs

  it: ndb.QueryIterator = query.iter(start_cursor=context.cursor_at_current())
  while (yield it.has_next_async()):
    try:
      if context.should_break_page(len(bugs)):
        context.save_cursor_at_page_break(it)
        break

      affected: osv.AffectedVersions = it.next()
      if affected.bug_id == last_matched_id:
        continue

      if affected_affects(version, affected):
        last_matched_id = affected.bug_id
        if include_details:
          bugs.append(
              get_from_bucket_async(GCS_BUCKET, affected.bug_id,
                                    affected.ecosystem))
        else:
          bugs.append(get_minimal_from_datastore_async(affected.bug_id))

        context.total_responses.add(1)
    except Exception:
      logging.exception('Failed to query by version')

  bugs = yield bugs
  return list(bugs)


def affected_affects(version: str, affected: osv.AffectedVersions) -> bool:
  """Checks if a given version is affected by the AffectedVersions entry."""
  ecosystem_helper = ecosystems.get(affected.ecosystem)
  if len(affected.versions) > 0:
    if ecosystem_helper and ecosystem_helper.supports_comparing:
      ver = ecosystem_helper.sort_key(version)
      return ver in (ecosystem_helper.sort_key(v) for v in affected.versions)
    else:
      return version in affected.versions

  if ecosystem_helper and ecosystem_helper.supports_comparing:
    ver = ecosystem_helper.sort_key(version)
    # Find where this version belongs in the sorted events list.
    for event in reversed(affected.events):
      event_ver = ecosystem_helper.sort_key(event.value)
      if event_ver == ver:
        return event.type in ('introduced', 'last_affected')
      if event_ver < ver:
        return event.type == 'introduced'
    return False

  return False


@ndb.tasklet
def get_from_datastore_async(bug_id: str):
  """Gets a full vulnerability from Datastore."""
  b: osv.Bug = yield osv.Bug.get_by_id_async(bug_id)
  vuln = yield b.to_vulnerability_async(True, True, True)
  return vuln


@ndb.tasklet
def get_minimal_from_datastore_async(bug_id: str):
  """Gets a minimal vulnerability from Datastore."""
  bug, alias, upstream = yield (osv.Bug.query(
      osv.Bug.db_id == bug_id,
      projection=[osv.Bug.last_modified]).get_async(),
                                osv.get_aliases_async(bug_id),
                                osv.get_upstream_async(bug_id))
  modified = None

  if bug and bug.last_modified:
    modified = bug.last_modified

  if alias and alias.last_modified:
    if modified is None:
      modified = alias.last_modified
    else:
      modified = max(modified, alias.last_modified)

  if upstream and upstream.last_modified:
    if modified is None:
      modified = upstream.last_modified
    else:
      modified = max(modified, upstream.last_modified)

  if modified is not None:
    ts = timestamp_pb2.Timestamp()
    ts.FromDatetime(modified)
    modified = ts

  return vulnerability_pb2.Vulnerability(id=bug_id, modified=modified)


def get_from_bucket(bucket: storage.Bucket, bug_id: str,
                    ecosystem: str) -> vulnerability_pb2.Vulnerability:
  """Gets a vulnerability from a GCS bucket."""
  ecosystem = ecosystems.normalize(ecosystem)
  # Directly create a blob object and download.
  # This avoids a metadata GET request and combines it with the data read.
  blob = bucket.blob(f'{ecosystem}/{bug_id}.json')
  try:
    data = blob.download_as_bytes()
    return json_format.Parse(data, vulnerability_pb2.Vulnerability())
  except storage.NotFound:
    # The blob doesn't exist, handle this case.
    # TODO: Add smarter error handling if the vuln isn't in the bucket.
    return vulnerability_pb2.Vulnerability()


def get_from_bucket_async(bucket: storage.Bucket, bug_id: str,
                          ecosystem: str) -> ndb.Future:
  """
  Asynchronously gets a vulnerability from a GCS bucket using a thread pool.
  """
  f = _GET_FROM_BUCKET_POOL.submit(get_from_bucket, bucket, bug_id, ecosystem)

  @ndb.tasklet
  def async_poll_result():
    while not f.done():
      yield tasklets.sleep(0.1)
    return f.result()

  def cleanup(_: ndb.Future):
    f.cancel()

  future = async_poll_result()
  future.add_done_callback(cleanup)
  return future