# Quick Start

## 1. Requirements

- Docker Desktop or a local RabbitMQ installation
- Python 3.10 or newer

## 2. Start RabbitMQ

From the repository root:

```bash
docker compose up -d
docker compose ps
```

Open the management UI at <http://localhost:15672>.

Development credentials:

```text
username: app
password: app-password
```

AMQP applications connect to port `5672`. The browser management UI uses
port `15672`.

## 3. Prepare Python

```bash
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

On Linux or macOS, activate with:

```bash
source .venv/bin/activate
```

## 4. Run the First Example

Start the consumer in terminal 1:

```bash
python code-examples/python/02_receive.py
```

Send messages from terminal 2:

```bash
python code-examples/python/01_send.py "Hello RabbitMQ"
python code-examples/python/01_send.py "Process order 101"
```

Stop the consumer with `Ctrl+C`.

## 5. Stop RabbitMQ

```bash
docker compose down
```

To remove RabbitMQ data too:

```bash
docker compose down -v
```

Do not use `down -v` when the stored messages or definitions are important.

## Common Setup Problems

| Problem | Check |
|---|---|
| Connection refused | Is `docker compose ps` showing a healthy container? |
| Authentication failed | Does `RABBITMQ_URL` contain the correct username and password? |
| Port already in use | Stop the other service or change the mapped host port |
| Consumer receives nothing | Producer and consumer must use the same vhost, exchange, queue, and binding |
| Messages disappear after restart | Check queue durability, message persistence, and publisher confirms |

