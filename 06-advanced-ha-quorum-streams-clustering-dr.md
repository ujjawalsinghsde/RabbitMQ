# SECTION 6 - Advanced RabbitMQ: Quorum Queues, Streams, Clustering, Federation, Shovel, Partitions, and Disaster Recovery

## 6.1 Advanced Architecture Map

```text
Single node RabbitMQ
   |
   +-- queues
   +-- exchanges
   +-- bindings

RabbitMQ cluster
   |
   +-- multiple nodes
   +-- replicated metadata
   +-- quorum queues / streams for replicated data
   +-- node-local classic queues
```

Clustering is not automatic magic. It gives a distributed broker, but queue type determines message data safety.

## 6.2 Classic Queues

Classic queues are the original queue type. In RabbitMQ 4.x, they are non-replicated.

Use when:

- workload is not mission critical
- messages can be regenerated
- low overhead matters
- local development
- short-lived queues

Avoid for:

- critical payment workflows
- long backlogs requiring node-failure tolerance
- HA requirements

## 6.3 Quorum Queues

Quorum queues are replicated durable queues based on Raft.

```text
quorum queue: payment.queue

node-1: leader
node-2: follower
node-3: follower
```

Writes must be replicated to a majority.

```text
Producer -> leader -> replicate -> majority ack -> confirm
```

Use quorum queues when:

- data safety is important
- queue must survive node failure
- you need predictable leader election
- you want modern RabbitMQ HA

Tradeoffs:

- more disk and network IO
- higher write cost than non-replicated queue
- not every classic queue feature behaves identically
- capacity planning must include replication factor

## 6.4 Raft in Simple Terms

Raft maintains a replicated log.

```text
Leader receives write.
Leader appends to log.
Leader sends to followers.
Majority persists.
Write is committed.
```

If leader fails:

```text
followers elect new leader from majority side
```

This protects against split-brain writes because only a majority can make progress.

## 6.5 Streams

RabbitMQ streams are replicated append-only structures designed for streaming use cases.

```text
Producer -> stream -> consumers read by offset
```

Use streams when:

- replay matters
- large fanout matters
- log-like access matters
- consumers need independent offsets
- high-throughput append is needed inside RabbitMQ ecosystem

RabbitMQ stream is closer to Kafka conceptually than a normal queue, but Kafka remains stronger as a broad event streaming platform at very large scale.

## 6.6 Clustering

A RabbitMQ cluster is multiple RabbitMQ nodes cooperating.

```text
+--------+     +--------+     +--------+
| node-1 | --- | node-2 | --- | node-3 |
+--------+     +--------+     +--------+
```

Cluster metadata is shared:

- exchanges
- bindings
- users
- vhosts
- policies

Message data is queue-type dependent:

- classic queue data lives on its queue node
- quorum queue data is replicated to queue members
- stream data is replicated to stream replicas

## 6.7 Load Balancers

Clients usually connect through a TCP load balancer.

```text
Application -> LB -> RabbitMQ nodes
```

Requirements:

- AMQP TCP support
- health checks
- connection draining
- sensible timeouts

RabbitMQ connections are long-lived, so load balancing happens mostly at connection creation time.

## 6.8 Network Partitions

A network partition splits nodes so they cannot all communicate.

```text
node-1 node-2  X  node-3
```

Risks:

- inconsistent state
- unavailable queues
- minority side cannot commit quorum queue writes
- clients connected to isolated node may fail

Architecture rule:

Place cluster nodes so a majority can survive expected failures. Three nodes across three failure domains is common.

## 6.9 Federation

Federation links brokers loosely over AMQP.

```text
RabbitMQ A -> federated exchange/queue -> RabbitMQ B
```

Use for:

- cross-region event movement
- loosely coupled organizations
- WAN links
- partial replication

Federation is not the same as clustering. It is better across unreliable networks because it tolerates loose coupling.

## 6.10 Shovel

Shovel moves messages from one broker/queue to another.

```text
source queue -> shovel -> destination exchange
```

Use for:

- migration
- bridge between clusters
- draining old queues
- one-way integration

Operational caution:

- understand ack behavior
- avoid loops
- monitor lag and errors
- secure credentials

## 6.11 Multi-Region Architecture

Do not stretch a RabbitMQ cluster across high-latency regions unless you deeply understand the failure and latency tradeoffs. Prefer separate regional clusters with federation/shovel/application-level replication.

```text
Region A RabbitMQ ---- federation ---- Region B RabbitMQ
```

Design questions:

- active-active or active-passive?
- where is source of truth?
- can messages be processed twice in two regions?
- what is the recovery point objective?
- what is the recovery time objective?

## 6.12 Disaster Recovery

DR plan includes:

- definitions of critical queues
- queue types and replication factor
- backup of definitions
- infrastructure-as-code
- data retention/backlog strategy
- runbooks
- restore tests
- application idempotency
- DLQ replay procedure

Definitions backup:

```text
users, vhosts, permissions, exchanges, queues, bindings, policies
```

Definitions are not the same as message data.

## 6.13 Mirrored Queues

Classic mirrored queues were deprecated years ago and removed in RabbitMQ 4.0. Modern RabbitMQ HA designs should use quorum queues and/or streams where replicated data safety is needed.

Interview-safe statement:

```text
For modern RabbitMQ, I would not design new systems with mirrored classic queues. I would evaluate quorum queues for replicated work queues and streams for replicated replay-oriented workloads.
```

## 6.14 Production Scenario: Critical Payment Queue

Recommended:

```text
payment.exchange -> payment.capture.queue (quorum)
```

Why:

- payment commands are critical
- duplicates must be safe
- node failure should not lose accepted work
- DLQ must be monitored

Additional patterns:

- outbox from order DB
- idempotency with payment gateway
- manual ack after state transition
- reconciliation workflow

## 6.15 Best Practices

- Use 3 or 5 nodes for quorum-based HA, not 2.
- Use quorum queues for critical replicated queues.
- Use streams when replay and fanout matter.
- Keep clusters within low-latency networks.
- Prefer federation/shovel for WAN movement.
- Test node failures before production incidents.
- Backup definitions.
- Automate policies and topology.
- Monitor leader distribution.
- Plan client reconnect behavior.

## 6.16 Anti-Patterns

- assuming a cluster replicates all queue messages automatically
- using classic queues for critical HA in RabbitMQ 4.x
- stretching clusters across distant regions casually
- two-node clusters for majority-based safety
- no DR runbook
- no test of broker restart or node loss
- treating federation as exactly-once replication

## 6.17 Performance Considerations

- Quorum queues have replication cost.
- Streams are efficient for append and replay.
- Cross-region federation adds latency.
- Leader placement affects node utilization.
- Too many quorum queues can increase resource cost.
- Network bandwidth matters for replicated queues.

## 6.18 Interview Questions

1. What is a quorum queue?
2. Why were mirrored classic queues removed?
3. What is the difference between clustering and federation?
4. How do quorum queues behave during node failure?
5. When would you use streams instead of queues?
6. Why are two-node quorum designs weak?
7. How would you design RabbitMQ for multi-region DR?

## 6.19 Practical Exercises

1. Create a quorum queue using queue arguments.
2. Kill one RabbitMQ node in a local cluster and observe behavior.
3. Export and import definitions.
4. Configure a shovel between two local brokers.
5. Compare queue behavior between classic and quorum queues.

## 6.20 Key Takeaways

- Clustering and replication are different concepts.
- Queue type determines message-data safety.
- Quorum queues are the modern RabbitMQ replicated queue choice.
- Streams are for replay-oriented streaming workloads.
- Federation and shovel are better fits than stretched clusters for loose cross-region movement.
