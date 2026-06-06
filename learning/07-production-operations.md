# Production Operations

## Security

- Never use the default `guest` account for applications.
- Create separate users and least-privilege permissions per application/vhost.
- Use TLS for untrusted networks.
- Store credentials in a secret manager and rotate them.
- Restrict management UI and metrics endpoints.
- Avoid secrets and unnecessary personal data in message bodies.


## High Availability

A RabbitMQ cluster lets nodes cooperate, but queue data safety depends on queue type. For critical queues, use quorum queues across an odd number of nodes, usually three. Losing a majority makes a quorum queue unavailable rather than accepting unsafe writes.

Place nodes with awareness of failure zones and test actual node, network, disk, and client-reconnection failures.


## Client Recovery

Applications should:

- use long-lived connections
- configure heartbeats
- reconnect with exponential backoff and jitter
- recreate channels after connection recovery
- redeclare idempotent topology or use managed definitions
- resume consumers
- treat uncertain publishes as potentially duplicated

Do not retry connection failures in a tight loop.


## Monitoring

Alert on trends and symptoms:

| Signal | What it may mean |
|---|---|
| Ready message count rising | Consumers are slower than publishers |
| Oldest message age rising | User-visible delay is increasing |
| Unacked messages high | Consumers are slow, stuck, or prefetch is too large |
| Redeliveries rising | Consumer failures or retry loop |
| DLQ growth | Poison messages or dependency failures |
| No consumers | Deployment or connection failure |
| Memory/disk alarm | Broker will apply flow control or block publishers |
| Connection/channel churn | Client connection misuse |
| Confirm latency rising | Disk, replication, or load problem |

Collect application metrics too: processing latency, success/failure count, retry count, message age at consumption, and downstream dependency latency.


## Deployment and Upgrade

- Pin a supported RabbitMQ version; do not rely on an unbounded `latest` tag.
- Read target-version release and upgrade notes.
- Back up definitions and required data according to the recovery plan.
- Test rolling upgrades and client compatibility in staging.
- Verify policies, plugins, feature flags, alarms, and dashboards afterward.


## Disaster Recovery

High availability and disaster recovery are different:

- **HA:** handles failures inside the active cluster.
- **DR:** recovers from loss of a cluster, region, credentials, or data.

Document recovery point objective (RPO), recovery time objective (RTO), DNS and client failover, data replication approach, and replay/reconciliation steps. Run recovery exercises.


## Production Readiness Questions

1. Which messages may be lost, if any?
2. What is the maximum acceptable delay?
3. What happens when a consumer is down for six hours?
4. Can every consumer process a duplicate safely?
5. Who owns and monitors each DLQ?
6. What limits stop unbounded growth?
7. How are schemas changed compatibly?
8. How is the system recovered after a regional failure?

