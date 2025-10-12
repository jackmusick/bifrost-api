"""
Integration tests for Organizations API
Tests full request/response cycle with Azurite
"""

import pytest
import json
import os
from unittest.mock import MagicMock, patch
import azure.functions as func

# Set development environment for mock auth
os.environ["AZURE_FUNCTIONS_ENVIRONMENT"] = "Development"

from functions.organizations import (
    list_organizations,
    create_organization,
    get_organization,
    update_organization,
    delete_organization
)
from shared.auth import AuthenticatedUser


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


class TestListOrganizations:
    """Integration tests for GET /api/organizations"""

    def test_list_organizations_with_access(
        self,
        test_user_with_full_permissions,
        azurite_tables
    ):
        """Test listing organizations when user has access"""
        # Create mock request with proper headers for local dev
        req = MagicMock(spec=func.HttpRequest)
        req.headers = MagicMock()
        req.headers.get = lambda key, default=None: {
            "X-Test-User-Id": test_user_with_full_permissions["user_id"],
            "X-Test-User-Email": test_user_with_full_permissions["email"],
            "X-Test-User-Name": test_user_with_full_permissions["display_name"]
        }.get(key, default)
        req.url = "http://localhost:7071/api/organizations"

        # Call endpoint (decorator will inject req.user)
        response = list_organizations(req)

        # Assertions
        assert response.status_code == 200
        orgs = json.loads(response.get_body())
        assert isinstance(orgs, list)
        assert len(orgs) == 1
        assert orgs[0]["id"] == test_user_with_full_permissions["org_id"]
        assert orgs[0]["name"] == "Test Organization"

    def test_list_organizations_no_access(self, test_user, azurite_tables):
        """Test listing organizations when user has no permissions"""
        # Create mock request
        req = create_mock_request(test_user["user_id"], test_user["email"])

        # Call endpoint
        response = list_organizations(req)

        # Assertions
        assert response.status_code == 200
        orgs = json.loads(response.get_body())
        assert isinstance(orgs, list)
        assert len(orgs) == 0


class TestCreateOrganization:
    """Integration tests for POST /api/organizations"""

    def test_create_organization_valid(self, test_user, azurite_tables):
        """Test creating a new organization with valid data"""
        # Create mock request
        req = create_mock_request(test_user["user_id"], test_user["email"])
        req.get_json.return_value = {
            "name": "New Test Org",
            "tenantId": "12345678-1234-1234-1234-123456789012"
        }

        # Call endpoint
        response = create_organization(req)

        # Assertions
        assert response.status_code == 201
        org = json.loads(response.get_body())
        assert org["name"] == "New Test Org"
        assert org["tenantId"] == "12345678-1234-1234-1234-123456789012"
        assert org["isActive"] is True
        assert org["createdBy"] == test_user["user_id"]
        assert "id" in org
        assert org["id"].startswith("org-")

    def test_create_organization_without_tenant_id(self, test_user, azurite_tables):
        """Test creating organization without tenantId (optional field)"""
        # Create mock request
        req = create_mock_request(test_user["user_id"], test_user["email"])
        req.get_json.return_value = {"name": "Org Without Tenant"}

        # Call endpoint
        response = create_organization(req)

        # Assertions
        assert response.status_code == 201
        org = json.loads(response.get_body())
        assert org["name"] == "Org Without Tenant"
        assert org["tenantId"] is None

    def test_create_organization_invalid_empty_name(self, test_user, azurite_tables):
        """Test creating organization with empty name fails validation"""
        # Create mock request
        req = create_mock_request(test_user["user_id"], test_user["email"])
        req.get_json.return_value = {"name": ""}

        # Call endpoint
        response = create_organization(req)

        # Assertions
        assert response.status_code == 400
        error = json.loads(response.get_body())
        assert error["error"] == "ValidationError"
        assert "errors" in error["details"]

    def test_create_organization_missing_name(self, test_user, azurite_tables):
        """Test creating organization without name fails validation"""
        # Create mock request
        req = create_mock_request(test_user["user_id"], test_user["email"])
        req.get_json.return_value = {}

        # Call endpoint
        response = create_organization(req)

        # Assertions
        assert response.status_code == 400
        error = json.loads(response.get_body())
        assert error["error"] == "ValidationError"


class TestGetOrganization:
    """Integration tests for GET /api/organizations/{orgId}"""

    def test_get_organization_with_access(
        self,
        test_user_with_full_permissions,
        azurite_tables
    ):
        """Test getting organization when user has access"""
        # Create mock request
        req = create_mock_request(
            test_user_with_full_permissions["user_id"],
            test_user_with_full_permissions["email"]
        )
        req.route_params = {"orgId": test_user_with_full_permissions["org_id"]}

        # Call endpoint
        response = get_organization(req)

        # Assertions
        assert response.status_code == 200
        org = json.loads(response.get_body())
        assert org["id"] == test_user_with_full_permissions["org_id"]
        assert org["name"] == "Test Organization"

    def test_get_organization_without_access(
        self,
        test_org,
        test_user_2,
        azurite_tables
    ):
        """Test getting organization when user has no access returns 403"""
        # Create mock request
        req = create_mock_request(test_user_2["user_id"], test_user_2["email"])
        req.route_params = {"orgId": test_org["org_id"]}

        # Call endpoint
        response = get_organization(req)

        # Assertions
        assert response.status_code == 403
        error = json.loads(response.get_body())
        assert error["error"] == "Forbidden"

    def test_get_organization_not_found(
        self,
        test_user_with_full_permissions,
        azurite_tables
    ):
        """Test getting non-existent organization returns 404"""
        # First, create a permission for a non-existent org
        from shared.storage import TableStorageService
        permissions_service = TableStorageService("UserPermissions")
        permissions_service.insert_entity({
            "PartitionKey": test_user_with_full_permissions["user_id"],
            "RowKey": "non-existent-org",
            "CanExecuteWorkflows": True,
            "CanManageConfig": True,
            "CanManageForms": True,
            "CanViewHistory": True,
            "GrantedBy": "test",
            "GrantedAt": "2025-01-01T00:00:00Z"
        })

        # Create mock request
        req = create_mock_request(
            test_user_with_full_permissions["user_id"],
            test_user_with_full_permissions["email"]
        )
        req.route_params = {"orgId": "non-existent-org"}

        # Call endpoint
        response = get_organization(req)

        # Assertions
        assert response.status_code == 404
        error = json.loads(response.get_body())
        assert error["error"] == "NotFound"


class TestUpdateOrganization:
    """Integration tests for PATCH /api/organizations/{orgId}"""

    def test_update_organization_name(
        self,
        test_user_with_full_permissions,
        azurite_tables
    ):
        """Test updating organization name"""
        # Create mock request
        req = create_mock_request(
            test_user_with_full_permissions["user_id"],
            test_user_with_full_permissions["email"]
        )
        req.route_params = {"orgId": test_user_with_full_permissions["org_id"]}
        req.get_json.return_value = {"name": "Updated Organization Name"}

        # Call endpoint
        response = update_organization(req)

        # Assertions
        assert response.status_code == 200
        org = json.loads(response.get_body())
        assert org["name"] == "Updated Organization Name"
        assert org["id"] == test_user_with_full_permissions["org_id"]

    def test_update_organization_without_permission(
        self,
        test_user_with_no_permissions,
        azurite_tables
    ):
        """Test updating organization without canManageConfig permission returns 403"""
        # Create mock request
        req = create_mock_request(
            test_user_with_no_permissions["user_id"],
            test_user_with_no_permissions["email"]
        )
        req.route_params = {"orgId": test_user_with_no_permissions["org_id"]}
        req.get_json.return_value = {"name": "Should Not Update"}

        # Call endpoint
        response = update_organization(req)

        # Assertions
        assert response.status_code == 403
        error = json.loads(response.get_body())
        assert error["error"] == "Forbidden"

    def test_update_organization_validation_error(
        self,
        test_user_with_full_permissions,
        azurite_tables
    ):
        """Test updating with invalid data fails validation"""
        # Create mock request
        req = create_mock_request(
            test_user_with_full_permissions["user_id"],
            test_user_with_full_permissions["email"]
        )
        req.route_params = {"orgId": test_user_with_full_permissions["org_id"]}
        req.get_json.return_value = {"name": ""}  # Empty name

        # Call endpoint
        response = update_organization(req)

        # Assertions
        assert response.status_code == 400
        error = json.loads(response.get_body())
        assert error["error"] == "ValidationError"


class TestDeleteOrganization:
    """Integration tests for DELETE /api/organizations/{orgId}"""

    def test_delete_organization(
        self,
        test_user_with_full_permissions,
        azurite_tables
    ):
        """Test soft deleting an organization"""
        # Create mock request
        req = create_mock_request(
            test_user_with_full_permissions["user_id"],
            test_user_with_full_permissions["email"]
        )
        req.route_params = {"orgId": test_user_with_full_permissions["org_id"]}

        # Call endpoint
        response = delete_organization(req)

        # Assertions
        assert response.status_code == 204

        # Verify org is marked inactive
        from shared.storage import TableStorageService
        orgs_service = TableStorageService("Organizations")
        org = orgs_service.get_entity("ORG", test_user_with_full_permissions["org_id"])
        assert org["IsActive"] is False

    def test_delete_organization_without_permission(
        self,
        test_user_with_no_permissions,
        azurite_tables
    ):
        """Test deleting organization without permission returns 403"""
        # Create mock request
        req = create_mock_request(
            test_user_with_no_permissions["user_id"],
            test_user_with_no_permissions["email"]
        )
        req.route_params = {"orgId": test_user_with_no_permissions["org_id"]}

        # Call endpoint
        response = delete_organization(req)

        # Assertions
        assert response.status_code == 403
        error = json.loads(response.get_body())
        assert error["error"] == "Forbidden"
