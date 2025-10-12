"""
Integration tests for IntegrationConfig API
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
    get_integrations,
    set_integration,
    delete_integration
)
from shared.storage import TableStorageService
from shared.models import IntegrationType


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


class TestGetIntegrations:
    """Integration tests for GET /api/organizations/{orgId}/integrations"""

    def test_get_integrations_with_permission(
        self,
        test_user_with_full_permissions,
        azurite_tables
    ):
        """Test getting integrations when user has canViewHistory permission"""
        # Create some test integrations
        integration_service = TableStorageService("IntegrationConfig")
        org_id = test_user_with_full_permissions["org_id"]

        # Add Microsoft Graph integration
        integration_service.insert_entity({
            "PartitionKey": org_id,
            "RowKey": "integration:msgraph",
            "Enabled": True,
            "Settings": json.dumps({
                "tenant_id": "12345678-1234-1234-1234-123456789012",
                "client_id": "87654321-4321-4321-4321-210987654321",
                "client_secret_ref": f"{org_id}-msgraph-secret"
            }),
            "UpdatedAt": "2025-01-01T00:00:00Z",
            "UpdatedBy": "test-user"
        })

        # Add HaloPSA integration
        integration_service.insert_entity({
            "PartitionKey": org_id,
            "RowKey": "integration:halopsa",
            "Enabled": False,
            "Settings": json.dumps({
                "api_url": "https://tenant.halopsa.com",
                "client_id": "halopsa-client-123",
                "api_key_ref": f"{org_id}-halopsa-key"
            }),
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
        response = get_integrations(req)

        # Assertions
        assert response.status_code == 200
        integrations = json.loads(response.get_body())
        assert isinstance(integrations, list)
        assert len(integrations) == 2

        # Check integrations
        integration_types = {i["type"] for i in integrations}
        assert "msgraph" in integration_types
        assert "halopsa" in integration_types

        # Check msgraph details
        msgraph = next(i for i in integrations if i["type"] == "msgraph")
        assert msgraph["enabled"] is True
        assert msgraph["settings"]["tenant_id"] == "12345678-1234-1234-1234-123456789012"

    def test_get_integrations_without_permission(
        self,
        test_user_with_no_permissions,
        azurite_tables
    ):
        """Test getting integrations when user lacks canViewHistory permission"""
        req = create_mock_request(
            test_user_with_no_permissions["user_id"],
            test_user_with_no_permissions["email"]
        )
        req.route_params = {"orgId": test_user_with_no_permissions["org_id"]}

        # Call endpoint
        response = get_integrations(req)

        # Assertions
        assert response.status_code == 403
        error = json.loads(response.get_body())
        assert error["error"] == "Forbidden"

    def test_get_integrations_empty(
        self,
        test_user_with_full_permissions,
        azurite_tables
    ):
        """Test getting integrations when no integrations exist"""
        req = create_mock_request(
            test_user_with_full_permissions["user_id"],
            test_user_with_full_permissions["email"]
        )
        req.route_params = {"orgId": test_user_with_full_permissions["org_id"]}

        # Call endpoint
        response = get_integrations(req)

        # Assertions
        assert response.status_code == 200
        integrations = json.loads(response.get_body())
        assert isinstance(integrations, list)
        assert len(integrations) == 0


class TestSetIntegration:
    """Integration tests for POST /api/organizations/{orgId}/integrations"""

    def test_set_msgraph_integration_create_new(
        self,
        test_user_with_full_permissions,
        azurite_tables
    ):
        """Test creating a new Microsoft Graph integration"""
        req = create_mock_request(
            test_user_with_full_permissions["user_id"],
            test_user_with_full_permissions["email"]
        )
        req.route_params = {"orgId": test_user_with_full_permissions["org_id"]}
        req.get_json.return_value = {
            "type": IntegrationType.MSGRAPH.value,
            "enabled": True,
            "settings": {
                "tenant_id": "12345678-1234-1234-1234-123456789012",
                "client_id": "87654321-4321-4321-4321-210987654321",
                "client_secret_ref": f"{test_user_with_full_permissions['org_id']}-msgraph-secret"
            }
        }

        # Call endpoint
        response = set_integration(req)

        # Assertions
        assert response.status_code == 201  # Created
        integration = json.loads(response.get_body())
        assert integration["type"] == "msgraph"
        assert integration["enabled"] is True
        assert integration["settings"]["tenant_id"] == "12345678-1234-1234-1234-123456789012"
        assert integration["updatedBy"] == test_user_with_full_permissions["user_id"]

    def test_set_halopsa_integration_create_new(
        self,
        test_user_with_full_permissions,
        azurite_tables
    ):
        """Test creating a new HaloPSA integration"""
        req = create_mock_request(
            test_user_with_full_permissions["user_id"],
            test_user_with_full_permissions["email"]
        )
        req.route_params = {"orgId": test_user_with_full_permissions["org_id"]}
        req.get_json.return_value = {
            "type": IntegrationType.HALOPSA.value,
            "enabled": True,
            "settings": {
                "api_url": "https://tenant.halopsa.com",
                "client_id": "halopsa-client-123",
                "api_key_ref": f"{test_user_with_full_permissions['org_id']}-halopsa-key"
            }
        }

        # Call endpoint
        response = set_integration(req)

        # Assertions
        assert response.status_code == 201  # Created
        integration = json.loads(response.get_body())
        assert integration["type"] == "halopsa"
        assert integration["enabled"] is True
        assert integration["settings"]["api_url"] == "https://tenant.halopsa.com"

    def test_set_integration_update_existing(
        self,
        test_user_with_full_permissions,
        azurite_tables
    ):
        """Test updating an existing integration"""
        org_id = test_user_with_full_permissions["org_id"]

        # Create existing integration
        integration_service = TableStorageService("IntegrationConfig")
        integration_service.insert_entity({
            "PartitionKey": org_id,
            "RowKey": "integration:msgraph",
            "Enabled": True,
            "Settings": json.dumps({
                "tenant_id": "old-tenant-id",
                "client_id": "old-client-id",
                "client_secret_ref": f"{org_id}-msgraph-secret"
            }),
            "UpdatedAt": "2025-01-01T00:00:00Z",
            "UpdatedBy": "old-user"
        })

        # Update integration
        req = create_mock_request(
            test_user_with_full_permissions["user_id"],
            test_user_with_full_permissions["email"]
        )
        req.route_params = {"orgId": org_id}
        req.get_json.return_value = {
            "type": IntegrationType.MSGRAPH.value,
            "enabled": False,  # Changed
            "settings": {
                "tenant_id": "new-tenant-id",  # Changed
                "client_id": "new-client-id",  # Changed
                "client_secret_ref": f"{org_id}-msgraph-secret-new"
            }
        }

        # Call endpoint
        response = set_integration(req)

        # Assertions
        assert response.status_code == 200  # OK (updated)
        integration = json.loads(response.get_body())
        assert integration["type"] == "msgraph"
        assert integration["enabled"] is False
        assert integration["settings"]["tenant_id"] == "new-tenant-id"
        assert integration["updatedBy"] == test_user_with_full_permissions["user_id"]

    def test_set_integration_without_permission(
        self,
        test_user_with_no_permissions,
        azurite_tables
    ):
        """Test setting integration when user lacks canManageConfig permission"""
        req = create_mock_request(
            test_user_with_no_permissions["user_id"],
            test_user_with_no_permissions["email"]
        )
        req.route_params = {"orgId": test_user_with_no_permissions["org_id"]}
        req.get_json.return_value = {
            "type": IntegrationType.MSGRAPH.value,
            "enabled": True,
            "settings": {
                "tenant_id": "12345678-1234-1234-1234-123456789012",
                "client_id": "87654321-4321-4321-4321-210987654321",
                "client_secret_ref": "test-secret"
            }
        }

        # Call endpoint
        response = set_integration(req)

        # Assertions
        assert response.status_code == 403
        error = json.loads(response.get_body())
        assert error["error"] == "Forbidden"

    def test_set_integration_validation_error_missing_tenant_id(
        self,
        test_user_with_full_permissions,
        azurite_tables
    ):
        """Test setting msgraph integration with missing tenant_id fails"""
        req = create_mock_request(
            test_user_with_full_permissions["user_id"],
            test_user_with_full_permissions["email"]
        )
        req.route_params = {"orgId": test_user_with_full_permissions["org_id"]}
        req.get_json.return_value = {
            "type": IntegrationType.MSGRAPH.value,
            "enabled": True,
            "settings": {
                # Missing tenant_id
                "client_id": "87654321-4321-4321-4321-210987654321",
                "client_secret_ref": "test-secret"
            }
        }

        # Call endpoint
        response = set_integration(req)

        # Assertions
        assert response.status_code == 400
        error = json.loads(response.get_body())
        assert error["error"] == "ValidationError"

    def test_set_integration_validation_error_invalid_type(
        self,
        test_user_with_full_permissions,
        azurite_tables
    ):
        """Test setting integration with invalid type fails"""
        req = create_mock_request(
            test_user_with_full_permissions["user_id"],
            test_user_with_full_permissions["email"]
        )
        req.route_params = {"orgId": test_user_with_full_permissions["org_id"]}
        req.get_json.return_value = {
            "type": "invalid_type",
            "enabled": True,
            "settings": {"foo": "bar"}
        }

        # Call endpoint
        response = set_integration(req)

        # Assertions
        assert response.status_code == 400
        error = json.loads(response.get_body())
        assert error["error"] == "ValidationError"


class TestDeleteIntegration:
    """Integration tests for DELETE /api/organizations/{orgId}/integrations/{type}"""

    def test_delete_integration(
        self,
        test_user_with_full_permissions,
        azurite_tables
    ):
        """Test deleting an existing integration"""
        org_id = test_user_with_full_permissions["org_id"]

        # Create integration to delete
        integration_service = TableStorageService("IntegrationConfig")
        integration_service.insert_entity({
            "PartitionKey": org_id,
            "RowKey": "integration:msgraph",
            "Enabled": True,
            "Settings": json.dumps({
                "tenant_id": "12345678-1234-1234-1234-123456789012",
                "client_id": "87654321-4321-4321-4321-210987654321",
                "client_secret_ref": f"{org_id}-msgraph-secret"
            }),
            "UpdatedAt": "2025-01-01T00:00:00Z",
            "UpdatedBy": "test-user"
        })

        # Delete integration
        req = create_mock_request(
            test_user_with_full_permissions["user_id"],
            test_user_with_full_permissions["email"]
        )
        req.route_params = {"orgId": org_id, "type": "msgraph"}

        # Call endpoint
        response = delete_integration(req)

        # Assertions
        assert response.status_code == 204

        # Verify integration is deleted
        try:
            integration_service.get_entity(org_id, "integration:msgraph")
            assert False, "Integration should have been deleted"
        except:
            pass  # Expected - integration doesn't exist

    def test_delete_integration_idempotent(
        self,
        test_user_with_full_permissions,
        azurite_tables
    ):
        """Test deleting a non-existent integration (idempotent)"""
        req = create_mock_request(
            test_user_with_full_permissions["user_id"],
            test_user_with_full_permissions["email"]
        )
        req.route_params = {
            "orgId": test_user_with_full_permissions["org_id"],
            "type": "nonexistent"
        }

        # Call endpoint
        response = delete_integration(req)

        # Assertions - should return 204 even if integration doesn't exist
        assert response.status_code == 204

    def test_delete_integration_without_permission(
        self,
        test_user_with_no_permissions,
        azurite_tables
    ):
        """Test deleting integration when user lacks canManageConfig permission"""
        req = create_mock_request(
            test_user_with_no_permissions["user_id"],
            test_user_with_no_permissions["email"]
        )
        req.route_params = {
            "orgId": test_user_with_no_permissions["org_id"],
            "type": "msgraph"
        }

        # Call endpoint
        response = delete_integration(req)

        # Assertions
        assert response.status_code == 403
        error = json.loads(response.get_body())
        assert error["error"] == "Forbidden"
