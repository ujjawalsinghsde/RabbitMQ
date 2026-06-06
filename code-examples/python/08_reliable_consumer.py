"""Reliable consumer with manual ack, delayed retry, and a final DLQ."""

import json
import os

import pika

from common import connect, declare_reliable_order_topology


MAX_RETRIES = 3


class PermanentError(Exception):
    """The message cannot succeed without changing its data or code."""


class TransientError(Exception):
    """A temporary dependency or infrastructure failure."""


def process_order(command):
    """Replace this demonstration logic with a transaction or idempotent API."""
    order_id = command.get("order_id")
    if not order_id:
        raise PermanentError("order_id is required")
    if os.getenv("SIMULATE_TRANSIENT_FAILURE") == "1":
        raise TransientError("simulated downstream timeout")
    print(f"Processed order {order_id}")


def retry_count(properties):
    headers = properties.headers or {}
    return int(headers.get("retry_count", 0))


def schedule_retry(channel, method, properties, body, error):
    """Publish a delayed retry, or dead-letter after the retry limit."""
    attempts = retry_count(properties)
    if attempts >= MAX_RETRIES:
        print(f"Retry limit reached: {error}; sending to DLQ")
        channel.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
        return

    headers = dict(properties.headers or {})
    headers["retry_count"] = attempts + 1
    print(f"Processing failed: {error}; delayed retry {attempts + 1}")

    try:
        channel.basic_publish(
            exchange="orders.retry",
            routing_key="orders.retry",
            body=body,
            mandatory=True,
            properties=pika.BasicProperties(
                content_type=properties.content_type,
                message_id=properties.message_id,
                correlation_id=properties.correlation_id,
                headers=headers,
                delivery_mode=pika.DeliveryMode.Persistent,
            ),
        )
    except (pika.exceptions.UnroutableError, pika.exceptions.NackError):
        # Keep the original delivery available if the retry publish failed.
        channel.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
        raise
    else:
        channel.basic_ack(delivery_tag=method.delivery_tag)


def consume(channel, method, properties, body):
    try:
        command = json.loads(body)
        process_order(command)
    except (json.JSONDecodeError, PermanentError) as error:
        print(f"Permanent failure: {error}; sending to DLQ")
        channel.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
    except Exception as error:
        # Unexpected errors are bounded too, preventing an infinite hot loop.
        schedule_retry(channel, method, properties, body, error)
    else:
        channel.basic_ack(delivery_tag=method.delivery_tag)


connection = connect()
channel = connection.channel()
declare_reliable_order_topology(channel)
channel.confirm_delivery()
channel.basic_qos(prefetch_count=10)
channel.basic_consume("orders.process", consume, auto_ack=False)

print("Reliable order consumer started. Press Ctrl+C to stop.")
try:
    channel.start_consuming()
except KeyboardInterrupt:
    channel.stop_consuming()
finally:
    connection.close()
