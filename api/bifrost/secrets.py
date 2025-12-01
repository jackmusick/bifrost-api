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
    async def get(key: str) -> str | None:
        """
        Get decrypted secret value.

        Args:
            key: Secret ref/name (full Key Vault secret name)

        Returns:
            str | None: Decrypted secret value, or None if not found

        Raises:
            RuntimeError: If no execution context

        Example:
            >>> from bifrost import secrets
            >>> api_key = await secrets.get("bifrost-global-api-stripe-abc123")
            >>> if api_key:
            ...     # Use the API key
            ...     pass
        """
        _context = get_context()  # Validates execution context exists

        try:
            async with KeyVaultClient() as kv_client:
                secret_value = await kv_client.get_secret(key)
                return secret_value
        except Exception as e:
            logger.warning(f"Failed to get secret {key}: {e}")
            return None

    @staticmethod
    async def set(key: str, value: str) -> None:
        """
        Set encrypted secret value.

        Requires: Permission to manage secrets (typically admin)

        Args:
            key: Secret ref/name (full Key Vault secret name)
            value: Secret value (will be encrypted)

        Raises:
            PermissionError: If user lacks permission
            RuntimeError: If no execution context

        Example:
            >>> from bifrost import secrets
            >>> await secrets.set("bifrost-global-api-stripe-abc123", "sk_live_xxxxx")
        """
        context = require_permission("secrets.write")

        async with KeyVaultClient() as kv_client:
            await kv_client.set_secret(key, value)
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
        context = get_context()
        target_org = org_id or context.scope

        async with KeyVaultClient() as kv_client:
            secret_keys = await kv_client.list_secrets(target_org)
            return secret_keys

    @staticmethod
    async def delete(key: str) -> bool:
        """
        Delete secret.

        Requires: Permission to manage secrets (typically admin)

        Args:
            key: Secret ref/name (full Key Vault secret name)

        Returns:
            bool: True if deleted, False if not found

        Raises:
            PermissionError: If user lacks permission
            RuntimeError: If no execution context

        Example:
            >>> from bifrost import secrets
            >>> await secrets.delete("bifrost-global-api-old-abc123")
        """
        context = require_permission("secrets.delete")

        try:
            async with KeyVaultClient() as kv_client:
                await kv_client.delete_secret(key)
            logger.info(f"Deleted secret {key} by user {context.user_id}")
            return True
        except Exception as e:
            logger.warning(f"Failed to delete secret {key}: {e}")
            return False
