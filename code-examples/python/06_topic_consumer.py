"""Bind a private queue to one or more topic patterns."""

import argparse
import json

from common import connect


parser = argparse.ArgumentParser()
parser.add_argument(
    "patterns",
    nargs="*",
    default=["order.#"],
    help='Examples: "order.#" "*.failed"',
)
args = parser.parse_args()

connection = connect()
channel = connection.channel()
channel.exchange_declare(
    exchange="domain.events",
    exchange_type="topic",
    durable=True,
)

# An exclusive generated queue is suitable for this temporary demonstration.
result = channel.queue_declare(queue="", exclusive=True)
queue_name = result.method.queue
for pattern in args.patterns:
    channel.queue_bind(
        exchange="domain.events",
        queue=queue_name,
        routing_key=pattern,
    )


def show_event(channel, method, properties, body):
    del properties
    event = json.loads(body)
    print(f"{method.routing_key}: {event}")
    channel.basic_ack(delivery_tag=method.delivery_tag)


channel.basic_consume(queue_name, show_event, auto_ack=False)
print(f"Listening for: {', '.join(args.patterns)}")
try:
    channel.start_consuming()
except KeyboardInterrupt:
    channel.stop_consuming()
finally:
    connection.close()

