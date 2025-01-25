import os
import json
import hashlib
from datetime import datetime

json_dt_fmt = '%Y-%m-%d %H:%M:%S'

__data_dir = 'data'

def hash_badge_data(punches: list):
    data_str = json.dumps(punches)
    hashval = hashlib.sha256(data_str.encode()).hexdigest()
    return hashval


def get_badges():
    local_filename = f'{__data_dir}/badges.json'
    if not os.path.exists(local_filename):
        with open(local_filename, 'w') as f:
            f.write(json.dumps({}))
    with open(local_filename, 'r') as f:
        return json.loads(f.read())


def store_badges(data: dict):
    with open(f'{__data_dir}/badges.json', 'w') as f:
        f.write(json.dumps(data, indent=4, sort_keys=True))


def read_punches(badge: str):
    datafile = f'{__data_dir}/punch_data_{badge}.json'
    if os.path.exists(datafile):
        with open(datafile, 'r') as f:
            punch_data = json.loads(f.read())
    else:
        punch_data = []
    # Sort by the ts_in property
    punch_data = sorted(punch_data, key=lambda x: x['ts_in'])
    return punch_data


def write_punches(badge: str, punch_data: list):
    punch_data = sorted(punch_data, key=lambda x: x['ts_in'])
    datafile = f'{__data_dir}/punch_data_{badge}.json'
    with open(datafile, 'w') as f:
        f.write(json.dumps(punch_data, indent=4, sort_keys=True))

def fix_badges():
    badges = get_badges()
    for badge in badges.keys():
        punch_data = read_punches(badge)
        badges = update_badge_status(badge, badges, punch_data)
    store_badges(badges)

def update_badge_status(badge: str, badges: list, punch_data: list, save_data=True):
    status = 'out'
    # If the last punch doesn't have a ts_out, then the badge is in
    if len(punch_data) > 0 and 'ts_out' not in punch_data[-1]:
        status = 'in'
    badges[badge]['status'] = status
    if save_data is True:
        store_badges(badges)
    return badges

def punch_in(badge: str, dt: datetime):
    json_dt = dt.strftime(json_dt_fmt)
    punch_data = read_punches(badge)
    punch_data.append({'ts_in': json_dt})
    write_punches(badge, punch_data)
    # Change status
    badges = get_badges()
    badges = update_badge_status(badge, badges, punch_data)
    return badges


def punch_out(badge: str, dt: datetime):
    json_dt = dt.strftime(json_dt_fmt)
    punch_data = read_punches(badge)
    punch_data = sorted(punch_data, key=lambda x: x['ts_in'])
    lrec = punch_data[-1]
    lrec['ts_out'] = json_dt
    write_punches(badge, punch_data)
    badges = get_badges()
    badges = update_badge_status(badge, badges, punch_data)
    print(f'punch out modify status {badge}')
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


# This will NOT run when imported!
# If you run this from the command line (python lib/tritime.py), it will run
# the following code
if __name__ == "__main__":
    print('testing cli')
