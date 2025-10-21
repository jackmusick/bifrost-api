"""
Unit tests for ConfigRepository
"""

import json

from shared.repositories.config import ConfigRepository
from shared.models import ConfigType, IntegrationType, SetIntegrationConfigRequest


class TestConfigRepositoryGet:
    """Test config retrieval"""

    def test_get_config_org_specific(self, mock_table_service, mock_context):
        """Test getting org-specific config"""
        repo = ConfigRepository(mock_context)

        mock_table_service.get_entity.return_value = {
            "PartitionKey": "test-org-123",
            "RowKey": "config:email_template",
            "Value": "custom_template.html",
            "Type": "string",
            "UpdatedAt": "2024-01-15T10:30:00",
            "UpdatedBy": "admin"
        }

        result = repo.get_config("email_template")

        assert result is not None
        assert result.value == "custom_template.html"
        assert result.key == "email_template"
        assert result.scope == "org"

    def test_get_config_fallback_to_global(self, mock_table_service, mock_context):
        """Test config with org -> GLOBAL fallback"""
        repo = ConfigRepository(mock_context)

        def side_effect(partition_key, row_key):
            if partition_key == "test-org-123":
                # Org-specific not found, return None
                return None
            if partition_key == "GLOBAL":
                return {
                    "PartitionKey": "GLOBAL",
                    "RowKey": "config:email_template",
                    "Value": "default_template.html",
                    "Type": "string",
                    "UpdatedAt": "2024-01-15T10:30:00",
                    "UpdatedBy": "system"
                }
            return None

        mock_table_service.get_entity.side_effect = side_effect

        result = repo.get_config("email_template", fallback_to_global=True)

        assert result is not None
        assert result.value == "default_template.html"
        assert result.scope == "GLOBAL"

    def test_get_config_not_found(self, mock_table_service, mock_context):
        """Test get returns None when config not found"""
        repo = ConfigRepository(mock_context)

        # Mock returns None for all lookups (not found anywhere)
        mock_table_service.get_entity.return_value = None

        result = repo.get_config("nonexistent")

        assert result is None

    def test_get_config_json_type(self, mock_table_service, mock_context):
        """Test getting JSON config value"""
        repo = ConfigRepository(mock_context)

        json_value = {"key1": "value1", "key2": "value2"}
        mock_table_service.get_entity.return_value = {
            "PartitionKey": "test-org-123",
            "RowKey": "config:settings",
            "Value": json.dumps(json_value),
            "Type": "json",
            "UpdatedAt": "2024-01-15T10:30:00",
            "UpdatedBy": "admin"
        }

        result = repo.get_config("settings")

        assert result is not None
        assert result.type == ConfigType.JSON


class TestConfigRepositorySet:
    """Test config setting/updating"""

    def test_set_config_success(self, mock_table_service, mock_context):
        """Test setting a config value"""
        repo = ConfigRepository(mock_context)

        mock_table_service.upsert_entity.return_value = None

        result = repo.set_config(
            "email_template",
            "custom_template.html",
            ConfigType.STRING,
            "Email template for notifications",
            "admin-user"
        )

        assert result is not None
        assert result.key == "email_template"
        assert result.value == "custom_template.html"
        mock_table_service.upsert_entity.assert_called_once()

    def test_set_config_json(self, mock_table_service, mock_context):
        """Test setting JSON config"""
        repo = ConfigRepository(mock_context)

        mock_table_service.upsert_entity.return_value = None

        json_value = {"timeout": 30, "retries": 3}
        result = repo.set_config(
            "workflow_settings",
            json.dumps(json_value),
            ConfigType.JSON,
            "Workflow configuration",
            "admin"
        )

        assert result is not None
        assert result.key == "workflow_settings"

    def test_set_config_upsert_behavior(self, mock_table_service, mock_context):
        """Test that set_config uses upsert (creates or updates)"""
        repo = ConfigRepository(mock_context)

        mock_table_service.upsert_entity.return_value = None

        repo.set_config("key1", "value1", ConfigType.STRING, None, "user")
        repo.set_config("key1", "value2", ConfigType.STRING, None, "user")

        # Should be called twice (upsert both times)
        assert mock_table_service.upsert_entity.call_count == 2


class TestConfigRepositoryList:
    """Test config listing"""

    def test_list_config_empty(self, mock_table_service, mock_context):
        """Test listing when no config exists"""
        repo = ConfigRepository(mock_context)

        mock_table_service.query_entities.return_value = iter([])

        result = repo.list_config()

        assert result == []

    def test_list_config_returns_multiple(self, mock_table_service, mock_context):
        """Test listing multiple config entries"""
        repo = ConfigRepository(mock_context)

        config_data = [
            {
                "PartitionKey": "test-org-123",
                "RowKey": "config:email_template",
                "Value": "template1",
                "Type": "string",
                "UpdatedAt": "2024-01-15T10:30:00",
                "UpdatedBy": "admin"
            },
            {
                "PartitionKey": "test-org-123",
                "RowKey": "config:timeout",
                "Value": "30",
                "Type": "int",
                "UpdatedAt": "2024-01-15T10:30:00",
                "UpdatedBy": "admin"
            }
        ]

        mock_table_service.query_entities.return_value = iter(config_data)

        result = repo.list_config()

        assert len(result) == 2
        assert result[0].key == "email_template"
        assert result[1].key == "timeout"


class TestConfigRepositoryDelete:
    """Test config deletion"""

    def test_delete_config_success(self, mock_table_service, mock_context):
        """Test deleting config"""
        repo = ConfigRepository(mock_context)

        mock_table_service.delete_entity.return_value = True

        result = repo.delete_config("email_template")

        assert result is True
        mock_table_service.delete_entity.assert_called_once()

    def test_delete_config_not_found(self, mock_table_service, mock_context):
        """Test delete returns False when not found"""
        repo = ConfigRepository(mock_context)

        mock_table_service.delete_entity.return_value = False

        result = repo.delete_config("nonexistent")

        assert result is False


class TestIntegrationConfig:
    """Test integration configuration"""

    def test_get_integration_config_success(self, mock_table_service, mock_context):
        """Test getting integration config"""
        repo = ConfigRepository(mock_context)

        settings = {"client_id": "123", "tenant": "default"}
        mock_table_service.get_entity.return_value = {
            "PartitionKey": "test-org-123",
            "RowKey": "integration:msgraph",
            "Type": "msgraph",
            "Enabled": True,
            "Settings": json.dumps(settings),
            "UpdatedAt": "2024-01-15T10:30:00",
            "UpdatedBy": "admin"
        }

        result = repo.get_integration_config(IntegrationType.MSGRAPH)

        assert result is not None
        assert result.type == IntegrationType.MSGRAPH
        assert result.enabled is True
        assert result.settings == settings

    def test_get_integration_config_not_found(self, mock_table_service, mock_context):
        """Test get integration returns None when not found"""
        repo = ConfigRepository(mock_context)

        # Mock returns None when not found (matches real behavior)
        mock_table_service.get_entity.return_value = None

        result = repo.get_integration_config(IntegrationType.HALOPSA)

        assert result is None

    def test_set_integration_config(self, mock_table_service, mock_context):
        """Test setting integration config"""
        repo = ConfigRepository(mock_context)

        mock_table_service.upsert_entity.return_value = None

        request = SetIntegrationConfigRequest(
            type=IntegrationType.MSGRAPH,
            enabled=True,
            settings={
                "client_id": "123",
                "tenant_id": "tenant-123",
                "client_secret_ref": "secret-ref"
            }
        )

        result = repo.set_integration_config(request, "admin")

        assert result is not None
        assert result.type == IntegrationType.MSGRAPH
        mock_table_service.upsert_entity.assert_called_once()

    def test_list_integrations_empty(self, mock_table_service, mock_context):
        """Test listing integrations when none exist"""
        repo = ConfigRepository(mock_context)

        mock_table_service.query_entities.return_value = iter([])

        result = repo.list_integrations()

        assert result == []

    def test_list_integrations_returns_multiple(self, mock_table_service, mock_context):
        """Test listing multiple integrations"""
        repo = ConfigRepository(mock_context)

        integrations_data = [
            {
                "PartitionKey": "test-org-123",
                "RowKey": "integration:msgraph",
                "Type": "msgraph",
                "Enabled": True,
                "Settings": json.dumps({"client_id": "123"}),
                "UpdatedAt": "2024-01-15T10:30:00",
                "UpdatedBy": "admin"
            },
            {
                "PartitionKey": "test-org-123",
                "RowKey": "integration:halopsa",
                "Type": "halopsa",
                "Enabled": False,
                "Settings": json.dumps({"api_key": "key"}),
                "UpdatedAt": "2024-01-15T10:30:00",
                "UpdatedBy": "admin"
            }
        ]

        mock_table_service.query_entities.return_value = iter(integrations_data)

        result = repo.list_integrations()

        assert len(result) == 2

    def test_delete_integration(self, mock_table_service, mock_context):
        """Test deleting integration config"""
        repo = ConfigRepository(mock_context)

        mock_table_service.delete_entity.return_value = True

        result = repo.delete_integration(IntegrationType.MSGRAPH)

        assert result is True
        mock_table_service.delete_entity.assert_called_once()
