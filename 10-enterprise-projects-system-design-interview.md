# SECTION 10 - Enterprise Projects, System Design Playbooks, Interview Preparation, and Master Checklist

## 10.1 Capstone Mindset

A staff-level RabbitMQ engineer can do four things:

1. Build correct producers and consumers.
2. Design topology that matches business ownership.
3. Predict failure behavior.
4. Operate and evolve the system safely.

This section turns concepts into projects and design playbooks.

## 10.2 Project 1: Notification Service

### Requirements

- email, SMS, and push
- critical and marketing priority
- provider rate limits
- retries
- DLQs
- user preference checks
- observability

### Architecture

```text
notification.topic
   |
   +-- notification.email.critical  -> email.critical.queue
   +-- notification.email.marketing -> email.marketing.queue
   +-- notification.sms.critical    -> sms.critical.queue
   +-- notification.push.*          -> push.queue
```

### Design

- transactional email separate from marketing
- each provider has its own worker pool
- retry queues per channel
- DLQ per channel
- idempotency key: `user_id + template + business_id`
- rate limiter in worker
- message age SLO by priority

### Failure Handling

- invalid recipient -> DLQ
- provider 429 -> delayed retry
- provider 500 -> retry with backoff
- template missing -> DLQ and alert
- duplicate message -> ack after idempotency check

## 10.3 Project 2: Order Processing System

### Architecture

```text
Checkout API
   |
   | DB transaction
   v
orders + outbox_events
   |
   v
Outbox Relay -> orders.topic
                  |
                  +-- order.created -> inventory.queue
                  +-- order.created -> payment.queue
                  +-- order.created -> invoice.queue
                  +-- order.created -> email.queue
```

### Reliability

- outbox ensures order event is eventually published
- consumers are idempotent
- payment worker uses gateway idempotency key
- invoice worker dedupes by order id
- inventory worker uses reservation state machine

### SLOs

- checkout API response under 300 ms
- inventory reservation under 5 seconds p95
- confirmation email under 1 minute p95
- DLQ alert within 1 minute

## 10.4 Project 3: Distributed Task Queue

Use cases:

- image resize
- PDF generation
- report building
- ML batch job

Architecture:

```text
task.direct
   |
   +-- image.resize    -> image.resize.queue
   +-- pdf.generate    -> pdf.generate.queue
   +-- report.generate -> report.generate.queue
```

Worker rules:

- prefetch based on task duration
- heartbeat progress for long tasks
- object storage for large files
- result table in database
- retry only transient failures
- DLQ poison tasks

## 10.5 Project 4: Payment Processing Pipeline

Architecture:

```text
payment.requested.queue (quorum)
   |
   v
Payment Worker -> Gateway
   |
   +-- payment.authorized
   +-- payment.failed
   +-- payment.unknown -> reconciliation.queue
```

Hard cases:

- gateway timeout after charge
- duplicate request
- callback arrives before worker response
- ledger write succeeds but ack fails

Required patterns:

- payment state machine
- idempotency key
- outbox
- inbox
- reconciliation
- immutable audit log
- manual intervention queue

## 10.6 Project 5: Retry Engine

Generic retry topology:

```text
main.exchange -> main.queue
       ^            |
       |            v
retry.exchange <- retry.1m.queue
       ^
       |
retry.5m.queue

fail exhausted -> dlq.exchange -> dead_letter.queue
```

Features:

- retry count tracking
- failure classification
- exponential delay buckets
- max attempts
- DLQ replay tool
- poison-message detection
- dashboards

## 10.7 Project 6: Event-Driven Microservices

Services:

- user
- order
- payment
- inventory
- notification
- audit

Integration:

```text
domain-events.topic
   |
   +-- user.*      -> notification.queue
   +-- order.*     -> audit.queue
   +-- payment.*   -> order_saga.queue
   +-- inventory.* -> order_saga.queue
```

Rules:

- each service owns its data
- events are facts
- commands target owners
- outbox per service
- correlation id across saga
- schema registry or documented versioning

## 10.8 System Design Playbook

When asked to design with RabbitMQ:

1. Clarify synchronous vs asynchronous requirements.
2. Identify source of truth.
3. Classify messages as commands or events.
4. Define exchanges, routing keys, queues, and owners.
5. Define durability and queue type.
6. Define ack strategy.
7. Define retry and DLQ strategy.
8. Define idempotency keys.
9. Define ordering requirements.
10. Define observability and SLOs.
11. Define scaling plan.
12. Define disaster recovery and replay story.

## 10.9 Enterprise Naming Conventions

Exchanges:

```text
orders.topic
payments.direct
notifications.topic
audit.fanout
```

Queues:

```text
notifications.email.critical.queue
payments.capture.queue
orders.projection.queue
inventory.reservation.queue
```

Routing keys:

```text
order.created
order.cancelled
payment.authorized
payment.failed
notification.email.critical
```

DLQs:

```text
payments.capture.dlq
notifications.email.critical.dlq
```

## 10.10 Senior Interview Deep Dives

### Question: Consumer crashes after DB commit before ack. What happens?

RabbitMQ redelivers. Consumer must be idempotent. The second attempt should detect the state already changed and ack without repeating unsafe side effects.

### Question: How do you prevent lost events after DB commit?

Use transactional outbox. Commit business row and outbox row together, then relay with publisher confirms.

### Question: How do you handle slow consumers?

Inspect ready, unacked, consumer count, processing duration, downstream latency. Tune prefetch, scale workers if downstream allows, split queues, add backpressure, and alert on message age.

### Question: RabbitMQ or Kafka for order events?

RabbitMQ for operational workflows like invoice/email/payment commands. Kafka for retained event log, analytics, replay, and stream processing. Hybrid is common.

### Question: What is your RabbitMQ HA strategy?

Use quorum queues for critical replicated queues, 3 or 5 nodes across failure domains, tested node failure, definitions backup, client reconnect, and DLQ/retry runbooks.

## 10.11 Master Best Practices

- Use RabbitMQ for asynchronous operational workflows.
- Keep messages small.
- Version schemas.
- Use manual ack.
- Use publisher confirms for critical publishing.
- Use outbox for database state changes.
- Make consumers idempotent.
- Use DLQs and monitor them.
- Avoid infinite retries.
- Separate critical and non-critical queues.
- Tune prefetch.
- Monitor oldest message age.
- Use quorum queues for replicated critical work.
- Use streams/Kafka when replay is central.
- Secure with TLS and least privilege.
- Test failures before production.

## 10.12 Master Anti-Patterns

- RabbitMQ as database
- no idempotency
- no DLQ owner
- auto ack for critical work
- one queue for everything
- huge messages
- hidden synchronous RPC over RabbitMQ
- using RabbitMQ for long-term analytics replay
- ignoring unacked messages
- no outbox for critical events
- two-node HA assumptions
- manual queue purges during incidents

## 10.13 Final Architecture Challenge

Design a multi-tenant e-commerce platform with:

- 10,000 orders/minute peak
- email/SMS notifications
- payment capture
- inventory reservation
- invoice generation
- fraud checks
- analytics
- audit trail
- tenant-specific rate limits
- regional failover

Expected senior answer:

- order DB source of truth
- outbox relay
- RabbitMQ for operational commands
- Kafka or stream platform for analytics
- quorum queues for payment/inventory
- topic exchange for domain events
- separate queues by tenant tier or workload class
- idempotency everywhere
- DLQs per domain
- retry buckets
- Prometheus/Grafana dashboards
- oldest message age SLOs
- runbooks
- regional clusters with federation/shovel or app-level replication
- reconciliation jobs

## 10.14 Final Checklist

Before shipping a RabbitMQ workflow, answer:

- What is the source of truth?
- What message type is this?
- Who owns the exchange?
- Who owns each queue?
- What queue type is used?
- Are messages persistent?
- Are publisher confirms enabled?
- What is the ack point?
- Is the consumer idempotent?
- What is the retry policy?
- Where do poison messages go?
- Who monitors the DLQ?
- What are the SLOs?
- What happens during consumer downtime?
- What happens during broker restart?
- What happens during node failure?
- What happens if downstream is slow?
- How are schemas versioned?
- How are secrets protected?
- How is the system tested under failure?

## 10.15 Key Takeaways

- RabbitMQ mastery is distributed-systems mastery applied to messaging.
- Good topology reflects business ownership.
- Reliability requires outbox, idempotency, confirms, acks, retries, and DLQs.
- Production success depends on observability and runbooks.
- Staff-level design is about tradeoffs, failure behavior, and operability.
