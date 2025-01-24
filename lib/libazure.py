import os
import json
import logging
import threading

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
   # Copilot, how do I specify a datetime type?
   ts: datetime = field(
        metadata={"encoder": lambda x: x.isoformat()}
    )
   details: Dict

   def to_json(self):
       data = asdict(self)
       data['ts'] = self.ts.isoformat()
       return json.dumps(data)

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
                        try:
                            # json_str = msg.body.decode('utf-8')
                            json_str = b''.join(msg.body).decode('utf-8')
                            obj: TriTimeEvent = TriTimeEvent.from_json(json_str)
                            # Skip processing our own messages
                            # And while this can be configured in Azure, it's a
                            # good idea to have a backup check
                            if obj.system_id != system_id():
                                handler(obj)
                            receiver.complete_message(msg)
                        except Exception as e:
                            logger.error(f"Error processing message: {e}")
                            receiver.abandon_message(msg)
                            raise e
                except Exception as e:
                    logger.error(f"Error receiving messages: {e}")

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
                    json_str = message.to_json()
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

def send_message(message: TriTimeEvent) -> None:
    """Add message to the outgoing queue."""
    payload = json.dumps(message, sort_keys=True, indent=4)
    message_queue.put(payload)
