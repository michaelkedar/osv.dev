from google.cloud import ndb
import osv

BATCH_SIZE=50

@ndb.tasklet
def main():
  i = 0
  it = osv.Bug.query(osv.Bug.db_id >= 'ASB-A-253344080').iter(limit=100)
  futures = []
  while (yield it.has_next_async()):
    bug = next(it)
    i += 1
    print(f'{i}: {bug.db_id}')
    futures.append(do_put(bug))
    if len(futures) >= BATCH_SIZE:
      ndb.wait_all(futures)
      futures = []
  ndb.wait_all(futures)

@ndb.tasklet
def do_put(bug):
  yield bug.put_async()


if __name__ == '__main__':
  with ndb.Client().context():
    main().result()