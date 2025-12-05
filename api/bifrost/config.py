"""
Configuration SDK for Bifrost.

Provides Python API for configuration management (get, set, list, delete).

All methods are synchronous and can be called directly (no await needed).
"""

from __future__ import annotations

import json as json_module
import logging
from typing import Any
from uuid import UUID

from sqlalchemy import select, or_

from src.models.enums import ConfigType
from src.models.orm import Config

from ._db import get_sync_session
from ._internal import get_context

logger = logging.getLogger(__name__)


class config:
    """
    Configuration management operations.

    Allows workflows to read and write configuration values scoped to organizations.

    All methods are synchronous - no await needed.
    """

    @staticmethod
    def get(key: str, org_id: str | None = None, default: Any = None) -> Any:
        """
        Get configuration value with automatic secret decryption.

        Args:
            key: Configuration key
            org_id: Organization ID (defaults to current org from context)
            default: Default value if key not found (optional)

        Returns:
            Any: Configuration value (with secret decrypted if secret type),
                 or default if not found

        Raises:
            RuntimeError: If no execution context or decryption fails

        Example:
            >>> from bifrost import config
            >>> api_key = config.get("api_key")  # Decrypts SECRET type automatically
            >>> timeout = config.get("timeout", default=30)
        """
        context = get_context()

        target_org_id = org_id or getattr(context, 'org_id', None) or getattr(context, 'scope', None)
        logger.debug(
            f"config.get('{key}'): context.scope={getattr(context, 'scope', None)}, "
            f"context.org_id={getattr(context, 'org_id', None)}, target_org_id={target_org_id}"
        )

        org_uuid = None
        if target_org_id and target_org_id != "GLOBAL":
            try:
                org_uuid = UUID(target_org_id)
            except ValueError:
                pass

        with get_sync_session() as db:
            # Try org-specific first, then GLOBAL fallback
            if org_uuid:
                logger.debug(f"config.get('{key}'): querying with org_uuid={org_uuid} (org-specific + global fallback)")
                query = (
                    select(Config)
                    .where(Config.key == key)
                    .where(or_(Config.organization_id == org_uuid, Config.organization_id.is_(None)))
                    .order_by(Config.organization_id.desc().nulls_last())
                    .limit(1)
                )
            else:
                logger.debug(f"config.get('{key}'): querying GLOBAL only (org_uuid is None)")
                query = (
                    select(Config)
                    .where(Config.key == key)
                    .where(Config.organization_id.is_(None))
                    .limit(1)
                )

            result = db.execute(query)
            row = result.scalars().first()

            if row is None:
                logger.debug(f"config.get('{key}'): no config found, returning default={default}")
                return default

            # Parse value based on config type
            config_value = row.value or {}
            raw_value = config_value.get("value", config_value) if isinstance(config_value, dict) else config_value
            # Get the string value from the enum for comparison
            config_type_val = row.config_type.value if row.config_type else "string"
            logger.debug(
                f"config.get('{key}'): found config with org_id={row.organization_id}, "
                f"type={config_type_val}, value={raw_value if config_type_val != 'secret' else '[SECRET]'}"
            )

            # Handle secret type - decrypt the value
            if config_type_val == "secret":
                from src.core.security import decrypt_secret
                try:
                    return decrypt_secret(raw_value)
                except Exception:
                    return None

            # Parse other types
            if config_type_val == "json":
                if isinstance(raw_value, str):
                    try:
                        return json_module.loads(raw_value)
                    except json_module.JSONDecodeError:
                        return raw_value
                return raw_value
            elif config_type_val == "bool":
                if isinstance(raw_value, bool):
                    return raw_value
                return str(raw_value).lower() == "true"
            elif config_type_val == "int":
                try:
                    return int(raw_value)
                except (ValueError, TypeError):
                    return raw_value
            else:
                return raw_value

    @staticmethod
    def set(key: str, value: Any, org_id: str | None = None, is_secret: bool = False) -> None:
        """
        Set configuration value.

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
            >>> config.set("api_url", "https://api.example.com")
            >>> config.set("api_key", "secret123", is_secret=True)
        """
        context = get_context()

        target_org_id = org_id or getattr(context, 'org_id', None) or getattr(context, 'scope', None)
        org_uuid = None
        if target_org_id and target_org_id != "GLOBAL":
            try:
                org_uuid = UUID(target_org_id)
            except ValueError:
                pass

        # Determine config type and process value
        config_type_enum: ConfigType
        if is_secret:
            from src.core.security import encrypt_secret
            config_type_enum = ConfigType.SECRET
            stored_value = encrypt_secret(str(value))
        elif isinstance(value, (dict, list)):
            config_type_enum = ConfigType.JSON
            stored_value = value
        elif isinstance(value, bool):
            config_type_enum = ConfigType.BOOL
            stored_value = value
        elif isinstance(value, int):
            config_type_enum = ConfigType.INT
            stored_value = value
        else:
            config_type_enum = ConfigType.STRING
            stored_value = value

        user_id = getattr(context, 'user_id', 'system')

        with get_sync_session() as db:
            # Try to find existing config
            if org_uuid:
                query = (
                    select(Config)
                    .where(Config.key == key)
                    .where(Config.organization_id == org_uuid)
                )
            else:
                query = (
                    select(Config)
                    .where(Config.key == key)
                    .where(Config.organization_id.is_(None))
                )

            result = db.execute(query)
            existing = result.scalars().first()

            if existing:
                # Update existing config
                existing.value = {"value": stored_value}
                existing.config_type = config_type_enum
                existing.updated_by = user_id
            else:
                # Create new config
                new_config = Config(
                    organization_id=org_uuid,
                    key=key,
                    value={"value": stored_value},
                    config_type=config_type_enum,
                    updated_by=user_id,
                )
                db.add(new_config)

    @staticmethod
    def list(org_id: str | None = None) -> dict[str, Any]:
        """
        List configuration key-value pairs.

        Note: Secret values are NOT decrypted in list - use get() for individual secrets.

        Args:
            org_id: Organization ID (optional, defaults to current org)

        Returns:
            dict[str, Any]: Configuration key-value pairs (secrets shown as "[SECRET]")

        Raises:
            RuntimeError: If no execution context

        Example:
            >>> from bifrost import config
            >>> org_config = config.list()
            >>> for key, value in org_config.items():
            ...     print(f"{key}: {value}")
        """
        context = get_context()

        target_org_id = org_id or getattr(context, 'org_id', None) or getattr(context, 'scope', None)
        org_uuid = None
        if target_org_id and target_org_id != "GLOBAL":
            try:
                org_uuid = UUID(target_org_id)
            except ValueError:
                pass

        with get_sync_session() as db:
            if org_uuid:
                query = (
                    select(Config)
                    .where(or_(Config.organization_id == org_uuid, Config.organization_id.is_(None)))
                )
            else:
                query = select(Config).where(Config.organization_id.is_(None))

            result = db.execute(query)
            rows = result.scalars().all()

            config_dict: dict[str, Any] = {}
            for row in rows:
                config_value = row.value or {}
                raw_value = config_value.get("value", config_value) if isinstance(config_value, dict) else config_value
                # Get the string value from the enum for comparison
                config_type_val = row.config_type.value if row.config_type else "string"

                # Don't expose secret values in list
                if config_type_val == "secret":
                    config_dict[row.key] = "[SECRET]"
                elif config_type_val == "json" and isinstance(raw_value, str):
                    try:
                        config_dict[row.key] = json_module.loads(raw_value)
                    except json_module.JSONDecodeError:
                        config_dict[row.key] = raw_value
                elif config_type_val == "bool":
                    config_dict[row.key] = str(raw_value).lower() == "true" if isinstance(raw_value, str) else bool(raw_value)
                elif config_type_val == "int":
                    try:
                        config_dict[row.key] = int(raw_value)
                    except (ValueError, TypeError):
                        config_dict[row.key] = raw_value
                else:
                    config_dict[row.key] = raw_value

            return config_dict

    @staticmethod
    def delete(key: str, org_id: str | None = None) -> bool:
        """
        Delete configuration value.

        Args:
            key: Configuration key
            org_id: Organization ID (defaults to current org from context)

        Returns:
            bool: True if deleted, False if not found

        Raises:
            RuntimeError: If no execution context

        Example:
            >>> from bifrost import config
            >>> config.delete("old_api_url")
        """
        context = get_context()

        target_org_id = org_id or getattr(context, 'org_id', None) or getattr(context, 'scope', None)
        org_uuid = None
        if target_org_id and target_org_id != "GLOBAL":
            try:
                org_uuid = UUID(target_org_id)
            except ValueError:
                pass

        with get_sync_session() as db:
            if org_uuid:
                query = (
                    select(Config)
                    .where(Config.key == key)
                    .where(Config.organization_id == org_uuid)
                )
            else:
                query = (
                    select(Config)
                    .where(Config.key == key)
                    .where(Config.organization_id.is_(None))
                )

            result = db.execute(query)
            existing = result.scalars().first()

            if existing:
                db.delete(existing)
                return True
            return False
