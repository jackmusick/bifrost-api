"""
Redis Client for Sync Execution Results

Provides Redis BLPOP/RPUSH pattern for synchronous workflow execution.
Used by API (waits for result) and Worker (pushes result).

Pattern:
1. API publishes workflow execution to RabbitMQ with sync=True
2. API waits: redis.blpop(f"result:{execution_id}", timeout=300)
3. Worker executes workflow
4. Worker pushes: redis.rpush(f"result:{execution_id}", result)
5. API's blpop returns with result
"""

import json
import logging
from typing import Any, Awaitable, cast

import redis.asyncio as redis

from src.config import get_settings

logger = logging.getLogger(__name__)

# Redis key prefix for sync execution results
RESULT_KEY_PREFIX = "bifrost:result:"

# Default timeout for sync execution (5 minutes)
DEFAULT_TIMEOUT_SECONDS = 300

# Result TTL for auto-cleanup (60 seconds after push)
RESULT_TTL_SECONDS = 60


class RedisClient:
    """
    Redis client wrapper for sync execution results.

    Provides:
    - push_result: Worker pushes result after execution
    - wait_for_result: API waits for result via BLPOP
    """

    def __init__(self):
        self._redis: redis.Redis | None = None

    async def _get_redis(self) -> redis.Redis:
        """Get or create Redis connection."""
        if self._redis is None:
            settings = get_settings()
            self._redis = redis.from_url(
                settings.redis_url,
                decode_responses=True,
            )
        return self._redis

    async def push_result(
        self,
        execution_id: str,
        status: str,
        result: Any = None,
        error: str | None = None,
        error_type: str | None = None,
        duration_ms: int | None = None,
    ) -> None:
        """
        Push execution result to Redis for sync callers.

        Called by Worker after workflow execution completes.

        Args:
            execution_id: Execution ID
            status: Execution status (Success, Failed, etc.)
            result: Workflow result data
            error: Error message if failed
            error_type: Error type if failed
            duration_ms: Execution duration in milliseconds
        """
        redis_client = await self._get_redis()
        key = f"{RESULT_KEY_PREFIX}{execution_id}"

        payload = {
            "status": status,
            "result": result,
            "error": error,
            "error_type": error_type,
            "duration_ms": duration_ms,
        }

        try:
            # Push result to list
            # Cast needed: redis-py returns Union[Awaitable[int], int] but we're async
            await cast(Awaitable[int], redis_client.rpush(key, json.dumps(payload)))
            # Set TTL for auto-cleanup
            await cast(Awaitable[bool], redis_client.expire(key, RESULT_TTL_SECONDS))
            logger.debug(f"Pushed result to Redis: {key}")
        except Exception as e:
            logger.error(f"Failed to push result to Redis: {e}")
            raise

    async def wait_for_result(
        self,
        execution_id: str,
        timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    ) -> dict[str, Any] | None:
        """
        Wait for execution result from Redis.

        Called by API for sync execution requests.

        Args:
            execution_id: Execution ID
            timeout_seconds: Max time to wait (default: 300s)

        Returns:
            Result dict or None if timeout
        """
        redis_client = await self._get_redis()
        key = f"{RESULT_KEY_PREFIX}{execution_id}"

        try:
            # BLPOP blocks until value available or timeout
            # Cast needed: redis-py returns Union[Awaitable[list], list] but we're async
            result = await cast(
                Awaitable[list[str] | None],
                redis_client.blpop([key], timeout=timeout_seconds)
            )

            if result is None:
                logger.warning(f"Timeout waiting for result: {execution_id}")
                return None

            # result is tuple (key, value)
            _, value = result
            return json.loads(value)

        except Exception as e:
            logger.error(f"Error waiting for result: {e}")
            raise

    async def set_cancel_flag(self, execution_id: str) -> None:
        """
        Set the cancellation flag for an execution.

        The execution pool checks this flag periodically and will terminate
        the worker process when it's set.

        Args:
            execution_id: Execution ID to cancel
        """
        redis_client = await self._get_redis()
        key = f"bifrost:exec:{execution_id}:cancel"
        try:
            # Set flag with 1 hour TTL (should be cleaned up much sooner)
            await redis_client.setex(key, 3600, "1")
            logger.debug(f"Set cancel flag: {key}")
        except Exception as e:
            logger.error(f"Failed to set cancel flag: {e}")
            raise

    async def close(self) -> None:
        """Close Redis connection."""
        if self._redis:
            await self._redis.close()
            self._redis = None


# Singleton instance
_redis_client: RedisClient | None = None


def get_redis_client() -> RedisClient:
    """Get singleton Redis client instance."""
    global _redis_client
    if _redis_client is None:
        _redis_client = RedisClient()
    return _redis_client


async def close_redis_client() -> None:
    """Close Redis client."""
    global _redis_client
    if _redis_client:
        await _redis_client.close()
        _redis_client = None
