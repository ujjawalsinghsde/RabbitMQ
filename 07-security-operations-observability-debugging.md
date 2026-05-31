# SECTION 7 - Security, Operations, Observability, Debugging, and Production Readiness

## 7.1 Production Readiness Mindset

RabbitMQ production engineering is about controlling access, observing flow, protecting resources, and making failure boring.

Production checklist:

- TLS
- authentication
- authorization
- vhost isolation
- least privilege users
- durable topology
- monitored queues
- alerting
- backup definitions
- DLQ runbooks
- capacity limits
- graceful application shutdown

## 7.2 Authentication

RabbitMQ supports username/password authentication and can integrate with external systems depending on plugins and deployment choices.

Development default:

```text
guest / guest
```

Production:

- disable or restrict guest
- unique users per service
- rotate credentials
- store secrets in secret manager
- avoid shared admin accounts

## 7.3 Authorization

Permissions are scoped per vhost:

- configure
- write
- read

Example service permissions:

```text
checkout-service:
  write: orders.exchange
  read:  none

email-worker:
  read:  email.queue
  write: email.retry.exchange
```

Least privilege limits blast radius.

## 7.4 TLS

Use TLS for production network traffic, especially across hosts or untrusted networks.

TLS protects:

- credentials
- message payloads
- metadata

Consider mutual TLS for stronger service identity in high-security environments.

## 7.5 Virtual Hosts for Isolation

```text
vhost: prod-payments
vhost: prod-notifications
vhost: staging
```

Use vhosts to separate permissions and topology. Do not rely only on naming conventions for sensitive boundaries.

## 7.6 Policies

Policies apply operational settings to queues/exchanges by pattern.

Examples:

- dead-letter exchange
- max length
- TTL
- queue type defaults
- federation settings

Why policies matter:

- operations can change behavior without redeploying every service
- consistency across queues
- easier migration and guardrails

## 7.7 Monitoring Metrics

Core broker metrics:

- node memory
- disk free
- file descriptors
- sockets
- Erlang process count
- CPU
- network IO
- cluster partition status

Core messaging metrics:

- publish rate
- deliver rate
- ack rate
- redeliver rate
- ready messages
- unacked messages
- consumer count
- oldest message age
- confirm latency

## 7.8 Prometheus and Grafana

RabbitMQ exposes metrics suitable for Prometheus via the Prometheus plugin.

Dashboard panels:

- node health
- queue depth by queue
- message rates
- consumer counts
- redelivery rates
- memory alarms
- disk alarms
- connection counts
- channel counts
- top queues by backlog

Alert examples:

```text
Queue oldest message age > 5 minutes for critical queue
DLQ ready messages > 0
Unacked messages > threshold
Consumers = 0 for queue with ready messages
Disk free below threshold
Memory alarm active
Redelivery rate spike
```

## 7.9 Logs

RabbitMQ logs reveal:

- connection churn
- authentication failures
- channel exceptions
- resource alarms
- cluster events
- queue leader changes
- plugin issues

Application logs should include:

- message id
- correlation id
- routing key
- queue
- attempt count
- processing duration
- failure classification

## 7.10 Distributed Tracing

RabbitMQ breaks normal request call stacks. Add trace context to message headers.

```text
HTTP request trace id -> message header -> consumer span
```

Message headers:

```text
traceparent
correlation_id
causation_id
producer
```

This makes async workflows debuggable.

## 7.11 Debugging Playbooks

### Queue Growing

Check:

- consumer count
- ack rate
- publish rate
- oldest message age
- downstream health
- recent deployment

Actions:

- scale consumers
- rollback bad consumer
- pause producers
- split workload
- inspect sample messages

### High Unacked

Check:

- prefetch count
- consumer processing time
- thread deadlocks
- downstream timeouts
- application memory

Actions:

- lower prefetch
- restart stuck workers
- add timeouts
- improve graceful shutdown

### High Redeliveries

Check:

- consumer crash loop
- poison messages
- nack/requeue loop
- deployment bug

Actions:

- stop consumers if causing damage
- route bad messages to DLQ
- deploy fix
- replay carefully

## 7.12 Management UI

Use the UI for inspection, not as the sole automation plane.

Important views:

- Overview
- Connections
- Channels
- Exchanges
- Queues
- Admin

Production caution:

- restrict access
- audit admin usage
- do not manually purge queues unless incident process approves
- use infrastructure-as-code for stable topology

## 7.13 Kubernetes Operations

Kubernetes concerns:

- persistent volumes
- stable network identity
- pod disruption budgets
- anti-affinity across nodes/zones
- readiness/liveness probes
- graceful termination
- resource requests and limits
- secret management

Consumer deployment:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: email-worker
spec:
  replicas: 3
  selector:
    matchLabels:
      app: email-worker
  template:
    metadata:
      labels:
        app: email-worker
    spec:
      terminationGracePeriodSeconds: 60
      containers:
        - name: worker
          image: example/email-worker:1.0.0
          env:
            - name: RABBITMQ_URL
              valueFrom:
                secretKeyRef:
                  name: rabbitmq
                  key: url
```

## 7.14 Production Runbook Example

Incident:

```text
payment.capture.queue oldest message age > 2 minutes
```

Runbook:

1. Check consumer count.
2. Check payment provider status.
3. Check recent deployments.
4. Check DLQ and redelivery rate.
5. Scale workers only if provider and DB can handle it.
6. If consumer bug, pause deployment and rollback.
7. If provider outage, allow queue to buffer and communicate delay.
8. After recovery, monitor drain rate.
9. Record incident timeline.

## 7.15 Best Practices

- Use unique service users.
- Enforce least privilege.
- Use TLS in production.
- Monitor message age, not just depth.
- Alert on DLQ messages.
- Include correlation ids in every message.
- Export definitions.
- Test restore and failover.
- Use policies for operational settings.
- Create runbooks for critical queues.

## 7.16 Anti-Patterns

- shared admin credentials in app configs
- exposing management UI publicly
- no queue owner
- no DLQ alert
- dashboards with only node CPU
- purging queues during incidents without analysis
- ignoring redeliveries
- no graceful shutdown in consumers
- no tracing context across messages

## 7.17 Interview Questions

1. What RabbitMQ metrics matter most in production?
2. How do you secure RabbitMQ?
3. What does high unacked count mean?
4. What alert would you create for a critical queue?
5. How do you debug a growing queue?
6. How do you operate RabbitMQ in Kubernetes?
7. Why is oldest message age often better than queue depth?

## 7.18 Practical Exercises

1. Create service-specific users and permissions.
2. Add correlation id to producer and consumer logs.
3. Create a DLQ alert rule.
4. Simulate consumer outage and observe dashboard behavior.
5. Write a runbook for `email.queue` backlog.

## 7.19 Key Takeaways

- Production RabbitMQ needs security, observability, and runbooks.
- Queue metrics are business workflow signals.
- DLQs require ownership.
- Async systems need correlation IDs and tracing.
- Operational discipline matters as much as broker configuration.
