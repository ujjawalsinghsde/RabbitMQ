# Python Examples

These examples use Pika's blocking adapter because it is easy to study. In a high-concurrency application, select a client/concurrency model that matches the framework and do not block its I/O loop with business work.

## Setup

Run commands from the repository root after completing [Quick Start](../../QUICKSTART.md).

## Lessons

### 1. First Message

Terminal 1:

```bash
python code-examples/python/02_receive.py
```

Terminal 2:

```bash
python code-examples/python/01_send.py "hello"
```

### 2. Competing Workers

Start `04_work_queue_consumer.py` in two or three terminals, then run:

```bash
python code-examples/python/03_work_queue_producer.py --count 10
```

Observe that each task goes to one worker.

### 3. Topic Routing

Terminal 1:

```bash
python code-examples/python/06_topic_consumer.py "order.#"
```

Terminal 2:

```bash
python code-examples/python/06_topic_consumer.py "*.failed"
```

Publish:

```bash
python code-examples/python/05_topic_producer.py order.created "Order 101"
python code-examples/python/05_topic_producer.py payment.failed "Card declined"
```

### 4. Reliable Processing

Start the consumer:

```bash
python code-examples/python/08_reliable_consumer.py
```

Publish:

```bash
python code-examples/python/07_reliable_producer.py ORD-101
```

Test delayed retry in PowerShell:

```powershell
$env:SIMULATE_TRANSIENT_FAILURE="1"
python code-examples/python/08_reliable_consumer.py
```

After testing, clear the variable:

```powershell
Remove-Item Env:SIMULATE_TRANSIENT_FAILURE
```

The reliable example demonstrates:

- quorum queues
- persistent messages
- publisher confirms
- mandatory routing
- manual acknowledgements
- prefetch
- delayed retry queue
- retry limit
- dead-letter queue

## Environment Variable

Override the connection URL when required:

```powershell
$env:RABBITMQ_URL="amqps://user:password@host:5671/vhost"
```

## Deliberate Simplifications

The sample consumer keeps retry count in a header. A production implementation should also persist idempotency state, classify all exception paths, emit metrics, propagate trace context, validate schemas, and use TLS/managed secrets. Operational queue settings are often better applied with RabbitMQ policies than hardcoded queue arguments.

