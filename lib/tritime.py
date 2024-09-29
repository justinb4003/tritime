import os
import json
import time
from queue import Queue
from threading import Thread
from datetime import datetime

from azure.servicebus import ServiceBusClient, ServiceBusMessage

json_dt_fmt = '%Y-%m-%d %H:%M:%S'
TOPIC_NAME = 'trisonics4003'

event_queue: Queue = Queue(maxsize=2048)


def send_queue():
    global event_queue
    conn_str = os.environ.get('TRITIME_MSG_CONN_STR')
    servicebus_client = ServiceBusClient.from_connection_string(conn_str)
    sender = servicebus_client.get_topic_sender(TOPIC_NAME)
    while queue_thread_run:
        # Iterate through event_queue
        failed_events = []
        while not event_queue.empty():
            event = event_queue.get()
            print(f'event: {event}')
            # Send event to server
            print('sending')
            message = ServiceBusMessage(
                body="This is the message body",
                content_type="application/json",
                subject="Event",
                application_properties={
                    "event_type": event['event'],
                    "ts": event['dt'],
                    "badge": event['badge']
                }
            )
            try:
                sender.send_messages(message)
            except azure.servicebus.exceptions.ServiceBusError as e:

            failed_events.append(event)
        for fe in failed_events:
            event_queue.put(fe)
        time.sleep(1)


def start_queue_loop():
    global queue_thread, queue_thread_run
    queue_thread_run = True
    queue_thread = Thread(target=send_queue)
    queue_thread.start()


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
    global event_queue
    # TODO: Make entry in queue
    print(f'punch_in: {badge} at {dt}')
    json_dt = datetime.now().strftime(json_dt_fmt)

    queue_entry = {
        'badge': badge,
        'dt': json_dt,
        'event': 'punch_in'
    }
    event_queue.put(queue_entry)

    punch_data = read_punches(badge)
    punch_data.append({'ts_in': json_dt})
    write_punches(badge, punch_data)

    # Change status
    badges = get_badges()
    badges[badge]['status'] = 'in'
    store_badges(badges)
    return badges


def punch_out(badge: str, dt: datetime):
    # TODO: Make entry in queue
    punch_data = read_punches(badge)
    punch_data = sorted(punch_data, key=lambda x: x['ts_in'])
    lrec = punch_data[-1]
    lrec['ts_out'] = datetime.now().strftime(json_dt_fmt)
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
