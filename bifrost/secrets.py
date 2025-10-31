"""
Secrets SDK for Bifrost.

Provides Python API for secrets management (get, set, list, delete).
Secrets are encrypted at rest in Azure Key Vault.

All methods are async and must be called with await.
"""

from __future__ import annotations

import logging

from shared.keyvault import KeyVaultClient

from ._internal import get_context, require_permission

logger = logging.getLogger(__name__)


class secrets:
    """
    Secrets management operations.

    Allows workflows to securely store and retrieve encrypted secrets.
    Secrets are encrypted at rest in Azure Key Vault and scoped to organizations.

    All methods are async and must be awaited.
    """

    @staticmethod
    async def get(key: str, org_id: str | None = None) -> str | None:
        """
        Get decrypted secret value.

        Args:
            key: Secret key
            org_id: Organization ID (defaults to current org from context)

        Returns:
            str | None: Decrypted secret value, or None if not found

        Raises:
            RuntimeError: If no execution context

        Example:
            >>> from bifrost import secrets
            >>> api_key = secrets.get("stripe_api_key")
            >>> if api_key:
            ...     # Use the API key
            ...     pass
        """
        context = get_context()
        target_org = org_id or context.org_id

        try:
            async with KeyVaultClient() as kv_client:
                secret_value = await kv_client.get_secret(target_org, key)
                return secret_value
        except Exception as e:
            logger.warning(f"Failed to get secret {key} for org {target_org}: {e}")
            return None

    @staticmethod
    async def set(key: str, value: str, org_id: str | None = None) -> None:
        """
        Set encrypted secret value.

        Requires: Permission to manage secrets (typically admin)

        Args:
            key: Secret key
            value: Secret value (will be encrypted)
            org_id: Organization ID (defaults to current org from context)

        Raises:
            PermissionError: If user lacks permission
            RuntimeError: If no execution context

        Example:
            >>> from bifrost import secrets
            >>> secrets.set("stripe_api_key", "sk_live_xxxxx")
        """
        context = require_permission("secrets.write")
        target_org = org_id or context.org_id

        async with KeyVaultClient() as kv_client:
            await kv_client.create_secret(target_org, key, value)
        logger.info(f"Set secret {key} for org {target_org} by user {context.user_id}")

    @staticmethod
    async def list(org_id: str | None = None) -> list[str]:
        """
        List all secret keys (NOT values - keys only for security).

        Args:
            org_id: Organization ID (defaults to current org from context)

        Returns:
            list[str]: List of secret keys

        Raises:
            RuntimeError: If no execution context

        Example:
            >>> from bifrost import secrets
            >>> keys = secrets.list()
            >>> for key in keys:
            ...     print(f"Secret exists: {key}")
        """
        context = get_context()
        target_org = org_id or context.org_id

        async with KeyVaultClient() as kv_client:
            secret_keys = await kv_client.list_secrets(target_org)
            return secret_keys

    @staticmethod
    async def delete(key: str, org_id: str | None = None) -> bool:
        """
        Delete secret.

        Requires: Permission to manage secrets (typically admin)

        Args:
            key: Secret key
            org_id: Organization ID (defaults to current org from context)

        Returns:
            bool: True if deleted, False if not found

        Raises:
            PermissionError: If user lacks permission
            RuntimeError: If no execution context

        Example:
            >>> from bifrost import secrets
            >>> secrets.delete("old_api_key")
        """
        context = require_permission("secrets.delete")
        target_org = org_id or context.org_id

        try:
            async with KeyVaultClient() as kv_client:
                await kv_client.delete_secret(target_org, key)
            logger.info(f"Deleted secret {key} for org {target_org} by user {context.user_id}")
            return True
        except Exception as e:
            logger.warning(f"Failed to delete secret {key} for org {target_org}: {e}")
            return False
