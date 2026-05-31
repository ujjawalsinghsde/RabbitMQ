# SECTION 4 - Reliability: Acknowledgements, Publisher Confirms, Durability, Retries, DLQs, Idempotency, and the Outbox Pattern

## 4.1 Reliability Starts With Failure Assumptions

In distributed systems, every boundary can fail:

```text
Producer -> RabbitMQ -> Consumer -> Database -> External API
```

Failures include:

- publish timeout
- broker restart
- network partition
- consumer crash
- database commit failure
- duplicate delivery
- poison message
- downstream timeout
- ack lost after successful processing

RabbitMQ helps, but the application must participate in reliability.

## 4.2 Consumer Acknowledgements

Manual ack means the consumer tells RabbitMQ when processing is complete.

```text
Queue -> Consumer
        process
Consumer -> ack
Queue deletes message
```

If the consumer dies before ack:

```text
message becomes eligible for redelivery
```

Use manual ack for important work.

## 4.3 Ack, Nack, Reject

Positive ack:

```python
channel.basic_ack(delivery_tag=method.delivery_tag)
```

Negative ack:

```python
channel.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
```

Reject one message:

```python
channel.basic_reject(delivery_tag=method.delivery_tag, requeue=False)
```

Use `requeue=True` carefully. Immediate requeue can create tight failure loops.

## 4.4 Publisher Confirms

Consumer acks protect delivery from broker to consumer. Publisher confirms protect publish from producer to broker.

```text
Producer -> RabbitMQ
Producer <- confirm
```

Without confirms, the producer may believe a message was accepted when it was lost during a connection failure.

Production guidance:

- enable confirms for critical publishing
- batch confirms for throughput
- handle nacks and timeouts
- persist outgoing intent in an outbox for critical database-triggered events

## 4.5 Durability and Persistence

For restart survival, usually use both:

```text
durable queue + persistent message
```

Durable queue:

```python
channel.queue_declare("payment.queue", durable=True)
```

Persistent message:

```python
pika.BasicProperties(delivery_mode=pika.DeliveryMode.Persistent)
```

Important nuance:

- durable queue survives restart
- persistent message is eligible for disk persistence
- publisher confirms tell you RabbitMQ accepted responsibility
- replicated queue type determines node-failure tolerance

## 4.6 Retry Design

Bad retry:

```text
fail -> requeue immediately -> fail -> requeue immediately forever
```

Good retry:

```text
main.queue
   |
   | fail
   v
retry.10s.queue -- TTL expires --> main.exchange --> main.queue
   |
   | too many failures
   v
dead_letter.queue
```

Retry strategies:

- fixed delay
- exponential backoff
- retry buckets: 10s, 1m, 5m, 30m
- max retry count
- DLQ after exhaustion

## 4.7 Dead-Letter Exchanges

Messages can be dead-lettered when:

- consumer nacks with `requeue=false`
- message expires
- queue exceeds length limit
- quorum queue delivery limit is exceeded

```text
main.queue -- dead-letter --> dlx.exchange -> dead_letter.queue
```

DLQ is not a trash can. It is an operational workflow.

Teams must define:

- who owns DLQ monitoring
- how alerts fire
- how messages are inspected
- when messages are replayed
- when messages are discarded
- how sensitive data is protected

## 4.8 Poison Messages

A poison message always fails.

Examples:

- invalid schema
- missing required field
- impossible state
- unsupported version
- payload references deleted object

Handling:

```text
validate -> reject non-retryable -> DLQ
timeout -> retry
rate limit -> retry later
bug -> DLQ after limit and alert
```

Do not treat every failure as retryable.

## 4.9 Idempotent Consumers

At-least-once delivery means duplicates are normal.

Consumer pattern:

```text
receive message
check processed_messages(message_id)
if exists: ack
else:
  transaction:
    apply business change
    insert processed message id
  ack
```

Pseudo-code:

```python
def handle(message):
    with db.transaction():
        if db.exists("processed_messages", message["message_id"]):
            return "already_done"

        apply_change(message)
        db.insert("processed_messages", message["message_id"])
```

Ack only after the database transaction commits.

## 4.10 The Database Commit vs Publish Problem

Classic failure:

```text
1. Order API writes order to database.
2. Order API publishes order.created.
3. Publish fails.
4. Database says order exists, but no downstream service knows.
```

Reverse failure:

```text
1. Publish message.
2. Database transaction fails.
3. Consumers see event for order that does not exist.
```

## 4.11 Transactional Outbox Pattern

Use one database transaction to write business state and outgoing message intent.

```text
Order API
  |
  | DB transaction
  v
+-------------------+
| orders            |
| outbox_events     |
+-------------------+
          |
          | relay publishes
          v
      RabbitMQ
```

Steps:

1. In one transaction, write order and outbox row.
2. Outbox relay reads unpublished rows.
3. Relay publishes to RabbitMQ with confirms.
4. Relay marks row as published.
5. Consumers remain idempotent.

This gives reliable eventual publishing without distributed transactions.

## 4.12 Exactly-Once Myth

In practical distributed systems:

```text
exactly-once effect = at-least-once delivery + idempotent side effects + transactional state
```

RabbitMQ can redeliver. Networks can lie. Consumers can crash between side effect and ack. Design for duplicates.

Payment example:

```text
Use payment_id as idempotency key with payment gateway.
Record gateway request and response.
Do not blindly charge on every delivery.
```

## 4.13 Failure Matrix

| Failure | RabbitMQ Behavior | Application Responsibility |
|---|---|---|
| Consumer crashes before ack | redelivery | idempotency |
| Producer loses connection | publish unknown | confirms/outbox |
| Broker restarts | durable/persistent survive best effort | queue type and confirms |
| Poison message | may redeliver forever | retry limit/DLQ |
| Downstream timeout | consumer decides | retry with backoff |
| Duplicate message | allowed | dedupe/idempotency |
| DLQ grows | stores failed work | alert and triage |

## 4.14 Production Retry Example: Email

```text
email.exchange
   |
   v
email.send.queue
   |
   | temporary provider failure
   v
email.retry.1m.queue
   |
   | TTL
   v
email.exchange -> email.send.queue
   |
   | retries exhausted
   v
email.dlq
```

Retryable:

- provider 429
- provider 503
- network timeout

Non-retryable:

- invalid email
- template missing
- unsupported message version

## 4.15 Best Practices

- Use publisher confirms for critical messages.
- Use manual consumer acks.
- Ack after durable side effects.
- Use durable queues and persistent messages.
- Use quorum queues for replicated critical queues.
- Use DLQs with ownership and alerts.
- Apply retry limits.
- Classify failures as retryable or non-retryable.
- Make consumers idempotent.
- Use outbox for database-triggered events.

## 4.16 Anti-Patterns

- auto ack for payment or order processing
- ack before writing to database
- publish after DB commit without outbox for critical workflows
- immediate infinite requeue
- DLQ nobody monitors
- retrying invalid schema forever
- assuming publisher success without confirms
- using RabbitMQ transactions for high-throughput publishing without understanding performance cost

## 4.17 Performance Considerations

Reliability costs throughput.

Tradeoffs:

- persistent messages require disk work
- confirms add latency unless batched
- quorum queues replicate writes
- small prefetch improves fairness but may reduce throughput
- high retry volume can overwhelm the broker

Optimizations:

- batch publisher confirms
- tune prefetch by workload
- keep messages small
- separate retry traffic from hot path
- avoid DLQ replay storms
- use faster disks for persistent workloads

## 4.18 Interview Questions

1. What is the difference between consumer acknowledgements and publisher confirms?
2. Why are durable queues not enough alone?
3. What is a poison message?
4. How would you design retries without infinite loops?
5. Why is exactly-once processing hard?
6. Explain the outbox pattern.
7. What happens if the consumer commits to DB and crashes before ack?
8. How do you safely replay a DLQ?

## 4.19 Practical Exercises

1. Build a consumer that crashes before ack and observe redelivery.
2. Add a processed-message table and prove duplicate safety.
3. Create a DLX and route failed messages to a DLQ.
4. Implement retry with one delay queue.
5. Write an outbox table schema for `order.created`.

## 4.20 Key Takeaways

- RabbitMQ reliability is a collaboration between broker and application.
- Manual ack and publisher confirms solve different sides of delivery.
- Durable queues plus persistent messages are baseline reliability, not full HA.
- At-least-once delivery is the normal production model.
- Idempotency, retries, DLQs, and outbox are mandatory patterns for serious systems.
