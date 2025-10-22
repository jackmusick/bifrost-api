"""
OAuth SDK for Bifrost.

Provides Python API for OAuth token management (get, set, list, delete).
"""

from __future__ import annotations

from typing import Any

from services.oauth_storage_service import OAuthStorageService

from ._internal import get_context, require_permission


class oauth:
    """
    OAuth token management operations.

    Allows workflows to retrieve and manage OAuth tokens for external integrations.
    """

    @staticmethod
    def get_token(provider: str, org_id: str | None = None) -> dict[str, Any] | None:
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
            >>> token = oauth.get_token("microsoft")
            >>> if token:
            ...     access_token = token["access_token"]
            ...     # Use the token for API calls
        """
        import asyncio
        from shared.keyvault import KeyVaultClient
        import json

        context = get_context()
        target_org = org_id or context.org_id

        storage = OAuthStorageService()

        # Get connection using async method
        loop = asyncio.new_event_loop()
        try:
            connection = loop.run_until_complete(
                storage.get_connection(target_org, provider)
            )
        finally:
            loop.close()

        if not connection or connection.status != "completed":
            return None

        # Retrieve OAuth response from Key Vault
        try:
            kv = KeyVaultClient()
            oauth_response_ref = connection.oauth_response_ref
            # oauth_response_ref contains the Key Vault secret name
            secret_value = kv.get_secret(target_org, oauth_response_ref.replace(f"oauth_{provider}_oauth_response", ""))
            if not secret_value:
                # Try alternate pattern
                keyvault_secret_name = f"{target_org}--oauth-{provider}-response"
                # Extract just the secret name part (after org--)
                parts = keyvault_secret_name.split("--", 1)
                if len(parts) == 2:
                    secret_value = kv.get_secret(target_org, parts[1])

            if secret_value:
                return json.loads(secret_value)
        except Exception:
            pass

        return None

    @staticmethod
    def set_token(
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
            >>> oauth.set_token("microsoft", {
            ...     "access_token": "ya29.xxx",
            ...     "refresh_token": "1//xxx",
            ...     "expires_at": 1234567890,
            ...     "token_type": "Bearer"
            ... })
        """
        context = require_permission("oauth.write")
        target_org = org_id or context.org_id

        storage = OAuthStorageService()
        storage.store_token(
            provider=provider,
            token_data=token_data,
            org_id=target_org,
            user_id=context.user_id
        )

    @staticmethod
    def list_providers(org_id: str | None = None) -> list[str]:
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
            >>> providers = oauth.list_providers()
            >>> for provider in providers:
            ...     print(f"OAuth configured for: {provider}")
        """
        import asyncio

        context = get_context()
        target_org = org_id or context.org_id

        storage = OAuthStorageService()

        # List connections using async method
        loop = asyncio.new_event_loop()
        try:
            connections = loop.run_until_complete(
                storage.list_connections(target_org, include_global=True)
            )
        finally:
            loop.close()

        # Extract connection names (providers)
        return [conn.connection_name for conn in connections]

    @staticmethod
    def delete_token(provider: str, org_id: str | None = None) -> bool:
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
            >>> oauth.delete_token("microsoft")
        """
        context = require_permission("oauth.delete")
        target_org = org_id or context.org_id

        storage = OAuthStorageService()
        return storage.delete_token(provider, target_org)

    @staticmethod
    def refresh_token(provider: str, org_id: str | None = None) -> dict[str, Any]:
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
            >>> new_token = oauth.refresh_token("microsoft")
            >>> access_token = new_token["access_token"]
        """
        context = get_context()
        target_org = org_id or context.org_id

        storage = OAuthStorageService()
        new_token = storage.refresh_token(provider, target_org)

        if not new_token:
            raise ValueError(f"Failed to refresh token for provider: {provider}")

        return new_token
