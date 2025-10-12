"""
Integration tests for Config API
Tests GLOBAL vs org-specific config, fallback pattern, and sensitive value masking
"""

import pytest
from shared.storage import TableStorageService
from shared.models import ConfigType
from functions.org_config import get_config_value, mask_sensitive_value
from datetime import datetime


@pytest.fixture
def config_service():
    """Get Config table service"""
    return TableStorageService("Config")


@pytest.fixture
def sample_global_config(config_service):
    """Create sample GLOBAL config"""
    entity = {
        "PartitionKey": "GLOBAL",
        "RowKey": "config:default_timeout",
        "Value": "300",
        "Type": ConfigType.INT.value,
        "Description": "Default timeout in seconds",
        "UpdatedAt": datetime.utcnow().isoformat(),
        "UpdatedBy": "admin@test.com"
    }
    config_service.upsert_entity(entity)
    yield entity
    # Cleanup
    try:
        config_service.delete_entity("GLOBAL", "config:default_timeout")
    except:
        pass


@pytest.fixture
def sample_org_config(config_service):
    """Create sample org-specific config"""
    entity = {
        "PartitionKey": "test-org-123",
        "RowKey": "config:default_timeout",
        "Value": "600",
        "Type": ConfigType.INT.value,
        "Description": "Org-specific timeout override",
        "UpdatedAt": datetime.utcnow().isoformat(),
        "UpdatedBy": "admin@test.com"
    }
    config_service.upsert_entity(entity)
    yield entity
    # Cleanup
    try:
        config_service.delete_entity("test-org-123", "config:default_timeout")
    except:
        pass


class TestConfigGlobalScope:
    """Test GLOBAL config operations"""

    def test_create_global_config(self, config_service):
        """Should create GLOBAL config successfully"""
        entity = {
            "PartitionKey": "GLOBAL",
            "RowKey": "config:test_key",
            "Value": "test_value",
            "Type": ConfigType.STRING.value,
            "Description": "Test config",
            "UpdatedAt": datetime.utcnow().isoformat(),
            "UpdatedBy": "admin@test.com"
        }

        config_service.upsert_entity(entity)

        # Verify it was created
        result = config_service.get_entity("GLOBAL", "config:test_key")
        assert result is not None
        assert result["Value"] == "test_value"
        assert result["PartitionKey"] == "GLOBAL"

        # Cleanup
        config_service.delete_entity("GLOBAL", "config:test_key")

    def test_get_global_config(self, config_service, sample_global_config):
        """Should retrieve GLOBAL config"""
        result = config_service.get_entity("GLOBAL", "config:default_timeout")

        assert result is not None
        assert result["Value"] == "300"
        assert result["Type"] == ConfigType.INT.value

    def test_update_global_config(self, config_service, sample_global_config):
        """Should update existing GLOBAL config"""
        # Update the config
        sample_global_config["Value"] = "450"
        sample_global_config["UpdatedAt"] = datetime.utcnow().isoformat()
        config_service.upsert_entity(sample_global_config)

        # Verify update
        result = config_service.get_entity("GLOBAL", "config:default_timeout")
        assert result["Value"] == "450"

    def test_delete_global_config(self, config_service):
        """Should delete GLOBAL config"""
        # Create config
        entity = {
            "PartitionKey": "GLOBAL",
            "RowKey": "config:temp_key",
            "Value": "temp",
            "Type": ConfigType.STRING.value,
            "UpdatedAt": datetime.utcnow().isoformat(),
            "UpdatedBy": "admin@test.com"
        }
        config_service.upsert_entity(entity)

        # Delete it
        config_service.delete_entity("GLOBAL", "config:temp_key")

        # Verify deletion
        result = config_service.get_entity("GLOBAL", "config:temp_key")
        assert result is None


class TestConfigOrgScope:
    """Test org-specific config operations"""

    def test_create_org_config(self, config_service):
        """Should create org-specific config successfully"""
        entity = {
            "PartitionKey": "org-456",
            "RowKey": "config:org_setting",
            "Value": "org_value",
            "Type": ConfigType.STRING.value,
            "Description": "Org-specific setting",
            "UpdatedAt": datetime.utcnow().isoformat(),
            "UpdatedBy": "admin@test.com"
        }

        config_service.upsert_entity(entity)

        # Verify it was created
        result = config_service.get_entity("org-456", "config:org_setting")
        assert result is not None
        assert result["Value"] == "org_value"
        assert result["PartitionKey"] == "org-456"

        # Cleanup
        config_service.delete_entity("org-456", "config:org_setting")

    def test_get_org_config(self, config_service, sample_org_config):
        """Should retrieve org-specific config"""
        result = config_service.get_entity("test-org-123", "config:default_timeout")

        assert result is not None
        assert result["Value"] == "600"
        assert result["PartitionKey"] == "test-org-123"


class TestConfigFallbackPattern:
