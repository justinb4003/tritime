import os
import json
from datetime import datetime


json_dt_fmt = '%Y-%m-%d %H:%M:%S'
def get_badges():
    with open('badges.json', 'r') as f:
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
    print(f'punch_in: {badge} at {dt}')
    punch_data = read_punches(badge)
    punch_data.append({
        'ts_in': datetime.now().strftime(json_dt_fmt)
    })
    write_punches(badge, punch_data)


def punch_out(badge: str, dt: datetime):
    punch_data = read_punches(badge)
    punch_data = sorted(punch_data, key=lambda x: x['ts_in'])
    lrec = punch_data[-1]
    lrec['ts_out'] = datetime.now().strftime(json_dt_fmt)
    write_punches(badge, punch_data)


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