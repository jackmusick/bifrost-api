"""
Contract tests for Secrets API models
Tests Pydantic validation rules for request/response models
"""

from datetime import datetime

import pytest
from pydantic import ValidationError

from shared.models import (
    KeyVaultHealthResponse,
    SecretCreateRequest,
    SecretListResponse,
    SecretResponse,
    SecretUpdateRequest,
)


class TestSecretListResponse:
    """Test validation for SecretListResponse model"""

    def test_valid_response_with_org_filter(self):
        """Test valid response with organization filter"""
        response = SecretListResponse(
            secrets=["org-123--api-key", "GLOBAL--smtp-password"],
            orgId="org-123",
            count=2
        )
        assert len(response.secrets) == 2
        assert response.orgId == "org-123"
        assert response.count == 2

    def test_valid_response_without_org_filter(self):
        """Test valid response without organization filter"""
        response = SecretListResponse(
            secrets=["GLOBAL--smtp-password", "GLOBAL--api-key"],
            orgId=None,
            count=2
        )
        assert len(response.secrets) == 2
        assert response.orgId is None
        assert response.count == 2

    def test_valid_response_empty_list(self):
        """Test valid response with empty secret list"""
        response = SecretListResponse(
            secrets=[],
            orgId="org-123",
            count=0
        )
        assert len(response.secrets) == 0
        assert response.count == 0

    def test_missing_required_fields(self):
        """Test that all required fields must be present"""
        with pytest.raises(ValidationError) as exc_info:
            SecretListResponse()

        errors = exc_info.value.errors()
        required_fields = {"secrets", "count"}
        missing_fields = {e["loc"][0] for e in errors if e["type"] == "missing"}
        assert required_fields.issubset(missing_fields)


class TestSecretCreateRequest:
    """Test validation for SecretCreateRequest model"""

    def test_valid_request_org_scoped(self):
        """Test valid request for org-scoped secret"""
        request = SecretCreateRequest(
            orgId="org-123",
            secretKey="api-key",
            value="test-secret-value"
        )
        assert request.orgId == "org-123"
        assert request.secretKey == "api-key"
        assert request.value == "test-secret-value"

    def test_valid_request_global_scoped(self):
        """Test valid request for global secret"""
        request = SecretCreateRequest(
            orgId="GLOBAL",
            secretKey="smtp-password",
            value="global-secret-value"
        )
        assert request.orgId == "GLOBAL"
        assert request.secretKey == "smtp-password"
        assert request.value == "global-secret-value"

    def test_valid_secret_key_with_hyphens(self):
        """Test that secret key can contain hyphens"""
        request = SecretCreateRequest(
            orgId="org-123",
            secretKey="api-key-name",
            value="test-value"
        )
        assert request.secretKey == "api-key-name"

    def test_valid_secret_key_with_underscores(self):
        """Test that secret key can contain underscores"""
        request = SecretCreateRequest(
            orgId="org-123",
            secretKey="api_key_name",
            value="test-value"
        )
        assert request.secretKey == "api_key_name"

    def test_invalid_secret_key_with_spaces(self):
        """Test that secret key with spaces is rejected"""
        with pytest.raises(ValidationError) as exc_info:
            SecretCreateRequest(
                orgId="org-123",
                secretKey="api key",  # Spaces not allowed
                value="test-value"
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("secretKey",) for e in errors)

    def test_invalid_secret_key_with_special_chars(self):
        """Test that secret key with special characters is rejected"""
        with pytest.raises(ValidationError) as exc_info:
            SecretCreateRequest(
                orgId="org-123",
                secretKey="api@key",  # @ not allowed
                value="test-value"
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("secretKey",) for e in errors)

    def test_invalid_secret_key_too_long(self):
        """Test that secret key exceeding 100 characters is rejected"""
        long_key = "a" * 101
        with pytest.raises(ValidationError) as exc_info:
            SecretCreateRequest(
                orgId="org-123",
                secretKey=long_key,
                value="test-value"
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("secretKey",) for e in errors)

    def test_invalid_empty_value(self):
        """Test that empty value is rejected"""
        with pytest.raises(ValidationError) as exc_info:
            SecretCreateRequest(
                orgId="org-123",
                secretKey="api-key",
                value=""
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("value",) for e in errors)

    def test_missing_required_fields(self):
        """Test that all required fields must be present"""
        with pytest.raises(ValidationError) as exc_info:
            SecretCreateRequest()

        errors = exc_info.value.errors()
        required_fields = {"orgId", "secretKey", "value"}
        missing_fields = {e["loc"][0] for e in errors if e["type"] == "missing"}
        assert required_fields.issubset(missing_fields)


class TestSecretUpdateRequest:
    """Test validation for SecretUpdateRequest model"""

    def test_valid_update_request(self):
        """Test valid update request"""
        request = SecretUpdateRequest(value="updated-secret-value")
        assert request.value == "updated-secret-value"

    def test_invalid_empty_value(self):
        """Test that empty value is rejected"""
        with pytest.raises(ValidationError) as exc_info:
            SecretUpdateRequest(value="")

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("value",) for e in errors)

    def test_missing_required_value(self):
        """Test that value is required"""
        with pytest.raises(ValidationError) as exc_info:
            SecretUpdateRequest()

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("value",) and e["type"] == "missing" for e in errors)


class TestSecretResponse:
    """Test SecretResponse model structure"""

    def test_valid_response_with_value(self):
        """Test valid response with secret value (after create/update)"""
        response = SecretResponse(
            name="org-123--api-key",
            orgId="org-123",
            secretKey="api-key",
            value="secret-value",
            message="Secret created successfully"
        )
        assert response.name == "org-123--api-key"
        assert response.orgId == "org-123"
        assert response.secretKey == "api-key"
        assert response.value == "secret-value"
        assert response.message == "Secret created successfully"

    def test_valid_response_without_value(self):
        """Test valid response without secret value (after delete)"""
        response = SecretResponse(
            name="org-123--api-key",
            orgId="org-123",
            secretKey="api-key",
            value=None,
            message="Secret deleted successfully"
        )
        assert response.name == "org-123--api-key"
        assert response.value is None
        assert response.message == "Secret deleted successfully"

    def test_missing_required_fields(self):
        """Test that all required fields must be present"""
        with pytest.raises(ValidationError) as exc_info:
            SecretResponse()

        errors = exc_info.value.errors()
        required_fields = {"name", "orgId", "secretKey", "message"}
        missing_fields = {e["loc"][0] for e in errors if e["type"] == "missing"}
        assert required_fields.issubset(missing_fields)

    def test_response_serialization(self):
        """Test that response can be serialized to dict/JSON"""
        response = SecretResponse(
            name="org-123--api-key",
            orgId="org-123",
            secretKey="api-key",
            value="secret-value",
            message="Success"
        )

        response_dict = response.model_dump()
        assert "name" in response_dict
        assert "orgId" in response_dict
        assert "secretKey" in response_dict
        assert "value" in response_dict
        assert "message" in response_dict


class TestKeyVaultHealthResponse:
    """Test KeyVaultHealthResponse model"""

    def test_valid_healthy_response(self):
        """Test valid healthy status response"""
        response = KeyVaultHealthResponse(
            status="healthy",
            message="Key Vault is accessible",
            vaultUrl="https://my-vault.vault.azure.net/",
            canConnect=True,
            canListSecrets=True,
            canGetSecrets=True,
            secretCount=15,
            lastChecked=datetime.utcnow()
        )
        assert response.status == "healthy"
        assert response.canConnect is True
        assert response.canListSecrets is True
        assert response.canGetSecrets is True
        assert response.secretCount == 15

    def test_valid_degraded_response(self):
        """Test valid degraded status response"""
        response = KeyVaultHealthResponse(
            status="degraded",
            message="Key Vault accessible but limited permissions",
            vaultUrl="https://my-vault.vault.azure.net/",
            canConnect=True,
            canListSecrets=False,
            canGetSecrets=True,
            secretCount=None,
            lastChecked=datetime.utcnow()
        )
        assert response.status == "degraded"
        assert response.canConnect is True
        assert response.canListSecrets is False
        assert response.secretCount is None

    def test_valid_unhealthy_response(self):
        """Test valid unhealthy status response"""
        response = KeyVaultHealthResponse(
            status="unhealthy",
            message="Cannot connect to Key Vault",
            vaultUrl=None,
            canConnect=False,
            canListSecrets=False,
            canGetSecrets=False,
            secretCount=None,
            lastChecked=datetime.utcnow()
        )
        assert response.status == "unhealthy"
        assert response.canConnect is False
        assert response.vaultUrl is None

    def test_invalid_status_value(self):
        """Test that invalid status value is rejected"""
        with pytest.raises(ValidationError) as exc_info:
            KeyVaultHealthResponse(
                status="invalid",  # Must be healthy, degraded, or unhealthy
                message="Test",
                canConnect=True,
                canListSecrets=True,
                canGetSecrets=True,
                lastChecked=datetime.utcnow()
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("status",) for e in errors)

    def test_missing_required_fields(self):
        """Test that all required fields must be present"""
        with pytest.raises(ValidationError) as exc_info:
            KeyVaultHealthResponse()

        errors = exc_info.value.errors()
        required_fields = {"status", "message", "canConnect", "canListSecrets", "canGetSecrets", "lastChecked"}
        missing_fields = {e["loc"][0] for e in errors if e["type"] == "missing"}
        assert required_fields.issubset(missing_fields)

    def test_health_response_serialization(self):
        """Test that health response can be serialized"""
        response = KeyVaultHealthResponse(
            status="healthy",
            message="All systems operational",
            vaultUrl="https://my-vault.vault.azure.net/",
            canConnect=True,
            canListSecrets=True,
            canGetSecrets=True,
            secretCount=10,
            lastChecked=datetime.utcnow()
        )

        response_dict = response.model_dump()
        assert "status" in response_dict
        assert "message" in response_dict
        assert "vaultUrl" in response_dict
        assert "canConnect" in response_dict
        assert "canListSecrets" in response_dict
        assert "canGetSecrets" in response_dict
        assert "secretCount" in response_dict
        assert "lastChecked" in response_dict
