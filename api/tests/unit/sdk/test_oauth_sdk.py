"""Tests for bifrost.oauth SDK methods"""

import json
import pytest
from unittest.mock import AsyncMock, Mock, patch, MagicMock

from bifrost.oauth import oauth


class TestOAuthGet:
    """Test oauth.get() returns full connection config with credentials"""

    @pytest.mark.asyncio
    async def test_get_returns_full_config_with_credentials(self):
        """oauth.get() should return connection config with client_secret and tokens"""
        with patch('bifrost.oauth.get_context') as mock_get_context, \
             patch('bifrost.oauth.OAuthStorageService') as MockStorage, \
             patch('bifrost.oauth.KeyVaultClient') as MockKV:

            # Setup mock context
            mock_context = Mock()
            mock_context.scope = "test-org"
            mock_get_context.return_value = mock_context

            # Setup mock connection
            mock_connection = Mock()
            mock_connection.connection_name = "partner_center"
            mock_connection.client_id = "test-client-id"
            mock_connection.client_secret_ref = "kv-secret-ref"
            mock_connection.authorization_url = "https://login.microsoftonline.com/common/oauth2/v2.0/authorize"
            mock_connection.token_url = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
            mock_connection.scopes = "offline_access https://api.partnercenter.microsoft.com/user_impersonation"
            mock_connection.oauth_response_ref = "kv-oauth-response-ref"

            mock_storage = MockStorage.return_value
            mock_storage.get_connection = AsyncMock(return_value=mock_connection)

            # Setup mock KeyVault client
            mock_kv_instance = MagicMock()
            mock_kv_instance.get_secret = AsyncMock(side_effect=[
                "test-client-secret",  # First call for client_secret
                json.dumps({  # Second call for oauth_response
                    "refresh_token": "test-refresh-token",
                    "access_token": "test-access-token",
                    "expires_at": "2025-11-25T23:00:00Z"
                })
            ])
            mock_kv_instance.__aenter__ = AsyncMock(return_value=mock_kv_instance)
            mock_kv_instance.__aexit__ = AsyncMock(return_value=None)
            MockKV.return_value = mock_kv_instance

            # Execute
            result = await oauth.get("partner_center")

            # Verify
            assert result is not None
            assert result["connection_name"] == "partner_center"
            assert result["client_id"] == "test-client-id"
            assert result["client_secret"] == "test-client-secret"
            assert result["authorization_url"] == "https://login.microsoftonline.com/common/oauth2/v2.0/authorize"
            assert result["token_url"] == "https://login.microsoftonline.com/common/oauth2/v2.0/token"
            assert result["scopes"] == "offline_access https://api.partnercenter.microsoft.com/user_impersonation"
            assert result["refresh_token"] == "test-refresh-token"
            assert result["access_token"] == "test-access-token"
            assert result["expires_at"] == "2025-11-25T23:00:00Z"

    @pytest.mark.asyncio
    async def test_get_returns_none_for_nonexistent_provider(self):
        """oauth.get() should return None if provider not found"""
        with patch('bifrost.oauth.get_context') as mock_get_context, \
             patch('bifrost.oauth.OAuthStorageService') as MockStorage:

            mock_context = Mock()
            mock_context.scope = "test-org"
            mock_get_context.return_value = mock_context

            mock_storage = MockStorage.return_value
            mock_storage.get_connection = AsyncMock(return_value=None)

            result = await oauth.get("nonexistent")

            assert result is None

    @pytest.mark.asyncio
    async def test_get_without_client_secret(self):
        """oauth.get() should work without client_secret (PKCE flow)"""
        with patch('bifrost.oauth.get_context') as mock_get_context, \
             patch('bifrost.oauth.OAuthStorageService') as MockStorage, \
             patch('bifrost.oauth.KeyVaultClient') as MockKV:

            mock_context = Mock()
            mock_context.scope = "test-org"
            mock_get_context.return_value = mock_context

            # Connection without client_secret_ref (PKCE)
            mock_connection = Mock()
            mock_connection.connection_name = "pkce_provider"
            mock_connection.client_id = "test-client-id"
            mock_connection.client_secret_ref = None  # No secret for PKCE
            mock_connection.authorization_url = "https://auth.example.com/authorize"
            mock_connection.token_url = "https://auth.example.com/token"
            mock_connection.scopes = "openid profile"
            mock_connection.oauth_response_ref = "kv-oauth-response-ref"

            mock_storage = MockStorage.return_value
            mock_storage.get_connection = AsyncMock(return_value=mock_connection)

            # Setup mock KeyVault for oauth_response only
            mock_kv_instance = MagicMock()
            mock_kv_instance.get_secret = AsyncMock(return_value=json.dumps({
                "refresh_token": "test-refresh-token",
                "access_token": "test-access-token",
                "expires_at": "2025-11-25T23:00:00Z"
            }))
            mock_kv_instance.__aenter__ = AsyncMock(return_value=mock_kv_instance)
            mock_kv_instance.__aexit__ = AsyncMock(return_value=None)
            MockKV.return_value = mock_kv_instance

            result = await oauth.get("pkce_provider")

            assert result is not None
            assert result["client_id"] == "test-client-id"
            assert result["client_secret"] is None  # No secret for PKCE
            assert result["refresh_token"] == "test-refresh-token"

    @pytest.mark.asyncio
    async def test_get_without_oauth_response(self):
        """oauth.get() should work without oauth_response (pre-auth connection)"""
        with patch('bifrost.oauth.get_context') as mock_get_context, \
             patch('bifrost.oauth.OAuthStorageService') as MockStorage, \
             patch('bifrost.oauth.KeyVaultClient') as MockKV:

            mock_context = Mock()
            mock_context.scope = "test-org"
            mock_get_context.return_value = mock_context

            # Connection without oauth_response_ref (not yet authorized)
            mock_connection = Mock()
            mock_connection.connection_name = "pending_provider"
            mock_connection.client_id = "test-client-id"
            mock_connection.client_secret_ref = "kv-secret-ref"
            mock_connection.authorization_url = "https://auth.example.com/authorize"
            mock_connection.token_url = "https://auth.example.com/token"
            mock_connection.scopes = "openid"
            mock_connection.oauth_response_ref = None  # No tokens yet

            mock_storage = MockStorage.return_value
            mock_storage.get_connection = AsyncMock(return_value=mock_connection)

            # Setup mock KeyVault for client_secret only
            mock_kv_instance = MagicMock()
            mock_kv_instance.get_secret = AsyncMock(return_value="test-client-secret")
            mock_kv_instance.__aenter__ = AsyncMock(return_value=mock_kv_instance)
            mock_kv_instance.__aexit__ = AsyncMock(return_value=None)
            MockKV.return_value = mock_kv_instance

            result = await oauth.get("pending_provider")

            assert result is not None
            assert result["client_id"] == "test-client-id"
            assert result["client_secret"] == "test-client-secret"
            assert result["refresh_token"] is None
            assert result["access_token"] is None

    @pytest.mark.asyncio
    async def test_get_uses_provided_org_id(self):
        """oauth.get() should use provided org_id instead of context scope"""
        with patch('bifrost.oauth.get_context') as mock_get_context, \
             patch('bifrost.oauth.OAuthStorageService') as MockStorage:

            mock_context = Mock()
            mock_context.scope = "default-org"
            mock_get_context.return_value = mock_context

            mock_storage = MockStorage.return_value
            mock_storage.get_connection = AsyncMock(return_value=None)

            await oauth.get("provider", org_id="custom-org")

            # Verify get_connection was called with custom org_id
            mock_storage.get_connection.assert_called_once_with("custom-org", "provider")

    @pytest.mark.asyncio
    async def test_get_handles_keyvault_error_gracefully(self):
        """oauth.get() should handle KeyVault errors and still return partial data"""
        with patch('bifrost.oauth.get_context') as mock_get_context, \
             patch('bifrost.oauth.OAuthStorageService') as MockStorage, \
             patch('bifrost.oauth.KeyVaultClient') as MockKV:

            mock_context = Mock()
            mock_context.scope = "test-org"
            mock_get_context.return_value = mock_context

            mock_connection = Mock()
            mock_connection.connection_name = "provider"
            mock_connection.client_id = "test-client-id"
            mock_connection.client_secret_ref = "kv-secret-ref"
            mock_connection.authorization_url = "https://auth.example.com/authorize"
            mock_connection.token_url = "https://auth.example.com/token"
            mock_connection.scopes = "openid"
            mock_connection.oauth_response_ref = "kv-oauth-response-ref"

            mock_storage = MockStorage.return_value
            mock_storage.get_connection = AsyncMock(return_value=mock_connection)

            # KeyVault raises error
            mock_kv_instance = MagicMock()
            mock_kv_instance.get_secret = AsyncMock(side_effect=Exception("KeyVault unavailable"))
            mock_kv_instance.__aenter__ = AsyncMock(return_value=mock_kv_instance)
            mock_kv_instance.__aexit__ = AsyncMock(return_value=None)
            MockKV.return_value = mock_kv_instance

            # Should still return partial data without raising
            result = await oauth.get("provider")

            assert result is not None
            assert result["client_id"] == "test-client-id"
            assert result["client_secret"] is None  # Failed to retrieve
            assert result["refresh_token"] is None  # Failed to retrieve
