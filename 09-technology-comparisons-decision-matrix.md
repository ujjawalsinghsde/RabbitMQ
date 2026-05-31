# SECTION 9 - Technology Comparisons and Architecture Decision Matrix

## 9.1 Comparison Mindset

RabbitMQ, Kafka, Redis Streams, SQS, ActiveMQ, Pulsar, and NATS overlap, but they are not interchangeable. Choose based on workflow semantics, durability, replay, routing, operations, latency, and team maturity.

## 9.2 RabbitMQ vs Kafka

```text
RabbitMQ: broker routes messages into queues; messages are acked and removed.
Kafka: distributed log stores records; consumers track offsets.
```

RabbitMQ strengths:

- flexible routing
- task queues
- per-message ack/nack
- retry/DLQ workflows
- command processing
- lower conceptual overhead for work dispatch

Kafka strengths:

- durable event log
- replay
- high-throughput ingestion
- partitioned ordering
- stream processing ecosystem
- many independent consumers reading history

Choose RabbitMQ for:

- email jobs
- payment command queue
- image processing
- workflow tasks
- service commands

Choose Kafka for:

- clickstream
- analytics pipelines
- event sourcing log
- fraud feature streams
- long retention event backbone

Hybrid:

```text
order.created -> RabbitMQ for operational side effects
order.created -> Kafka for analytics and replay
```

## 9.3 RabbitMQ vs Redis Streams

Redis Streams strengths:

- simple if Redis already exists
- fast in-memory operations
- consumer groups
- lightweight stream use cases

RabbitMQ strengths:

- richer routing
- mature broker semantics
- stronger queueing patterns
- DLX/retry ecosystem
- protocol support
- operational separation from cache

Choose Redis Streams for:

- lightweight internal streams
- small teams already operating Redis
- low-latency ephemeral workflows

Choose RabbitMQ for:

- complex routing
- broker-centered integration
- many queue patterns
- enterprise messaging

## 9.4 RabbitMQ vs AWS SQS

SQS strengths:

- fully managed
- highly available
- simple queue semantics
- no broker operations
- integrates with AWS IAM/Lambda

RabbitMQ strengths:

- exchanges and rich routing
- AMQP features
- low-latency local broker
- protocol flexibility
- complex topology
- self-managed control

Choose SQS for:

- AWS-native simple queues
- minimal ops
- elastic managed queueing

Choose RabbitMQ for:

- routing-heavy systems
- on-prem/hybrid
- AMQP compatibility
- advanced broker patterns

## 9.5 RabbitMQ vs ActiveMQ

ActiveMQ is a traditional enterprise message broker with JMS heritage.

RabbitMQ often wins for:

- AMQP ecosystem
- operational simplicity
- routing model
- cloud-native deployments

ActiveMQ may fit:

- JMS-heavy legacy systems
- existing enterprise integration
- Java-centric environments

## 9.6 RabbitMQ vs Pulsar

Pulsar is a distributed pub/sub and streaming platform with separation of compute brokers and storage via BookKeeper.

Pulsar strengths:

- multi-tenancy
- geo-replication
- streaming and queueing models
- long retention

RabbitMQ strengths:

- simpler broker model
- work queues
- routing
- lower operational footprint

Choose Pulsar when:

- large multi-tenant streaming platform is needed
- geo-replication and retention are central

Choose RabbitMQ when:

- operational task routing and command queues are central

## 9.7 RabbitMQ vs NATS

NATS strengths:

- extremely lightweight
- very low latency
- simple pub/sub
- service mesh-style messaging
- JetStream adds persistence

RabbitMQ strengths:

- mature work queue semantics
- exchanges and routing
- ack/retry/DLQ patterns
- enterprise broker behavior

Choose NATS for:

- low-latency control plane messaging
- simple pub/sub
- lightweight cloud-native communication

Choose RabbitMQ for:

- durable business workflows
- complex retry and routing
- task queues

## 9.8 Decision Matrix

| Requirement | Best Fit |
|---|---|
| Task queue with retries | RabbitMQ |
| Complex routing | RabbitMQ |
| Event replay for months | Kafka/Pulsar |
| Simple AWS managed queue | SQS |
| Lightweight Redis-native stream | Redis Streams |
| Very low-latency pub/sub | NATS |
| JMS legacy integration | ActiveMQ |
| Multi-tenant streaming platform | Pulsar |
| Operational side effects after business event | RabbitMQ |
| Analytics event backbone | Kafka |

## 9.9 When Not to Use RabbitMQ

Avoid RabbitMQ when:

- long-term event replay is core
- consumers need to scan historical event logs
- data volume is massive streaming analytics
- managed queue service is enough and ops team is small
- strong synchronous consistency is required
- the team cannot design idempotency/retries
- the problem is just an in-process background task

## 9.10 Architecture Decision Record Template

```text
Decision: Use RabbitMQ for notification command processing.

Context:
- Checkout must not block on email/SMS providers.
- Notifications need retries and DLQ.
- Message replay beyond operational retry is not required.

Options:
- RabbitMQ
- Kafka
- SQS
- Redis Streams

Decision:
- RabbitMQ direct/topic exchanges with separate queues per channel and priority.

Consequences:
- Consumers must be idempotent.
- Operations must monitor queue age and DLQ.
- Kafka remains preferred for analytics events.
```

## 9.11 Best Practices

- Choose based on semantics, not popularity.
- Separate operational workflows from analytical event streams when needed.
- Prefer managed services when operations capacity is limited.
- Document decision tradeoffs.
- Re-evaluate when scale or retention requirements change.

## 9.12 Anti-Patterns

- using Kafka as a simple job queue without understanding consumer groups and offsets
- using RabbitMQ as a long-retention event store
- using Redis Streams for critical workflows without persistence/HA clarity
- choosing technology by benchmark alone
- forcing one messaging system to serve every use case

## 9.13 Interview Questions

1. RabbitMQ vs Kafka?
2. RabbitMQ vs Redis Streams?
3. RabbitMQ vs SQS?
4. When is RabbitMQ the wrong tool?
5. How would you design a hybrid RabbitMQ + Kafka architecture?
6. What tradeoffs matter more than raw throughput?

## 9.14 Practical Exercises

1. Write an ADR for choosing RabbitMQ for email notifications.
2. Write an ADR rejecting RabbitMQ for clickstream analytics.
3. Design a hybrid order system using RabbitMQ and Kafka.
4. Compare retry handling in RabbitMQ vs SQS.

## 9.15 Key Takeaways

- RabbitMQ is a broker for routed operational messaging.
- Kafka is a distributed log for retained event streams.
- Redis Streams is lightweight and Redis-native.
- SQS is managed simple queueing.
- Pulsar and NATS solve different messaging niches.
- The right choice follows workload semantics.
