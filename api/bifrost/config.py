"""
Configuration SDK for Bifrost.

Provides Python API for configuration management (get, set, list, delete).

All methods are async and must be called with await.
"""

from __future__ import annotations

import json as json_module
import logging
from typing import Any
from uuid import UUID

from ._internal import get_context

logger = logging.getLogger(__name__)


class config:
    """
    Configuration management operations.

    Allows workflows to read and write configuration values scoped to organizations.

    All methods are async and must be awaited.
    """

    @staticmethod
    async def get(key: str, org_id: str | None = None, default: Any = None) -> Any:
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
            >>> api_key = await config.get("api_key")  # Decrypts SECRET type automatically
            >>> timeout = await config.get("timeout", default=30)
        """
        from sqlalchemy import select, or_
        from src.core.database import get_session_factory
        from src.models import Config as ConfigModel

        context = get_context()
        session_factory = get_session_factory()

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

        async with session_factory() as db:
            # Try org-specific first, then GLOBAL fallback
            if org_uuid:
                logger.debug(f"config.get('{key}'): querying with org_uuid={org_uuid} (org-specific + global fallback)")
                query = select(ConfigModel).where(
                    ConfigModel.key == key,
                    or_(
                        ConfigModel.organization_id == org_uuid,
                        ConfigModel.organization_id.is_(None)
                    )
                ).order_by(ConfigModel.organization_id.desc().nulls_last())
            else:
                logger.debug(f"config.get('{key}'): querying GLOBAL only (org_uuid is None)")
                query = select(ConfigModel).where(
                    ConfigModel.key == key,
                    ConfigModel.organization_id.is_(None)
                )

            result = await db.execute(query)
            cfg = result.scalars().first()

            if cfg is None:
                logger.debug(f"config.get('{key}'): no config found, returning default={default}")
                return default

            # Parse value based on config type
            config_value = cfg.value or {}
            raw_value = config_value.get("value", config_value)
            config_type = str(cfg.config_type.value) if cfg.config_type else "string"
            logger.debug(
                f"config.get('{key}'): found config with org_id={cfg.organization_id}, "
                f"type={config_type}, value={raw_value if config_type != 'secret' else '[SECRET]'}"
            )

            # Handle secret type - decrypt the value
            if config_type == "secret":
                from src.core.security import decrypt_secret
                try:
                    return decrypt_secret(raw_value)
                except Exception:
                    return None

            # Parse other types
            if config_type == "json":
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
        from sqlalchemy import select
        from src.core.database import get_session_factory
        from src.models import Config as ConfigModel
        from src.models.enums import ConfigType

        context = get_context()
        session_factory = get_session_factory()

        target_org_id = org_id or getattr(context, 'org_id', None) or getattr(context, 'scope', None)
        org_uuid = None
        if target_org_id and target_org_id != "GLOBAL":
            try:
                org_uuid = UUID(target_org_id)
            except ValueError:
                pass

        # Determine config type and process value
        if is_secret:
            from src.core.security import encrypt_secret
            config_type = ConfigType.SECRET
            stored_value = encrypt_secret(str(value))
        elif isinstance(value, (dict, list)):
            config_type = ConfigType.JSON
            stored_value = value
        elif isinstance(value, bool):
            config_type = ConfigType.BOOL
            stored_value = value
        elif isinstance(value, int):
            config_type = ConfigType.INT
            stored_value = value
        else:
            config_type = ConfigType.STRING
            stored_value = value

        async with session_factory() as db:
            # Check if config exists
            query = select(ConfigModel).where(
                ConfigModel.key == key,
                ConfigModel.organization_id == org_uuid
            )
            result = await db.execute(query)
            existing = result.scalars().first()

            if existing:
                existing.value = {"value": stored_value}
                existing.config_type = config_type
                existing.updated_by = getattr(context, 'user_id', 'system')
            else:
                new_config = ConfigModel(
                    organization_id=org_uuid,
                    key=key,
                    value={"value": stored_value},
                    config_type=config_type,
                    updated_by=getattr(context, 'user_id', 'system')
                )
                db.add(new_config)

            await db.commit()

    @staticmethod
    async def list(org_id: str | None = None) -> dict[str, Any]:
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
            >>> org_config = await config.list()
            >>> for key, value in org_config.items():
            ...     print(f"{key}: {value}")
        """
        from sqlalchemy import select, or_
        from src.core.database import get_session_factory
        from src.models import Config as ConfigModel

        context = get_context()
        session_factory = get_session_factory()

        target_org_id = org_id or getattr(context, 'org_id', None) or getattr(context, 'scope', None)
        org_uuid = None
        if target_org_id and target_org_id != "GLOBAL":
            try:
                org_uuid = UUID(target_org_id)
            except ValueError:
                pass

        async with session_factory() as db:
            if org_uuid:
                query = select(ConfigModel).where(
                    or_(
                        ConfigModel.organization_id == org_uuid,
                        ConfigModel.organization_id.is_(None)
                    )
                )
            else:
                query = select(ConfigModel).where(
                    ConfigModel.organization_id.is_(None)
                )

            result = await db.execute(query)
            configs = result.scalars().all()

            config_dict: dict[str, Any] = {}
            for cfg in configs:
                config_value = cfg.value or {}
                raw_value = config_value.get("value", config_value)
                config_type = str(cfg.config_type.value) if cfg.config_type else "string"

                # Don't expose secret values in list
                if config_type == "secret":
                    config_dict[cfg.key] = "[SECRET]"
                elif config_type == "json" and isinstance(raw_value, str):
                    try:
                        config_dict[cfg.key] = json_module.loads(raw_value)
                    except json_module.JSONDecodeError:
                        config_dict[cfg.key] = raw_value
                elif config_type == "bool":
                    config_dict[cfg.key] = str(raw_value).lower() == "true" if isinstance(raw_value, str) else bool(raw_value)
                elif config_type == "int":
                    try:
                        config_dict[cfg.key] = int(raw_value)
                    except (ValueError, TypeError):
                        config_dict[cfg.key] = raw_value
                else:
                    config_dict[cfg.key] = raw_value

            return config_dict

    @staticmethod
    async def delete(key: str, org_id: str | None = None) -> bool:
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
            >>> await config.delete("old_api_url")
        """
        from sqlalchemy import select
        from src.core.database import get_session_factory
        from src.models import Config as ConfigModel

        context = get_context()
        session_factory = get_session_factory()

        target_org_id = org_id or getattr(context, 'org_id', None) or getattr(context, 'scope', None)
        org_uuid = None
        if target_org_id and target_org_id != "GLOBAL":
            try:
                org_uuid = UUID(target_org_id)
            except ValueError:
                pass

        async with session_factory() as db:
            query = select(ConfigModel).where(
                ConfigModel.key == key,
                ConfigModel.organization_id == org_uuid
            )
            result = await db.execute(query)
            existing = result.scalars().first()

            if not existing:
                return False

            db.delete(existing)
            await db.commit()
            return True
