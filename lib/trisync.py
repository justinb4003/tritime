import os
import json
import queue
import time
import azure
import requests
from queue import Queue
from threading import Thread
from datetime import datetime
from azure.servicebus import ServiceBusClient, ServiceBusMessage
from azure.cosmos import CosmosClient, PartitionKey
from azure.core.exceptions import AzureError, ResourceNotFoundError

json_dt_fmt = '%Y-%m-%d %H:%M:%S'
event_queue: Queue = Queue(maxsize=2048)
queue_thread: Thread = None


def read_local_punches(badge: str):
    with open(f'punch_data_{badge}.json', 'r') as f:
        punch_data = json.load(f)
    return punch_data


def extract_entity_path(connection_string):
    # Split the connection string into its individual components
    parts = connection_string.split(';')
    # Parse each part as a key-value pair
    components = {k: v for k, v in (part.split('=', 1) for part in parts if '=' in part)}
    # Extract the EntityPath if it exists
    entity_path = components.get("EntityPath")
    return entity_path


def decode_bytes_dict(byte_dict):
    return {key.decode('utf-8'): value.decode('utf-8') if isinstance(value, bytes) else value for key, value in byte_dict.items()}



def process_queue():
    global event_queue
    conn_str = os.environ.get('TRITIME_TOPIC_CONN_STR')
    sys_id = os.environ.get('TRITIME_SYS_ID')
    machine_id = os.environ.get('TRITIME_MACHINE_ID')
    servicebus_client = ServiceBusClient.from_connection_string(conn_str)
    sender = servicebus_client.get_topic_sender('trisonics4003')
    recv = servicebus_client.get_subscription_receiver(
        sys_id, f'{sys_id}.testbed'
    )
    while queue_thread_run:
        # Iterate through event_queue
        failed_events = []
        while not event_queue.empty():
            event = event_queue.get()
            print(f'event: {event}')
            # Send event to server
            print('sending')
            body_text = f'{event["badge"]} {event["event"]} at {event["dt"]}'
            message = ServiceBusMessage(
                body=body_text,
                content_type="text/plain",
                subject="Event",
                application_properties={
                    "sys_id": sys_id,
                    "machine_id": machine_id,
                    "event_type": event['event'],
                    "ts": event['dt'],
                    "badge": event['badge']
                }
            )
            try:
                sender.send_messages(message)
            except azure.servicebus.exceptions.ServiceBusError:  # noqa
                failed_events.append(event)
        for fe in failed_events:
            event_queue.put(fe)
        save_queue()


        messages = recv.receive_messages(max_message_count=10, max_wait_time=5)
        for msg in messages:
            # Do stuff with it
            props = msg.application_properties
            if props:
                props = decode_bytes_dict(props)
                print(props.keys())
                msg_machine_id = props['machine_id']
                msg_event_type = props['event_type']
                badge = props['badge']
                print(f'event_type: {msg_event_type}')
                if msg_machine_id == machine_id:
                    print('machine id matches self')
                    if msg_event_type == 'punch_in':
                        print('clearing punch_in message')
                        recv.complete_message(msg)
                        pass
                    elif msg_event_type == 'punch_out':
                        print('clearing punch_out message')
                        recv.complete_message(msg)
                        pass
                    elif msg_event_type == 'backfill_request':
                        print(f'Sending backfill data for {badge}')
                        bf = read_local_punches(badge)
                        bfjson = json.dumps(bf, indent=4, sort_keys=True)
                        url = f'http://localhost:7071/api/backfill?badge={badge}&sys_id={sys_id}&machine_id={machine_id}'
                        requests.post(url, data=bfjson)
                        recv.complete_message(msg)
                        pass
                else:
                    print('machine id DOES NOT match self')
        time.sleep(10)

def start_queue_loop():
    global queue_thread, queue_thread_run
    queue_thread_run = True
    queue_thread = Thread(target=process_queue)
    queue_thread.start()


def stop_queue_loop():
    global queue_thread, queue_thread_run
    queue_thread_run = False
    queue_thread.join()


def load_queue():
    global event_queue
    if os.path.exists('event_queue.json'):
        with open('event_queue.json', 'r') as f:
            queue_json = f.read()
        event_queue = Queue(maxsize=2048)
        for entry in json.loads(queue_json):
            event_queue.put(entry)


def save_queue():
    queue_json = json.dumps(list(event_queue.queue))
    with open('event_queue.json', 'w') as f:
        f.write(queue_json)
    pass


def add_queue_entry(badge: str, event: str, dt: datetime):
    global event_queue
    json_dt = dt.strftime(json_dt_fmt)
    queue_entry = {
        'badge': badge,
        'dt': json_dt,
        'event': event
    }
    event_queue.put(queue_entry)
    save_queue()


# Cosmos related stuff goes here
def get_cosmos_client():
    endpoint = os.environ['TRITIME_ENDPOINT']
    key = os.environ['TRITIME_KEY']
    print(f'endpoint: {endpoint}')
    print(f'key: {key}')
    client = CosmosClient(endpoint, key)
    return client


def _get_db(client, dbname=None):
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
        db = _get_db(get_cosmos_client())
    return _get_container(db, 'badges', 'badge_num')


def get_punch_container(db=None):
    if db is None:
        db = _get_db(get_cosmos_client())
    return _get_container(db, 'punch_data', 'badge_num')


# I probably shouldn't bother leaving this here but I'm going to until
# I get the functionality plugged in somewhere else
abandoned_code = """
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
"""


def get_badges():
    bcont = get_badge_container()
    bdata = bcont.read_all_items()
    badges = {}
    for bd in bdata:
        num = bd['badge_num']
        badges[num] = bd
    return badges


def store_badges(data: dict):
    bcont = get_badge_container()
    for badge_num, b in data.items():
        if 'id' not in b.keys():
            b['id'] = badge_num
        if 'badge_num' not in b.keys():
            b['badge_num'] = badge_num
        bcont.upsert_item(b)


def read_punches(badge: str):
    pcont = get_punch_container()
    try:
        punch_data = pcont.read_item(item=badge, partition_key=badge)
    except ResourceNotFoundError:
        return []
    return punch_data['punch_data']


if __name__ == "__main__":
    print('testing cli')
    cosmos = get_cosmos_client()
    db = _get_db(cosmos)
    badge_container = get_badge_container(db)
    punch_container = get_punch_container(db)
