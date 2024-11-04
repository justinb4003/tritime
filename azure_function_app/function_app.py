import os
import azure.functions as func
import datetime
import json
import logging

import modules.trisync as libts
import hashlib

from azure.servicebus import ServiceBusClient, ServiceBusMessage
from azure.cosmos import CosmosClient, PartitionKey
from azure.core.exceptions import AzureError, ResourceNotFoundError

app = func.FunctionApp()

logging.getLogger('azure').setLevel(logging.WARNING)


def publish_checksum(sys_id, machine_id, badge_num, punch_data):
    js = json.dumps(punch_data)
    checksum = hashlib.sha256(js.encode('utf-8')).hexdigest()
    logging.info(f'punch data checksum {checksum}')
    conn_str = os.environ.get('ServiceBusConnectionString', '')
    servicebus_client = ServiceBusClient.from_connection_string(conn_str)
    sender = servicebus_client.get_topic_sender(sys_id)
    body_text = f'Publishing checksum for badge {badge_num}'
    message = ServiceBusMessage(
        body=body_text,
        content_type="text/plain",
        subject="Event",
        application_properties={
            "sys_id": sys_id,
            "machine_id": machine_id,
            "event_type": 'checksum_publish',
            "badge": badge_num,
            "checksum": checksum,
        }
    )
    sender.send_messages(message)


def request_backfill(sys_id: str, machine_id: str, badge_num: str):
    conn_str = os.environ.get('ServiceBusConnectionString', '')
    servicebus_client = ServiceBusClient.from_connection_string(conn_str)
    sender = servicebus_client.get_topic_sender(sys_id)
    body_text = f'Requesting backfill for badge {badge_num}'
    message = ServiceBusMessage(
        body=body_text,
        content_type="text/plain",
        subject="Event",
        application_properties={
            "sys_id": sys_id,
            "machine_id": machine_id,
            "event_type": 'backfill_request',
            "badge": badge_num,
        }
    )
    sender.send_messages(message)


# ServiceBusTopicTrigger Decorator
@app.function_name(name="ServiceBusClockEvent")
@app.service_bus_topic_trigger(
    connection="ServiceBusConnectionString",
    topic_name="TriSonics4003",
    subscription_name="TriSonics4003.All",
    arg_name="msg"
)
def TriSonics4003_event(msg: func.ServiceBusMessage):
    bus_clock_event(msg)


def bus_clock_event(msg: func.ServiceBusMessage):
    # Extract the message body
    message_body = msg.get_body().decode('utf-8')
    # Log the message
    logging.info(f"Received message: {message_body}")
    props = msg.application_properties
    if props:
        for key, value in props.items():
            logging.info(f"Custom Property - Key: {key}, Value: {value}")
        badge_num = props['badge']
        event_type = props['event_type']
        if event_type == 'backfill_request':
            return  # We don't process that event in this section
        sys_id = props['sys_id']
        machine_id = props['machine_id']
        logging.info(f'Badge number: {badge_num}')
        # Now get all punch data for this badge number
        punch_data = libts.read_punches(badge_num)
        if len(punch_data) == 0:
            logging.error('No punches found for badge number')
            # if we have none we have to do something to get the timeclock to send
            # us the data like, all of it, to backfill what the local system
            # already has.
            # And I cannot think of a better way to do it than to make a topic
            # for each machine and have the clock check that queue for
            # instructions on syncing data.
            request_backfill(sys_id, machine_id, badge_num)
            # Mark msg as completed
        else:
            for punch in punch_data:
                logging.info(f'Punch: {punch}')

        # That would also be a good time to scan the dead-letter queue for
        # punch data that failed to process. We can then reprocess it while
        # rejecting duplicates of what we already have.

    # Process the message (your business logic here)


@app.route(route="backfill",
           auth_level=func.AuthLevel.ANONYMOUS)
def receive_backfill(req: func.HttpRequest) -> func.HttpResponse:
    # TODO: Use these to control which container/database to use
    sys_id = req.params.get('sys_id')
    machine_id = req.params.get('machine_id')
    badge = req.params.get('badge')
    # Read body of request as json
    req_body = req.get_json()
    logging.info(f'Request body: {req_body}')
    pc = libts.get_punch_container()
    newdoc = {
        'badge_num': badge,
        'id': badge,
        'punch_data': req_body
    }
    pc.upsert_item(newdoc)
    publish_checksum(sys_id, machine_id, badge, req_body)

    return func.HttpResponse(
            "OK",
            status_code=200
    )


@app.route(route="sendbackfill",
           auth_level=func.AuthLevel.ANONYMOUS)
def send_backfill(req: func.HttpRequest) -> func.HttpResponse:
    # TODO: Use these to control which container/database to use
    sys_id = req.params.get('sys_id')
    badge = req.params.get('badge')
    pd_json = json.dumps(libts.read_punches(badge))
    return func.HttpResponse(
            pd_json,
            status_code=200
    )


@app.route(route="sendchecksums",
           auth_level=func.AuthLevel.ANONYMOUS)
def send_checksums(req: func.HttpRequest) -> func.HttpResponse:
    # TODO: Use these to control which container/database to use
    sys_id = req.params.get('sys_id')
    pc = libts.get_punch_container()
    items = pc.query_items(
        query="SELECT * FROM c",
        enable_cross_partition_query=True
    )
    checksum_list = []
    for i in items:
        entry = {
            'badge_num': i['badge_num'],
            'checksum': hashlib.sha256(json.dumps(i['punch_data']).encode('utf-8')).hexdigest()
        }
        checksum_list.append(entry)
    checksum_json = json.dumps(checksum_list)
    return func.HttpResponse(
            checksum_json,
            status_code=200
    )



@app.route(route="punch",
           auth_level=func.AuthLevel.ANONYMOUS)
def punch_trigger(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Punch it')
    badge = req.params.get('badge')
    action = req.params.get('action')
    logging.info(f'badge = {badge}')
    logging.info(f'action = {action}')
    # TODO: Alter the record in Cosmos
    punch_data = libts.read_punches(badge)
    publish_checksum('TriSonics4003', 'testbed', badge, punch_data)
    return func.HttpResponse(
            "OK",
            status_code=200
    )