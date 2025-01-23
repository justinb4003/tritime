
import os
from azure.servicebus import ServiceBusClient, ServiceBusMessage
from queue import Queue
import threading
import logging
from typing import Callable, Any, Optional

# Module level variables
message_queue = Queue()
should_run = threading.Event()
receiver_thread = None
sender_thread = None
logger = logging.getLogger(__name__)

def get_config() -> dict:
    """Get configuration from environment variables."""
    return {
        'connection_string': os.environ['AZURE_SERVICE_BUS_CONNECTION_STRING'],
        'queue_name': os.environ.get('AZURE_SERVICE_BUS_QUEUE_NAME', ''),
        'topic_name': os.environ.get('AZURE_SERVICE_BUS_TOPIC_NAME'),
        'subscription_name': os.environ.get('AZURE_SERVICE_BUS_SUBSCRIPTION_NAME')
    }

def _get_sb_client() -> ServiceBusClient:
    config = get_config()
    ServiceBusClient.from_connection_string(config['connection_string'])

def receive_queue_messages(handler: Callable[[Any], None]) -> None:
    config = get_config()
    """Process messages from a Service Bus queue."""
    with _get_sb_client() as client:
        with client.get_queue_receiver(queue_name=config['queue_name']) as receiver:
            while should_run.is_set():
                try:
                    messages = receiver.receive_messages(max_message_count=10, max_wait_time=5)
                    for msg in messages:
                        try:
                            handler(msg)
                            receiver.complete_message(msg)
                        except Exception as e:
                            logger.error(f"Error processing message: {e}")
                            receiver.abandon_message(msg)
                except Exception as e:
                    logger.error(f"Error receiving messages: {e}")

def receive_subscription_messages(config: dict, handler: Callable[[Any], None]) -> None:
    """Process messages from a Service Bus topic subscription."""
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
                            handler(msg)
                            receiver.complete_message(msg)
                        except Exception as e:
                            logger.error(f"Error processing message: {e}")
                            receiver.abandon_message(msg)
                except Exception as e:
                    logger.error(f"Error receiving messages: {e}")

def process_outgoing_messages(config: dict) -> None:
    config = get_config()
    """Send messages from the outgoing queue to Service Bus."""
    with _get_sb_client() as client:
        with client.get_queue_sender(queue_name=config['queue_name']) as sender:
            while should_run.is_set():
                try:
                    message = message_queue.get(timeout=1)
                    msg = ServiceBusMessage(str(message))
                    sender.send_messages(msg)
                except Exception as e:
                    if not isinstance(e, threading.ThreadError):
                        logger.error(f"Error sending message: {e}")

def start(message_handler: Callable[[Any], None]) -> None:
    """Start the service bus listener and sender threads."""
    global receiver_thread, sender_thread

    should_run.set()

    receiver_thread = threading.Thread(
        target=receive_queue_messages,
        args=(message_handler,)
    )

    sender_thread = threading.Thread(
        target=process_outgoing_messages,
        args=()
    )

    receiver_thread.start()
    sender_thread.start()

def stop() -> None:
    """Stop all running threads."""
    should_run.clear()
    if receiver_thread:
        receiver_thread.join()
    if sender_thread:
        sender_thread.join()

def send_message(message: Any) -> None:
    """Add message to the outgoing queue."""
    message_queue.put(message)

# Usage example:
"""
def message_handler(message):
    print(f"Received: {message}")

# Set environment variables
os.environ["AZURE_SERVICE_BUS_CONNECTION_STRING"] = "your_connection_string"
os.environ["AZURE_SERVICE_BUS_QUEUE_NAME"] = "your_queue_name"

# Start the service
start(message_handler)

# Send a message
send_message("Hello, Azure!")

# Stop the service
stop()
"""