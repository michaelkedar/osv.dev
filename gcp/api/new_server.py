import concurrent.futures
import logging

from google.cloud import ndb

import osv
from osv import ecosystems
from osv import vulnerability_pb2


@ndb.tasklet
def query_by_version_new(
  context,
  package_name: str | None,
  ecosystem: str | None,
  version: str,
  include_details: bool = True
) -> list[vulnerability_pb2.Vulnerability]:
  
  # TODO: this & AffectedVersions does not handle some unqualified ecosystems
  # e.g. 'Debian' (instead of 'Debian:11')
  # AffectedVersions probably needs to also create the bare versions?
  
  # TODO: also doesn't support querying Git tags
  
  if not package_name:
    return []
  
  query = osv.AffectedVersions.query(osv.AffectedVersions.name == package_name)
  if ecosystem:
    query = query.filter(osv.AffectedVersions.ecosystem == ecosystem)
  query = query.order(osv.AffectedVersions.bug_id)

  bugs = []
  # in case something matches multiple times
  # since the ids are in order, we only need to track the last matched one
  # TODO: if this gets paginated, it might return the same vuln multiple times
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
        # bugs.append(osv.Bug.get_by_id_async(affected.bug_id))
        # bugs.append(vulnerability_pb2.Vulnerability(id=affected.bug_id))
        # bugs.append(get_from_bucket_async(affected.bug_id, affected.ecosystem))
        bugs.append(get_from_datastore_async(affected.bug_id))
        
        context.total_responses.add(1)
    except:
      logging.exception('failed to query by versions')

  bugs = yield bugs
  if not include_details:
    return [vulnerability_pb2.Vulnerability(id=b.id, modified=b.modified) for b in bugs]
  return list(bugs)
  # return bugs


def affected_affects(version: str, affected: osv.AffectedVersions) -> bool:
  ecosystem_helper = ecosystems.get(affected.ecosystem)
  if len(affected.versions) > 0:
    if ecosystem_helper and ecosystem_helper.supports_comparing:
      ver = ecosystem_helper.sort_key(version)
      return ver in (ecosystem_helper.sort_key(v) for v in affected.versions)
    else:
      return version in affected.versions

  if ecosystem_helper and ecosystem_helper.supports_comparing:
    ver = ecosystem_helper.sort_key(version)
    # Find where this version belongs in the sorted events list
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
  b: osv.Bug = yield osv.Bug.get_by_id_async(bug_id)
  vuln = yield b.to_vulnerability_async(True, True, True)
  return vuln


from google.cloud import storage
from google.protobuf import json_format
from google.cloud.ndb import tasklets
import concurrent.futures

def get_from_bucket(bug_id: str, ecosystem: str) -> vulnerability_pb2.Vulnerability:
  cl = storage.Client()
  bucket = cl.bucket('michaelkedar-test-osv-export')
  ecosystem = ecosystems.normalize(ecosystem)
  blob = bucket.get_blob(f'{ecosystem}/{bug_id}.json')
  if blob is None:
    # TODO: some smarter error if the vuln isn't in the bucket
    return vulnerability_pb2.Vulnerability()
  else:
    data = blob.download_as_bytes()
    return json_format.Parse(data, vulnerability_pb2.Vulnerability())

# TODO: not too sure about this global ThreadPoolExecutor
_get_from_bucket_pool = concurrent.futures.ThreadPoolExecutor(max_workers=128)

def get_from_bucket_async(bug_id: str, ecosystem: str) -> ndb.Future:
  f = _get_from_bucket_pool.submit(get_from_bucket, bug_id, ecosystem)

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
