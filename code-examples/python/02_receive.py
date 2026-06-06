"""Consume messages and acknowledge them after successful processing."""

import pika

from common import connect


def handle_message(channel, method, properties, body):
    del properties
    message = body.decode("utf-8")
    print(f"Received: {message}")

    # Real business work belongs here. Ack only after it succeeds.
    channel.basic_ack(delivery_tag=method.delivery_tag)


connection = connect()
channel = connection.channel()
channel.queue_declare(queue="hello", durable=True)
channel.basic_qos(prefetch_count=1)
channel.basic_consume(
    queue="hello",
    on_message_callback=handle_message,
    auto_ack=False,
)

print("Waiting for messages. Press Ctrl+C to stop.")
try:
    channel.start_consuming()
except KeyboardInterrupt:
    channel.stop_consuming()
finally:
    connection.close()

