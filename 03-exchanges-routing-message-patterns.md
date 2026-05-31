# SECTION 3 - Exchanges, Routing, Work Queues, Pub/Sub, RPC, and Message Design

## 3.1 Why Routing Matters

Routing decides which consumers see which messages. Bad routing creates coupling, duplicate work, missed work, and operational confusion. Good routing gives each downstream capability a clear queue, owner, scaling model, and failure strategy.

```text
Producer -> Exchange -> Binding rules -> Queues -> Consumers
```

## 3.2 Direct Exchange

A direct exchange routes by exact routing-key match.

```text
orders.direct
   | order.created
   v
email.queue

orders.direct
   | order.cancelled
   v
refund.queue
```

Use direct exchanges for commands or simple event routing.

Example:

```python
channel.exchange_declare("orders.direct", "direct", durable=True)
channel.queue_declare("invoice.queue", durable=True)
channel.queue_bind("invoice.queue", "orders.direct", "order.created")
channel.basic_publish("orders.direct", "order.created", b"{...}")
```

Advantages:

- simple
- predictable
- fast
- easy to reason about

Disadvantages:

- exact matching can lead to many bindings
- less expressive for hierarchical event taxonomies

Common mistake:

```text
Using one direct exchange with vague routing keys like "process".
```

## 3.3 Topic Exchange

A topic exchange routes by wildcard pattern.

Wildcards:

- `*` matches one word
- `#` matches zero or more words

```text
routing key: order.created.eu

binding order.*.eu      -> matches
binding order.#         -> matches
binding *.created.us    -> does not match
```

Diagram:

```text
events.topic
   |
   +-- order.*       -> order_projection.queue
   +-- payment.#     -> finance.queue
   +-- *.failed      -> incident.queue
```

Use topic exchanges for domain events and routing families.

Best practices:

- keep routing keys stable
- use domain-first naming
- avoid overly broad `#` consumers unless intentional
- document event taxonomy

Anti-pattern:

```text
# -> mega_consumer.queue
```

That recreates tight coupling under a new name.

## 3.4 Fanout Exchange

A fanout exchange ignores routing keys and sends every message to every bound queue.

```text
system.broadcast
   |
   +--> cache_invalidator.queue
   +--> websocket_push.queue
   +--> audit.queue
```

Use fanout when all subscribers should receive the same message.

Good cases:

- cache invalidation
- simple broadcast
- local development event taps

Weaknesses:

- no selective routing
- easy to accidentally over-deliver
- every bound queue increases broker work

## 3.5 Headers Exchange

A headers exchange routes using message headers instead of routing keys.

```text
headers:
  channel=email
  priority=critical
  tenant=enterprise
```

Use sparingly. Headers exchanges are powerful but less visible than routing keys and can be harder to operate.

Good case:

```text
Route notifications by tenant tier, channel, and compliance region.
```

## 3.6 Default Exchange

The default exchange has an empty name. Every queue is implicitly bound to it by queue name.

```text
basic_publish(exchange="", routing_key="email.queue")
```

This publishes directly to `email.queue`.

Good for:

- tutorials
- simple scripts
- debugging

Production caution:

- hides routing architecture
- couples producers to queue names
- makes refactoring harder

## 3.7 Work Queue Pattern

Work queues distribute tasks among competing consumers.

```text
task.queue
   |
   +--> worker-1
   +--> worker-2
   +--> worker-3
```

Each message is processed by one consumer.

Use cases:

- image processing
- email sending
- PDF generation
- video transcoding
- background jobs

### Fair Dispatch

Use prefetch to avoid one worker hoarding messages.

```python
channel.basic_qos(prefetch_count=1)
```

For slow tasks, `1` may be right. For fast tasks, `10`, `50`, or more may improve throughput.

## 3.8 Publish/Subscribe Pattern

In pub/sub, one event is copied to multiple queues.

```text
order.created
   |
   v
orders.topic
   |
   +--> email.queue
   +--> invoice.queue
   +--> inventory.queue
   +--> analytics.queue
```

Each queue gets its own copy. Each service can process independently.

Key rule:

Never let one subscriber's failure block another subscriber.

## 3.9 RPC Pattern

RabbitMQ can implement request/reply using `reply_to` and `correlation_id`.

```text
Client -> rpc.request.queue -> Worker
Client <- callback.queue    <- Worker
```

Use only when you truly need asynchronous request/reply. Many RPC use cases are better handled with HTTP/gRPC.

Python sketch:

```python
props = pika.BasicProperties(
    reply_to=callback_queue,
    correlation_id=request_id,
)
channel.basic_publish("", "pricing.rpc", body, props)
```

Risks:

- harder timeouts
- hidden synchronous coupling
- callback queue lifecycle complexity
- duplicate replies

Best practice:

- use explicit timeout
- use correlation id
- make server idempotent
- prefer direct APIs for simple immediate queries

## 3.10 Message Schema Design

Good messages are small, explicit, versioned, and idempotent.

Recommended envelope:

```json
{
  "message_id": "msg_01",
  "type": "order.created",
  "version": 1,
  "occurred_at": "2026-06-01T10:15:00Z",
  "producer": "checkout-service",
  "correlation_id": "req_123",
  "idempotency_key": "order:ord_123:created",
  "payload": {
    "order_id": "ord_123",
    "user_id": "usr_456"
  }
}
```

Important fields:

- `message_id`: unique message identity
- `type`: semantic name
- `version`: schema evolution
- `correlation_id`: trace workflow
- `idempotency_key`: duplicate protection
- `payload`: business data

## 3.11 Commands vs Events

Command:

```text
send.email
reserve.inventory
capture.payment
```

Event:

```text
order.created
payment.captured
inventory.reserved
```

Command has an intended handler. Event announces a fact.

Design smell:

```text
Event named order.create
```

That is a command disguised as an event.

## 3.12 Ordering Guarantees

RabbitMQ queues have FIFO tendencies, but ordering can be affected by:

- multiple consumers
- prefetch greater than one
- nacks and redeliveries
- priorities
- dead-letter/retry loops
- sharding across queues

If strict per-entity order matters:

- route all messages for the same entity to the same queue
- use single active consumer or one consumer for that key
- make handlers detect stale versions
- consider Kafka partitioning for event-log ordering

Example:

```text
routing key order.123 -> order-events-shard-3.queue
```

## 3.13 Production Scenario: Notification Routing

```text
notification.topic
   |
   +-- notification.email.critical   -> email_critical.queue
   +-- notification.email.marketing  -> email_marketing.queue
   +-- notification.sms.*            -> sms.queue
   +-- notification.push.*           -> push.queue
```

Why separate critical and marketing queues:

- different SLOs
- different rate limits
- different retry policies
- different worker pools
- avoids priority inversion

## 3.14 Failure Cases

### Unroutable Command

```text
Producer -> exchange -> no matching queue
```

Handle with:

- mandatory publishing
- alternate exchange
- topology tests
- alerts

### Subscriber Down

```text
order.created -> email.queue grows
invoice.queue healthy
```

Pub/sub isolates failure if each subscriber owns a queue.

### Bad Wildcard Binding

```text
binding: order.#
```

Consumer unexpectedly receives `order.internal.debug` or `order.test`.

Fix:

- namespace routing keys
- review bindings
- use least-broad pattern

## 3.15 Best Practices

- Use direct exchanges for commands.
- Use topic exchanges for event taxonomies.
- Use fanout only for true broadcast.
- Keep messages small and versioned.
- Include correlation and idempotency identifiers.
- Give each service its own queue for events.
- Do not share one queue between services with different ownership.
- Keep routing keys meaningful and documented.
- Validate messages at consumer boundaries.

## 3.16 Anti-Patterns

- publishing all events to one queue
- using RabbitMQ RPC for every service call
- using vague routing keys
- broad topic bindings that accidentally consume too much
- relying on queue order with many consumers
- putting secrets or huge payloads in messages
- changing message schema without versioning

## 3.17 Performance Considerations

- Direct routing is simple and efficient.
- Topic routing is flexible but binding complexity matters.
- Many tiny queues are usually fine, but extreme queue counts need capacity testing.
- Very large messages reduce throughput and increase memory/disk pressure.
- Serialization cost can dominate consumer CPU.
- Batching publish confirms improves publisher throughput.

## 3.18 Interview Questions

1. Direct vs topic exchange: when would you use each?
2. How does pub/sub differ from competing consumers?
3. Why should each subscriber have its own queue?
4. What is the RabbitMQ RPC pattern and why can it be risky?
5. How do routing keys affect architecture?
6. How do you design message schemas for evolution?
7. What can break message ordering?

## 3.19 Practical Exercises

1. Build one direct exchange with two routing keys.
2. Build one topic exchange with `order.*` and `payment.#` bindings.
3. Add two consumers to one queue and observe competing behavior.
4. Add two queues to one exchange and observe pub/sub copies.
5. Publish an unroutable message with `mandatory=true`.

## 3.20 Key Takeaways

- Exchanges are RabbitMQ's routing brain.
- Work queues distribute one task to one worker.
- Pub/sub copies one event to multiple service-owned queues.
- RPC is possible but should be used carefully.
- Message schema design is a long-term compatibility contract.
