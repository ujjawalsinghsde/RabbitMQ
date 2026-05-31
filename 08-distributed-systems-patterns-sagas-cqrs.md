# SECTION 8 - Distributed Systems Patterns: Event-Driven Architecture, CQRS, Sagas, Outbox, Inbox, and Consistency

## 8.1 RabbitMQ in System Design

RabbitMQ is often the backbone for operational workflows.

```text
Service commits state -> publishes event/command -> other services react
```

It helps systems become:

- decoupled
- resilient
- scalable
- eventually consistent
- observable through queues

But it also introduces:

- duplicates
- delayed processing
- ordering concerns
- distributed failure modes
- schema evolution problems

## 8.2 Event-Driven Architecture

Event-driven architecture uses facts as integration points.

```text
Order Service -> order.created -> Email Service
                              -> Inventory Service
                              -> Invoice Service
```

Benefits:

- services are loosely coupled
- new subscribers can be added
- producers do not know consumers
- failures are isolated by queues

Risks:

- event sprawl
- unclear ownership
- eventual consistency surprises
- hard debugging without tracing

## 8.3 Command-Based Architecture

Commands request work.

```text
Order Service -> reserve.inventory -> Inventory Worker
Order Service -> send.email        -> Email Worker
```

Commands are useful when:

- exactly one logical service should perform work
- result may be asynchronous
- work must be queued and retried

Do not call everything an event. Command vs event clarity affects ownership.

## 8.4 CQRS

Command Query Responsibility Segregation separates writes from reads.

```text
Write model -> events -> projection workers -> read model
```

RabbitMQ can drive projections:

```text
order.created -> order_read_model.queue -> projection DB
order.shipped -> order_read_model.queue -> projection DB
```

Considerations:

- projections lag behind writes
- consumers must be idempotent
- version numbers help detect stale updates
- rebuild/replay is limited with normal queues
- Kafka or RabbitMQ streams may be better for full replay

## 8.5 Saga Pattern

A saga coordinates a business transaction across services without a distributed database transaction.

Example order saga:

```text
Create order
  -> reserve inventory
  -> authorize payment
  -> create shipment
  -> confirm order
```

If payment fails:

```text
release inventory
cancel order
notify user
```

## 8.6 Choreography Saga

Services react to events.

```text
OrderCreated -> InventoryReserved -> PaymentAuthorized -> OrderConfirmed
                      |
                      v
              InventoryRejected -> OrderCancelled
```

Pros:

- decentralized
- low coupling
- easy to add subscribers

Cons:

- flow is hard to see
- cyclic dependencies can emerge
- debugging is harder
- business process ownership can blur

## 8.7 Orchestration Saga

A saga orchestrator sends commands and waits for replies/events.

```text
OrderSaga
   |
   +-> reserve.inventory
   +-> authorize.payment
   +-> create.shipment
```

Pros:

- central visibility
- clearer process ownership
- easier timeout handling

Cons:

- orchestrator can become complex
- risk of central coupling

RabbitMQ fits both styles.

## 8.8 Inbox Pattern

Outbox protects publishing. Inbox protects consuming.

Inbox table:

```text
inbox_messages
  message_id
  received_at
  processed_at
  status
```

Consumer flow:

```text
receive -> insert inbox if new -> process transactionally -> mark processed -> ack
```

Use when duplicate prevention and auditability are critical.

## 8.9 Eventual Consistency

With RabbitMQ, downstream state is often eventually consistent.

```text
Order DB committed at 10:00:00
Email sent at 10:00:03
Search index updated at 10:00:08
Analytics updated at 10:01:00
```

Architecture must define:

- acceptable lag
- user-visible states
- reconciliation jobs
- retry policies
- manual repair processes

## 8.10 Financial Systems Pattern

For money:

```text
Ledger DB = source of truth
RabbitMQ = workflow and notification transport
```

Payment workflow:

```text
PaymentRequested
  -> gateway command
  -> PaymentAuthorized
  -> ledger posting
  -> receipt notification
  -> reconciliation
```

Rules:

- idempotency keys everywhere
- immutable audit trail
- explicit state machine
- no blind retries against gateway
- reconcile with external provider
- never use queue as ledger

## 8.11 E-Commerce Architecture

```text
Checkout API
   |
   | DB transaction + outbox
   v
Outbox Relay -> orders.topic
                  |
                  +--> inventory.queue
                  +--> payment.queue
                  +--> invoice.queue
                  +--> email.queue
                  +--> analytics bridge
```

Critical choices:

- payment and inventory queues use stronger reliability
- marketing email separated from transactional email
- invoice consumer idempotent by `order_id`
- order state machine handles partial completion
- DLQs per domain

## 8.12 Ride Booking Pattern

```text
RideRequested
   |
   +--> driver_matching.queue
   +--> pricing_audit.queue
   +--> notification.queue
```

Challenges:

- real-time latency
- cancellation races
- duplicate driver offers
- location updates too frequent for normal RabbitMQ queues

RabbitMQ is useful for workflow commands. High-frequency location streams may fit Kafka, Redis, or specialized real-time infrastructure better.

## 8.13 Audit Logging

RabbitMQ can move audit events, but audit truth should be stored durably.

```text
Service -> audit.event -> audit.queue -> append-only audit store
```

For compliance:

- use outbox
- sign/hash records if needed
- keep immutable storage
- monitor audit queue aggressively

## 8.14 Best Practices

- Distinguish commands from events.
- Define source of truth per domain.
- Use outbox for state-change events.
- Use inbox/idempotency for critical consumers.
- Model long workflows as state machines.
- Design compensating actions.
- Define eventual consistency SLOs.
- Use correlation and causation IDs.
- Keep event schemas versioned.

## 8.15 Anti-Patterns

- event soup with no ownership
- queues as hidden distributed transactions
- saga with no compensating actions
- payment retries without idempotency
- read models with no lag monitoring
- consumers making assumptions about producer database timing
- using normal RabbitMQ queues when long-term replay is required

## 8.16 Performance Considerations

- Saga orchestration adds message hops and latency.
- Projections can lag under load.
- Fanout increases broker work.
- Inbox/outbox tables need indexing and cleanup.
- Reconciliation jobs need rate limits.

## 8.17 Interview Questions

1. Explain event-driven architecture with RabbitMQ.
2. Command vs event: what is the difference?
3. How does RabbitMQ fit CQRS?
4. What is a saga?
5. Choreography vs orchestration?
6. What is the outbox pattern?
7. What is the inbox pattern?
8. How do you design eventual consistency for checkout?

## 8.18 Practical Exercises

1. Design an order saga with compensation.
2. Add outbox and inbox tables to a sample service.
3. Build a projection consumer.
4. Add correlation IDs across three message hops.
5. Write a reconciliation worker for payments.

## 8.19 Key Takeaways

- RabbitMQ is excellent for operational event-driven workflows.
- It does not remove the need for source-of-truth thinking.
- Sagas require explicit failure and compensation design.
- Outbox and inbox patterns are core reliability tools.
- Eventual consistency must be explained to product and operations teams, not hidden.
