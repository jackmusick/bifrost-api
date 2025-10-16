"""
Contract tests for IntegrationConfig API models
Tests Pydantic validation rules for request/response models
"""

from datetime import datetime

import pytest
from pydantic import ValidationError

from shared.models import IntegrationConfig, IntegrationType, SetIntegrationConfigRequest


class TestSetIntegrationConfigRequest:
    """Test validation for SetIntegrationConfigRequest model"""

    def test_valid_msgraph_request(self):
        """Test valid Microsoft Graph integration request"""
        request = SetIntegrationConfigRequest(
            type=IntegrationType.MSGRAPH,
            enabled=True,
            settings={
                "tenant_id": "12345678-1234-1234-1234-123456789012",
                "client_id": "87654321-4321-4321-4321-210987654321",
                "client_secret_ref": "org-123-msgraph-secret"
            }
        )
        assert request.type == IntegrationType.MSGRAPH
        assert request.enabled is True
        assert request.settings["tenant_id"] == "12345678-1234-1234-1234-123456789012"
        assert request.settings["client_secret_ref"] == "org-123-msgraph-secret"

    def test_valid_halopsa_request(self):
        """Test valid HaloPSA integration request"""
        request = SetIntegrationConfigRequest(
            type=IntegrationType.HALOPSA,
            enabled=True,
            settings={
                "api_url": "https://tenant.halopsa.com",
                "client_id": "halopsa-client-123",
                "api_key_ref": "org-123-halopsa-key"
            }
        )
        assert request.type == IntegrationType.HALOPSA
        assert request.enabled is True
        assert request.settings["api_url"] == "https://tenant.halopsa.com"
        assert request.settings["api_key_ref"] == "org-123-halopsa-key"

    def test_valid_disabled_integration(self):
        """Test valid integration with enabled=False"""
        request = SetIntegrationConfigRequest(
            type=IntegrationType.MSGRAPH,
            enabled=False,
            settings={
                "tenant_id": "12345678-1234-1234-1234-123456789012",
                "client_id": "87654321-4321-4321-4321-210987654321",
                "client_secret_ref": "org-123-msgraph-secret"
            }
        )
        assert request.enabled is False

    def test_enabled_defaults_to_true(self):
        """Test that enabled defaults to True if not specified"""
        request = SetIntegrationConfigRequest(
            type=IntegrationType.MSGRAPH,
            settings={
                "tenant_id": "12345678-1234-1234-1234-123456789012",
                "client_id": "87654321-4321-4321-4321-210987654321",
                "client_secret_ref": "org-123-msgraph-secret"
            }
        )
        assert request.enabled is True

    def test_invalid_type_enum(self):
        """Test that invalid integration type is rejected"""
        with pytest.raises(ValidationError) as exc_info:
            SetIntegrationConfigRequest(
                type="invalid_type",
                settings={}
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("type",) for e in errors)

    def test_msgraph_missing_tenant_id(self):
        """Test that msgraph integration requires tenant_id"""
        with pytest.raises(ValidationError) as exc_info:
            SetIntegrationConfigRequest(
                type=IntegrationType.MSGRAPH,
                settings={
                    "client_id": "87654321-4321-4321-4321-210987654321",
                    "client_secret_ref": "org-123-msgraph-secret"
                }
            )

        errors = exc_info.value.errors()
        assert any("tenant_id" in str(e) for e in errors)

    def test_msgraph_missing_client_id(self):
        """Test that msgraph integration requires client_id"""
        with pytest.raises(ValidationError) as exc_info:
            SetIntegrationConfigRequest(
                type=IntegrationType.MSGRAPH,
                settings={
                    "tenant_id": "12345678-1234-1234-1234-123456789012",
                    "client_secret_ref": "org-123-msgraph-secret"
                }
            )

        errors = exc_info.value.errors()
        assert any("client_id" in str(e) for e in errors)

    def test_msgraph_missing_client_secret_ref(self):
        """Test that msgraph integration requires client_secret_ref"""
        with pytest.raises(ValidationError) as exc_info:
            SetIntegrationConfigRequest(
                type=IntegrationType.MSGRAPH,
                settings={
                    "tenant_id": "12345678-1234-1234-1234-123456789012",
                    "client_id": "87654321-4321-4321-4321-210987654321"
                }
            )

        errors = exc_info.value.errors()
        assert any("client_secret_ref" in str(e) for e in errors)

    def test_halopsa_missing_api_url(self):
        """Test that halopsa integration requires api_url"""
        with pytest.raises(ValidationError) as exc_info:
            SetIntegrationConfigRequest(
                type=IntegrationType.HALOPSA,
                settings={
                    "client_id": "halopsa-client-123",
                    "api_key_ref": "org-123-halopsa-key"
                }
            )

        errors = exc_info.value.errors()
        assert any("api_url" in str(e) for e in errors)

    def test_halopsa_missing_client_id(self):
        """Test that halopsa integration requires client_id"""
        with pytest.raises(ValidationError) as exc_info:
            SetIntegrationConfigRequest(
                type=IntegrationType.HALOPSA,
                settings={
                    "api_url": "https://tenant.halopsa.com",
                    "api_key_ref": "org-123-halopsa-key"
                }
            )

        errors = exc_info.value.errors()
        assert any("client_id" in str(e) for e in errors)

    def test_halopsa_missing_api_key_ref(self):
        """Test that halopsa integration requires api_key_ref"""
        with pytest.raises(ValidationError) as exc_info:
            SetIntegrationConfigRequest(
                type=IntegrationType.HALOPSA,
                settings={
                    "api_url": "https://tenant.halopsa.com",
                    "client_id": "halopsa-client-123"
                }
            )

        errors = exc_info.value.errors()
        assert any("api_key_ref" in str(e) for e in errors)

    def test_msgraph_with_extra_settings(self):
        """Test that msgraph integration accepts extra settings beyond required"""
        request = SetIntegrationConfigRequest(
            type=IntegrationType.MSGRAPH,
            settings={
                "tenant_id": "12345678-1234-1234-1234-123456789012",
                "client_id": "87654321-4321-4321-4321-210987654321",
                "client_secret_ref": "org-123-msgraph-secret",
                "scope": "https://graph.microsoft.com/.default",
                "authority": "https://login.microsoftonline.com"
            }
        )
        assert request.settings["scope"] == "https://graph.microsoft.com/.default"
        assert request.settings["authority"] == "https://login.microsoftonline.com"

    def test_missing_required_type(self):
        """Test that type is required"""
        with pytest.raises(ValidationError) as exc_info:
            SetIntegrationConfigRequest(
                settings={
                    "tenant_id": "12345678-1234-1234-1234-123456789012",
                    "client_id": "87654321-4321-4321-4321-210987654321",
                    "client_secret_ref": "org-123-msgraph-secret"
                }
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("type",) and e["type"] == "missing" for e in errors)

    def test_missing_required_settings(self):
        """Test that settings is required"""
        with pytest.raises(ValidationError) as exc_info:
            SetIntegrationConfigRequest(
                type=IntegrationType.MSGRAPH
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("settings",) and e["type"] == "missing" for e in errors)


class TestIntegrationConfigResponse:
    """Test IntegrationConfig response model structure"""

    def test_valid_msgraph_response(self):
        """Test valid Microsoft Graph integration response"""
        config = IntegrationConfig(
            type=IntegrationType.MSGRAPH,
            enabled=True,
            settings={
                "tenant_id": "12345678-1234-1234-1234-123456789012",
                "client_id": "87654321-4321-4321-4321-210987654321",
                "client_secret_ref": "org-123-msgraph-secret"
            },
            updatedAt=datetime.utcnow(),
            updatedBy="user-123"
        )
        assert config.type == IntegrationType.MSGRAPH
        assert config.enabled is True
        assert isinstance(config.settings, dict)
        assert isinstance(config.updatedAt, datetime)

    def test_valid_halopsa_response(self):
        """Test valid HaloPSA integration response"""
        config = IntegrationConfig(
            type=IntegrationType.HALOPSA,
            enabled=False,
            settings={
                "api_url": "https://tenant.halopsa.com",
                "client_id": "halopsa-client-123",
                "api_key_ref": "org-123-halopsa-key"
            },
            updatedAt=datetime.utcnow(),
            updatedBy="user-456"
        )
        assert config.type == IntegrationType.HALOPSA
        assert config.enabled is False

    def test_integration_config_missing_required_fields(self):
        """Test that all required fields must be present"""
        with pytest.raises(ValidationError) as exc_info:
            IntegrationConfig(
                type=IntegrationType.MSGRAPH,
                enabled=True,
                settings={"test": "value"}
                # Missing: updatedAt, updatedBy
            )

        errors = exc_info.value.errors()
        required_fields = {"updatedAt", "updatedBy"}
        missing_fields = {e["loc"][0] for e in errors if e["type"] == "missing"}
        assert required_fields.issubset(missing_fields)

    def test_integration_config_serialization(self):
        """Test that integration config can be serialized to dict/JSON"""
        config = IntegrationConfig(
            type=IntegrationType.MSGRAPH,
            enabled=True,
            settings={
                "tenant_id": "12345678-1234-1234-1234-123456789012",
                "client_id": "87654321-4321-4321-4321-210987654321",
                "client_secret_ref": "org-123-msgraph-secret"
            },
            updatedAt=datetime.utcnow(),
            updatedBy="user-123"
        )

        config_dict = config.model_dump()
        assert "type" in config_dict
        assert "enabled" in config_dict
        assert "settings" in config_dict
        assert "updatedAt" in config_dict
        assert "updatedBy" in config_dict

    def test_integration_config_json_serialization(self):
        """Test that integration config can be serialized to JSON mode"""
        config = IntegrationConfig(
            type=IntegrationType.MSGRAPH,
            enabled=True,
            settings={
                "tenant_id": "12345678-1234-1234-1234-123456789012",
                "client_id": "87654321-4321-4321-4321-210987654321",
                "client_secret_ref": "org-123-msgraph-secret"
            },
            updatedAt=datetime.utcnow(),
            updatedBy="user-123"
        )

        config_dict = config.model_dump(mode="json")
        assert isinstance(config_dict["updatedAt"], str)  # datetime -> ISO string
        assert config_dict["type"] == "msgraph"  # Enum -> string value


class TestIntegrationTypeEnum:
    """Test IntegrationType enum values"""

    def test_all_integration_types(self):
        """Test that all expected integration types are available"""
        assert IntegrationType.MSGRAPH == "msgraph"
        assert IntegrationType.HALOPSA == "halopsa"

    def test_integration_type_in_request(self):
        """Test using enum in request"""
        for integration_type in [IntegrationType.MSGRAPH, IntegrationType.HALOPSA]:
            if integration_type == IntegrationType.MSGRAPH:
                settings = {
                    "tenant_id": "12345678-1234-1234-1234-123456789012",
                    "client_id": "87654321-4321-4321-4321-210987654321",
                    "client_secret_ref": "org-123-msgraph-secret"
                }
            else:
                settings = {
                    "api_url": "https://tenant.halopsa.com",
                    "client_id": "halopsa-client-123",
                    "api_key_ref": "org-123-halopsa-key"
                }

            request = SetIntegrationConfigRequest(
                type=integration_type,
                settings=settings
            )
            assert request.type == integration_type
