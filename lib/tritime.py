import os
import json
import hashlib
from datetime import datetime
from azure.core.exceptions import AzureError
from azure.cosmos import CosmosClient, PartitionKey

# Maybe make this conditional ?
from lib.trisync import add_queue_entry

json_dt_fmt = '%Y-%m-%d %H:%M:%S'


def hash_badge_data(punches: list):
    data_str = json.dumps(punches)
    hashval = hashlib.sha256(data_str.encode()).hexdigest()
    return hashval


def get_badges():
    local_filename = 'badges.json'
    if not os.path.exists(local_filename):
        with open(local_filename, 'w') as f:
            f.write(json.dumps({}))
    with open(local_filename, 'r') as f:
        return json.loads(f.read())


def _get_badges_cosmos():
    bcont = get_badge_container()
    bdata = bcont.read_all_items()
    badges = {}
    for bd in bdata:
        num = bd['badge_num']
        badges[num] = bd
    return badges


def get_badges():
    if _use_cosmos():
        return _get_badges_cosmos()
    else:
        return _get_badges_local()


def _store_badges_local(data: dict):
    with open('badges.json', 'w') as f:
        f.write(json.dumps(data, indent=4, sort_keys=True))


def _store_badges_cosmos(data: dict):
    bcont = get_badge_container()
    for badge_num, b in data.items():
        if 'id' not in b.keys():
            b['id'] = badge_num
        if 'badge_num' not in b.keys():
            b['badge_num'] = badge_num
        bcont.upsert_item(b)


def store_badges(data: dict):
    if _use_cosmos():
        _store_badges_cosmos(data)
    else:
        _store_badges_local(data)


def _read_punches_local(badge: str):
    datafile = f'punch_data_{badge}.json'
    if os.path.exists(datafile):
        with open(datafile, 'r') as f:
            punch_data = json.loads(f.read())
    else:
        punch_data = []
    return punch_data


def _read_punches_cosmos(badge: str):
    bcont = get_badge_container()
    badge_data = bcont.read_item(item=badge, partition_key=badge)
    pass


def read_punches(badge: str):
    if _use_cosmos():
        return _read_punches_cosmos(badge)
    else:
        return _read_punches_local(badge)


def write_punches(badge: str, punch_data: list):
    punch_data = sorted(punch_data, key=lambda x: x['ts_in'])
    datafile = f'punch_data_{badge}.json'
    with open(datafile, 'w') as f:
        f.write(json.dumps(punch_data, indent=4, sort_keys=True))


def punch_in(badge: str, dt: datetime):
    json_dt = dt.strftime(json_dt_fmt)
    punch_data = read_punches(badge)
    punch_data.append({'ts_in': json_dt})
    write_punches(badge, punch_data)

    # Change status
    badges = get_badges()
    badges[badge]['status'] = 'in'
    store_badges(badges)
    return badges


def punch_out(badge: str, dt: datetime):
    json_dt = dt.strftime(json_dt_fmt)
    add_queue_entry(badge, 'punch_out', dt)
    punch_data = read_punches(badge)
    punch_data = sorted(punch_data, key=lambda x: x['ts_in'])
    lrec = punch_data[-1]
    lrec['ts_out'] = json_dt
    write_punches(badge, punch_data)
    badges = get_badges()
    badges[badge]['status'] = 'out'
    store_badges(badges)
    return badges


def create_user(badge_num: str, display_name: str, photo_url: str):
    # TODO: Make entry in queue
    badges = get_badges()
    badges[badge_num] = {
        'display_name': display_name,
        'photo_url': photo_url,
        'status': 'out'
    }
    store_badges(badges)


def tabulate_badge(badge: str):
    punch_data = read_punches(badge)
    # Sort punch_data by ts_in
    punch_data = sorted(punch_data, key=lambda x: x['ts_in'])
    for pd in punch_data:
        if 'ts_out' not in pd:
            tdiff = None
        else:
            tdiff = (
                datetime.strptime(pd['ts_out'], json_dt_fmt)
                -
                datetime.strptime(pd['ts_in'], json_dt_fmt)
            ).total_seconds()
        pd['duration'] = tdiff
    write_punches(badge, punch_data)


def get_cosmos_client():
    endpoint = os.environ['TRITIME_ENDPOINT']
    key = os.environ['TRITIME_KEY']
    print(f'endpoint: {endpoint}')
    print(f'key: {key}')
    client = CosmosClient(endpoint, key)
    return client


def get_db(client, dbname=None):
    if dbname is None:
        dbname = os.environ.get('TRITIME_DATABASE')
    try:
        db = client.create_database_if_not_exists(id=dbname)
    except AzureError as e:
        print(f'Error creating database: {e}')
        db = client.get_database_client(dbname)
    return db


def _get_container(db, container_name, partition_key='id'):
    try:
        container = db.create_container_if_not_exists(
            id=container_name,
            partition_key=PartitionKey(path=partition_key)
        )
    except AzureError as e:
        print(f'Error creating container: {e}')
        container = db.get_container_client(container_name)
    return container


def get_badge_container(db=None):
    if db is None:
        db = get_db(get_cosmos_client())
    return _get_container(db, 'badges', 'badge_num')


def get_punch_contaier(db=None):
    if db is None:
        db = get_db(get_cosmos_client())
    return _get_container(db, 'punch_data', 'badge_num')


def badges_to_cosmos(bcont):
    badges = _get_badges_local()
    for badge_num, badge_data in badges.items():
        badge_data['id'] = badge_num
        badge_data['badge_num'] = badge_num
        print(f'badge_data: {badge_data}')
        bcont.upsert_item(badge_data)
    pass


def punches_to_cosmos(pcont):
    badges = _get_badges_local()
    for badge_num in badges:
        punch_data = read_punches(badge_num)
        newdoc = {}
        newdoc['badge_num'] = badge_num
        newdoc['id'] = badge_num
        newdoc['punch_data'] = punch_data
        # print(newdoc)
        pcont.upsert_item(newdoc)
    pass


# This will NOT run when imported!
# If you run this from the command line (python lib/tritime.py), it will run
# the following code
if __name__ == "__main__":
    print('testing cli')
    cosmos = get_cosmos_client()
    db = get_db(cosmos)
    badge_container = get_badge_container(db)
    punch_container = get_punch_contaier(db)
    badges_to_cosmos(badge_container)
    punches_to_cosmos(punch_container)
