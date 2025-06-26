import os
from google.cloud import ndb
import osv


def main():
  start_cursor = None
  if cursor_str := os.getenv('START_CURSOR'):
    start_cursor=ndb.Cursor.from_websafe_string(cursor_str)
  it = osv.Bug.query().iter(start_cursor=start_cursor)
  for i, bug in enumerate(it):
    cursor: ndb.Cursor = it.cursor_after()
    print(f'{i}: {bug.db_id} {cursor.to_websafe_string()}')
    bug.put()


if __name__ == '__main__':
  with ndb.Client().context(cache_policy=False):
    main()