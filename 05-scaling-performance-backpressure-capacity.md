# SECTION 5 - Scaling, Performance Tuning, Backpressure, Flow Control, and Capacity Planning

## 5.1 Scaling Mindset

RabbitMQ performance is shaped by message size, queue type, routing complexity, persistence, confirms, consumer speed, disk IO, network latency, and queue topology.

Basic equation:

```text
backlog growth = publish rate - successful processing rate
```

If producers publish 10,000 messages/minute and consumers ack 7,000 messages/minute, backlog grows by 3,000 messages/minute.

## 5.2 Throughput vs Latency

Throughput:

```text
messages processed per second
```

Latency:

```text
time from publish to successful processing
```

Optimizing one can hurt the other.

Example:

- batching confirms improves throughput
- but individual message latency may increase

## 5.3 Producer Performance

Producer optimizations:

- reuse connections
- reuse channels
- batch publisher confirms
- avoid large messages
- compress only when CPU tradeoff is worth it
- use async clients for high throughput
- avoid synchronous publish-per-request bottlenecks

Publisher confirm modes:

```text
slow: publish -> wait confirm -> publish next
fast: publish many -> track confirms asynchronously
```

## 5.4 Consumer Performance

Consumer levers:

- prefetch count
- worker concurrency
- batch database writes
- connection pooling to downstream services
- timeout external calls
- avoid blocking event loops
- scale horizontally

Prefetch:

```text
prefetch = max unacked messages per consumer/channel
```

Low prefetch:

- better fairness
- safer for slow tasks
- lower memory held by consumers

High prefetch:

- better throughput for fast tasks
- risk of uneven distribution
- more redelivery after crash

## 5.5 Competing Consumers

```text
queue
  |
  +--> worker-1
  +--> worker-2
  +--> worker-3
```

Scale by adding workers until another bottleneck appears:

- database
- external API
- RabbitMQ queue leader
- CPU
- disk
- network

Scaling consumers does not help if the downstream system is the bottleneck.

## 5.6 Hot Queue Problem

One queue can become a bottleneck.

```text
all producers -> mega.queue -> all consumers
```

Symptoms:

- high ready count
- high publish rate
- queue process CPU pressure
- uneven node utilization

Solutions:

- split by domain
- shard by key
- use multiple queues
- route high and low priority separately
- consider streams or Kafka for very high-throughput event workloads

Sharding example:

```text
orders.exchange
   |
   +-- order.shard.0.queue
   +-- order.shard.1.queue
   +-- order.shard.2.queue
   +-- order.shard.3.queue
```

## 5.7 Backpressure and Flow Control

Backpressure means the system slows producers or consumers to prevent collapse.

RabbitMQ can apply flow control when:

- memory watermark is reached
- disk free limit is reached
- connections are publishing too fast

Application-level backpressure:

- reject non-critical requests
- rate-limit producers
- pause marketing campaigns
- shed low-value work
- return `202 Accepted` and process later

## 5.8 Memory Management

RabbitMQ uses memory for:

- connections
- channels
- queues
- message metadata
- unacked deliveries
- management stats
- internal processes

Modern RabbitMQ moves queue data to disk more actively than older versions, but memory still matters.

High unacked messages are dangerous because delivered messages are held in consumer responsibility limbo.

```text
ready high   -> consumers behind
unacked high -> consumers holding too much or stuck
```

## 5.9 Disk IO

Persistent messages and durable replicated queues depend on disk.

Disk bottleneck symptoms:

- publish confirms slow
- queue growth slow
- high IO wait
- broker alarms
- delayed persistence

Production guidance:

- use SSD/NVMe for critical workloads
- monitor disk free space
- set disk alarms
- separate RabbitMQ data from noisy workloads
- benchmark with realistic message sizes

## 5.10 Queue Type Performance

Classic queues:

- good general-purpose non-replicated queues
- useful when data safety is less critical
- no modern mirrored HA in RabbitMQ 4.x

Quorum queues:

- replicated and durable
- safer for critical work
- write amplification due to Raft replication
- best for workloads where safety matters more than maximum raw throughput

Streams:

- replicated append-only stream
- good for large fanout, replay, log-like access
- different consumption model than classic task queues

## 5.11 Lazy Queues

Older RabbitMQ used "lazy queues" to keep messages mostly on disk. In modern versions, queue storage behavior changed significantly and classic queues v2/quorum queues actively manage memory and disk. Treat old lazy-queue tuning advice as version-specific.

Architecture lesson:

Always tune against the RabbitMQ version you operate.

## 5.12 Benchmarking Strategy

Benchmark with:

- real message sizes
- real durability settings
- publisher confirms enabled if production uses them
- same queue type as production
- realistic consumer work
- same network region
- failure injection

Metrics:

- publish rate
- confirm latency
- deliver rate
- ack rate
- end-to-end latency
- queue depth
- redeliveries
- CPU
- memory
- disk IO
- network

## 5.13 Capacity Planning

Ask:

- peak publish rate?
- average processing rate?
- message size distribution?
- retention/backlog tolerance?
- maximum acceptable delay?
- consumer downtime tolerance?
- retry volume during provider outage?
- DLQ storage requirements?
- node failure tolerance?

Backlog storage estimate:

```text
backlog bytes = message_size * message_count * overhead_factor
```

Use an overhead factor because metadata, indexes, replication, and filesystem behavior add cost.

## 5.14 Production Scenario: Sale Event Spike

Normal:

```text
publish: 1,000/min
ack:     1,200/min
```

Sale:

```text
publish: 50,000/min
ack:     20,000/min
```

Backlog grows 30,000/min.

Plan:

- pre-scale workers
- split critical queues
- enforce provider rate limits
- define acceptable delay SLO
- monitor queue growth slope
- pause non-critical events
- verify disk capacity before event

## 5.15 Kubernetes Scaling

Horizontal Pod Autoscaler can scale consumers using custom metrics:

- queue ready count
- oldest message age
- publish rate vs ack rate

Example scaling rule:

```text
desired workers = ceil(ready_messages / 1000)
```

Be careful:

- too many workers can overload downstream APIs
- scale-up takes time
- scale-down can kill pods holding unacked messages
- graceful shutdown must stop consuming, finish work, ack/nack, then exit

## 5.16 Graceful Shutdown

Consumer shutdown:

```text
1. receive SIGTERM
2. stop accepting new deliveries
3. finish in-flight messages
4. ack successful work
5. nack/requeue unfinished work
6. close channel and connection
```

This prevents long redelivery delays and duplicate side effects.

## 5.17 Best Practices

- Tune prefetch per workload.
- Benchmark with production-like durability.
- Use confirms asynchronously for high-volume publishers.
- Split unrelated workloads into separate queues.
- Scale consumers only after checking downstream capacity.
- Monitor oldest message age, not only queue depth.
- Set resource alarms and alert before saturation.
- Keep messages small.
- Use quorum queues for critical replicated workloads.
- Design retry traffic so it cannot overwhelm the main path.

## 5.18 Anti-Patterns

- increasing consumers until the database falls over
- ignoring unacked counts
- benchmarking with transient messages but deploying persistent messages
- one hot queue for the whole company
- using huge messages
- treating queue depth as the only latency signal
- replaying DLQ all at once
- scaling down consumers without graceful shutdown

## 5.19 Interview Questions

1. How do you tune prefetch?
2. What causes high unacked messages?
3. How do publisher confirms affect throughput?
4. How do you handle a hot queue?
5. What metrics define RabbitMQ health?
6. How do you capacity-plan for a traffic spike?
7. Why can adding consumers make a system worse?
8. How would you autoscale RabbitMQ consumers on Kubernetes?

## 5.20 Practical Exercises

1. Run one producer and measure publish rate with and without confirms.
2. Change consumer prefetch from 1 to 100 and observe behavior.
3. Simulate a slow downstream dependency with sleep.
4. Create queue-depth alerts.
5. Benchmark persistent vs transient messages.

## 5.21 Key Takeaways

- RabbitMQ scaling is queue, consumer, disk, network, and downstream scaling together.
- Prefetch is one of the most important consumer tuning tools.
- Backpressure is a feature, not a failure.
- Queue depth must be interpreted with rates and message age.
- Critical performance tests must use production-like reliability settings.
