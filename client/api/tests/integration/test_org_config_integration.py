"""
Integration tests for OrgConfig API
Tests full request/response cycle with Azurite
"""

import pytest
import json
import os
from unittest.mock import MagicMock
import azure.functions as func

# Set development environment for mock auth
os.environ["AZURE_FUNCTIONS_ENVIRONMENT"] = "Development"

from functions.org_config import (
    get_config,
    set_config,
    delete_config
)
from shared.storage import TableStorageService
from shared.models import ConfigType


def create_mock_request(user_id, email="test@example.com", display_name="Test User", **kwargs):
    """Helper to create a properly mocked request for testing"""
    req = MagicMock(spec=func.HttpRequest)
    req.headers = MagicMock()
    req.headers.get = lambda key, default=None: {
        "X-Test-User-Id": user_id,
        "X-Test-User-Email": email,
        "X-Test-User-Name": display_name
    }.get(key, default)
    req.url = "http://localhost:7071/api/test"

    # Add any additional attributes
    for key, value in kwargs.items():
        setattr(req, key, value)

    return req


class TestGetOrgConfig:
    """Integration tests for GET /api/organizations/{orgId}/config"""

    def test_get_org_config_with_permission(
        self,
        test_user_with_full_permissions,
        azurite_tables
    ):
        """Test getting org config when user has canViewHistory permission"""
        # Create some test config entries
        config_service = TableStorageService("Config")
        org_id = test_user_with_full_permissions["org_id"]

        config_service.insert_entity({
            "PartitionKey": org_id,
            "RowKey": "config:api_timeout",
            "Value": "30",
            "Type": ConfigType.INT.value,
            "Description": "API timeout in seconds",
            "UpdatedAt": "2025-01-01T00:00:00Z",
            "UpdatedBy": "test-user"
        })

        config_service.insert_entity({
            "PartitionKey": org_id,
            "RowKey": "config:enable_notifications",
            "Value": "true",
            "Type": ConfigType.BOOL.value,
            "Description": None,
            "UpdatedAt": "2025-01-01T00:00:00Z",
            "UpdatedBy": "test-user"
        })

        # Create mock request
        req = create_mock_request(
            test_user_with_full_permissions["user_id"],
            test_user_with_full_permissions["email"]
        )
        req.route_params = {"orgId": org_id}

        # Call endpoint
        response = get_config(req)

        # Assertions
        assert response.status_code == 200
        configs = json.loads(response.get_body())
        assert isinstance(configs, list)
        assert len(configs) == 2

        # Check config entries
        config_keys = {c["key"] for c in configs}
        assert "api_timeout" in config_keys
        assert "enable_notifications" in config_keys

    def test_get_org_config_without_permission(
        self,
        test_user_with_no_permissions,
        azurite_tables
    ):
        """Test getting org config when user lacks canViewHistory permission"""
        req = create_mock_request(
            test_user_with_no_permissions["user_id"],
            test_user_with_no_permissions["email"]
        )
        req.route_params = {"orgId": test_user_with_no_permissions["org_id"]}

        # Call endpoint
        response = get_config(req)

        # Assertions
        assert response.status_code == 403
        error = json.loads(response.get_body())
        assert error["error"] == "Forbidden"

    def test_get_org_config_empty(
        self,
        test_user_with_full_permissions,
        azurite_tables
    ):
        """Test getting org config when no config exists"""
        req = create_mock_request(
            test_user_with_full_permissions["user_id"],
            test_user_with_full_permissions["email"]
        )
        req.route_params = {"orgId": test_user_with_full_permissions["org_id"]}

        # Call endpoint
        response = get_config(req)

        # Assertions
        assert response.status_code == 200
        configs = json.loads(response.get_body())
        assert isinstance(configs, list)
        assert len(configs) == 0


class TestSetOrgConfig:
    """Integration tests for POST /api/organizations/{orgId}/config"""

    def test_set_org_config_create_new(
        self,
        test_user_with_full_permissions,
        azurite_tables
    ):
        """Test creating a new config key"""
        req = create_mock_request(
            test_user_with_full_permissions["user_id"],
            test_user_with_full_permissions["email"]
        )
        req.route_params = {"orgId": test_user_with_full_permissions["org_id"]}
        req.get_json.return_value = {
            "key": "api_timeout",
            "value": "30",
            "type": ConfigType.INT.value,
            "description": "API timeout in seconds"
        }

        # Call endpoint
        response = set_config(req)

        # Assertions
        assert response.status_code == 201  # Created
        config = json.loads(response.get_body())
        assert config["key"] == "api_timeout"
        assert config["value"] == "30"
        assert config["type"] == ConfigType.INT.value
        assert config["description"] == "API timeout in seconds"
        assert config["updatedBy"] == test_user_with_full_permissions["user_id"]

    def test_set_org_config_update_existing(
        self,
        test_user_with_full_permissions,
        azurite_tables
    ):
        """Test updating an existing config key"""
        org_id = test_user_with_full_permissions["org_id"]

        # Create existing config
        config_service = TableStorageService("Config")
        config_service.insert_entity({
            "PartitionKey": org_id,
            "RowKey": "config:api_timeout",
            "Value": "30",
            "Type": ConfigType.INT.value,
            "Description": "Old description",
            "UpdatedAt": "2025-01-01T00:00:00Z",
            "UpdatedBy": "old-user"
        })

        # Update config
        req = create_mock_request(
            test_user_with_full_permissions["user_id"],
            test_user_with_full_permissions["email"]
        )
        req.route_params = {"orgId": org_id}
        req.get_json.return_value = {
            "key": "api_timeout",
            "value": "60",
            "type": ConfigType.INT.value,
            "description": "Updated timeout"
        }

        # Call endpoint
        response = set_config(req)

        # Assertions
        assert response.status_code == 200  # OK (updated)
        config = json.loads(response.get_body())
        assert config["key"] == "api_timeout"
        assert config["value"] == "60"
        assert config["description"] == "Updated timeout"
        assert config["updatedBy"] == test_user_with_full_permissions["user_id"]

    def test_set_org_config_without_permission(
        self,
        test_user_with_no_permissions,
        azurite_tables
    ):
        """Test setting config when user lacks canManageConfig permission"""
        req = create_mock_request(
            test_user_with_no_permissions["user_id"],
            test_user_with_no_permissions["email"]
        )
        req.route_params = {"orgId": test_user_with_no_permissions["org_id"]}
        req.get_json.return_value = {
            "key": "test_key",
            "value": "test_value",
            "type": ConfigType.STRING.value
        }

        # Call endpoint
        response = set_config(req)

        # Assertions
        assert response.status_code == 403
        error = json.loads(response.get_body())
        assert error["error"] == "Forbidden"

    def test_set_org_config_validation_error(
        self,
        test_user_with_full_permissions,
        azurite_tables
    ):
        """Test setting config with invalid key format"""
        req = create_mock_request(
            test_user_with_full_permissions["user_id"],
            test_user_with_full_permissions["email"]
        )
        req.route_params = {"orgId": test_user_with_full_permissions["org_id"]}
        req.get_json.return_value = {
            "key": "invalid-key!",  # Invalid: contains special chars
            "value": "test_value",
            "type": ConfigType.STRING.value
        }

        # Call endpoint
        response = set_config(req)

        # Assertions
        assert response.status_code == 400
        error = json.loads(response.get_body())
        assert error["error"] == "ValidationError"

    def test_set_org_config_all_types(
        self,
        test_user_with_full_permissions,
        azurite_tables
    ):
        """Test setting config with all supported types"""
        test_configs = [
            ("string_key", "string_value", ConfigType.STRING),
            ("int_key", "42", ConfigType.INT),
            ("bool_key", "true", ConfigType.BOOL),
            ("json_key", '{"foo": "bar"}', ConfigType.JSON),
            ("secret_key", "vault://secrets/key", ConfigType.SECRET_REF),
        ]

        for key, value, config_type in test_configs:
            req = create_mock_request(
                test_user_with_full_permissions["user_id"],
                test_user_with_full_permissions["email"]
            )
            req.route_params = {"orgId": test_user_with_full_permissions["org_id"]}
            req.get_json.return_value = {
                "key": key,
                "value": value,
                "type": config_type.value
            }

            response = set_config(req)
            assert response.status_code == 201
            config = json.loads(response.get_body())
            assert config["key"] == key
            assert config["value"] == value
            assert config["type"] == config_type.value


class TestDeleteOrgConfig:
    """Integration tests for DELETE /api/organizations/{orgId}/config/{key}"""

    def test_delete_org_config(
        self,
        test_user_with_full_permissions,
        azurite_tables
    ):
        """Test deleting an existing config key"""
        org_id = test_user_with_full_permissions["org_id"]

        # Create config to delete
        config_service = TableStorageService("Config")
        config_service.insert_entity({
            "PartitionKey": org_id,
            "RowKey": "config:test_key",
            "Value": "test_value",
            "Type": ConfigType.STRING.value,
            "Description": None,
            "UpdatedAt": "2025-01-01T00:00:00Z",
            "UpdatedBy": "test-user"
        })

        # Delete config
        req = create_mock_request(
            test_user_with_full_permissions["user_id"],
            test_user_with_full_permissions["email"]
        )
        req.route_params = {"orgId": org_id, "key": "test_key"}

        # Call endpoint
        response = delete_config(req)

        # Assertions
        assert response.status_code == 204

        # Verify config is deleted
        try:
            config_service.get_entity(org_id, "config:test_key")
            assert False, "Config should have been deleted"
        except:
            pass  # Expected - config doesn't exist

    def test_delete_org_config_idempotent(
        self,
        test_user_with_full_permissions,
        azurite_tables
    ):
        """Test deleting a non-existent config (idempotent)"""
        req = create_mock_request(
            test_user_with_full_permissions["user_id"],
            test_user_with_full_permissions["email"]
        )
        req.route_params = {
            "orgId": test_user_with_full_permissions["org_id"],
            "key": "nonexistent_key"
        }

        # Call endpoint
        response = delete_config(req)

        # Assertions - should return 204 even if key doesn't exist
        assert response.status_code == 204

    def test_delete_org_config_without_permission(
        self,
        test_user_with_no_permissions,
        azurite_tables
    ):
        """Test deleting config when user lacks canManageConfig permission"""
        req = create_mock_request(
            test_user_with_no_permissions["user_id"],
            test_user_with_no_permissions["email"]
        )
        req.route_params = {
            "orgId": test_user_with_no_permissions["org_id"],
            "key": "test_key"
        }

        # Call endpoint
        response = delete_config(req)

        # Assertions
        assert response.status_code == 403
        error = json.loads(response.get_body())
        assert error["error"] == "Forbidden"
