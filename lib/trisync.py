import os
import json
import time
import azure
import hashlib
from queue import Queue
from threading import Thread
from datetime import datetime

from azure.servicebus import ServiceBusClient, ServiceBusMessage

json_dt_fmt = '%Y-%m-%d %H:%M:%S'
event_queue: Queue = Queue(maxsize=2048)


def extract_entity_path(connection_string):
    # Split the connection string into its individual components
    parts = connection_string.split(';')

    # Parse each part as a key-value pair
    components = {k: v for k, v in (part.split('=', 1) for part in parts if '=' in part)}

    # Extract the EntityPath if it exists
    entity_path = components.get("EntityPath")

    return entity_path


def send_queue():
    global event_queue
    conn_str = os.environ.get('TRITIME_MSG_CONN_STR')
    sysid = os.environ.get('TRITIME_SYSID')
    topic_name = extract_entity_path(conn_str)
    servicebus_client = ServiceBusClient.from_connection_string(conn_str)
    sender = servicebus_client.get_topic_sender(topic_name)
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
                    "sysid": sysid,
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
        time.sleep(1)


def start_queue_loop():
    global queue_thread, queue_thread_run
    queue_thread_run = True
    queue_thread = Thread(target=send_queue)
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