"""Publish an order command with confirms and unroutable-message detection."""

import json
import sys
import uuid

import pika

from common import connect, declare_reliable_order_topology


order_id = sys.argv[1] if len(sys.argv) > 1 else "ORD-101"
message_id = str(uuid.uuid4())
command = {
    "message_id": message_id,
    "command": "process_order",
    "order_id": order_id,
}

connection = connect()
try:
    channel = connection.channel()
    declare_reliable_order_topology(channel)
    channel.confirm_delivery()

    try:
        channel.basic_publish(
            exchange="orders.commands",
            routing_key="orders.process",
            body=json.dumps(command).encode(),
            mandatory=True,
            properties=pika.BasicProperties(
                content_type="application/json",
                message_id=message_id,
                correlation_id=message_id,
                delivery_mode=pika.DeliveryMode.Persistent,
            ),
        )
    except (pika.exceptions.UnroutableError, pika.exceptions.NackError) as error:
        print(f"Publish was not accepted: {error}", file=sys.stderr)
        raise SystemExit(1) from error

    print(f"Confirmed order command {message_id} for {order_id}")
finally:
    connection.close()

