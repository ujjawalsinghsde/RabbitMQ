# RabbitMQ: Beginner to Advanced

> Current baseline: RabbitMQ 4.x and AMQP 0-9-1. Examples use Python and Pika.

## Complete Index

### Theory

| Level | Topic | What you will learn |
|---|---|---|
| Beginner | [01 - Introduction](./learning/01-introduction.md) | What RabbitMQ is, why it exists, and when to use it |
| Beginner | [02 - Core Concepts](./learning/02-core-concepts.md) | Producer, exchange, binding, queue, consumer, connection, channel |
| Beginner | [03 - Exchanges and Routing](./learning/03-exchanges-and-routing.md) | Direct, fanout, topic, headers, and default exchanges |
| Intermediate | [04 - Message Lifecycle](./learning/04-message-lifecycle.md) | Publishing, routing, consuming, acknowledgements, and ordering |
| Intermediate | [05 - Reliability and Retries](./learning/05-reliability-and-retries.md) | Confirms, durable data, DLQ, retry, duplicates, idempotency |
| Intermediate | [06 - Scaling and Performance](./learning/06-scaling-and-performance.md) | Competing consumers, prefetch, back pressure, queue choices |
| Advanced | [07 - Production Operations](./learning/07-production-operations.md) | Security, monitoring, clustering, recovery, and deployment |
| Advanced | [08 - Advanced Patterns](./learning/08-advanced-patterns.md) | RPC, priority, delayed work, outbox, saga, streams |

### Architecture

- [Architecture Guide](./architecture/README.md)
- [E-commerce Order Processing](./architecture/01-ecommerce-orders.md)
- [Notification Platform](./architecture/02-notification-system.md)
- [Media Processing Pipeline](./architecture/03-media-processing.md)
- [Microservice Events and Workflows](./architecture/04-microservices-events.md)

### Python Code

- [Python Examples Guide](./code-examples/python/README.md)
- `01_send.py` and `02_receive.py`: first producer and consumer
- `03_work_queue_producer.py` and `04_work_queue_consumer.py`: competing workers
- `05_topic_producer.py` and `06_topic_consumer.py`: topic routing
- `07_reliable_producer.py`: persistent messages and publisher confirms
- `08_reliable_consumer.py`: manual ack, prefetch, retry, and DLQ

### Interview Preparation

- [Beginner Questions](./interview-questions/beginner.md)
- [Intermediate Questions](./interview-questions/intermediate.md)
- [Advanced Questions](./interview-questions/advanced.md)
- [Scenario Questions](./interview-questions/scenarios.md)

### Fast Revision

- [RabbitMQ Interview Revision](./cheatsheets/rabbitmq-revision.md)
- [Commands Cheatsheet](./cheatsheets/commands.md)
- [Production Design Checklist](./cheatsheets/production-checklist.md)

## Mental Model

```text
Producer -> Exchange --binding/routing key--> Queue -> Consumer
                |
                +--> another queue -> another consumer
```

A producer normally sends a message to an **exchange**, not directly to a queue. The exchange applies routing rules and sends the message to one or more queues. A consumer receives work from a queue and acknowledges it after successful processing.

## Golden Rules

1. Acknowledge only after the business operation succeeds.
2. Use publisher confirms when losing a published message is unacceptable.
3. Make consumers idempotent because redelivery can create duplicates.
4. Use bounded retries and a dead-letter queue; never retry forever.
5. Monitor queue depth, message age, publish rate, delivery rate, unacked messages, redeliveries, connections, disk, and memory.
6. Prefer policies for operational settings such as dead-lettering and TTL.
7. Use quorum queues for replicated, long-lived, critical queues.
8. Do not use RabbitMQ as a database or assume it provides end-to-end exactly-once processing.
