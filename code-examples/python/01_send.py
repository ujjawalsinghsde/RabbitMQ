"""Publish one persistent message to the hello queue."""

import sys

import pika

from common import connect


message = " ".join(sys.argv[1:]) or "Hello RabbitMQ"
connection = connect()

try:
    channel = connection.channel()
    channel.queue_declare(queue="hello", durable=True)
    channel.basic_publish(
        exchange="",
        routing_key="hello",
        body=message.encode("utf-8"),
        properties=pika.BasicProperties(
            content_type="text/plain",
            delivery_mode=pika.DeliveryMode.Persistent,
        ),
    )
    print(f"Sent: {message}")
finally:
    connection.close()

