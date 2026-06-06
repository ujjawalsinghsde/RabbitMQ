# RabbitMQ Scenario Interview Questions

## 1. Payment Was Charged Twice

**Question:** A payment consumer updates the provider, crashes, and receives the same message again. How do you prevent another charge?

**Good answer:** Use a stable payment-operation idempotency key at the provider, store the message/business key with a unique constraint locally, and make the state transition conditional. Acknowledge after committing the local result.

## 2. Queue Keeps Growing

**Question:** What do you investigate before adding consumers?

**Good answer:** Check message age, ingress and ack rates, consumer count, processing latency, unacked count, downstream capacity/rate limits, broker alarms, payload changes, and recent deployments. More consumers can overload the database or provider.

## 3. Email and Analytics Share a Queue

**Question:** Sometimes only one service sees `order.created`. Why?

**Good answer:** Consumers on the same queue compete. Give Email and Analytics separate queues bound to the same event exchange.

## 4. Infinite Retry Storm

**Question:** A failing database causes high CPU and repeated redeliveries.

**Good answer:** Stop immediate requeue. Use delayed exponential retries with a limit and jitter, then DLQ. Apply back pressure and alert on the dependency.

## 5. Producer Says Success but No Queue Has the Message

**Question:** Publisher confirms were enabled. What could happen?

**Good answer:** The exchange may have had no matching binding. Confirms can acknowledge the exchange's handling of an unroutable message. Use `mandatory=True`, handle returns, or configure an alternate exchange.

## 6. Broker Restart Lost Messages

**Question:** The queue was durable. Why were messages lost?

**Good answer:** Queue durability only preserves topology. Check message persistence, publisher confirms, queue type/replication, and whether shutdown or storage failure occurred before data was safely accepted.

## 7. Strict Order and Ten Consumers

**Question:** The product requires strict customer order and high throughput.

**Good answer:** Clarify whether order is global or per customer. Partition by customer ID and process each partition serially, or use streams/consistent routing. Global order limits parallelism.

## 8. Database Commit and Publish

**Question:** How do you avoid an order existing without `order.created`?

**Good answer:** Write the order and an outbox row in one transaction. Publish the outbox asynchronously with confirms and make downstream consumers idempotent.

## 9. Six-Hour Consumer Outage

**Question:** How do you design for it?

**Good answer:** Estimate backlog using rate and duration, provision disk and limits, monitor message age, verify TTL does not expire required work, plan catch-up capacity without overloading dependencies, and use a suitable queue or stream type.

## 10. Regional Failure

**Question:** Is a three-node quorum queue enough?

**Good answer:** It provides HA only across the failure domains containing those nodes. Regional DR requires a separate recovery design, RPO/RTO, supported data movement, application failover, and reconciliation testing.

## Architecture Whiteboard Checklist

Explain these while drawing:

- producers and consumers
- command versus event
- exchange type and routing keys
- one queue per independent subscriber
- queue type and replication
- confirms and manual acknowledgements
- idempotency store
- retries and DLQs
- schema and trace metadata
- metrics, alerts, security, and DR

