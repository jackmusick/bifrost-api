"""
Secrets SDK for Bifrost.

Provides Python API for secrets management (get, set, list, delete).
Secrets are encrypted at rest in PostgreSQL.

All methods are async and must be called with await.
"""

from __future__ import annotations

import logging

from ._internal import get_context, require_permission

logger = logging.getLogger(__name__)


class secrets:
    """
    Secrets management operations.

    Allows workflows to securely store and retrieve encrypted secrets.
    Secrets are encrypted at rest in PostgreSQL and scoped to organizations.

    All methods are async and must be awaited.
    """

    @staticmethod
    async def get(key: str, org_id: str | None = None) -> str | None:
        """
        Get decrypted secret value.

        Args:
            key: Secret key name
            org_id: Organization ID (defaults to current org from context)

        Returns:
            str | None: Decrypted secret value, or None if not found

        Raises:
            RuntimeError: If no execution context

        Example:
            >>> from bifrost import secrets
            >>> api_key = await secrets.get("stripe_api_key")
            >>> if api_key:
            ...     # Use the API key
            ...     pass
        """
        from sqlalchemy import select, or_
        from src.core.database import get_session_factory
        from src.models import Config as ConfigModel
        from uuid import UUID

        context = get_context()
        target_org = org_id or context.scope
        org_uuid = None
        if target_org and target_org != "GLOBAL":
            try:
                org_uuid = UUID(target_org)
            except ValueError:
                pass

        session_factory = get_session_factory()
        try:
            async with session_factory() as db:
                # Try org-specific first, then GLOBAL fallback
                if org_uuid:
                    query = select(ConfigModel).where(
                        ConfigModel.key == key,
                        or_(
                            ConfigModel.organization_id == org_uuid,
                            ConfigModel.organization_id.is_(None)
                        )
                    ).order_by(ConfigModel.organization_id.desc().nulls_last())
                else:
                    query = select(ConfigModel).where(
                        ConfigModel.key == key,
                        ConfigModel.organization_id.is_(None)
                    )

                result = await db.execute(query)
                cfg = result.scalars().first()

                if cfg is None:
                    return None

                # Check if it's a secret type
                config_type = str(cfg.config_type.value) if cfg.config_type else "string"
                if config_type != "secret":
                    return None

                # Get the secret value
                config_value = cfg.value or {}
                raw_value = config_value.get("value", config_value)

                # Decrypt the secret
                from src.core.security import decrypt_secret
                try:
                    return decrypt_secret(raw_value)
                except Exception:
                    return None

        except Exception as e:
            logger.warning(f"Failed to get secret {key}: {e}")
            return None

    @staticmethod
    async def set(key: str, value: str, org_id: str | None = None) -> None:
        """
        Set encrypted secret value.

        Requires: Permission to manage secrets (typically admin)

        Args:
            key: Secret key name
            value: Secret value (will be encrypted)
            org_id: Organization ID (defaults to current org from context)

        Raises:
            PermissionError: If user lacks permission
            RuntimeError: If no execution context

        Example:
            >>> from bifrost import secrets
            >>> await secrets.set("stripe_api_key", "sk_live_xxxxx")
        """
        from sqlalchemy import select
        from src.core.database import get_session_factory
        from src.models import Config as ConfigModel
        from src.models.enums import ConfigType
        from src.core.security import encrypt_secret
        from uuid import UUID

        context = require_permission("secrets.write")
        target_org = org_id or context.scope
        org_uuid = None
        if target_org and target_org != "GLOBAL":
            try:
                org_uuid = UUID(target_org)
            except ValueError:
                pass

        session_factory = get_session_factory()
        async with session_factory() as db:
            # Check if config exists
            query = select(ConfigModel).where(
                ConfigModel.key == key,
                ConfigModel.organization_id == org_uuid
            )
            result = await db.execute(query)
            existing = result.scalars().first()

            encrypted_value = encrypt_secret(str(value))

            if existing:
                existing.value = {"value": encrypted_value}
                existing.config_type = ConfigType.SECRET
                existing.updated_by = context.user_id
            else:
                new_config = ConfigModel(
                    organization_id=org_uuid,
                    key=key,
                    value={"value": encrypted_value},
                    config_type=ConfigType.SECRET,
                    updated_by=context.user_id
                )
                db.add(new_config)

            await db.commit()
        logger.info(f"Set secret {key} by user {context.user_id}")

    @staticmethod
    async def list(org_id: str | None = None) -> list[str]:
        """
        List all secret keys (NOT values - keys only for security).

        Args:
            org_id: Organization ID to filter by (optional)

        Returns:
            list[str]: List of secret keys

        Raises:
            RuntimeError: If no execution context

        Example:
            >>> from bifrost import secrets
            >>> keys = await secrets.list()
            >>> for key in keys:
            ...     print(f"Secret exists: {key}")
        """
        from sqlalchemy import select, or_
        from src.core.database import get_session_factory
        from src.models import Config as ConfigModel
        from uuid import UUID

        context = get_context()
        target_org = org_id or context.scope
        org_uuid = None
        if target_org and target_org != "GLOBAL":
            try:
                org_uuid = UUID(target_org)
            except ValueError:
                pass

        session_factory = get_session_factory()
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

            # Filter to only SECRET type and return keys only
            return [c.key for c in configs if c.config_type and str(c.config_type.value) == "secret"]

    @staticmethod
    async def delete(key: str, org_id: str | None = None) -> bool:
        """
        Delete secret.

        Requires: Permission to manage secrets (typically admin)

        Args:
            key: Secret key name
            org_id: Organization ID (defaults to current org from context)

        Returns:
            bool: True if deleted, False if not found

        Raises:
            PermissionError: If user lacks permission
            RuntimeError: If no execution context

        Example:
            >>> from bifrost import secrets
            >>> await secrets.delete("old_api_key")
        """
        from sqlalchemy import select
        from src.core.database import get_session_factory
        from src.models import Config as ConfigModel
        from uuid import UUID

        context = require_permission("secrets.delete")
        target_org = org_id or context.scope
        org_uuid = None
        if target_org and target_org != "GLOBAL":
            try:
                org_uuid = UUID(target_org)
            except ValueError:
                pass

        try:
            session_factory = get_session_factory()
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
                logger.info(f"Deleted secret {key} by user {context.user_id}")
                return True
        except Exception as e:
            logger.warning(f"Failed to delete secret {key}: {e}")
            return False
