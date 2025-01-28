import os
import json
import logging
import threading

from . import tritime

from datetime import datetime
from azure.servicebus import ServiceBusClient, ServiceBusMessage
from typing import Callable, Any, Optional, Dict
from dataclasses import dataclass, field, asdict
from queue import Queue


from typing import Dict

@dataclass
class TriTimeEvent:
   system_id: str
   badge_num: str
   event_type: str
   ts: datetime
   details: Any

   def to_json(self):
       return json.dumps({
           'system_id': self.system_id,
           'badge_num': self.badge_num,
           'event_type': self.event_type,
           'ts': self.ts.isoformat(),
           'details': self.details
       })

   @classmethod
   def json_serializer(clazz, obj):
       if isinstance(obj, datetime):
           return obj.isoformat()
       if isinstance(obj, TriTimeEvent):
           return asdict(obj)
       raise TypeError("Type not serializable")

   @classmethod
   def from_json(clazz, json_str):
       data = json.loads(json_str)
       obj = TriTimeEvent(
              system_id=data['system_id'],
              badge_num=data['badge_num'],
              event_type=data['event_type'],
              ts=datetime.fromisoformat(data['ts']),
              details=data['details']
       )
       return obj

   @classmethod
   def from_dict(clazz, data):
       obj = TriTimeEvent(
           system_id=data['system_id'],
           badge_num=data['badge_num'],
           event_type=data['event_type'],
           ts=datetime.fromisoformat(data['ts']),
           details=data['details']
       )
       return obj

class TriTimeEventEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, TriTimeEvent):
            return asdict(obj)
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

# Module level variables
message_queue = Queue()
should_run = threading.Event()
receiver_thread = None
sender_thread = None
logger = logging.getLogger(__name__)


def system_id() -> str:
    return os.environ.get('SYSTEM_ID')

def get_config() -> dict:
    """Get configuration from environment variables."""
    v = {
        'connection_string': os.environ['AZURE_SERVICE_BUS_CONNECTION_STRING'],
        'topic_name': os.environ.get('AZURE_SERVICE_BUS_TOPIC_NAME'),
        'subscription_name': os.environ.get('SYSTEM_ID')
    }
    return v

def _get_sb_client() -> ServiceBusClient:
    config = get_config()
    client = ServiceBusClient.from_connection_string(config['connection_string'])
    return client

def receive_subscription_messages(handler: Callable) -> None:
    """Process messages from a Service Bus topic subscription."""
    config = get_config()
    with _get_sb_client() as client:
        with client.get_subscription_receiver(
            topic_name=config['topic_name'],
            subscription_name=config['subscription_name']
        ) as receiver:
            while should_run.is_set():
                try:
                    messages = receiver.receive_messages(max_message_count=10, max_wait_time=5)
                    for msg in messages:
                        print('msg received from queue')
                        # json_str = msg.body.decode('utf-8')
                        json_str = b''.join(msg.body).decode('utf-8')
                        print(f"received json_str: {json_str}")
                        obj: TriTimeEvent = TriTimeEvent.from_json(json_str)
                        # Skip processing our own messages
                        # And while this can be configured in Azure, it's a
                        # good idea to have a backup check
                        if obj.system_id != system_id():
                            print('processing the message')
                            handler(obj)
                        print('marking message completed in queu')
                        receiver.complete_message(msg)
                except Exception as e:
                    logger.error(f"Error receiving messages: {e}")
                    raise e

def publish_outgoing_messages() -> None:
    config = get_config()
    """Send messages from the outgoing queue to Service Bus topic."""
    with _get_sb_client() as client:
        with client.get_topic_sender(topic_name=config['topic_name']) as sender:
            while should_run.is_set():
                try:
                    if message_queue.empty():
                        from time import sleep
                        sleep(0.1)
                        continue
                    message: TriTimeEvent = message_queue.get(timeout=1)
                    print(f"jsonning message: {message}")
                    json_str = json.dumps(message, default=TriTimeEvent.json_serializer)
                    print(f"sending json_str: {json_str}")
                    msg = ServiceBusMessage(json_str)
                    sender.send_messages(msg)
                except Exception as e:
                    if not isinstance(e, threading.ThreadError):
                        logger.error(f"Error sending message: {e}")
                        raise e

def start(azure_message_handler) -> None:
    """Start the service bus listener and sender threads."""
    global receiver_thread, sender_thread

    should_run.set()

    receiver_thread = threading.Thread(
        target=receive_subscription_messages,
        args=(azure_message_handler,)
    )

    sender_thread = threading.Thread(
        target=publish_outgoing_messages,
        args=()
    )

    receiver_thread.start()
    sender_thread.start()

# This is not a fast shutdown; not sure what to do about that yet.
def stop() -> None:
    """Stop all running threads."""
    should_run.clear()
    if receiver_thread:
        receiver_thread.join()
    if sender_thread:
        sender_thread.join()

def publish_data() -> None:
    """This system will publish its stored data to the service bus
       so other systems can sync up to it."""
    badges = tritime.get_badges()
    message = TriTimeEvent(
        system_id=system_id(),
        badge_num=None,
        event_type='badges_sync',
        ts=datetime.now(),
        details=badges,
    )
    queue_message(message)
    for num in badges.keys():
        pd = tritime.read_punches(num)
        message = TriTimeEvent(
            system_id=system_id(),
            badge_num=num,
            event_type='punch_data_sync',
            ts=datetime.now(),
            details=pd,
        )
        queue_message(message)


def queue_message(message: TriTimeEvent) -> None:
    """Add message to the outgoing queue."""
    message_queue.put(message)
