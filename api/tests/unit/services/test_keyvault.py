"""
Unit tests for KeyVaultClient

Tests cover:
- Creating secrets
- Retrieving secrets
- Updating secrets
- Deleting secrets
- Listing secrets
- Error handling (auth, not found, permission denied)
- Health checks
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from azure.core.exceptions import (
    ResourceNotFoundError,
    HttpResponseError,
    ClientAuthenticationError,
    ServiceRequestError,
)

from shared.keyvault import KeyVaultClient


class TestKeyVaultClientInitialization:
    """Test KeyVaultClient initialization"""

    async def test_init_with_vault_url(self, mock_secret_client, mock_default_credential):
        """Should initialize with provided vault URL"""
        vault_url = "https://test-vault.vault.azure.net/"

        client = KeyVaultClient(vault_url=vault_url)

        assert client.vault_url == vault_url
        mock_secret_client["client_class"].assert_called_once()

    async def test_init_with_env_variable(self, mock_secret_client, mock_default_credential):
        """Should use AZURE_KEY_VAULT_URL environment variable"""
        with patch.dict("os.environ", {"AZURE_KEY_VAULT_URL": "https://env-vault.vault.azure.net/"}):
            client = KeyVaultClient()
            assert client.vault_url == "https://env-vault.vault.azure.net/"

    async def test_init_without_url_raises_error(self, mock_default_credential):
        """Should raise error when no vault URL provided"""
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(ValueError, match="AZURE_KEY_VAULT_URL"):
                KeyVaultClient()


class TestKeyVaultClientSecrets:
    """Test secret operations"""

    async def test_create_secret_success(self, mock_secret_client, mock_default_credential):
        """Should create a new secret"""
        client = KeyVaultClient(vault_url="https://test-vault.vault.azure.net/")

        result = await client.set_secret("test-org--api-key", "secret-value-123")

        assert result["name"] == "test-org--api-key"
        assert "saved" in result["message"].lower()

    async def test_create_secret_with_global_org(self, mock_secret_client, mock_default_credential):
        """Should create secret with GLOBAL org scope"""
        client = KeyVaultClient(vault_url="https://test-vault.vault.azure.net/")

        result = await client.set_secret("GLOBAL--platform-key", "platform-secret")

        assert result["name"] == "GLOBAL--platform-key"

    async def test_create_secret_invalid_name(self, mock_secret_client, mock_default_credential):
        """Should reject secret with invalid name"""
        client = KeyVaultClient(vault_url="https://test-vault.vault.azure.net/")

        # Name with invalid characters
        with pytest.raises(ValueError, match="Invalid secret name"):
            await client.set_secret("invalid@name!", "value")

    async def test_update_secret_success(self, mock_secret_client, mock_default_credential):
        """Should update existing secret"""
        client = KeyVaultClient(vault_url="https://test-vault.vault.azure.net/")

        result = await client.set_secret("test-org--api-key", "new-secret-value")

        assert result["name"] == "test-org--api-key"
        assert "saved" in result["message"].lower()

    async def test_get_secret_success(self, mock_secret_client, mock_default_credential):
        """Should retrieve secret value"""
        client = KeyVaultClient(vault_url="https://test-vault.vault.azure.net/")

        # First create a secret
        await client.set_secret("test-org--test-key", "secret-value")

        # Then retrieve it
        result = await client.get_secret("test-org--test-key")

        assert result == "secret-value"

    async def test_get_secret_not_found(self, mock_secret_client, mock_default_credential):
        """Should raise error when secret not found"""
        client = KeyVaultClient(vault_url="https://test-vault.vault.azure.net/")

        with pytest.raises(ResourceNotFoundError):
            await client.get_secret("nonexistent-key")

    async def test_delete_secret_success(self, mock_secret_client, mock_default_credential):
        """Should delete secret"""
        client = KeyVaultClient(vault_url="https://test-vault.vault.azure.net/")

        # Create and delete
        await client.set_secret("test-org--temp-key", "temp-value")
        result = await client.delete_secret("test-org--temp-key")

        assert result["name"] == "test-org--temp-key"
        assert "deleted" in result["message"].lower()

    async def test_delete_secret_not_found(self, mock_default_credential):
        """Should raise error when deleting non-existent secret"""
        with patch("shared.keyvault.SecretClient") as mock_client_class:
            mock_instance = MagicMock()
            mock_client_class.return_value = mock_instance

            # Mock the delete_secret to raise ResourceNotFoundError
            mock_instance.delete_secret = AsyncMock(side_effect=ResourceNotFoundError("Secret not found"))

            client = KeyVaultClient(vault_url="https://test-vault.vault.azure.net/")
            with pytest.raises(ResourceNotFoundError):
                await client.delete_secret("nonexistent-key")


class TestKeyVaultClientList:
    """Test listing secrets"""

    async def test_list_all_secrets(self, mock_secret_client, mock_default_credential):
        """Should list all secrets in vault"""
        client = KeyVaultClient(vault_url="https://test-vault.vault.azure.net/")

        # Create some secrets
        await client.set_secret("org1--key1", "value1")
        await client.set_secret("org1--key2", "value2")
        await client.set_secret("org2--key3", "value3")

        result = await client.list_secrets()

        assert len(result) == 3
        assert "org1--key1" in result
        assert "org2--key3" in result

    async def test_list_org_secrets(self, mock_secret_client, mock_default_credential):
        """Should filter secrets by organization"""
        client = KeyVaultClient(vault_url="https://test-vault.vault.azure.net/")

        # Create secrets for different orgs
        await client.set_secret("org1--key1", "value1")
        await client.set_secret("org1--key2", "value2")
        await client.set_secret("org2--key3", "value3")
        await client.set_secret("GLOBAL--global-key", "global-value")

        # List org1 secrets (should include GLOBAL)
        result = await client.list_secrets(org_id="org1")

        assert "org1--key1" in result
        assert "org1--key2" in result
        assert "org2--key3" not in result
        # Should include GLOBAL secrets
        assert "GLOBAL--global-key" in result

    async def test_list_secrets_empty_vault(self, mock_secret_client, mock_default_credential):
        """Should return empty list for empty vault"""
        client = KeyVaultClient(vault_url="https://test-vault.vault.azure.net/")

        result = await client.list_secrets()

        assert result == []

    async def test_list_secrets_permission_denied(self, mock_secret_client, mock_default_credential):
        """Should handle permission denied gracefully"""
        client = KeyVaultClient(vault_url="https://test-vault.vault.azure.net/")

        # Mock permission denied error
        error = HttpResponseError("Permission denied")
        error.status_code = 403
        mock_secret_client["instance"].list_properties_of_secrets.side_effect = error

        result = await client.list_secrets()

        # Should return empty list instead of raising
        assert result == []


class TestKeyVaultClientSecretBuilding:
    """Test secret name building and validation"""

    def test_build_secret_name_org_scoped(self, mock_secret_client, mock_default_credential):
        """Should build org-scoped secret names"""
        client = KeyVaultClient(vault_url="https://test-vault.vault.azure.net/")

        name = client._build_secret_name("test-org", "api-key")

        assert name == "test-org--api-key"

    async def test_build_secret_name_global(self, mock_secret_client, mock_default_credential):
        """Should build global secret names"""
        client = KeyVaultClient(vault_url="https://test-vault.vault.azure.net/")

        name = client._build_secret_name("GLOBAL", "platform-key")

        assert name == "GLOBAL--platform-key"

    async def test_is_valid_secret_name_valid_cases(self, mock_secret_client, mock_default_credential):
        """Should accept valid secret names"""
        valid_names = [
            "test-secret",
            "test-secret-123",
            "test",
            "GLOBAL--api-key",
            "org-id--secret-key-123",
        ]

        for name in valid_names:
            assert KeyVaultClient._is_valid_secret_name(name) is True

    async def test_is_valid_secret_name_invalid_cases(self, mock_secret_client, mock_default_credential):
        """Should reject invalid secret names"""
        invalid_names = [
            "test@secret",  # Special char
            "test secret",  # Space
            "test_secret",  # Underscore (not allowed)
            "",  # Empty
            "x" * 128,  # Too long
        ]

        for name in invalid_names:
            assert KeyVaultClient._is_valid_secret_name(name) is False


class TestKeyVaultClientErrorHandling:
    """Test error handling"""

    async def test_create_secret_permission_denied(self, mock_default_credential):
        """Should handle permission denied error"""
        with patch("shared.keyvault.SecretClient") as mock_client_class:
            mock_instance = MagicMock()
            mock_client_class.return_value = mock_instance

            # Mock permission denied
            error = HttpResponseError("Permission denied")
            error.status_code = 403
            mock_instance.set_secret.side_effect = error

            client = KeyVaultClient(vault_url="https://test-vault.vault.azure.net/")
            with pytest.raises(HttpResponseError):
                await client.set_secret("test-org--key", "value")

    async def test_get_secret_connection_error(self, mock_secret_client, mock_default_credential):
        """Should handle connection errors"""
        client = KeyVaultClient(vault_url="https://test-vault.vault.azure.net/")

        # Mock connection error
        mock_secret_client["instance"].get_secret.side_effect = ResourceNotFoundError("Not found")

        with pytest.raises(ResourceNotFoundError):
            await client.get_secret("test-org--key")


class TestKeyVaultClientHealthCheck:
    """Test health check functionality"""

    async def test_health_check_healthy(self, mock_secret_client, mock_default_credential):
        """Should report healthy status"""
        client = KeyVaultClient(vault_url="https://test-vault.vault.azure.net/")

        # Add a secret for testing
        await client.set_secret("test-org--health-check", "value")

        result = await client.health_check()

        assert result["status"] == "healthy"
        assert result["can_connect"] is True
        assert result["can_list_secrets"] is True
        assert result["can_get_secrets"] is True
        assert result["secret_count"] >= 1
        assert result["error"] is None

    async def test_health_check_empty_vault(self, mock_secret_client, mock_default_credential):
        """Should report healthy for empty vault"""
        client = KeyVaultClient(vault_url="https://test-vault.vault.azure.net/")

        result = await client.health_check()

        assert result["status"] == "healthy"
        assert result["can_connect"] is True
        assert result["secret_count"] == 0

    async def test_health_check_list_permission_denied(self, mock_default_credential):
        """Should report degraded status when list permission denied"""
        with patch("shared.keyvault.SecretClient") as mock_client_class:
            mock_instance = MagicMock()
            mock_client_class.return_value = mock_instance

            # Mock list permission denied
            error = HttpResponseError("Permission denied")
            error.status_code = 403
            mock_instance.list_properties_of_secrets.side_effect = error

            client = KeyVaultClient(vault_url="https://test-vault.vault.azure.net/")
            result = await client.health_check()

            assert result["status"] == "degraded"
            assert result["can_connect"] is True
            assert result["can_list_secrets"] is False

    async def test_health_check_authentication_error(self, mock_default_credential):
        """Should report unhealthy status on auth error"""
        with patch("shared.keyvault.SecretClient") as mock_client_class:
            mock_instance = MagicMock()
            mock_client_class.return_value = mock_instance

            # Mock auth error
            mock_instance.list_properties_of_secrets.side_effect = ClientAuthenticationError("Auth failed")

            client = KeyVaultClient(vault_url="https://test-vault.vault.azure.net/")
            result = await client.health_check()

            assert result["status"] == "unhealthy"
            assert result["can_connect"] is False
            assert "Authentication" in result["error"]

    async def test_health_check_connection_error(self, mock_default_credential):
        """Should report unhealthy status on connection error"""
        with patch("shared.keyvault.SecretClient") as mock_client_class:
            mock_instance = MagicMock()
            mock_client_class.return_value = mock_instance

            # Mock connection error
            mock_instance.list_properties_of_secrets.side_effect = ServiceRequestError("Network error")

            client = KeyVaultClient(vault_url="https://test-vault.vault.azure.net/")
            result = await client.health_check()

            assert result["status"] == "unhealthy"
            assert result["can_connect"] is False
            assert "Network" in result["error"]
