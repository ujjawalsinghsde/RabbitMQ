# RabbitMQ Commands Cheatsheet

Commands below assume the Docker Compose service in this repository.

## Docker

```bash
docker compose up -d
docker compose ps
docker compose logs -f rabbitmq
docker compose restart rabbitmq
docker compose down
```

Delete local broker data only when intentional:

```bash
docker compose down -v
```

## Health and Status

```bash
docker compose exec rabbitmq rabbitmq-diagnostics -q ping
docker compose exec rabbitmq rabbitmq-diagnostics status
docker compose exec rabbitmq rabbitmqctl cluster_status
docker compose exec rabbitmq rabbitmq-diagnostics check_running
docker compose exec rabbitmq rabbitmq-diagnostics check_local_alarms
```

## Inspect Runtime State

```bash
docker compose exec rabbitmq rabbitmqctl list_vhosts
docker compose exec rabbitmq rabbitmqctl list_users
docker compose exec rabbitmq rabbitmqctl list_exchanges -p learning name type durable
docker compose exec rabbitmq rabbitmqctl list_queues -p learning name type messages_ready messages_unacknowledged consumers
docker compose exec rabbitmq rabbitmqctl list_bindings -p learning
docker compose exec rabbitmq rabbitmqctl list_connections name user state channels
docker compose exec rabbitmq rabbitmqctl list_channels connection number consumer_count messages_unacknowledged
```

## Users, Vhosts, and Permissions

Use secrets instead of putting real production passwords in shell history.

```bash
docker compose exec rabbitmq rabbitmqctl add_vhost my-app
docker compose exec rabbitmq rabbitmqctl add_user my-user change-me
docker compose exec rabbitmq rabbitmqctl set_permissions -p my-app my-user ".*" ".*" ".*"
docker compose exec rabbitmq rabbitmqctl list_permissions -p my-app
```

The three permission regexes are configure, write, and read. Production regexes should be narrower than `.*`.

## Policies

List policies:

```bash
docker compose exec rabbitmq rabbitmqctl list_policies -p learning
```

Example DLX policy:

```bash
docker compose exec rabbitmq rabbitmqctl set_policy -p learning orders-dlx "^orders\." '{"dead-letter-exchange":"orders.dlx"}' --apply-to queues
```

Policies are usually better than hardcoded optional arguments for settings that operators may change.

## Definitions

```bash
docker compose exec rabbitmq rabbitmqctl export_definitions /tmp/definitions.json
docker compose cp rabbitmq:/tmp/definitions.json ./definitions.json
```

Definitions contain topology and users/permissions metadata, not queued message data. Treat exported definitions as sensitive.

## Management

- UI: <http://localhost:15672>
- AMQP: `localhost:5672`
- Development vhost: `learning`

Always verify commands against the documentation for the deployed RabbitMQ version before production use.

