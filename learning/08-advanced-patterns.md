# Advanced Patterns

## Request/Reply (RPC)

A requester publishes with a `reply_to` destination and a unique `correlation_id`. The responder sends the result to that destination.

Use RPC sparingly. It creates synchronous waiting and failure coupling while looking asynchronous. Set a timeout, handle duplicate replies, and avoid creating an unbounded number of temporary queues. Direct Reply-to may help for appropriate short-lived replies.

## Priority

Priority queues can favor important messages, but they add complexity and can starve low-priority work. Separate queues and consumer capacity are often clearer for strongly different service levels.

## Delayed Work

Options include:

- TTL retry queues plus dead-letter routing
- quorum queue delayed retry features where appropriate
- delayed-message exchange plugin, if the operational dependency is accepted
- an external scheduler for long or business-critical schedules

RabbitMQ is not a complete durable workflow scheduler.

## Single Active Consumer

Multiple consumers may connect, but only one receives deliveries until it fails. This is useful when one-at-a-time consumption is needed with automatic failover. It does not remove the need for idempotency.

## Saga

A saga coordinates a business process across services using local transactions and compensating actions:

```text
Order created -> payment charged -> stock reserved -> shipment requested
                     |
                     + failure -> refund payment
```

Two styles:

- **Choreography:** services react to events. Flexible, but the flow becomes difficult to see as it grows.
- **Orchestration:** one coordinator sends commands and records workflow state. Easier to observe, but the coordinator is an important component.

Persist saga state outside RabbitMQ and make every step idempotent.

## Schema Evolution

- Add fields compatibly before removing old fields.
- Consumers should tolerate unknown optional fields.
- Include a schema version.
- Deploy tolerant consumers before new producers.
- Use contract tests and a schema registry when organizational scale needs it.
- Never silently change the meaning of an existing field.

## Federation and Shovel

- **Federation:** loosely couples brokers or clusters and forwards selected messages or exchanges, often across WAN links.
- **Shovel:** moves messages from a source to a destination using a configured client-like worker.

These solve movement between brokers, not queue replication inside one cluster.

## Outbox and Inbox

- **Outbox:** safely connects a database commit to later message publishing.
- **Inbox/dedup table:** records consumed message IDs with the business update.

Together they support reliable, idempotent service integration without claiming distributed exactly-once transactions.

## RabbitMQ Queue or Stream?

Choose a queue when work should normally disappear after acknowledgement and one logical consumer group handles each copy. Choose a stream when retention, replay, large backlogs, or independent repeated reads are central requirements.

