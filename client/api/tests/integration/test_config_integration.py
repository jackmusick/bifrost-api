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
        result = config_service.get_entity(
            "test-org-123", "config:default_timeout")

        assert result is not None
        assert result["Value"] == "600"
        assert result["PartitionKey"] == "test-org-123"


class TestConfigFallbackPattern:
    """Test config fallback: org-specific � GLOBAL � None"""

    def test_fallback_finds_org_config_first(self, config_service, sample_global_config, sample_org_config):
        """When both GLOBAL and org config exist, should return org config"""
        result = get_config_value("default_timeout", "test-org-123")

        assert result is not None
        assert result["Value"] == "600"  # Org value, not GLOBAL 300
        assert result["PartitionKey"] == "test-org-123"

    def test_fallback_to_global_when_org_missing(self, config_service, sample_global_config):
        """When org config missing, should fallback to GLOBAL"""
        result = get_config_value("default_timeout", "nonexistent-org")

        assert result is not None
        assert result["Value"] == "300"  # GLOBAL value
        assert result["PartitionKey"] == "GLOBAL"

    def test_fallback_returns_none_when_both_missing(self, config_service):
        """When both org and GLOBAL missing, should return None"""
        result = get_config_value("nonexistent_key", "test-org-123")

        assert result is None

    def test_fallback_global_only_when_no_org_id(self, config_service, sample_global_config):
        """When no org_id provided, should only check GLOBAL"""
        result = get_config_value("default_timeout", None)

        assert result is not None
        assert result["Value"] == "300"
        assert result["PartitionKey"] == "GLOBAL"


class TestSensitiveValueMasking:
    """Test sensitive config value masking"""

    def test_mask_secret_keyword(self):
        """Keys containing 'secret' should be masked"""
        masked = mask_sensitive_value(
            "client_secret", "super-secret-value-12345")
        assert masked == "supe***2345"
        assert "secret" not in masked.lower()

    def test_mask_password_keyword(self):
        """Keys containing 'password' should be masked"""
        masked = mask_sensitive_value("database_password", "MyP@ssw0rd123!")
        assert masked == "MyP@***123!"

    def test_mask_token_keyword(self):
        """Keys containing 'token' should be masked"""
        masked = mask_sensitive_value("api_token", "tok_abcdefgh1234567890")
        assert masked == "tok_***7890"

    def test_mask_key_keyword(self):
        """Keys containing 'key' should be masked"""
        masked = mask_sensitive_value("api_key", "sk_live_1234567890abcdef")
        assert masked == "sk_l***cdef"

    def test_mask_credential_keyword(self):
        """Keys containing 'credential' should be masked"""
        masked = mask_sensitive_value(
            "azure_credential", "credential_value_123")
        assert masked == "cred***_123"

    def test_no_mask_for_non_sensitive(self):
        """Non-sensitive keys should not be masked"""
        value = "normal_config_value"
        masked = mask_sensitive_value("timeout", value)
        assert masked == value

    def test_mask_short_value(self):
        """Short sensitive values should be fully masked"""
        masked = mask_sensitive_value("secret", "short")
        assert masked == "***"

    def test_mask_case_insensitive(self):
        """Masking should be case-insensitive"""
        masked = mask_sensitive_value("CLIENT_SECRET", "value123")
        assert "***" in masked


class TestConfigTypes:
    """Test different config value types"""

    def test_string_type(self, config_service):
        """Should store and retrieve STRING type"""
        entity = {
            "PartitionKey": "GLOBAL",
            "RowKey": "config:app_name",
            "Value": "Bifrost Integrations",
            "Type": ConfigType.STRING.value,
            "UpdatedAt": datetime.utcnow().isoformat(),
            "UpdatedBy": "admin@test.com"
        }
        config_service.upsert_entity(entity)

        result = config_service.get_entity("GLOBAL", "config:app_name")
        assert result["Type"] == "string"
        assert isinstance(result["Value"], str)

        config_service.delete_entity("GLOBAL", "config:app_name")

    def test_int_type(self, config_service):
        """Should store and retrieve INT type"""
        entity = {
            "PartitionKey": "GLOBAL",
            "RowKey": "config:max_retries",
            "Value": "5",
            "Type": ConfigType.INT.value,
            "UpdatedAt": datetime.utcnow().isoformat(),
            "UpdatedBy": "admin@test.com"
        }
        config_service.upsert_entity(entity)

        result = config_service.get_entity("GLOBAL", "config:max_retries")
        assert result["Type"] == "int"
        assert result["Value"] == "5"

        config_service.delete_entity("GLOBAL", "config:max_retries")

    def test_bool_type(self, config_service):
        """Should store and retrieve BOOL type"""
        entity = {
            "PartitionKey": "GLOBAL",
            "RowKey": "config:debug_mode",
            "Value": "true",
            "Type": ConfigType.BOOL.value,
            "UpdatedAt": datetime.utcnow().isoformat(),
            "UpdatedBy": "admin@test.com"
        }
        config_service.upsert_entity(entity)

        result = config_service.get_entity("GLOBAL", "config:debug_mode")
        assert result["Type"] == "bool"
        assert result["Value"] == "true"

        config_service.delete_entity("GLOBAL", "config:debug_mode")

    def test_secret_ref_type(self, config_service):
        """Should store SECRET_REF type (pointer to Key Vault)"""
        entity = {
            "PartitionKey": "test-org",
            "RowKey": "config:database_connection",
            "Value": "test-org--db-connection-string",
            "Type": ConfigType.SECRET_REF.value,
            "UpdatedAt": datetime.utcnow().isoformat(),
            "UpdatedBy": "admin@test.com"
        }
        config_service.upsert_entity(entity)

        result = config_service.get_entity(
            "test-org", "config:database_connection")
        assert result["Type"] == "secret_ref"

        config_service.delete_entity("test-org", "config:database_connection")


class TestConfigQueryByScope:
    """Test querying configs by scope (GLOBAL vs org)"""

    def test_query_global_configs(self, config_service, sample_global_config):
        """Should query all GLOBAL configs"""
        # Create another GLOBAL config
        entity2 = {
            "PartitionKey": "GLOBAL",
            "RowKey": "config:another_setting",
            "Value": "value2",
            "Type": ConfigType.STRING.value,
            "UpdatedAt": datetime.utcnow().isoformat(),
            "UpdatedBy": "admin@test.com"
        }
        config_service.upsert_entity(entity2)

        # Query all GLOBAL configs
        results = list(config_service.query_by_org(
            "GLOBAL", row_key_prefix="config:"))

        assert len(results) >= 2
        assert all(r["PartitionKey"] == "GLOBAL" for r in results)

        # Cleanup
        config_service.delete_entity("GLOBAL", "config:another_setting")

    def test_query_org_configs(self, config_service, sample_org_config):
        """Should query all configs for specific org"""
        # Create another org config
        entity2 = {
            "PartitionKey": "test-org-123",
            "RowKey": "config:org_specific_setting",
            "Value": "org_value2",
            "Type": ConfigType.STRING.value,
            "UpdatedAt": datetime.utcnow().isoformat(),
            "UpdatedBy": "admin@test.com"
        }
        config_service.upsert_entity(entity2)

        # Query all configs for this org
        results = list(config_service.query_by_org(
            "test-org-123", row_key_prefix="config:"))

        assert len(results) >= 2
        assert all(r["PartitionKey"] == "test-org-123" for r in results)

        # Cleanup
        config_service.delete_entity(
            "test-org-123", "config:org_specific_setting")
