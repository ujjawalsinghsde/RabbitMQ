# RabbitMQ Interview Revision

## Core Flow

```text
Producer -> Exchange -> Binding -> Queue -> Consumer -> Ack
```

- Producer publishes to an exchange.
- Exchange routes; queue stores.
- Consumers on one queue compete.
- Independent services need separate queues.
- Connection is TCP; channel is a lightweight AMQP session.
- Vhost isolates topology and permissions.

## Exchange Types

| Type | Routing |
|---|---|
| Direct | exact key |
| Fanout | every bound queue |
| Topic | pattern: `*` one word, `#` zero or more |
| Headers | header values |
| Default | queue name used as routing key |

Remember: alternate exchange handles **unroutable publishes**. Dead-letter exchange handles messages that were **in a queue and then failed/expired**.

## Reliability

```text
durable topology
+ persistent message
+ publisher confirms
+ mandatory/alternate routing
+ replicated queue when required
+ manual consumer ack
+ idempotent processing
= practical reliable design
```

- Confirm: broker accepted producer publish.
- Ack: consumer successfully processed delivery.
- At-least-once means duplicates are possible.
- Exactly-once business outcome requires application idempotency.
- Ack after database transaction or durable side effect.
- Unacked delivery is normally redelivered after consumer failure.

## Failure Handling

```text
Transient -> delayed retry with backoff + jitter
Permanent -> DLQ
Business rejection -> record outcome; usually no technical retry
```

- Never requeue forever.
- Track retry count and cap attempts.
- Alert on DLQ arrival.
- Replay only after inspection and correction.
- Use outbox for database + publish dual-write.
- Use inbox/dedup record for consumed message IDs.

## Scale and Production

- Competing consumers scale one queue.
- Prefetch controls unacked work in flight.
- Queue growth means arrival rate exceeds completion rate.
- Monitor oldest message age, not only count.
- Keep payloads small; send object-storage references.
- Quorum queues: replicated critical long-lived work.
- Streams: replay, retention, large backlogs, log-like access.
- Classic queues: non-replicated ordinary/temporary cases.
- More consumers can overload downstream systems.

## Architecture Answers

Mention:

1. command or event semantics
2. topic/direct exchange and routing contract
3. separate queue per service
4. quorum queue for critical work
5. confirms + mandatory publishing
6. manual ack after commit
7. unique message ID and idempotency
8. bounded delayed retries and DLQ
9. schema version and correlation ID
10. metrics, alerts, TLS, least privilege, RPO/RTO

## Five Interview Traps

1. Durable queue alone does not make messages safe.
2. Publisher confirm does not mean consumer processed the message.
3. Consumers on one queue do not each receive a copy.
4. FIFO does not guarantee observed order with retries and concurrency.
5. RabbitMQ does not provide automatic end-to-end exactly once.

