# RabbitMQ Production Design Checklist

## Message Contract

- [ ] Is it clearly a command, event, or reply?
- [ ] Does it have a unique message ID?
- [ ] Does it have a schema version and UTC timestamp?
- [ ] Is correlation/trace context included?
- [ ] Is the payload small and free of secrets?
- [ ] Is schema evolution backward compatible?

## Topology

- [ ] Is the exchange type justified?
- [ ] Does every independent subscriber have its own queue?
- [ ] Are names stable, documented, and owned?
- [ ] Is queue type appropriate: classic, quorum, or stream?
- [ ] Are operational arguments managed by policies where possible?
- [ ] Is unroutable publishing handled with mandatory returns or an alternate exchange?

## Producer

- [ ] Are connections long-lived?
- [ ] Are important messages persistent?
- [ ] Are publisher confirms handled?
- [ ] Are confirm timeout and ambiguous outcomes handled as possible duplicates?
- [ ] Is the database/message dual write solved with an outbox when required?
- [ ] Are publish failures measured and alerted?

## Consumer

- [ ] Is manual acknowledgement used for important work?
- [ ] Does ack happen after durable business success?
- [ ] Is processing idempotent?
- [ ] Is prefetch measured and bounded?
- [ ] Are validation and exception classes explicit?
- [ ] Are shutdown and connection recovery graceful?

## Retry and DLQ

- [ ] Are transient, permanent, business, and unknown failures separated?
- [ ] Do retries use delay, backoff, jitter, and a maximum?
- [ ] Is immediate infinite requeue impossible?
- [ ] Does each DLQ have an owner and alert?
- [ ] Is there a documented, throttled replay process?
- [ ] Are TTL, queue length, and retention intentional?

## Capacity and Availability

- [ ] Are normal rate, burst rate, payload size, and processing time known?
- [ ] Can storage hold the planned outage backlog?
- [ ] Can downstream systems handle catch-up traffic?
- [ ] Are critical queues replicated across failure domains?
- [ ] Have node, network, disk, and consumer failures been tested?
- [ ] Are RPO and RTO documented and tested?

## Operations and Security

- [ ] Are queue count, oldest age, unacked count, redelivery, DLQ, and confirm latency monitored?
- [ ] Are memory/disk alarms and connection churn monitored?
- [ ] Are application processing metrics and traces available?
- [ ] Are users least-privileged per vhost/application?
- [ ] Is TLS enabled where required?
- [ ] Are secrets managed and rotated?
- [ ] Is the management UI restricted?
- [ ] Is the RabbitMQ version pinned, supported, and upgrade-tested?

