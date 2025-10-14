"""
Unit Tests: Key Vault Client

Tests the KeyVaultClient class in isolation:
- Secret retrieval with org-scoped fallback
- Caching behavior
- Local environment variable fallback
- Error handling
- Secret name formatting
"""

import pytest
import os
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta


class TestKeyVaultClient:
    """Unit tests for KeyVaultClient"""

    @pytest.fixture
    def mock_secret_client(self):
        """Create a mock SecretClient"""
        return Mock()

    @pytest.fixture
    def keyvault_client(self, mock_secret_client):
        """Create KeyVaultClient with mocked dependencies"""
        from shared.keyvault import KeyVaultClient

        with patch('engine.shared.keyvault.SecretClient', return_value=mock_secret_client):
            with patch('engine.shared.keyvault.DefaultAzureCredential'):
                client = KeyVaultClient(
                    vault_url="https://test-vault.vault.azure.net/",
                    cache_duration=3600
                )
                client._client = mock_secret_client
                return client

    def test_initialization_with_vault_url(self):
        """Test client initializes with provided vault URL"""
        from shared.keyvault import KeyVaultClient

        with patch('engine.shared.keyvault.SecretClient'):
            with patch('engine.shared.keyvault.DefaultAzureCredential'):
                client = KeyVaultClient(vault_url="https://my-vault.vault.azure.net/")
                assert client.vault_url == "https://my-vault.vault.azure.net/"

    def test_initialization_from_env_var(self):
        """Test client initializes from AZURE_KEY_VAULT_URL environment variable"""
        from shared.keyvault import KeyVaultClient

        with patch.dict(os.environ, {'AZURE_KEY_VAULT_URL': 'https://env-vault.vault.azure.net/'}):
            with patch('engine.shared.keyvault.SecretClient'):
                with patch('engine.shared.keyvault.DefaultAzureCredential'):
                    client = KeyVaultClient()
                    assert client.vault_url == "https://env-vault.vault.azure.net/"

    def test_secret_name_formatting_org_scoped(self, keyvault_client):
        """Test secret name formatting for org-scoped secrets"""
        name = keyvault_client._build_secret_name("org-123", "api-key")
        assert name == "org-123--api-key"

    def test_secret_name_formatting_global(self, keyvault_client):
        """Test secret name formatting for global secrets"""
        name = keyvault_client._build_secret_name("GLOBAL", "smtp-password")
        assert name == "GLOBAL--smtp-password"

    def test_get_secret_from_keyvault(self, keyvault_client, mock_secret_client):
        """Test successful secret retrieval from Key Vault"""
        # Mock the secret response
        mock_secret = Mock()
        mock_secret.value = "secret-value-from-vault"
        mock_secret_client.get_secret.return_value = mock_secret

        result = keyvault_client.get_secret("org-123", "api-key")

        assert result == "secret-value-from-vault"
        mock_secret_client.get_secret.assert_called_once_with("org-123--api-key")

    def test_get_secret_org_fallback_to_global(self, keyvault_client, mock_secret_client):
        """Test fallback from org-scoped to global secret"""
        from azure.core.exceptions import ResourceNotFoundError

        # First call (org-scoped) raises NotFound
        # Second call (global) succeeds
        mock_secret = Mock()
        mock_secret.value = "global-secret-value"

        def side_effect(name):
            if name == "org-123--api-key":
                raise ResourceNotFoundError("Not found")
            else:  # GLOBAL--api-key
                return mock_secret

        mock_secret_client.get_secret.side_effect = side_effect

        result = keyvault_client.get_secret("org-123", "api-key")

        assert result == "global-secret-value"
        assert mock_secret_client.get_secret.call_count == 2
        mock_secret_client.get_secret.assert_any_call("org-123--api-key")
        mock_secret_client.get_secret.assert_any_call("GLOBAL--api-key")

    def test_get_secret_fallback_to_env_var(self, keyvault_client, mock_secret_client):
        """Test fallback to environment variable when Key Vault unavailable"""
        from azure.core.exceptions import ResourceNotFoundError

        # Both Key Vault calls fail
        mock_secret_client.get_secret.side_effect = ResourceNotFoundError("Not found")

        # Set environment variable (note: org-123 becomes ORG_123)
        with patch.dict(os.environ, {'ORG_123__API_KEY': 'env-var-value'}):
            result = keyvault_client.get_secret("org-123", "api-key")

        assert result == "env-var-value"

    def test_get_secret_global_fallback_to_env_var(self, keyvault_client, mock_secret_client):
        """Test global secret fallback to environment variable"""
        from azure.core.exceptions import ResourceNotFoundError

        mock_secret_client.get_secret.side_effect = ResourceNotFoundError("Not found")

        with patch.dict(os.environ, {'GLOBAL__SMTP_PASSWORD': 'global-env-value'}):
            result = keyvault_client.get_secret("GLOBAL", "smtp-password")

        assert result == "global-env-value"

    def test_get_secret_not_found_raises_error(self, keyvault_client, mock_secret_client):
        """Test that missing secret raises KeyError"""
        from azure.core.exceptions import ResourceNotFoundError

        mock_secret_client.get_secret.side_effect = ResourceNotFoundError("Not found")

        with pytest.raises(KeyError, match="not found"):
            keyvault_client.get_secret("org-123", "nonexistent-key")

    def test_secret_caching(self, keyvault_client, mock_secret_client):
        """Test that secrets are cached for the configured duration"""
        mock_secret = Mock()
        mock_secret.value = "cached-secret-value"
        mock_secret_client.get_secret.return_value = mock_secret

        # First call
        result1 = keyvault_client.get_secret("org-123", "api-key")
        # Second call (should use cache)
        result2 = keyvault_client.get_secret("org-123", "api-key")

        assert result1 == "cached-secret-value"
        assert result2 == "cached-secret-value"

        # Should only call Key Vault once (second call uses cache)
        mock_secret_client.get_secret.assert_called_once_with("org-123--api-key")

    def test_cache_expiration(self, keyvault_client, mock_secret_client):
        """Test that cache expires after configured duration"""
        mock_secret = Mock()
        mock_secret.value = "secret-value"
        mock_secret_client.get_secret.return_value = mock_secret

        # First call (populate cache)
        keyvault_client.get_secret("org-123", "api-key")

        # Manually expire the cache entry
        cache_key = "org-123--api-key"
        if cache_key in keyvault_client._cache:
            value, timestamp = keyvault_client._cache[cache_key]
            # Set timestamp to past expiration
            keyvault_client._cache[cache_key] = (value, timestamp - 7200)

        # Second call (cache expired, should fetch again)
        keyvault_client.get_secret("org-123", "api-key")

        # Should call Key Vault twice
        assert mock_secret_client.get_secret.call_count == 2

    def test_env_var_name_conversion(self, keyvault_client):
        """Test conversion of secret key to environment variable name"""
        # org-123 -> ORG_123 (uppercase, hyphens to underscores)
        # api-key -> API_KEY (uppercase, hyphens to underscores)
        env_name = keyvault_client._build_env_var_name("org-123", "api-key")
        assert env_name == "ORG_123__API_KEY"

    def test_env_var_name_conversion_global(self, keyvault_client):
        """Test conversion of global secret key to environment variable name"""
        env_name = keyvault_client._build_env_var_name("GLOBAL", "smtp-password")
        assert env_name == "GLOBAL__SMTP_PASSWORD"

    def test_list_secrets_from_keyvault(self, keyvault_client, mock_secret_client):
        """Test listing secrets from Key Vault"""
        # Mock secret properties
        mock_props1 = Mock()
        mock_props1.name = "org-123--api-key"
        mock_props2 = Mock()
        mock_props2.name = "GLOBAL--smtp-password"
        mock_props3 = Mock()
        mock_props3.name = "org-456--client-secret"

        mock_secret_client.list_properties_of_secrets.return_value = [
            mock_props1, mock_props2, mock_props3
        ]

        result = keyvault_client.list_secrets()

        assert len(result) == 3
        assert "org-123--api-key" in result
        assert "GLOBAL--smtp-password" in result
        assert "org-456--client-secret" in result

    def test_list_secrets_with_org_filter(self, keyvault_client, mock_secret_client):
        """Test listing secrets filtered by organization"""
        mock_props1 = Mock()
        mock_props1.name = "org-123--api-key"
        mock_props2 = Mock()
        mock_props2.name = "GLOBAL--smtp-password"
        mock_props3 = Mock()
        mock_props3.name = "org-456--client-secret"

        mock_secret_client.list_properties_of_secrets.return_value = [
            mock_props1, mock_props2, mock_props3
        ]

        result = keyvault_client.list_secrets(org_id="org-123")

        # Should include org-123 secrets AND global secrets
        assert len(result) == 2
        assert "org-123--api-key" in result
        assert "GLOBAL--smtp-password" in result
        assert "org-456--client-secret" not in result

    def test_list_secrets_error_handling(self, keyvault_client, mock_secret_client):
        """Test error handling when listing secrets fails"""
        mock_secret_client.list_properties_of_secrets.side_effect = Exception("Connection error")

        with pytest.raises(Exception, match="Connection error"):
            keyvault_client.list_secrets()

    def test_keyvault_unavailable_fallback(self, keyvault_client, mock_secret_client):
        """Test graceful fallback when Key Vault is completely unavailable"""
        from azure.core.exceptions import ServiceRequestError

        # Simulate network error
        mock_secret_client.get_secret.side_effect = ServiceRequestError("Network unavailable")

        with patch.dict(os.environ, {'ORG_123__API_KEY': 'fallback-value'}):
            result = keyvault_client.get_secret("org-123", "api-key")

        assert result == "fallback-value"

    def test_no_vault_url_allows_initialization(self):
        """Test that missing vault URL allows initialization but client is None"""
        from shared.keyvault import KeyVaultClient

        with patch.dict(os.environ, {}, clear=True):
            client = KeyVaultClient()
            # Client should be initialized but vault_url is None and _client is None
            assert client.vault_url is None
            assert client._client is None
