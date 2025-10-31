"""
Test OAuth global fallback behavior.

Verifies that oauth.get_token() falls back to GLOBAL scope
when a token is not found in the org-specific scope.
"""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from shared.services.oauth_storage_service import OAuthStorageService


class TestOAuthGlobalFallback:
    """Test that OAuth tokens fall back to GLOBAL scope"""

    @pytest.mark.asyncio
    async def test_get_connection_fallback_to_global(self):
        """Test that get_connection falls back to GLOBAL when not found in org"""
        from datetime import datetime, timedelta

        # Mock KeyVaultClient to avoid real Azure access
        with patch('shared.services.oauth_storage_service.KeyVaultClient') as mock_kv_class:
            mock_kv = MagicMock()
            mock_kv_class.return_value.__aenter__ = AsyncMock(return_value=mock_kv)
            mock_kv_class.return_value.__aexit__ = AsyncMock(return_value=None)
            mock_kv.set_secret = AsyncMock()
            mock_kv.delete_secret = AsyncMock()

            storage = OAuthStorageService()

            # Create connection in GLOBAL scope
            test_provider = "test_fallback_provider"

            # First create the connection
            from shared.models import CreateOAuthConnectionRequest
            connection_create = CreateOAuthConnectionRequest(
                connection_name=test_provider,
                oauth_flow_type="authorization_code",
                authorization_url="https://example.com/auth",
                token_url="https://example.com/token",
                client_id="test_client"
            )
            await storage.create_connection("GLOBAL", connection_create, "test-user")

            # Store tokens in GLOBAL
            expires_at = datetime.utcnow() + timedelta(hours=1)
            await storage.store_tokens(
                org_id="GLOBAL",
                connection_name=test_provider,
                access_token="global_test_token_123",
                refresh_token="global_refresh_456",
                expires_at=expires_at,
                token_type="Bearer",
                updated_by="test-user"
            )

            try:
                # Try to get from a different org (should fall back to GLOBAL)
                connection = await storage.get_connection("test-org-123", test_provider)

                # Verify we got the GLOBAL connection
                assert connection is not None
                assert connection.connection_name == test_provider
                assert connection.status == "completed"

            finally:
                # Cleanup
                await storage.delete_connection("GLOBAL", test_provider)

    @pytest.mark.asyncio
    async def test_get_connection_org_specific_takes_precedence(self):
        """Test that org-specific tokens take precedence over GLOBAL"""
        from datetime import datetime, timedelta
        import json

        # Mock KeyVaultClient to avoid real Azure access
        with patch('shared.services.oauth_storage_service.KeyVaultClient') as mock_kv_class:
            mock_kv = MagicMock()
            mock_kv_class.return_value.__aenter__ = AsyncMock(return_value=mock_kv)
            mock_kv_class.return_value.__aexit__ = AsyncMock(return_value=None)
            mock_kv.set_secret = AsyncMock()
            mock_kv.delete_secret = AsyncMock()

            # Track secret values by name for get_secret calls
            secrets_store = {}
            async def mock_get_secret(ref):
                return secrets_store.get(ref, '{"access_token": "default"}')

            async def mock_set_secret(ref, value):
                secrets_store[ref] = value

            mock_kv.get_secret = AsyncMock(side_effect=mock_get_secret)
            mock_kv.set_secret = AsyncMock(side_effect=mock_set_secret)

            storage = OAuthStorageService()

            test_provider = "test_precedence_provider"
            test_org = "test-org-456"

            # Create connection in GLOBAL
            from shared.models import CreateOAuthConnectionRequest
            connection_create = CreateOAuthConnectionRequest(
                connection_name=test_provider,
                oauth_flow_type="authorization_code",
                authorization_url="https://example.com/auth",
                token_url="https://example.com/token",
                client_id="test_client"
            )
            await storage.create_connection("GLOBAL", connection_create, "test-user")

            # Store token in GLOBAL
            expires_at = datetime.utcnow() + timedelta(hours=1)
            await storage.store_tokens(
                org_id="GLOBAL",
                connection_name=test_provider,
                access_token="global_token",
                refresh_token=None,
                expires_at=expires_at,
                token_type="Bearer",
                updated_by="test-user"
            )

            # Create connection in org-specific
            await storage.create_connection(test_org, connection_create, "test-user")

            # Store different token in org-specific
            await storage.store_tokens(
                org_id=test_org,
                connection_name=test_provider,
                access_token="org_specific_token",
                refresh_token=None,
                expires_at=expires_at,
                token_type="Bearer",
                updated_by="test-user"
            )

            try:
                # Get connection for the specific org
                connection = await storage.get_connection(test_org, test_provider)

                # Verify we got the org-specific connection (not GLOBAL)
                assert connection is not None
                assert connection.org_id == test_org

                # Verify the token ref points to org-specific token
                secret_value = await mock_kv.get_secret(connection.oauth_response_ref)
                token = json.loads(secret_value)
                # Should get org-specific token, not global
                assert token["access_token"] == "org_specific_token"

            finally:
                # Cleanup both
                await storage.delete_connection("GLOBAL", test_provider)
                await storage.delete_connection(test_org, test_provider)

    @pytest.mark.asyncio
    async def test_get_connection_returns_none_when_not_found(self):
        """Test that get_connection returns None when token not found anywhere"""
        storage = OAuthStorageService()

        # Try to get a connection that doesn't exist
        connection = await storage.get_connection(
            "nonexistent-org",
            "nonexistent_provider_xyz"
        )

        # Should return None
        assert connection is None
