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
    async def get(provider: str, org_id: str | None = None) -> dict[str, Any] | None:
        """
        Get OAuth connection configuration for a provider.

        Returns the full OAuth configuration including credentials needed for
        custom token operations (e.g., cross-tenant exchanges).

        Args:
            provider: OAuth provider/connection name (e.g., "microsoft", "partner_center")
            org_id: Organization ID (defaults to current org from context)

        Returns:
            dict | None: OAuth connection config with keys:
                - connection_name: str
                - client_id: str
                - client_secret: str | None (if configured)
                - authorization_url: str | None
                - token_url: str
                - scopes: str
                - refresh_token: str | None (if available)
                - access_token: str | None (if available)
                - expires_at: str | None (ISO format, if available)
            Returns None if connection not found.

        Raises:
            RuntimeError: If no execution context

        Example:
            >>> from bifrost import oauth
            >>> conn = await oauth.get("partner_center")
            >>> if conn:
            ...     # Use for cross-tenant token exchange
            ...     refresh_token = conn["refresh_token"]
            ...     client_id = conn["client_id"]
            ...     client_secret = conn["client_secret"]
        """
        import json
        import logging

        logger = logging.getLogger(__name__)
        context = get_context()
        target_org = org_id or context.scope

        storage = OAuthStorageService()

        # Get connection metadata
        connection = await storage.get_connection(target_org, provider)

        if not connection:
            logger.warning(f"OAuth connection '{provider}' not found for org '{target_org}'")
            return None

        # Build result with connection config
        result: dict[str, Any] = {
            "connection_name": connection.connection_name,
            "client_id": connection.client_id,
            "client_secret": None,
            "authorization_url": connection.authorization_url,
            "token_url": connection.token_url,
            "scopes": connection.scopes,
            "refresh_token": None,
            "access_token": None,
            "expires_at": None,
        }

        # Retrieve client_secret from Key Vault if ref exists
        if connection.client_secret_ref:
            try:
                async with KeyVaultClient() as kv:
                    result["client_secret"] = await kv.get_secret(connection.client_secret_ref)
            except Exception as e:
                logger.warning(f"Could not retrieve client_secret for '{provider}': {e}")

        # Retrieve OAuth tokens from Key Vault if ref exists
        if connection.oauth_response_ref:
            try:
                async with KeyVaultClient() as kv:
                    secret_value = await kv.get_secret(connection.oauth_response_ref)
                    if secret_value:
                        oauth_response = json.loads(secret_value)
                        result["refresh_token"] = oauth_response.get("refresh_token")
                        result["access_token"] = oauth_response.get("access_token")
                        result["expires_at"] = oauth_response.get("expires_at")
            except Exception as e:
                logger.warning(f"Could not retrieve OAuth tokens for '{provider}': {e}")

        return result

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
