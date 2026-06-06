# Scaling and Performance
---
## Competing Consumers

Multiple consumers on one queue share the work:

```text
tasks -> worker 1
      -> worker 2
      -> worker 3
```

This scales command or job processing. It is not broadcast. For broadcast, create a separate queue for each interested service.

---
## Scaling Checklist

1. Measure publish rate and processing rate.
2. Measure message age, not only queue length.
3. Add consumers when processing is safely parallel.
4. Tune prefetch for task cost and memory.
5. Confirm downstream databases and APIs can accept the added load.
6. Set sensible connection, heartbeat, and blocked-connection timeouts.
7. Keep messages small; store large files in object storage and send references.

---
## Back Pressure

If producers are faster than consumers, queue depth grows. A queue buffers a temporary spike; it does not create unlimited capacity.

Possible responses:

- scale consumers
- optimize slow work
- rate-limit publishers
- shed noncritical work
- set queue length and message TTL policies
- separate slow and fast workloads

---
## Queue Types

### Classic Queue

Good for non-replicated queues and cases where replication is unnecessary. Classic queue mirroring was removed in RabbitMQ 4.x.

### Quorum Queue

A durable, replicated queue based on Raft. Prefer it for long-lived, critical work where data safety and availability matter. Use an odd replica count, commonly three. Publishers should use confirms and consumers should use manual acknowledgements.

Avoid quorum queues for temporary/exclusive high-churn queues, minimum-latency requirements, or extremely large backlogs where streams may fit better.

### Stream

An append-only replicated log designed for high throughput, large backlogs, replay, and multiple consumers reading independently. Streams have a different consumption model from ordinary queues.

---
## Performance Trade-offs

- Persistence and replication improve safety but cost latency and I/O.
- Confirms one message at a time are safe but slow; batch or asynchronous confirm handling improves throughput.
- Larger prefetch increases in-flight work but may reduce fairness.
- More queues improve isolation but add broker metadata and operational cost.
- Very large messages hurt memory, disk, network, and recovery.

---
## Capacity Thinking

Use Little's Law as a rough guide:

```text
messages in system = arrival rate x average time in system
```

At 1,000 messages/second and 10 seconds average delay, expect about 10,000 messages in the system. Test with realistic payloads, durability, confirms, consumer work, and failure scenarios.

