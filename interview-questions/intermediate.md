# Intermediate RabbitMQ Interview Questions

## 1. Publisher confirm versus consumer acknowledgement?

A publisher confirm covers producer-to-broker acceptance. A consumer acknowledgement covers broker-to-consumer processing. They are independent; a publisher confirm does not mean business processing finished.

## 2. What is at-least-once delivery?

The system avoids silent loss by retrying or redelivering, but a message may be processed more than once. Consumers must be idempotent.

## 3. Why can a message be duplicated?

A consumer may complete its database update but lose the connection before its ack reaches RabbitMQ. RabbitMQ redelivers the unacked message.

## 4. How do you make a consumer idempotent?

Use a unique message or business-operation ID. Store it with the business update in one transaction, or use conditional state transitions and downstream idempotency keys.

## 5. What is a dead-letter exchange?

An exchange to which messages can be republished after rejection without requeue, expiration, queue-length overflow, or quorum delivery-limit behavior. A queue bound to it is commonly called a DLQ.

## 6. DLQ versus retry queue?

A retry queue temporarily delays a potentially recoverable message before another attempt. A DLQ holds messages that exhausted retries or cannot be processed automatically.

## 7. Why is `nack(requeue=True)` dangerous?

If the problem remains, the message can return immediately and create a tight retry loop that wastes CPU and blocks useful work.

## 8. How would you implement delayed retry?

Publish failed messages to a retry queue with TTL. Its dead-letter exchange routes expired messages back to the main queue. Track attempt count, use increasing delays, and cap attempts.

## 9. Persistent message versus durable queue?

Persistence applies to message storage. Durability applies to queue/exchange topology. Reliable restart behavior needs both, plus confirms and an appropriate queue type.

## 10. What does `mandatory` publishing do?

It asks RabbitMQ to return a message that cannot route to any queue. Publisher confirms alone can confirm an unroutable publish, so mandatory returns or an alternate exchange are needed to detect routing failure.

## 11. Direct versus topic exchange?

Direct uses exact key equality. Topic uses dot-separated wildcard patterns, making it useful for categories such as `order.*` or `order.#`.

## 12. Fanout exchange versus several consumers?

A fanout exchange with several bound queues creates a copy per queue. Several consumers on one queue compete for one copy.

## 13. What happens to unacked messages after consumer failure?

RabbitMQ normally requeues them for redelivery when the channel or connection closes.

## 14. How does prefetch affect performance?

Low prefetch improves fairness and limits in-flight work but may underuse fast consumers. High prefetch may improve throughput but can increase memory use, unfairness, and recovery work.

## 15. How do you handle poison messages?

Validate early, classify permanent failures, cap redelivery/retry, dead-letter the message, alert the owner, and provide a controlled repair/replay process.

## 16. How do you change a message schema safely?

Add optional fields, deploy tolerant consumers first, version contracts, keep old forms during migration, and use contract tests.

## 17. What is the transactional outbox?

Business data and an outbox record are committed in one database transaction. A separate process publishes outbox records with confirms. It solves the database/message dual-write gap but may publish duplicates.

## 18. What should you monitor?

Queue depth, oldest message age, publish/delivery/ack rates, unacked messages, redeliveries, DLQ count, consumers, confirm latency, connection churn, memory, disk, node health, and application processing failures.

## 19. Why keep messages small?

Large messages consume broker memory, disk, network bandwidth, and recovery time. Store large data in object storage and send a reference.

## 20. How should clients reconnect?

Use heartbeats and exponential backoff with jitter, recreate channels and consumers, redeclare idempotent topology if appropriate, and treat uncertain publishes as possibly duplicated.

