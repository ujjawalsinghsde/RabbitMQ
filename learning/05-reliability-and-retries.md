# Reliability, Retries, and Idempotency

## Understanding Two Different Confirmations

This confuses almost everyone at first, so let's be crystal clear: **Publisher confirms and consumer acknowledgements are completely different mechanisms that solve different problems.**

### Publisher Confirms (Producer → RabbitMQ)

**Question answered:** "Did RabbitMQ safely receive and store my message?"

```text
Producer --[publish message]--> RabbitMQ --[confirm: "yes, I have it"]--> Producer ✓
```

**What it does NOT tell you:**
- Whether any consumer received the message
- Whether any consumer processed the message successfully
- Whether the message was routed to a queue
- What happened to the message after RabbitMQ stored it

**Example:**
```python
channel.confirm_delivery()  # Enable publisher confirms
try:
    channel.basic_publish(exchange='orders', routing_key='order.created', body=message)
    # If we reach here, RabbitMQ confirmed it has the message
    print("RabbitMQ confirmed receipt")
except pika.exceptions.UnroutableError:
    print("Message couldn't be routed to any queue!")
except pika.exceptions.NackError:
    print("RabbitMQ explicitly rejected the message!")
```

### Consumer Acknowledgements (Consumer → RabbitMQ)

**Question answered:** "Did the consumer successfully process this message?"

```text
RabbitMQ --[deliver message]--> Consumer --[ack: "yes, I processed it"]--> RabbitMQ ✓
```

**What it does NOT tell you:**
- Whether the producer's publish succeeded
- Whether RabbitMQ crashed before persisting
- Whether the message was safely replicated

**Example:**
```python
def callback(ch, method, properties, body):
    try:
        process_order(body)
        update_database()
        ch.basic_ack(delivery_tag=method.delivery_tag)
        # RabbitMQ now knows this consumer processed successfully
    except Exception:
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
```

### The Complete Picture

```text
[Producer] 
    ↓ publish
[RabbitMQ]
    ↓ publisher confirm tells Producer "I have it"
[RabbitMQ stores message]
    ↓ delivery
[Consumer]
    ↓ consumer ack tells RabbitMQ "I processed it"
[RabbitMQ deletes message]
```

**Key insight:** A publisher confirm tells you RabbitMQ accepted the message. A consumer ack tells you someone processed it. You need both for end-to-end reliability.


## Reliable Publishing: Complete Checklist

If you're publishing important messages (orders, payments, critical notifications), follow this checklist. Each item addresses a specific failure mode.

### 1. Declare Durable Topology

**What:** Exchanges and queues survive RabbitMQ restart.

```python
# Durable exchange
channel.exchange_declare(
    exchange='orders',
    exchange_type='topic',
    durable=True  # ✓ Survives restart
)

# Durable queue
channel.queue_declare(
    queue='payment.commands',
    durable=True  # ✓ Survives restart
)
```

**Why:** If RabbitMQ restarts and your topology isn't durable, queues and exchanges disappear. Messages have nowhere to go.

**Failure mode prevented:** RabbitMQ restart causing topology loss.

### 2. Publish Persistent Messages

**What:** Ask RabbitMQ to write messages to disk.

```python
channel.basic_publish(
    exchange='orders',
    routing_key='order.created',
    body=message_body,
    properties=pika.BasicProperties(
        delivery_mode=2  # 2 = persistent, 1 = transient
    )
)
```

**Why:** Non-persistent messages live only in memory. If RabbitMQ crashes before flushing to disk, they're lost.

**Failure mode prevented:** RabbitMQ crash causing message loss.

**Trade-off:** Persistence is slower (disk I/O). Acceptable for important business data.

### 3. Enable Publisher Confirms

**What:** RabbitMQ acknowledges that it has safely accepted each message.

```python
channel.confirm_delivery()  # Enable confirms

try:
    channel.basic_publish(...)
    # Success - RabbitMQ confirmed
except Exception as e:
    # Failed - handle it (log, retry, alert)
    handle_publish_failure(e)
```

**Why:** Without confirms, `publish()` might return success even though the message never reached RabbitMQ (network issue, internal error).

**Failure mode prevented:** Silent message loss during network issues or RabbitMQ internal errors.

**Trade-off:** Adds latency (wait for confirmation). Worth it for critical messages.

### 4. Handle Publish Failure and Timeout

**What:** Explicitly handle when publishes fail or time out.

```python
import time

def publish_with_retry(channel, exchange, routing_key, body, max_retries=3):
    for attempt in range(max_retries):
        try:
            channel.basic_publish(
                exchange=exchange,
                routing_key=routing_key,
                body=body,
                properties=pika.BasicProperties(delivery_mode=2)
            )
            return True  # Success
        except Exception as e:
            print(f"Publish attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # Exponential backoff
            else:
                # Max retries exceeded - store locally, alert, log
                store_failed_publish(body)
                alert_operations()
                return False
```

**Why:** Temporary network issues, RabbitMQ overload, or connection drops can cause publish failures.

**Failure mode prevented:** Losing messages due to temporary issues.

### 5. Use `mandatory=True` or Alternate Exchange

**What:** Detect when messages can't be routed to any queue.

```python
# Option 1: mandatory flag (raises exception if unroutable)
channel.basic_publish(
    exchange='orders',
    routing_key='unknown.key',  # No queue bound to this
    body=message,
    mandatory=True  # ✓ Will raise exception if unroutable
)

# Option 2: Alternate exchange (catches unroutable messages)
channel.exchange_declare(
    exchange='orders',
    exchange_type='topic',
    durable=True,
    arguments={'alternate-exchange': 'unrouted.orders'}
)
```

**Why:** By default, if a message can't be routed to any queue, it's silently discarded. You might not notice for weeks.

**Failure mode prevented:** Messages silently lost due to routing misconfiguration.

**Example scenario prevented:**
```text
1. Developer types routing_key='order.create' (typo - should be 'order.created')
2. No queue is bound to 'order.create'
3. Without mandatory or alternate exchange: message vanishes silently ❌
4. With protection: Exception raised or captured in alternate exchange ✓
```

### 6. Use Replicated Queues (Quorum Queues)

**What:** Messages are copied to multiple RabbitMQ nodes in a cluster.

```python
channel.queue_declare(
    queue='payment.commands',
    durable=True,
    arguments={'x-queue-type': 'quorum'}  # ✓ Replicated
)
```

**Why:** If one RabbitMQ server dies completely (hardware failure), queues on that node are lost unless replicated.

**Failure mode prevented:** Data loss from complete node failure.

**Requirement:** Need a RabbitMQ cluster (3+ nodes typical).

**Trade-off:** Slower (replication takes time), but necessary for critical data.

### Putting It All Together: Maximum Reliability

```python
# Setup (once)
channel.exchange_declare(
    exchange='orders',
    exchange_type='topic',
    durable=True,
    arguments={'alternate-exchange': 'unrouted.orders'}
)

channel.queue_declare(
    queue='payment.commands',
    durable=True,
    arguments={'x-queue-type': 'quorum'}
)

channel.queue_bind(
    exchange='orders',
    queue='payment.commands',
    routing_key='order.created'
)

# Publishing (every message)
channel.confirm_delivery()  # Enable confirms

try:
    channel.basic_publish(
        exchange='orders',
        routing_key='order.created',
        body=message_json,
        properties=pika.BasicProperties(
            delivery_mode=2,  # Persistent
            content_type='application/json'
        ),
        mandatory=True
    )
    print("✓ Published and confirmed")
except pika.exceptions.UnroutableError:
    print("❌ Message couldn't be routed - check bindings!")
    alert_operations()
except Exception as e:
    print(f"❌ Publish failed: {e}")
    retry_or_store_locally()
```

### The Ambiguous Result Problem

Even with all protections, one scenario remains tricky:

```text
1. Producer publishes message
2. RabbitMQ receives and stores message successfully
3. RabbitMQ tries to send confirmation back to producer
4. Network fails before confirmation arrives ❌
5. Producer doesn't know if message was accepted or lost
```

**What should the producer do?**
- Retry? Risk duplicate message.
- Don't retry? Risk lost message.

**Solution:** Accept that duplicates are possible. Make consumers idempotent (covered next).


## At-Least-Once Delivery: The Reality of Distributed Systems

Most RabbitMQ systems implement **at-least-once** delivery semantics. Understanding what this means is crucial.

### What "At-Least-Once" Means

**Guarantee:** A message will be delivered one or more times. It will not be silently lost.

**No guarantee:** It won't be delivered exactly once. Duplicates are possible.

### How Duplicates Happen

**Scenario 1: Network Failure During Ack**
```text
1. Consumer receives message
2. Consumer updates database (✓ successful)
3. Consumer sends acknowledgement to RabbitMQ
4. Network fails before RabbitMQ receives the ack ❌
5. RabbitMQ thinks message wasn't processed
6. RabbitMQ redelivers message to same or different consumer
7. Database update happens again → duplicate processing ❌
```

**Scenario 2: Consumer Crash After Processing**
```text
1. Consumer receives message
2. Consumer sends email (✓ email sent)
3. Consumer crashes before sending ack ❌
4. RabbitMQ redelivers message
5. Email is sent again → customer gets duplicate email ❌
```

**Scenario 3: Publisher Retry on Ambiguous Result**
```text
1. Producer publishes message
2. RabbitMQ stores message (✓)
3. Network issue prevents confirmation from reaching producer ❌
4. Producer retries (because it didn't get confirmation)
5. RabbitMQ now has the message twice → duplicate ❌
```

### Why Not Exactly-Once?

Distributed systems have fundamental limitations. Achieving true exactly-once processing across network boundaries requires:
- Distributed transactions (slow, complex, fragile)
- Coordinated two-phase commits
- Additional infrastructure (transaction coordinators)

RabbitMQ chose a pragmatic approach: guarantee no message loss (at-least-once), and let applications handle duplicates (idempotency).

### The Solution: Idempotent Consumers

Make your consumers safe to run multiple times with the same message. This is covered in the next section.


## Idempotent Consumer: Making Duplicates Safe

**Idempotency** means processing a message multiple times produces the same result as processing it once.

### The Goal

```text
Process message once: Account balance = $100
Process same message twice: Account balance = $100 (not $200!) ✓
```

### Strategy 1: Store Message ID (Deduplication Table)

Track which messages you've already processed using the message's unique ID.

```python
def process_payment(ch, method, properties, body):
    message = json.loads(body)
    message_id = message['message_id']
    
    # Check if already processed
    if already_processed(message_id):
        print(f"Duplicate message {message_id}, skipping")
        ch.basic_ack(delivery_tag=method.delivery_tag)
        return
    
    try:
        # Process payment
        charge_credit_card(message['amount'])
        
        # Mark as processed (in same transaction as business logic)
        mark_processed(message_id)
        
        ch.basic_ack(delivery_tag=method.delivery_tag)
    except Exception as e:
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

def already_processed(message_id):
    # Database table: processed_messages (message_id PRIMARY KEY)
    result = db.execute("SELECT 1 FROM processed_messages WHERE message_id = %s", [message_id])
    return result.rowcount > 0

def mark_processed(message_id):
    # Insert into deduplication table
    db.execute("INSERT INTO processed_messages (message_id, processed_at) VALUES (%s, NOW())", [message_id])
    db.commit()
```

**Database schema:**
```sql
CREATE TABLE processed_messages (
    message_id VARCHAR(255) PRIMARY KEY,
    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Optional: Add TTL cleanup for old entries
CREATE INDEX idx_processed_at ON processed_messages(processed_at);
```

**Critical:** The business logic and `mark_processed()` must be in **the same database transaction**:

```python
def process_payment(message):
    with db.transaction():  # Single atomic transaction
        # Business logic
        db.execute("UPDATE accounts SET balance = balance - %s WHERE id = %s", 
                   [amount, account_id])
        
        # Mark processed
        db.execute("INSERT INTO processed_messages (message_id) VALUES (%s)", 
                   [message_id])
    # Both succeed or both fail together ✓
```

### Strategy 2: Use Business Keys

Instead of a generic message_id, use business-level uniqueness.

**Example 1: Order Processing**
```python
def process_order(message):
    order_id = message['order_id']
    
    # Database constraint ensures one order can only be processed once
    try:
        db.execute("""
            INSERT INTO processed_orders (order_id, processed_at)
            VALUES (%s, NOW())
        """, [order_id])
        
        # Process the order
        charge_payment(order_id)
        reserve_inventory(order_id)
        
        db.commit()
    except IntegrityError:  # Duplicate order_id
        print(f"Order {order_id} already processed")
        db.rollback()
```

**Database schema:**
```sql
CREATE TABLE processed_orders (
    order_id VARCHAR(255) PRIMARY KEY,
    processed_at TIMESTAMP,
    amount DECIMAL(10,2)
);
```

**Example 2: Composite Key**

For operations that can happen multiple times but not duplicates:

```python
# Business key: order_id + operation_type
key = f"{order_id}:{operation}"  # e.g., "ORD-123:payment_charged"

db.execute("""
    INSERT INTO order_operations (order_id, operation, processed_at)
    VALUES (%s, %s, NOW())
""", [order_id, operation])
```

### Strategy 3: Conditional State Transitions

Make operations conditional on current state.

```python
# Idempotent: Only update if current state allows it
result = db.execute("""
    UPDATE orders
    SET status = 'paid', paid_at = NOW()
    WHERE order_id = %s AND status = 'pending'
""", [order_id])

if result.rowcount == 0:
    print(f"Order {order_id} already paid or doesn't exist")
    # This is fine - message is duplicate or order is in wrong state
```

**State machine example:**
```python
# Valid transitions
TRANSITIONS = {
    'pending': ['paid', 'cancelled'],
    'paid': ['shipped', 'refunded'],
    'shipped': ['delivered'],
    # 'paid' cannot transition to 'paid' again
}

def update_order_status(order_id, new_status):
    current_status = get_current_status(order_id)
    
    if new_status not in TRANSITIONS.get(current_status, []):
        print(f"Invalid transition: {current_status} → {new_status}")
        return False  # Idempotent: duplicate has no effect
    
    db.execute("""
        UPDATE orders SET status = %s 
        WHERE order_id = %s AND status = %s
    """, [new_status, order_id, current_status])
```

### Strategy 4: External Idempotency Keys (APIs)

When calling external APIs (payment processors, email services), use their idempotency features.

**Example: Stripe Payments**
```python
import stripe

message_id = message['message_id']

# Stripe uses idempotency_key to deduplicate requests
stripe.PaymentIntent.create(
    amount=1000,
    currency='usd',
    idempotency_key=message_id  # ✓ Duplicate calls are safe
)
```

If the same `idempotency_key` is used twice, Stripe returns the result from the first call instead of charging twice.

### Strategy 5: Naturally Idempotent Operations

Some operations are inherently idempotent—design toward these when possible.

**Idempotent examples:**
```python
# Setting a value (not incrementing)
UPDATE users SET email = 'new@example.com' WHERE user_id = 123

# Upserting (INSERT ... ON CONFLICT UPDATE)
INSERT INTO user_settings (user_id, theme) VALUES (123, 'dark')
ON CONFLICT (user_id) DO UPDATE SET theme = 'dark'

# Adding to a set (not a count)
db.sadd(f"user:{user_id}:tags", "premium")

# Absolute timestamps, not relative times
UPDATE orders SET cancelled_at = '2026-06-07T10:30:00Z' WHERE order_id = 'ORD-123'
```

**Non-idempotent examples (avoid or protect):**
```python
# Incrementing ❌
UPDATE accounts SET balance = balance + 100 WHERE account_id = 123

# Appending to array without deduplication ❌
UPDATE users SET login_history = array_append(login_history, NOW())

# Sending email without deduplication ❌
send_email(user_email, "Welcome!")
```

### Real-World Pattern: Transaction + Deduplication

```python
def handle_order_payment(message):
    order_id = message['order_id']
    message_id = message['message_id']
    amount = message['amount']
    
    with db.transaction():
        # 1. Check for duplicate
        if db.exists("SELECT 1 FROM processed_messages WHERE message_id = %s", [message_id]):
            print("Duplicate, skipping")
            return
        
        # 2. Business logic
        db.execute("""
            INSERT INTO payments (order_id, amount, created_at)
            VALUES (%s, %s, NOW())
        """, [order_id, amount])
        
        db.execute("""
            UPDATE orders SET status = 'paid'
            WHERE order_id = %s AND status = 'pending'
        """, [order_id])
        
        # 3. Mark as processed
        db.execute("""
            INSERT INTO processed_messages (message_id, processed_at)
            VALUES (%s, NOW())
        """, [message_id])
        
        # Everything succeeds or fails atomically
    
    # 4. Send external notifications (outside transaction, with idempotency)
    send_confirmation_email(order_id, idempotency_key=message_id)
```

### Cleanup: Don't Keep Deduplication Records Forever

```python
# Periodic cleanup job (cron/scheduled task)
def cleanup_old_processed_messages():
    # Keep records for 30 days (adjust based on your duplicate window)
    db.execute("""
        DELETE FROM processed_messages
        WHERE processed_at < NOW() - INTERVAL '30 days'
    """)
```

### The Bottom Line

**Accept that duplicates will happen** in distributed systems. **Make your consumers idempotent** so duplicates are harmless.

Formula for reliability:
```text
At-least-once delivery + Idempotent consumers = Effectively-once outcome ✓
```


## Retry Classification

| Failure | Example | Action |
|---|---|---|
| Transient | timeout, temporary 503 | Retry with backoff |
| Permanent | invalid schema, missing required field | Dead-letter immediately |
| Business | card declined, stock unavailable | Record business result; usually do not technical-retry |
| Unknown | unexpected exception | Limited retry, alert, then DLQ |


## Retry Architecture

```text
main queue
   | transient failure
   v
retry queue (TTL)
   | message expires
   v
main exchange -> main queue

After max attempts -> dead-letter exchange -> DLQ
```

Use increasing delays such as 10 seconds, 1 minute, and 5 minutes. Add jitter when many messages might retry together. Always cap attempts.


## Dead-Letter Queue

A DLQ is not a solution by itself. It needs:

- alerting on new messages
- enough context to diagnose the failure
- a documented replay process
- access control
- retention or cleanup rules
- protection from blindly replaying poison messages

Prefer RabbitMQ policies for DLX and TTL configuration because operators can change policies without redeploying every application.


## Transactional Outbox

The dual-write problem:

```text
Database commit succeeds + RabbitMQ publish fails = inconsistent system
```

With an outbox, the application writes business data and an outbox row in one database transaction. A separate publisher reads unsent rows, publishes with confirms, and marks them sent. Duplicate publishing remains possible, so consumers still need idempotency.


## Exactly Once

RabbitMQ does not provide automatic end-to-end exactly-once business processing. Aim for:

```text
at-least-once delivery + idempotent consumer = effectively-once outcome
```

