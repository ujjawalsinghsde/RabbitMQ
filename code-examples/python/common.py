"""Shared connection and topology helpers for the learning examples."""

import os

import pika


RABBITMQ_URL = os.getenv(
    "RABBITMQ_URL",
    "amqp://app:app-password@localhost:5672/learning",
)


def connect() -> pika.BlockingConnection:
    """Create a connection with practical development timeouts."""
    parameters = pika.URLParameters(RABBITMQ_URL)
    parameters.heartbeat = 30
    parameters.blocked_connection_timeout = 30
    parameters.connection_attempts = 5
    parameters.retry_delay = 2
    return pika.BlockingConnection(parameters)


def declare_reliable_order_topology(channel: pika.channel.Channel) -> None:
    """Declare the topology used by examples 07 and 08."""
    channel.exchange_declare(
        exchange="orders.commands",
        exchange_type="direct",
        durable=True,
    )
    channel.exchange_declare(
        exchange="orders.retry",
        exchange_type="direct",
        durable=True,
    )
    channel.exchange_declare(
        exchange="orders.dlx",
        exchange_type="direct",
        durable=True,
    )

    channel.queue_declare(
        queue="orders.process",
        durable=True,
        arguments={
            "x-queue-type": "quorum",
            "x-dead-letter-exchange": "orders.dlx",
            "x-dead-letter-routing-key": "orders.failed",
        },
    )
    channel.queue_bind(
        queue="orders.process",
        exchange="orders.commands",
        routing_key="orders.process",
    )

    channel.queue_declare(
        queue="orders.retry.10s",
        durable=True,
        arguments={
            "x-queue-type": "quorum",
            "x-message-ttl": 10_000,
            "x-dead-letter-exchange": "orders.commands",
            "x-dead-letter-routing-key": "orders.process",
        },
    )
    channel.queue_bind(
        queue="orders.retry.10s",
        exchange="orders.retry",
        routing_key="orders.retry",
    )

    channel.queue_declare(
        queue="orders.failed",
        durable=True,
        arguments={"x-queue-type": "quorum"},
    )
    channel.queue_bind(
        queue="orders.failed",
        exchange="orders.dlx",
        routing_key="orders.failed",
    )

