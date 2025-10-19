"""
Unit tests for health handlers
Tests health check logic with mocked dependencies
"""

from datetime import datetime
from unittest.mock import MagicMock

from shared.handlers.health_handlers import (
    check_api_health,
    check_keyvault_health,
    perform_general_health_check,
    perform_keyvault_health_check,
)
from shared.models import GeneralHealthResponse, HealthCheck, KeyVaultHealthResponse


class TestCheckApiHealth:
    """Tests for check_api_health"""

    def test_returns_healthy_check(self):
        """Test that API health is always healthy"""
        result = check_api_health()

        assert isinstance(result, HealthCheck)
        assert result.service == "API"
        assert result.healthy is True
        assert result.message == "API is running"
        assert result.metadata == {}

    def test_check_structure(self):
        """Test the HealthCheck model structure"""
        result = check_api_health()

        # Verify all expected fields
        assert hasattr(result, 'service')
        assert hasattr(result, 'healthy')
        assert hasattr(result, 'message')
        assert hasattr(result, 'metadata')


class TestCheckKeyVaultHealth:
    """Tests for check_keyvault_health"""

    def test_none_manager_returns_degraded(self):
        """Test health check when manager is None"""
        result_check, status = check_keyvault_health(None)

        assert isinstance(result_check, HealthCheck)
        assert result_check.service == "Key Vault"
        assert result_check.healthy is False
        assert result_check.message == "Key Vault manager not initialized"
        assert status == "degraded"
        assert result_check.metadata == {}

    def test_healthy_manager(self):
        """Test health check when Key Vault is healthy"""
        mock_manager = MagicMock()
        mock_manager.vault_url = "https://test-vault.vault.azure.net/"
        mock_manager.health_check.return_value = {
            "status": "healthy",
            "can_connect": True,
            "can_list_secrets": True,
            "can_get_secrets": True,
            "secret_count": 10
        }

        result_check, status = check_keyvault_health(mock_manager)

        assert result_check.service == "Key Vault"
        assert result_check.healthy is True
        assert result_check.message == "Key Vault accessible"
        assert status == "healthy"
        assert result_check.metadata["vaultUrl"] == "https://test-vault.vault.azure.net/"
        assert result_check.metadata["canConnect"] is True
        assert result_check.metadata["canListSecrets"] is True
        assert result_check.metadata["canGetSecrets"] is True
        assert result_check.metadata["secretCount"] == 10

    def test_degraded_manager(self):
        """Test health check when Key Vault is degraded"""
        mock_manager = MagicMock()
        mock_manager.vault_url = "https://test-vault.vault.azure.net/"
        mock_manager.health_check.return_value = {
            "status": "degraded",
            "can_connect": True,
            "can_list_secrets": False,
            "can_get_secrets": True,
            "secret_count": 5,
            "error": "Some permissions limited"
        }

        result_check, status = check_keyvault_health(mock_manager)

        assert result_check.service == "Key Vault"
        assert result_check.healthy is False
        assert result_check.message == "Some permissions limited"
        assert status == "degraded"
        assert result_check.metadata["canListSecrets"] is False

    def test_unhealthy_manager(self):
        """Test health check when Key Vault is unhealthy"""
        mock_manager = MagicMock()
        mock_manager.vault_url = "https://test-vault.vault.azure.net/"
        mock_manager.health_check.return_value = {
            "status": "unhealthy",
            "can_connect": False,
            "can_list_secrets": False,
            "can_get_secrets": False,
            "secret_count": None,
            "error": "Connection refused"
        }

        result_check, status = check_keyvault_health(mock_manager)

        assert result_check.service == "Key Vault"
        assert result_check.healthy is False
        assert result_check.message == "Connection refused"
        assert status == "degraded"  # API still healthy, so overall is degraded not unhealthy
        assert result_check.metadata["canConnect"] is False

    def test_exception_handling(self):
        """Test exception handling during health check"""
        mock_manager = MagicMock()
        mock_manager.health_check.side_effect = Exception("Connection timeout")

        result_check, status = check_keyvault_health(mock_manager)

        assert result_check.service == "Key Vault"
        assert result_check.healthy is False
        assert "Connection timeout" in result_check.message
        assert status == "degraded"
        assert result_check.metadata == {}

    def test_manager_without_vault_url(self):
        """Test health check when manager doesn't have vault_url attribute"""
        mock_manager = MagicMock()
        # Delete vault_url to simulate missing attribute
        delattr(mock_manager, 'vault_url')
        mock_manager.health_check.return_value = {
            "status": "healthy",
            "can_connect": True,
            "can_list_secrets": True,
            "can_get_secrets": True,
            "secret_count": 10
        }

        result_check, status = check_keyvault_health(mock_manager)

        assert result_check.metadata["vaultUrl"] is None
        assert result_check.healthy is True


class TestPerformGeneralHealthCheck:
    """Tests for perform_general_health_check"""

    def test_all_healthy(self):
        """Test general health check when all components are healthy"""
        mock_manager = MagicMock()
        mock_manager.vault_url = "https://test-vault.vault.azure.net/"
        mock_manager.health_check.return_value = {
            "status": "healthy",
            "can_connect": True,
            "can_list_secrets": True,
            "can_get_secrets": True,
            "secret_count": 10
        }

        response = perform_general_health_check(mock_manager)

        assert isinstance(response, GeneralHealthResponse)
        assert response.status == "healthy"
        assert response.service == "Bifrost Integrations API"
        assert len(response.checks) == 2
        assert response.checks[0].service == "API"
        assert response.checks[1].service == "Key Vault"
        assert response.checks[0].healthy is True
        assert response.checks[1].healthy is True

    def test_keyvault_degraded(self):
        """Test general health check when Key Vault is degraded"""
        mock_manager = MagicMock()
        mock_manager.vault_url = "https://test-vault.vault.azure.net/"
        mock_manager.health_check.return_value = {
            "status": "degraded",
            "can_connect": True,
            "can_list_secrets": False,
            "can_get_secrets": True,
            "secret_count": 5
        }

        response = perform_general_health_check(mock_manager)

        assert response.status == "degraded"
        assert len(response.checks) == 2
        assert response.checks[0].healthy is True  # API still healthy
        assert response.checks[1].healthy is False  # KV degraded

    def test_keyvault_not_initialized(self):
        """Test general health check when Key Vault is not initialized"""
        response = perform_general_health_check(None)

        assert response.status == "degraded"
        assert len(response.checks) == 2
        assert response.checks[0].service == "API"
        assert response.checks[0].healthy is True
        assert response.checks[1].service == "Key Vault"
        assert response.checks[1].healthy is False
        assert "not initialized" in response.checks[1].message

    def test_response_structure(self):
        """Test response has correct structure with timestamp"""
        mock_manager = MagicMock()
        mock_manager.vault_url = "https://test-vault.vault.azure.net/"
        mock_manager.health_check.return_value = {
            "status": "healthy",
            "can_connect": True,
            "can_list_secrets": True,
            "can_get_secrets": True,
            "secret_count": 10
        }

        response = perform_general_health_check(mock_manager)

        assert isinstance(response.timestamp, datetime)
        assert response.service == "Bifrost Integrations API"
        assert isinstance(response.checks, list)


class TestPerformKeyVaultHealthCheck:
    """Tests for perform_keyvault_health_check"""

    def test_manager_not_initialized(self):
        """Test Key Vault health check when manager is None"""
        response = perform_keyvault_health_check(None)

        assert isinstance(response, KeyVaultHealthResponse)
        assert response.status == "unhealthy"
        assert "not initialized" in response.message
        assert response.vaultUrl is None
        assert response.canConnect is False
        assert response.canListSecrets is False
        assert response.canGetSecrets is False
        assert response.secretCount is None

    def test_healthy_keyvault(self):
        """Test Key Vault health check when healthy"""
        mock_manager = MagicMock()
        mock_manager.vault_url = "https://test-vault.vault.azure.net/"
        mock_manager.health_check.return_value = {
            "status": "healthy",
            "can_connect": True,
            "can_list_secrets": True,
            "can_get_secrets": True,
            "secret_count": 15
        }

        response = perform_keyvault_health_check(mock_manager)

        assert response.status == "healthy"
        assert "accessible and all permissions" in response.message
        assert response.vaultUrl == "https://test-vault.vault.azure.net/"
        assert response.canConnect is True
        assert response.canListSecrets is True
        assert response.canGetSecrets is True
        assert response.secretCount == 15

    def test_degraded_keyvault(self):
        """Test Key Vault health check when degraded"""
        mock_manager = MagicMock()
        mock_manager.vault_url = "https://test-vault.vault.azure.net/"
        mock_manager.health_check.return_value = {
            "status": "degraded",
            "can_connect": True,
            "can_list_secrets": False,
            "can_get_secrets": True,
            "secret_count": 8
        }

        response = perform_keyvault_health_check(mock_manager)

        assert response.status == "degraded"
        assert "permissions may be limited" in response.message
        assert response.canConnect is True
        assert response.canListSecrets is False

    def test_unhealthy_keyvault(self):
        """Test Key Vault health check when unhealthy"""
        mock_manager = MagicMock()
        mock_manager.vault_url = "https://test-vault.vault.azure.net/"
        mock_manager.health_check.return_value = {
            "status": "unhealthy",
            "can_connect": False,
            "can_list_secrets": False,
            "can_get_secrets": False,
            "secret_count": None,
            "error": "Network timeout"
        }

        response = perform_keyvault_health_check(mock_manager)

        assert response.status == "unhealthy"
        assert "Network timeout" in response.message
        assert response.canConnect is False

    def test_exception_during_health_check(self):
        """Test exception handling during health check"""
        mock_manager = MagicMock()
        mock_manager.vault_url = "https://test-vault.vault.azure.net/"
        mock_manager.health_check.side_effect = RuntimeError("Unexpected error")

        response = perform_keyvault_health_check(mock_manager)

        assert response.status == "unhealthy"
        assert "Unexpected error" in response.message
        assert response.canConnect is False
        assert response.vaultUrl == "https://test-vault.vault.azure.net/"

    def test_response_has_timestamp(self):
        """Test response includes timestamp"""
        mock_manager = MagicMock()
        mock_manager.vault_url = "https://test-vault.vault.azure.net/"
        mock_manager.health_check.return_value = {
            "status": "healthy",
            "can_connect": True,
            "can_list_secrets": True,
            "can_get_secrets": True,
            "secret_count": 10
        }

        response = perform_keyvault_health_check(mock_manager)

        assert isinstance(response.lastChecked, datetime)

    def test_missing_health_result_fields(self):
        """Test handling of missing fields in health check result"""
        mock_manager = MagicMock()
        mock_manager.vault_url = "https://test-vault.vault.azure.net/"
        mock_manager.health_check.return_value = {
            "status": "healthy"
            # Missing optional fields
        }

        response = perform_keyvault_health_check(mock_manager)

        assert response.status == "healthy"
        assert response.canConnect is False  # Default when missing
        assert response.canListSecrets is False
        assert response.canGetSecrets is False
        assert response.secretCount is None

    def test_manager_without_vault_url_attribute(self):
        """Test handling when manager doesn't have vault_url attribute"""
        mock_manager = MagicMock()
        # Delete vault_url to simulate missing attribute
        delattr(mock_manager, 'vault_url')
        mock_manager.health_check.return_value = {
            "status": "healthy",
            "can_connect": True,
            "can_list_secrets": True,
            "can_get_secrets": True,
            "secret_count": 10
        }

        response = perform_keyvault_health_check(mock_manager)

        assert response.vaultUrl is None
        assert response.status == "healthy"


class TestIntegration:
    """Integration-like tests combining multiple handlers"""

    def test_full_health_check_flow_healthy(self):
        """Test complete health check flow with healthy system"""
        mock_manager = MagicMock()
        mock_manager.vault_url = "https://test-vault.vault.azure.net/"
        mock_manager.health_check.return_value = {
            "status": "healthy",
            "can_connect": True,
            "can_list_secrets": True,
            "can_get_secrets": True,
            "secret_count": 20
        }

        # Test general health
        general_response = perform_general_health_check(mock_manager)
        assert general_response.status == "healthy"

        # Test specific health
        specific_response = perform_keyvault_health_check(mock_manager)
        assert specific_response.status == "healthy"

    def test_full_health_check_flow_degraded(self):
        """Test complete health check flow with degraded system"""
        mock_manager = MagicMock()
        mock_manager.vault_url = "https://test-vault.vault.azure.net/"
        mock_manager.health_check.return_value = {
            "status": "degraded",
            "can_connect": True,
            "can_list_secrets": False,
            "can_get_secrets": True,
            "secret_count": 12,
            "error": "List permissions denied"
        }

        # Test general health
        general_response = perform_general_health_check(mock_manager)
        assert general_response.status == "degraded"
        assert len(general_response.checks) == 2

        # Test specific health
        specific_response = perform_keyvault_health_check(mock_manager)
        assert specific_response.status == "degraded"
        assert specific_response.canListSecrets is False

    def test_null_keyvault_scenario(self):
        """Test health check when Key Vault is not available"""
        # General health with no manager
        general_response = perform_general_health_check(None)
        assert general_response.status == "degraded"
        assert len(general_response.checks) == 2
        assert general_response.checks[1].healthy is False

        # Specific health with no manager
        specific_response = perform_keyvault_health_check(None)
        assert specific_response.status == "unhealthy"
