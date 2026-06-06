"""Publish a domain event using a topic routing key."""

import argparse
import json
import uuid
from datetime import datetime, timezone

import pika

from common import connect


parser = argparse.ArgumentParser()
parser.add_argument("routing_key", nargs="?", default="order.created")
parser.add_argument("text", nargs="?", default="Example event")
args = parser.parse_args()

event = {
    "message_id": str(uuid.uuid4()),
    "event_type": args.routing_key,
    "occurred_at": datetime.now(timezone.utc).isoformat(),
    "data": {"text": args.text},
}

connection = connect()
try:
    channel = connection.channel()
    channel.exchange_declare(
        exchange="domain.events",
        exchange_type="topic",
        durable=True,
    )
    channel.basic_publish(
        exchange="domain.events",
        routing_key=args.routing_key,
        body=json.dumps(event).encode(),
        properties=pika.BasicProperties(
            content_type="application/json",
            message_id=event["message_id"],
            type=event["event_type"],
            delivery_mode=pika.DeliveryMode.Persistent,
        ),
    )
    print(f"Published {args.routing_key}: {event['message_id']}")
finally:
    connection.close()

