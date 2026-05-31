# SECTION 2 - Core Architecture: AMQP, Broker Internals, Connections, Channels, Exchanges, Queues, and Bindings

## 2.1 Mental Model

RabbitMQ is an AMQP message broker. Applications connect to the broker, publish messages to exchanges, exchanges route messages through bindings, queues store messages, and consumers process messages with acknowledgements.

```text
+-------------+       TCP/AMQP       +-------------------------------+
| Application | <-------------------> | RabbitMQ Node                 |
+-------------+                      |                               |
                                     |  +----------+     +--------+   |
                                     |  | Exchange | --> | Queue  |   |
                                     |  +----------+     +--------+   |
                                     +-------------------------------+
```

The broker is a reliability and routing boundary, not a business authority. Your database remains the source of truth for business state.

## 2.2 AMQP 0-9-1

AMQP defines the wire-level model for:

- connections
- channels
- exchanges
- queues
- bindings
- basic publish
- basic consume
- acknowledgements
- transactions

RabbitMQ adds important extensions such as publisher confirms.

### Why AMQP Exists

Before standard messaging protocols, applications were coupled to vendor-specific broker APIs. AMQP gives a common model:

```text
Producer -> Exchange -> Queue -> Consumer
```

This lets many languages and clients interact with RabbitMQ consistently.

## 2.3 Broker Node Internals

RabbitMQ runs on the Erlang VM. Erlang/OTP is well suited to brokers because it provides lightweight processes, supervision, message passing, distribution, and fault isolation.

Simplified internal structure:

```text
RabbitMQ node
|
+-- TCP listener
+-- connection processes
+-- channel processes
+-- exchange routing logic
+-- queue processes
+-- message store
+-- management and metrics
+-- clustering subsystem
```

Each connection and many queues are represented internally by Erlang processes. This does not mean one operating-system process per queue; Erlang processes are lightweight runtime entities.

### Internal Workflow

```text
1. TCP listener accepts client connection.
2. Client authenticates and opens AMQP connection.
3. Client opens channel.
4. Producer publishes frame sequence.
5. Channel validates exchange, permissions, and properties.
6. Exchange routes to queues using bindings.
7. Queue accepts message and updates ready/unacked state.
8. Consumer channel receives delivery.
9. Consumer sends ack/nack/reject.
10. Queue deletes, requeues, or dead-letters the message.
```

## 2.4 Virtual Hosts

A virtual host, or vhost, is a logical namespace inside RabbitMQ.

```text
RabbitMQ cluster
|
+-- vhost: /
+-- vhost: payments
+-- vhost: notifications
+-- vhost: analytics
```

Each vhost has its own:

- exchanges
- queues
- bindings
- permissions
- policies

Use vhosts for isolation between applications, environments, or tenants when full cluster separation is unnecessary.

### Production Considerations

Good use:

```text
prod-payments vhost
prod-notifications vhost
staging vhost
```

Risky use:

```text
one vhost per customer for thousands of customers
```

That can become operationally heavy. For large multi-tenant systems, prefer naming conventions, policies, and sometimes separate clusters by tenant tier.

## 2.5 Connections

A connection is a long-lived TCP connection from a client to RabbitMQ.

```text
service instance ---- TCP connection ---- RabbitMQ node
```

Connections are expensive compared with channels.

Best practices:

- keep connections long-lived
- reconnect with exponential backoff
- use heartbeats
- avoid one connection per message
- separate publisher and consumer connection pools for busy services

Failure case:

```text
API creates connection per HTTP request
```

Impact:

- high CPU
- high file descriptor usage
- connection churn
- broker instability
- poor latency

## 2.6 Channels

A channel is a lightweight virtual session inside a connection.

```text
TCP connection
|
+-- channel 1: publisher
+-- channel 2: consumer
+-- channel 3: topology declaration
```

Channels are where most AMQP methods happen.

Rules:

- delivery tags are scoped to a channel
- acknowledgements must happen on the same channel that received the delivery
- many client libraries do not allow channel sharing across threads
- channel exceptions usually close the channel, not the whole connection

Common channel-closing mistakes:

- declaring an existing queue with different durability or arguments
- acking an unknown delivery tag
- publishing to a non-existent exchange
- passive-declaring a missing queue

## 2.7 Exchanges

An exchange routes messages to queues. Producers publish to exchanges, not usually to queues.

```text
Producer -> Exchange -> Binding rules -> Queues
```

Exchange properties:

- name
- type
- durable or transient
- auto-delete
- internal or public
- arguments

Exchange types:

- direct
- topic
- fanout
- headers
- default exchange
- plugin-based types such as delayed exchange

## 2.8 Queues

A queue stores messages until consumers process them.

Queue states:

```text
ready:   messages waiting for delivery
unacked: messages delivered but not acknowledged
```

```text
+-------------------------------------+
| queue: invoice.queue                |
| ready   [m4] [m5] [m6]              |
| unacked [m1->workerA] [m2->workerB] |
+-------------------------------------+
```

Queue properties:

- durable
- exclusive
- auto-delete
- queue type
- max length
- TTL
- dead-letter exchange
- single active consumer
- quorum settings

Modern RabbitMQ queue types:

- classic queues: general-purpose, non-replicated in RabbitMQ 4.x
- quorum queues: durable replicated queues based on Raft
- streams: replicated append-only log-like structure for streaming workloads

Official RabbitMQ guidance for data safety is to use quorum queues or streams when replication is required. Classic queue mirroring was deprecated and removed in RabbitMQ 4.0.

## 2.9 Bindings and Routing Keys

A binding connects an exchange to a queue.

```text
orders.exchange -- routing key order.created --> email.queue
orders.exchange -- routing key order.created --> invoice.queue
orders.exchange -- routing key order.cancelled --> refund.queue
```

Routing key is a string chosen by the producer.

Good routing keys:

```text
order.created
order.cancelled
payment.completed
notification.email.critical
```

Bad routing keys:

```text
data
event
message
queue1
```

Routing keys are architecture. Name them deliberately.

## 2.10 Topology Declaration

Applications commonly declare exchanges, queues, and bindings at startup.

```text
declare exchange
declare queue
bind queue
consume/publish
```

This is idempotent only when properties match exactly. If one service declares `email.queue` as durable and another declares it as non-durable, RabbitMQ closes the channel with a precondition failure.

Best practice:

- centralize topology ownership
- use infrastructure-as-code for production topology
- make app startup declarations match production definitions
- avoid accidental queue argument drift

## 2.11 Message Lifecycle

```text
Producer
  |
  | publish
  v
Exchange
  |
  | route
  v
Queue
  |
  | deliver
  v
Consumer
  |
  | ack
  v
Queue deletes message
```

Failure variations:

```text
Producer publish fails             -> producer retry/outbox
Exchange cannot route              -> mandatory return or drop
Queue is full                      -> reject/policy behavior
Consumer crashes before ack        -> requeue/redeliver
Consumer nacks requeue=false       -> dead-letter or discard
Broker restarts with transient msg -> lost
```

## 2.12 Mandatory Publishing

If a message reaches an exchange but matches no queue, it can be dropped unless the producer uses the `mandatory` flag and handles returned messages.

```text
Producer -> Exchange -> no binding -> return to producer if mandatory=true
```

Use `mandatory` for command messages where unroutable messages are bugs.

## 2.13 Production Scenarios

### Scenario: API Startup Storm

One hundred service instances restart and all declare topology.

Risk:

- channel errors if declarations drift
- broker load spike
- slow deployments

Mitigation:

- topology managed by deployment tooling
- app declarations limited to development or verified declarations
- policies for DLX, quorum, TTL, max length

### Scenario: Consumer Stuck

Symptoms:

```text
ready: low
unacked: very high
ack rate: low
```

Likely causes:

- consumer deadlock
- downstream dependency hanging
- prefetch too high
- no timeout around external call

Fix:

- enforce timeouts
- lower prefetch
- graceful consumer shutdown
- restart unhealthy workers
- expose per-message processing duration

## 2.14 Best Practices

- Use long-lived connections.
- Use separate channels for publishing and consuming.
- Keep topology names explicit and stable.
- Prefer durable exchanges and queues for production workflows.
- Use quorum queues for replicated critical queues.
- Use the `mandatory` flag for commands that must route.
- Keep queue arguments consistent across services.
- Use policies for operational settings that may need to change.
- Do not use RabbitMQ queues as service-owned databases.

## 2.15 Anti-Patterns

- one connection per message
- hidden queue declarations from many services with conflicting arguments
- publishing to the default exchange everywhere in production systems
- one global queue for unrelated workflows
- no ownership for exchanges and routing keys
- ignoring unroutable messages
- treating RabbitMQ topology as incidental code instead of architecture

## 2.16 Performance Considerations

Architecture-level performance levers:

- connection reuse
- channel reuse
- publisher confirms in batches
- consumer prefetch
- message size
- queue type choice
- disk speed
- network latency
- queue count and hot queue distribution

Hot queue problem:

```text
all producers -> one queue -> one logical bottleneck
```

Solutions:

- shard by routing key
- split workloads by business domain
- use multiple queues and consumer pools
- verify ordering requirements before sharding

## 2.17 Interview Questions

1. Why does RabbitMQ have exchanges instead of publishing directly to queues?
2. What is the difference between a connection and a channel?
3. Why can redeclaring a queue close a channel?
4. What is a virtual host?
5. What happens to an unroutable message?
6. Why are classic mirrored queues not a modern HA strategy?
7. What does `ready` vs `unacked` mean?
8. How would you diagnose high unacked messages?

## 2.18 Practical Exercises

1. Create a direct exchange, queue, and binding from the management UI.
2. Publish a message with a matching routing key and observe queue depth.
3. Publish with a non-matching routing key and observe the result.
4. Write a consumer with `prefetch_count=1`, then change it to `50` and compare unacked behavior.
5. Declare a queue with one durability setting, then try redeclaring it differently in a script and inspect the channel error.

## 2.19 Key Takeaways

- AMQP gives RabbitMQ its core exchange/queue/binding model.
- Connections are TCP sessions; channels are lightweight AMQP sessions.
- Exchanges route; queues store; bindings define routing rules.
- RabbitMQ internals are built on Erlang/OTP processes and supervision.
- Queue type choice is an architecture decision.
- In modern RabbitMQ, quorum queues and streams are the primary replicated data structures.
