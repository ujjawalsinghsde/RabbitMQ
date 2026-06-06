"""Process tasks. Run this script in several terminals to share the work."""

import json
import time

from common import connect


def process_task(channel, method, properties, body):
    del properties
    task = json.loads(body)
    print(f"Starting task {task['task_number']}")
    try:
        time.sleep(task["work_seconds"])
    except Exception:
        channel.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
        raise
    else:
        channel.basic_ack(delivery_tag=method.delivery_tag)
        print(f"Finished task {task['task_number']}")


connection = connect()
channel = connection.channel()
channel.queue_declare(queue="tasks", durable=True)
channel.basic_qos(prefetch_count=1)
channel.basic_consume("tasks", process_task, auto_ack=False)

print("Worker started. Press Ctrl+C to stop.")
try:
    channel.start_consuming()
except KeyboardInterrupt:
    channel.stop_consuming()
finally:
    connection.close()

