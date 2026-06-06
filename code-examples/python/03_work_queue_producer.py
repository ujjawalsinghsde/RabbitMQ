"""Create numbered tasks for multiple competing workers."""

import argparse
import json
import uuid

import pika

from common import connect


parser = argparse.ArgumentParser()
parser.add_argument("--count", type=int, default=10)
args = parser.parse_args()

connection = connect()
try:
    channel = connection.channel()
    channel.queue_declare(queue="tasks", durable=True)

    for number in range(1, args.count + 1):
        task = {
            "message_id": str(uuid.uuid4()),
            "task_number": number,
            "work_seconds": (number % 3) + 1,
        }
        channel.basic_publish(
            exchange="",
            routing_key="tasks",
            body=json.dumps(task).encode(),
            properties=pika.BasicProperties(
                content_type="application/json",
                message_id=task["message_id"],
                delivery_mode=pika.DeliveryMode.Persistent,
            ),
        )
        print(f"Sent task {number}")
finally:
    connection.close()

