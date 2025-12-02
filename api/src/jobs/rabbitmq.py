"""
RabbitMQ Consumer Infrastructure

Provides the base consumer class and connection management for processing
background jobs from RabbitMQ queues.
"""

import asyncio
import json
import logging
from abc import ABC, abstractmethod
from typing import Any

import aio_pika
from aio_pika import IncomingMessage, RobustConnection, RobustChannel
from aio_pika.pool import Pool

from src.config import get_settings

logger = logging.getLogger(__name__)


class RabbitMQConnection:
    """
    Manages RabbitMQ connection pool.

    Uses connection pooling for efficient resource usage across multiple consumers.
    """

    _instance: "RabbitMQConnection | None" = None
    _connection_pool: Pool | None = None
    _channel_pool: Pool | None = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def get_connection(self):
        """Get a connection context manager from the pool."""
        if self._connection_pool is None:
            raise RuntimeError("Connection pool not initialized. Call init_pools() first.")
        return self._connection_pool.acquire()

    def get_channel(self):
        """Get a channel context manager from the pool."""
        if self._channel_pool is None:
            raise RuntimeError("Channel pool not initialized. Call init_pools() first.")
        return self._channel_pool.acquire()

    async def init_pools(self) -> None:
        """Initialize connection and channel pools. Must be called before using the connection."""
        if self._connection_pool is not None:
            return  # Already initialized
        await self._init_pools()

    async def _init_pools(self) -> None:
        """Initialize connection and channel pools."""
        settings = get_settings()

        async def get_connection() -> RobustConnection:
            return await aio_pika.connect_robust(settings.rabbitmq_url)

        async def get_channel() -> RobustChannel:
            async with self._connection_pool.acquire() as connection:
                return await connection.channel()

        self._connection_pool = Pool(get_connection, max_size=2)
        self._channel_pool = Pool(get_channel, max_size=10)

        logger.info("RabbitMQ connection pools initialized")

    async def close(self) -> None:
        """Close all connections."""
        if self._channel_pool:
            await self._channel_pool.close()
        if self._connection_pool:
            await self._connection_pool.close()
        logger.info("RabbitMQ connections closed")


# Global connection manager
rabbitmq = RabbitMQConnection()


class BaseConsumer(ABC):
    """
    Base class for RabbitMQ consumers.

    Provides:
    - Automatic connection and channel management
    - Message acknowledgment handling
    - Error handling with dead letter queue support
    - Graceful shutdown
    """

    def __init__(
        self,
        queue_name: str,
        prefetch_count: int = 1,
        dead_letter_exchange: str | None = None,
    ):
        """
        Initialize consumer.

        Args:
            queue_name: Name of the queue to consume from
            prefetch_count: Number of messages to prefetch (QoS)
            dead_letter_exchange: Exchange for failed messages (poison queue)
        """
        self.queue_name = queue_name
        self.prefetch_count = prefetch_count
        self.dead_letter_exchange = dead_letter_exchange or f"{queue_name}-dlx"

        self._channel: RobustChannel | None = None
        self._queue: aio_pika.Queue | None = None
        self._running = False

    async def start(self) -> None:
        """Start consuming messages."""
        self._running = True

        # Initialize pools and get a dedicated connection for this consumer
        await rabbitmq.init_pools()
        # Store the context manager so it stays open
        self._connection_ctx = rabbitmq.get_connection()
        connection = await self._connection_ctx.__aenter__()
        self._channel = await connection.channel()
        await self._channel.set_qos(prefetch_count=self.prefetch_count)

        # Declare dead letter exchange
        dlx = await self._channel.declare_exchange(
            self.dead_letter_exchange,
            aio_pika.ExchangeType.DIRECT,
            durable=True,
        )

        # Declare dead letter queue
        dlq = await self._channel.declare_queue(
            f"{self.queue_name}-poison",
            durable=True,
        )
        await dlq.bind(dlx, routing_key=self.queue_name)

        # Declare main queue with dead letter routing
        self._queue = await self._channel.declare_queue(
            self.queue_name,
            durable=True,
            arguments={
                "x-dead-letter-exchange": self.dead_letter_exchange,
                "x-dead-letter-routing-key": self.queue_name,
            },
        )

        logger.info(f"Consumer started for queue: {self.queue_name}")

        # Start consuming
        await self._queue.consume(self._on_message)

    async def stop(self) -> None:
        """Stop consuming messages."""
        self._running = False
        if self._channel:
            await self._channel.close()
        if hasattr(self, '_connection_ctx') and self._connection_ctx:
            await self._connection_ctx.__aexit__(None, None, None)
        logger.info(f"Consumer stopped for queue: {self.queue_name}")

    async def _on_message(self, message: IncomingMessage) -> None:
        """
        Handle incoming message.

        Spawns a task to process each message concurrently, allowing
        multiple messages to be processed in parallel up to prefetch_count.
        """
        # Create task for concurrent processing - don't await here
        asyncio.create_task(self._process_message_with_ack(message))

    async def _process_message_with_ack(self, message: IncomingMessage) -> None:
        """
        Process a message with proper acknowledgment handling.

        This runs as a separate task to enable concurrent message processing.
        """
        async with message.process(requeue=False):
            try:
                # Parse message body
                body = json.loads(message.body.decode())

                logger.info(
                    f"Processing message from {self.queue_name}",
                    extra={"message_id": message.message_id},
                )

                # Process the message
                await self.process_message(body)

                logger.info(
                    "Message processed successfully",
                    extra={"message_id": message.message_id},
                )

            except Exception as e:
                logger.error(
                    f"Error processing message from {self.queue_name}: {e}",
                    extra={
                        "message_id": message.message_id,
                        "error": str(e),
                        "error_type": type(e).__name__,
                    },
                    exc_info=True,
                )
                # Message will be moved to DLQ due to requeue=False
                raise

    @abstractmethod
    async def process_message(self, body: dict[str, Any]) -> None:
        """
        Process a message from the queue.

        Must be implemented by subclasses.

        Args:
            body: Parsed message body
        """
        pass


async def publish_message(
    queue_name: str,
    message: dict[str, Any],
    priority: int = 0,
) -> None:
    """
    Publish a message to a queue.

    Args:
        queue_name: Target queue name
        message: Message body (will be JSON encoded)
        priority: Message priority (0-9, higher = more important)
    """
    await rabbitmq.init_pools()
    async with rabbitmq.get_connection() as connection:
        channel = await connection.channel()

        try:
            dead_letter_exchange = f"{queue_name}-dlx"

            # Declare dead letter exchange
            await channel.declare_exchange(
                dead_letter_exchange,
                aio_pika.ExchangeType.DIRECT,
                durable=True,
            )

            # Declare dead letter queue
            dlq = await channel.declare_queue(
                f"{queue_name}-poison",
                durable=True,
            )
            await dlq.bind(dead_letter_exchange, routing_key=queue_name)

            # Declare main queue with dead letter routing (matches consumer)
            await channel.declare_queue(
                queue_name,
                durable=True,
                arguments={
                    "x-dead-letter-exchange": dead_letter_exchange,
                    "x-dead-letter-routing-key": queue_name,
                },
            )

            # Publish message
            await channel.default_exchange.publish(
                aio_pika.Message(
                    body=json.dumps(message).encode(),
                    delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                    priority=priority,
                ),
                routing_key=queue_name,
            )

            logger.debug(f"Published message to {queue_name}")

        finally:
            await channel.close()
