# Advanced RabbitMQ Interview Questions

## 1. Classic queue versus quorum queue versus stream?

- Classic: non-replicated ordinary queue use cases.
- Quorum: replicated, Raft-based, long-lived critical queue focused on safety.
- Stream: replicated append-only log for replay, large backlogs, and high
  throughput.

The choice depends on semantics, availability, latency, backlog, and replay, not only throughput.

## 2. Why did mirrored classic queue advice become outdated?

Classic queue mirroring was removed in RabbitMQ 4.x. Quorum queues are the modern replicated queue choice for critical workloads.

## 3. What does quorum imply during a network partition?

A majority must be available to elect/operate the leader safely. The minority side becomes unavailable rather than accepting divergent writes. This favors consistency and data safety over total availability.

## 4. When should you not use a quorum queue?

Temporary or exclusive high-churn queues, absolute minimum latency, workloads that do not need safety, and very large log-like backlogs or fanout replay where streams fit better.

## 5. Can publisher confirms guarantee no duplicates?

No. A connection can fail after the broker accepted a message but before the producer receives the confirm. Retrying can duplicate the publish.

## 6. Can RabbitMQ guarantee end-to-end exactly once?

Not automatically. Broker delivery and application database transactions are separate boundaries. Use at-least-once delivery, idempotency, outbox/inbox patterns, and reconciliation for an effectively-once business outcome.

## 7. How do you preserve ordering while scaling?

Global ordering conflicts with parallel processing. Partition messages by a stable key into queues/streams, preserve order within each partition, and use a single active consumer or ordered stream consumer per partition.

## 8. How do retries affect ordering?

A failed message that is delayed or requeued may be processed after later messages. If order is a business invariant, retry the partition as a unit or design state transitions to tolerate this.

## 9. Why prefer policies over hardcoded optional queue arguments?

Operators can update policies without changing and redeploying every application. Hardcoded arguments can also cause declaration inequivalence when applications disagree.

## 10. What is flow control?

RabbitMQ slows or blocks publishers when internal resources cannot safely accept data, including memory or disk alarms. Clients must set blocked connection timeouts and expose this state.

## 11. How do you plan capacity?

Measure realistic payload size, ingress rate, processing time, burst duration, retention/backlog, replication, confirms, disk IOPS, network, and recovery. Load-test failure and catch-up behavior, not only steady-state throughput.

## 12. What is a hot queue?

A queue whose workload is concentrated enough to limit throughput or resource distribution. Partitioning may help, but it sacrifices simple global order and adds routing/consumer complexity.

## 13. RabbitMQ cluster versus federation?

A cluster is a tightly coupled logical broker deployment. Federation connects loosely coupled brokers/clusters, often over WAN, and forwards selected message flows. Federation is not queue replica consensus.

## 14. Federation versus shovel?

Federation follows upstream topology and demand for ongoing links. Shovel is a configured message-moving worker from a source to a destination. The exact choice depends on routing, ownership, and operational control.

## 15. How would you perform disaster recovery?

Define RPO/RTO, supported cross-site movement or backup strategy, credential and DNS failover, application reconciliation, topology restoration, and tested runbooks. A three-node cluster in one region is HA, not regional DR.

## 16. How do you debug growing unacked messages?

Check processing latency, blocked downstream calls, consumer logs, prefetch, thread/event-loop blocking, ack code paths, memory, and whether consumers are alive but stuck. Restarting may only redeliver the backlog.

## 17. How do you debug growing ready messages?

Compare arrival and acknowledgement rates, oldest age, consumer count, consumer utilization, downstream limits, poison-message loops, partition imbalance, and broker alarms. Scale only after confirming downstream capacity.

## 18. How should DLQ replay work?

Inspect and classify, fix code/data, select messages deliberately, preserve IDs and trace context, throttle replay, publish with confirms, and monitor the result. Never bulk-replay unknown poison messages into a live incident.

## 19. What is single active consumer?

Only one registered consumer receives deliveries while others wait for failover. It supports active/passive consumption and ordering goals, but does not create exactly-once processing.

## 20. What makes an event architecture maintainable?

Clear event ownership, stable contracts, schema compatibility, correlation IDs, per-consumer queues, idempotency, an event catalog, end-to-end tracing, bounded failure handling, and explicit workflows when choreography becomes hard to understand.

