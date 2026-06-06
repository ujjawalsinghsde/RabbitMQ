# Exchanges and Routing

## Understanding Exchanges First

When you're new to RabbitMQ, you might wonder: "Why can't I just send messages directly to queues? Why this exchange thing?"

**The answer:** Exchanges provide **flexible routing without changing your code**. 

Imagine if producers had to know the exact queue names of every consumer. When you add a new consumer (like a new analytics service), you'd have to update and redeploy the producer code. With exchanges, you just add a new queue binding—no code changes needed.

**Think of exchanges like:** A smart mail sorting center with routing rules. You just send mail to the sorting center; the rules determine where it goes. Change the rules, not the senders.


## Default Exchange

The **default exchange** is a special exchange with an empty name: `""`. It's a shortcut for beginners.

### How It Works

Every queue you create is automatically bound to the default exchange using the queue name as the routing key.

```python
# Declare a queue named "tasks"
channel.queue_declare(queue='tasks')

# Publish to the default exchange
channel.basic_publish(
    exchange="",           # Empty string = default exchange
    routing_key="tasks",   # This must match the queue name
    body=b"resize image",
)
```

This message goes directly to the "tasks" queue.

### When to Use It

- Quick prototypes and learning
- Simple point-to-point messaging (one producer → one queue → one consumer type)
- Very small projects

### When NOT to Use It

- Production systems with multiple consumers
- When you want flexible routing
- When you might add new consumers later without changing producers
- Any system that will grow and evolve

**Best practice:** Use named exchanges for any real project. The default exchange is training wheels.


## Direct Exchange

A **direct exchange** delivers messages to queues where the **binding key exactly matches the routing key**.

### How It Works

```text
Producer publishes with routing_key="payment"
                            |
                            v
                    direct exchange "commands"
                       /              \
        binding_key="payment"     binding_key="inventory"
                    /                      \
                   v                        v
          "payment.queue"           "inventory.queue"
```

Message goes ONLY to "payment.queue" because routing key matches the binding key exactly.

### Practical Example: Command Routing

```python
# Setup
channel.exchange_declare(exchange='commands', exchange_type='direct')

channel.queue_declare(queue='payment.commands')
channel.queue_bind(exchange='commands', queue='payment.commands', routing_key='payment')

channel.queue_declare(queue='inventory.commands')
channel.queue_bind(exchange='commands', queue='inventory.commands', routing_key='inventory')

# Publishing
channel.basic_publish(
    exchange='commands',
    routing_key='payment',  # Goes ONLY to payment.commands
    body='{"action": "charge", "amount": 99.99}'
)
```

### Multiple Queues, Same Routing Key

You can bind multiple queues with the same routing key:

```text
direct exchange "logs"
        |
routing_key="error"
       / \
      /   \
     v     v
 "email.errors"   "disk.errors"
```

Both queues receive messages with routing_key="error". This is useful for:
- Multiple services handling the same command type
- Separate logging destinations
- Different processing strategies for the same event

### When to Use Direct Exchanges

✅ Routing commands to specific services (payment commands, inventory commands)
✅ Log severity routing (error logs to error queue, info logs to info queue)
✅ Task distribution by category (high-priority tasks, low-priority tasks)
✅ Simple, predictable routing rules

❌ Not great when you need pattern matching or wildcards


## Fanout Exchange

A **fanout exchange** is the simplest type: it broadcasts every message to every bound queue. It completely ignores the routing key.

### How It Works

```text
           Producer publishes
                 |
                 v
          fanout exchange "releases"
           /      |      \
          /       |       \
         v        v        v
    queue1    queue2    queue3
```

All three queues get a copy of every message.

### Practical Example: Event Broadcasting

```python
# Setup
channel.exchange_declare(exchange='user.events', exchange_type='fanout')

# Three different services each create their own queue
channel.queue_declare(queue='email.user.events')
channel.queue_bind(exchange='user.events', queue='email.user.events')

channel.queue_declare(queue='analytics.user.events')
channel.queue_bind(exchange='user.events', queue='analytics.user.events')

channel.queue_declare(queue='audit.user.events')
channel.queue_bind(exchange='user.events', queue='audit.user.events')

# Publishing
channel.basic_publish(
    exchange='user.events',
    routing_key='',  # Ignored by fanout exchanges
    body='{"event": "user.registered", "user_id": "U123"}'
)
```

All three queues (email, analytics, audit) receive this message.

### Important: Each Service Needs Its Own Queue

❌ **Wrong approach:**
```text
fanout exchange → single shared queue → 3 competing consumers
```
Result: Only ONE consumer gets each message (they compete for work).

✅ **Correct approach:**
```text
fanout exchange → queue1 → email service
                → queue2 → analytics service  
                → queue3 → audit service
```
Result: Each service gets a copy of every message.

### Real-World Examples

**1. Application Release Notifications**
```text
"releases" fanout exchange
    → email.release.queue (send emails to admins)
    → cache.release.queue (invalidate caches)
    → audit.release.queue (log release for compliance)
```

**2. User Registration**
```text
"user.registered" fanout exchange
    → welcome.email.queue (send welcome email)
    → crm.sync.queue (create CRM record)
    → analytics.queue (track signup metrics)
    → gift.queue (send new user coupon)
```

### When to Use Fanout Exchanges

✅ Broadcasting announcements (system maintenance, new features)
✅ Real-time updates to multiple dashboards
✅ One event needs to trigger multiple independent actions
✅ When you might add more listeners later without changing the publisher

### When NOT to Use Fanout

❌ When different messages should go to different queues (use topic or direct instead)
❌ When you need only one consumer to process each message (use a single queue with competing consumers)

### Key Insight

With fanout exchanges, **adding a new consumer is just:**
1. Create a new queue
2. Bind it to the existing exchange
3. No changes to the publisher
4. No changes to other consumers

This is loose coupling at its finest.


## Topic Exchange

**Topic exchanges** are the most flexible and commonly used in production. They match routing keys using wildcard patterns.

### Pattern Matching Rules

- `*` (star) matches **exactly one word**
- `#` (hash) matches **zero or more words**
- Words are separated by dots (`.`)

### Understanding Through Examples

| Routing Key | Binding Pattern | Match? |
|-------------|----------------|--------|
| `order.created` | `order.*` | ✅ Yes |
| `order.eu.created` | `order.*` | ❌ No (too many words) |
| `order.eu.created` | `order.#` | ✅ Yes |
| `order.created` | `order.#` | ✅ Yes |
| `payment.created` | `order.#` | ❌ No (doesn't start with "order") |
| `payment.failed` | `*.failed` | ✅ Yes |
| `payment.card.failed` | `*.failed` | ❌ No (too many words) |
| `payment.card.failed` | `payment.#.failed` | ✅ Yes |
| `payment.failed` | `payment.#.failed` | ✅ Yes (# matches zero words) |
| `notification.email.sent` | `notification.*.sent` | ✅ Yes |
| `notification.sms.sent` | `notification.*.sent` | ✅ Yes |

### Practical Example 1: Event System

```python
# Setup topic exchange
channel.exchange_declare(exchange='events', exchange_type='topic')

# Payment service cares about ALL payment events
channel.queue_declare(queue='payment.service.queue')
channel.queue_bind(
    exchange='events',
    queue='payment.service.queue',
    routing_key='payment.#'  # Matches payment.created, payment.failed, payment.refunded
)

# Email service cares about ANY failures
channel.queue_declare(queue='email.failures.queue')
channel.queue_bind(
    exchange='events',
    queue='email.failures.queue',
    routing_key='*.failed'  # Matches payment.failed, order.failed, etc.
)

# Audit service cares about EVERYTHING
channel.queue_declare(queue='audit.all.queue')
channel.queue_bind(
    exchange='events',
    queue='audit.all.queue',
    routing_key='#'  # Matches absolutely everything
)

# Publishing different events
channel.basic_publish(exchange='events', routing_key='payment.created', body='...')
# Goes to: payment.service.queue, audit.all.queue

channel.basic_publish(exchange='events', routing_key='payment.failed', body='...')
# Goes to: payment.service.queue, email.failures.queue, audit.all.queue

channel.basic_publish(exchange='events', routing_key='order.failed', body='...')
# Goes to: email.failures.queue, audit.all.queue
```

### Practical Example 2: Multi-Region, Multi-Environment Logs

```python
# Routing key structure: <environment>.<region>.<level>
# Examples: prod.us.error, staging.eu.info, dev.local.debug

# Setup
channel.exchange_declare(exchange='logs', exchange_type='topic')

# Queue 1: ALL production errors, any region
channel.queue_bind(exchange='logs', queue='prod.errors', routing_key='prod.*.error')

# Queue 2: ALL errors from EU region, any environment
channel.queue_bind(exchange='logs', queue='eu.errors', routing_key='*.eu.error')

# Queue 3: Everything from production
channel.queue_bind(exchange='logs', queue='prod.all', routing_key='prod.#')

# Publishing
channel.basic_publish(exchange='logs', routing_key='prod.us.error', body='...')
# Goes to: prod.errors, prod.all

channel.basic_publish(exchange='logs', routing_key='prod.eu.error', body='...')
# Goes to: prod.errors, eu.errors, prod.all

channel.basic_publish(exchange='logs', routing_key='staging.eu.error', body='...')
# Goes to: eu.errors
```

### Practical Example 3: Order Events by Geography

```python
# Routing key structure: order.<country>.<action>
# Examples: order.us.created, order.de.shipped, order.jp.cancelled

# US fulfillment center only cares about US orders
channel.queue_bind(exchange='orders', queue='us.fulfillment', routing_key='order.us.#')

# EU fulfillment handles multiple countries
channel.queue_bind(exchange='orders', queue='eu.fulfillment', routing_key='order.de.#')
channel.queue_bind(exchange='orders', queue='eu.fulfillment', routing_key='order.fr.#')
channel.queue_bind(exchange='orders', queue='eu.fulfillment', routing_key='order.uk.#')

# Global analytics wants all orders everywhere
channel.queue_bind(exchange='orders', queue='analytics', routing_key='order.#')

# Cancellation team only cares about cancelled orders
channel.queue_bind(exchange='orders', queue='cancellations', routing_key='order.*.cancelled')
```

### Designing Good Routing Keys

✅ **Good hierarchy examples:**
```text
<domain>.<entity>.<action>
    order.created
    payment.refunded
    user.deleted

<domain>.<region>.<severity>
    app.us-east.error
    app.eu-west.info

<service>.<resource>.<operation>
    api.user.read
    api.order.write
```

❌ **Bad examples:**
```text
msg1                    (meaningless)
2026-06-07-order-123   (includes timestamps/IDs that change)
createOrder            (not hierarchical)
a.b.c.d.e.f.g.h       (too deep, hard to understand)
```

### Common Pattern: Three-Part Routing Keys

Many systems use `<category>.<subcategory>.<action>`:

```text
order.us.created
order.us.cancelled  
order.eu.created
payment.card.charged
payment.card.failed
user.admin.registered
user.customer.registered
```

This structure works well with topic patterns:
- `order.#` = all orders
- `*.*.created` = all creation events
- `order.us.*` = all US orders
- `payment.card.#` = all card operations

### When to Use Topic Exchanges

✅ **Best for:**
- Domain events in microservices
- Multi-tenant or multi-region systems
- Systems where new consumers might subscribe to subsets of events
- Flexible filtering without changing publishers

✅ **Examples:**
- E-commerce platform publishing order/payment/shipping events
- Logging system routing by environment, service, and severity
- IoT platform routing device events by location and type

### Topic Exchange vs. Direct Exchange

**Use topic when:** You need flexibility, pattern matching, or might add new consumers with specific filtering needs.

**Use direct when:** You need exact, simple routing with no patterns (like routing specific commands to specific workers).

### Pro Tip: Start Broad, Filter Narrow

When designing routing keys, start with broad categories and get more specific:

```text
payment.charged              → Good
payment.card.charged         → Better (can filter by card vs bank transfer)
payment.card.visa.charged    → Maybe too specific?
```

Find the right level of granularity for your use case. Too broad and you can't filter; too specific and your routing keys become a mess.


## Headers Exchange

A **headers exchange** routes messages based on message headers instead of the routing key. It's more complex but occasionally useful for specific scenarios.

### How It Works

Instead of looking at the routing key, the exchange examines the message headers (arbitrary key-value pairs in the message properties).

### Binding Configuration

When creating a binding, you specify:
- Header key-value pairs to match
- `x-match` argument: `all` or `any`

**`x-match=all`:** Message must have ALL specified headers matching
**`x-match=any`:** Message must have ANY ONE of the specified headers matching

### Practical Example

```python
# Declare headers exchange
channel.exchange_declare(exchange='tasks', exchange_type='headers')

# Bind queue with match requirements
channel.queue_declare(queue='image.processor')
channel.queue_bind(
    exchange='tasks',
    queue='image.processor',
    arguments={
        'x-match': 'all',
        'type': 'image',
        'format': 'jpg'
    }
)

channel.queue_declare(queue='video.processor')
channel.queue_bind(
    exchange='tasks',
    queue='video.processor',
    arguments={
        'x-match': 'all',
        'type': 'video',
        'priority': 'high'
    }
)

# Publishing with headers
headers = {'type': 'image', 'format': 'jpg', 'size': 'large'}
properties = pika.BasicProperties(headers=headers)

channel.basic_publish(
    exchange='tasks',
    routing_key='',  # Ignored by headers exchange
    body='process this image',
    properties=properties
)
# This goes to image.processor (matches type=image AND format=jpg)
```

### When to Use Headers Exchanges

✅ **Rare valid use cases:**
- When routing logic needs multiple independent dimensions (type AND priority AND region)
- When routing key patterns become too complex or cryptic
- When message attributes truly don't fit a hierarchical structure

❌ **Usually better alternatives:**
- Most of the time, topic exchanges with well-designed routing keys are simpler and more transparent
- Header matching adds operational complexity (harder to debug, harder to understand message flow)

### The Honest Truth

In 90% of systems, topic exchanges are clearer and easier to maintain. Header exchanges exist for edge cases, but be skeptical before using them.

## Alternate Exchange

An **alternate exchange** (AE) catches messages that couldn't be routed by the main exchange.

### The Problem It Solves

```text
Producer publishes message with routing_key="payment.created"
                    ↓
            exchange "events"
                    ↓
        No queues bound with "payment.created"
                    ↓
            Message is lost! ❌
```

Without an alternate exchange, unroutable messages just disappear silently. You might not realize for weeks that certain messages are never being processed.

### How Alternate Exchange Helps

```text
Producer publishes message with routing_key="payment.created"
                    ↓
            exchange "events"
                    ↓
        No queues bound with "payment.created"
                    ↓
        Route to alternate exchange
                    ↓
        "unrouted.messages" queue (for investigation)
```

### Practical Example

```python
# Declare alternate exchange first
channel.exchange_declare(exchange='unrouted.events', exchange_type='fanout')

# Declare queue to catch unrouted messages
channel.queue_declare(queue='unrouted.messages')
channel.queue_bind(exchange='unrouted.events', queue='unrouted.messages')

# Declare main exchange with alternate
channel.exchange_declare(
    exchange='events',
    exchange_type='topic',
    arguments={'alternate-exchange': 'unrouted.events'}
)

# Now, if a message can't be routed, it goes to unrouted.messages queue
```

### Alternate Exchange vs. Dead-Letter Exchange

These are different concepts that confuse people:

**Alternate Exchange:**
- Triggers when message **cannot be routed** to any queue from the exchange
- Problem: publisher misconfigured routing key, or no bindings exist
- Happens at **publish time**

**Dead-Letter Exchange:**
- Triggers when message **was in a queue** but got rejected, expired, or hit queue limits
- Problem: consumer rejected it, message got too old, queue is full
- Happens **after** the message was already in a queue

### When to Use Alternate Exchanges

✅ **Use for:**
- Detecting routing configuration errors
- Alerting when messages can't be delivered
- Development/staging environments to catch mistakes

❌ **Don't use for:**
- Normal error handling (use dead-letter exchanges)
- Expected routing scenarios

### Monitoring Tip

Set up alerts if the unrouted messages queue starts filling up. It usually means:
- Someone published with the wrong routing key
- Someone deleted a binding by mistake
- Configuration drift between environments


## Routing Design Tips

Let's pull together the best practices for designing your routing architecture:

### 1. Use Stable, Semantic Keys

✅ **Good:**
```text
order.created.v1
payment.charged.v1
user.registered.v1
```

❌ **Bad:**
```text
msg1
xyz123
order_created_20260607
```

**Why:** Semantic keys are self-documenting. Version numbers help with schema evolution. Random strings or timestamps make debugging a nightmare.

### 2. Don't Encode Sensitive Data in Routing Keys

❌ **Never:**
```text
payment.user-john-doe.card-4532-1234-5678-9010.charged
user.ssn-123-45-6789.registered
```

Routing keys appear in:
- RabbitMQ management UI (visible to operators)
- Log files
- Monitoring systems
- Tracing tools

**Keep sensitive data in the message body**, where it can be encrypted and access-controlled.

### 3. Don't Encode Random IDs in Routing Keys

❌ **Bad:**
```text
order.67fc5b0e-2b31-4dc1-9026-5be993abe068.created
```

**Why:** This breaks topic pattern matching. If every order has a unique UUID in the routing key, you can't use patterns like `order.*.created` to match all order creation events.

✅ **Good:** Put the ID in the message body, use generic routing key:
```text
Routing key: order.created
Message body: {"order_id": "67fc5b0e-...", "total": 99.99}
```

### 4. Give Each Service Its Own Queue for Events

For events (broadcasts), each consuming service needs its own queue:

✅ **Correct architecture:**
```text
"order.created" event
    → email.service.queue (Email Service consumes)
    → inventory.service.queue (Inventory Service consumes)
    → analytics.service.queue (Analytics Service consumes)
```

Each service gets every event and processes at its own pace.

❌ **Wrong architecture:**
```text
"order.created" event
    → shared.order.queue (all three services compete for messages)
```

With a shared queue, only ONE service gets each message. That's competing consumers, not event broadcast.

### 5. Commands: One Logical Owner

For commands (targeted work requests), use one queue:

✅ **Correct:**
```text
"send.email" command → email.commands.queue
Multiple email workers compete to process → horizontal scaling
```

### 6. Treat Exchange/Queue Names as API Contracts

Once you deploy these names to production:
- They're contracts between services
- Changing them breaks consumers
- Version them if you must change semantics
- Document them like you document REST APIs

### 7. Prefer Policies for Operational Settings

Instead of hard-coding queue settings in application code:

❌ **Hard-coded:**
```python
channel.queue_declare(
    queue='payments',
    arguments={
        'x-message-ttl': 3600000,
        'x-max-length': 10000,
        'x-dead-letter-exchange': 'dlx'
    }
)
```

✅ **Use RabbitMQ policies:**
```bash
# Operators can change this without redeploying apps
rabbitmqctl set_policy payments-policy "^payments$" \
  '{"message-ttl":3600000,"max-length":10000,"dead-letter-exchange":"dlx"}'
```

**Why:** Operators can tune TTL, queue length, and dead-letter settings without waiting for developers to redeploy code.

### 8. Document Your Routing Architecture

Create a document showing:
- What exchanges exist
- What queues exist  
- Who publishes what
- Who consumes what
- What routing keys mean

#### Example documentation:
##### Events Exchange

**Name:** `app.events`
**Type:** topic
**Purpose:** Domain events for inter-service communication

##### Routing Keys

- `order.created` - Published by Order Service when order is placed
- `order.shipped` - Published by Fulfillment Service when shipped
- `payment.charged` - Published by Payment Service after charge succeeds
- `payment.failed` - Published by Payment Service when charge fails

##### Consumers

- Inventory Service subscribes to `order.#`
- Email Service subscribes to `*.#` (all events)
- Analytics Service subscribes to `#` (everything)

This documentation saves countless hours of confusion and debugging.

