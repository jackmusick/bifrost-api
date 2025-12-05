"""
Configuration SDK for Bifrost.

Provides Python API for configuration management (get, set, list, delete).

All methods are async and must be awaited.
"""

from __future__ import annotations

import json as json_module
import logging
from typing import Any

from shared.cache import config_hash_key, get_redis

from ._internal import get_context
from ._write_buffer import get_write_buffer

logger = logging.getLogger(__name__)


class config:
    """
    Configuration management operations.

    Allows workflows to read and write configuration values scoped to organizations.
    Reads from Redis cache (populated by pre-warming), writes to buffer (flushed post-execution).

    All methods are async - await is required.
    """

    @staticmethod
    async def get(key: str, org_id: str | None = None, default: Any = None) -> Any:
        """
        Get configuration value with automatic secret decryption.

        Reads from Redis cache (pre-warmed before execution). Secrets are
        already decrypted at pre-warm time.

        Args:
            key: Configuration key
            org_id: Organization ID (defaults to current org from context)
            default: Default value if key not found (optional)

        Returns:
            Any: Configuration value, or default if not found

        Raises:
            RuntimeError: If no execution context

        Example:
            >>> from bifrost import config
            >>> api_key = await config.get("api_key")
            >>> timeout = await config.get("timeout", default=30)
        """
        context = get_context()

        target_org_id = org_id or getattr(context, 'org_id', None) or getattr(context, 'scope', None)
        logger.debug(
            f"config.get('{key}'): context.scope={getattr(context, 'scope', None)}, "
            f"context.org_id={getattr(context, 'org_id', None)}, target_org_id={target_org_id}"
        )

        # Read from Redis cache (pre-warmed)
        async with get_redis() as r:
            data = await r.hget(config_hash_key(target_org_id), key)  # type: ignore[misc]

            if data is None:
                logger.debug(f"config.get('{key}'): not found in cache, returning default={default}")
                return default

            try:
                cache_entry = json_module.loads(data)
            except json_module.JSONDecodeError:
                return default

            raw_value = cache_entry.get("value")
            config_type = cache_entry.get("type", "string")

            logger.debug(
                f"config.get('{key}'): found in cache with "
                f"type={config_type}, value={raw_value if config_type != 'secret' else '[SECRET]'}"
            )

            # Parse value based on type
            if config_type == "secret":
                # Already decrypted at pre-warm time
                return raw_value
            elif config_type == "json":
                if isinstance(raw_value, str):
                    try:
                        return json_module.loads(raw_value)
                    except json_module.JSONDecodeError:
                        return raw_value
                return raw_value
            elif config_type == "bool":
                if isinstance(raw_value, bool):
                    return raw_value
                return str(raw_value).lower() == "true"
            elif config_type == "int":
                try:
                    return int(raw_value)
                except (ValueError, TypeError):
                    return raw_value
            else:
                return raw_value

    @staticmethod
    async def set(key: str, value: Any, org_id: str | None = None, is_secret: bool = False) -> None:
        """
        Set configuration value.

        Writes to Redis buffer (flushed to Postgres after execution completes).

        Args:
            key: Configuration key
            value: Configuration value (must be JSON-serializable)
            org_id: Organization ID (defaults to current org from context)
            is_secret: If True, encrypts the value before storage

        Raises:
            RuntimeError: If no execution context
            ValueError: If value is not JSON-serializable

        Example:
            >>> from bifrost import config
            >>> await config.set("api_url", "https://api.example.com")
            >>> await config.set("api_key", "secret123", is_secret=True)
        """
        context = get_context()

        target_org_id = org_id or getattr(context, 'org_id', None) or getattr(context, 'scope', None)

        # Determine config type
        if is_secret:
            from src.core.security import encrypt_secret
            config_type = "secret"
            stored_value = encrypt_secret(str(value))
        elif isinstance(value, (dict, list)):
            config_type = "json"
            stored_value = value
        elif isinstance(value, bool):
            config_type = "bool"
            stored_value = value
        elif isinstance(value, int):
            config_type = "int"
            stored_value = value
        else:
            config_type = "string"
            stored_value = value

        # Write to buffer
        buffer = get_write_buffer()
        await buffer.add_config_change(
            operation="set",
            key=key,
            value=stored_value,
            org_id=target_org_id,
            config_type=config_type,
        )

    @staticmethod
    async def list(org_id: str | None = None) -> dict[str, Any]:
        """
        List configuration key-value pairs.

        Note: Secret values are shown as the decrypted value (or "[SECRET]" on error).

        Args:
            org_id: Organization ID (optional, defaults to current org)

        Returns:
            dict[str, Any]: Configuration key-value pairs

        Raises:
            RuntimeError: If no execution context

        Example:
            >>> from bifrost import config
            >>> org_config = await config.list()
            >>> for key, value in org_config.items():
            ...     print(f"{key}: {value}")
        """
        context = get_context()

        target_org_id = org_id or getattr(context, 'org_id', None) or getattr(context, 'scope', None)

        # Read all configs from Redis hash
        async with get_redis() as r:
            all_data = await r.hgetall(config_hash_key(target_org_id))  # type: ignore[misc]

            if not all_data:
                return {}

            config_dict: dict[str, Any] = {}
            for config_key, data in all_data.items():
                try:
                    cache_entry = json_module.loads(data)
                except json_module.JSONDecodeError:
                    continue

                raw_value = cache_entry.get("value")
                config_type = cache_entry.get("type", "string")

                # Parse value based on type
                if config_type == "secret":
                    # Already decrypted at pre-warm time
                    config_dict[config_key] = raw_value if raw_value else "[SECRET]"
                elif config_type == "json" and isinstance(raw_value, str):
                    try:
                        config_dict[config_key] = json_module.loads(raw_value)
                    except json_module.JSONDecodeError:
                        config_dict[config_key] = raw_value
                elif config_type == "bool":
                    config_dict[config_key] = str(raw_value).lower() == "true" if isinstance(raw_value, str) else bool(raw_value)
                elif config_type == "int":
                    try:
                        config_dict[config_key] = int(raw_value)
                    except (ValueError, TypeError):
                        config_dict[config_key] = raw_value
                else:
                    config_dict[config_key] = raw_value

            return config_dict

    @staticmethod
    async def delete(key: str, org_id: str | None = None) -> bool:
        """
        Delete configuration value.

        Writes to buffer (deletion applied to Postgres after execution completes).

        Args:
            key: Configuration key
            org_id: Organization ID (defaults to current org from context)

        Returns:
            bool: True (deletion queued)

        Raises:
            RuntimeError: If no execution context

        Example:
            >>> from bifrost import config
            >>> await config.delete("old_api_url")
        """
        context = get_context()

        target_org_id = org_id or getattr(context, 'org_id', None) or getattr(context, 'scope', None)

        # Write delete to buffer
        buffer = get_write_buffer()
        await buffer.add_config_change(
            operation="delete",
            key=key,
            org_id=target_org_id,
        )

        return True
