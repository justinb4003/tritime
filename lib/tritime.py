import os
import json
import time
import azure
import hashlib
from queue import Queue
from threading import Thread
from datetime import datetime

from azure.servicebus import ServiceBusClient, ServiceBusMessage
# Maybe make this conditional ?
from lib.trisync import add_queue_entry

json_dt_fmt = '%Y-%m-%d %H:%M:%S'


def hash_badge_data(badge: str):
    pd = read_punches(badge)
    data_str = json.dumps(pd)
    hashval = hashlib.sha256(data_str.encode()).hexdigest()
    return hashval


def get_badges():
    local_filename = 'badges.json'
    if not os.path.exists(local_filename):
        with open(local_filename, 'w') as f:
            f.write(json.dumps({}))
    with open(local_filename, 'r') as f:
        return json.loads(f.read())


def store_badges(data: dict):
    with open('badges.json', 'w') as f:
        f.write(json.dumps(data, indent=4, sort_keys=True))


def read_punches(badge: str):
    datafile = f'punch_data_{badge}.json'
    if os.path.exists(datafile):
        with open(datafile, 'r') as f:
            punch_data = json.loads(f.read())
    else:
        punch_data = []
    return punch_data


def write_punches(badge: str, punch_data: list):
    punch_data = sorted(punch_data, key=lambda x: x['ts_in'])
    datafile = f'punch_data_{badge}.json'
    with open(datafile, 'w') as f:
        f.write(json.dumps(punch_data, indent=4, sort_keys=True))


def punch_in(badge: str, dt: datetime):
    json_dt = dt.strftime(json_dt_fmt)
    add_queue_entry(badge, 'punch_in', dt)
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


if __name__ == "__main__":
    print('testing cli')
    punch_in('justin', datetime.now())
