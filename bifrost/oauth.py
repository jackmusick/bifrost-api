"""
OAuth SDK for Bifrost.

Provides Python API for OAuth token management (get, set, list, delete).

All methods are async and must be called with await.
"""

from __future__ import annotations

from typing import Any

from shared.keyvault import KeyVaultClient
from shared.services.oauth_storage_service import OAuthStorageService

from ._internal import get_context, require_permission


class oauth:
    """
    OAuth token management operations.

    Allows workflows to retrieve and manage OAuth tokens for external integrations.

    All methods are async and must be awaited.
    """

    @staticmethod
    async def get_token(provider: str, org_id: str | None = None) -> dict[str, Any] | None:
        """
        Get OAuth token for a provider.

        Args:
            provider: OAuth provider name (e.g., "microsoft", "google")
            org_id: Organization ID (defaults to current org from context)

        Returns:
            dict | None: OAuth token data (access_token, refresh_token, expires_at, etc.)
                        or None if not found

        Raises:
            RuntimeError: If no execution context

        Example:
            >>> from bifrost import oauth
            >>> token = await oauth.get_token("microsoft")
            >>> if token:
            ...     access_token = token["access_token"]
            ...     # Use the token for API calls
        """
        import json
        import logging

        logger = logging.getLogger(__name__)
        context = get_context()
        target_org = org_id or context.scope  # Use scope instead of org_id (scope is always a string)

        storage = OAuthStorageService()

        # Get connection using async method
        connection = await storage.get_connection(target_org, provider)

        if not connection:
            logger.warning(f"OAuth connection '{provider}' not found for org '{target_org}'")
            return None

        if connection.status != "completed":
            logger.warning(f"OAuth connection '{provider}' status is '{connection.status}', not 'completed'")
            return None

        # Retrieve OAuth response from Key Vault using direct ref
        try:
            if not connection.oauth_response_ref:
                logger.warning(f"OAuth connection '{provider}' has no oauth_response_ref")
                return None

            async with KeyVaultClient() as kv:
                secret_value = await kv.get_secret(connection.oauth_response_ref)
                if secret_value:
                    return json.loads(secret_value)
                else:
                    logger.warning(f"OAuth connection '{provider}' token secret is empty")
                    return None
        except Exception as e:
            logger.error(f"Failed to retrieve OAuth token for '{provider}': {e}", exc_info=True)
            return None

    @staticmethod
    async def set_token(
        provider: str,
        token_data: dict[str, Any],
        org_id: str | None = None
    ) -> None:
        """
        Set OAuth token for a provider.

        Requires: Permission to manage OAuth tokens (typically admin)

        Args:
            provider: OAuth provider name (e.g., "microsoft", "google")
            token_data: OAuth token data (access_token, refresh_token, expires_at, etc.)
            org_id: Organization ID (defaults to current org from context)

        Raises:
            PermissionError: If user lacks permission
            RuntimeError: If no execution context
            ValueError: If token_data is invalid

        Example:
            >>> from bifrost import oauth
            >>> await oauth.set_token("microsoft", {
            ...     "access_token": "ya29.xxx",
            ...     "refresh_token": "1//xxx",
            ...     "expires_at": 1234567890,
            ...     "token_type": "Bearer"
            ... })
        """
        context = require_permission("oauth.write")
        target_org = org_id or context.scope  # Use scope instead of org_id (scope is always a string)

        storage = OAuthStorageService()
        await storage.store_tokens(
            provider=provider,
            token_data=token_data,
            org_id=target_org,
            user_id=context.user_id
        )

    @staticmethod
    async def list_providers(org_id: str | None = None) -> list[str]:
        """
        List all OAuth providers with stored tokens.

        Args:
            org_id: Organization ID (defaults to current org from context)

        Returns:
            list[str]: List of provider names

        Raises:
            RuntimeError: If no execution context

        Example:
            >>> from bifrost import oauth
            >>> providers = await oauth.list_providers()
            >>> for provider in providers:
            ...     print(f"OAuth configured for: {provider}")
        """
        context = get_context()
        target_org = org_id or context.scope  # Use scope instead of org_id (scope is always a string)

        storage = OAuthStorageService()

        # List connections using async method
        connections = await storage.list_connections(target_org, include_global=True)

        # Extract connection names (providers)
        return [conn.connection_name for conn in connections]

    @staticmethod
    async def delete_token(provider: str, org_id: str | None = None) -> bool:
        """
        Delete OAuth token for a provider.

        Requires: Permission to manage OAuth tokens (typically admin)

        Args:
            provider: OAuth provider name (e.g., "microsoft", "google")
            org_id: Organization ID (defaults to current org from context)

        Returns:
            bool: True if deleted, False if not found

        Raises:
            PermissionError: If user lacks permission
            RuntimeError: If no execution context

        Example:
            >>> from bifrost import oauth
            >>> await oauth.delete_token("microsoft")
        """
        context = require_permission("oauth.delete")
        target_org = org_id or context.scope  # Use scope instead of org_id (scope is always a string)

        storage = OAuthStorageService()
        return await storage.delete_connection(target_org, provider)

    @staticmethod
    async def refresh_token(provider: str, org_id: str | None = None) -> dict[str, Any]:
        """
        Refresh OAuth token for a provider.

        Args:
            provider: OAuth provider name (e.g., "microsoft", "google")
            org_id: Organization ID (defaults to current org from context)

        Returns:
            dict: New OAuth token data

        Raises:
            RuntimeError: If no execution context or refresh fails
            ValueError: If provider not found or refresh token invalid

        Example:
            >>> from bifrost import oauth
            >>> new_token = await oauth.refresh_token("microsoft")
            >>> access_token = new_token["access_token"]
        """
        context = get_context()
        target_org = org_id or context.scope  # Use scope instead of org_id (scope is always a string)

        storage = OAuthStorageService()
        new_token = await storage.refresh_token(provider, target_org)

        if not new_token:
            raise ValueError(f"Failed to refresh token for provider: {provider}")

        return new_token
