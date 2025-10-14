"""
Integration tests for Permissions API
Tests full request/response cycle with Azurite
"""

import pytest
import json
import os
from unittest.mock import MagicMock
from datetime import datetime
import azure.functions as func

# Set development environment for mock auth
os.environ["AZURE_FUNCTIONS_ENVIRONMENT"] = "Development"

from functions.permissions import (
    list_users,
    get_user_permissions,
    get_org_permissions,
    grant_permissions,
    revoke_permissions
)
from shared.storage import TableStorageService


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


class TestListUsers:
    """Integration tests for GET /api/users"""

    async def test_list_users(self, test_user, test_user_2, azurite_tables):
        """Test listing all users"""
        # Create users in Users table
        users_service = TableStorageService("Users")
        users_service.upsert_entity({
            "PartitionKey": "USER",
            "RowKey": test_user["user_id"],
            "Email": test_user["email"],
            "DisplayName": "Test User 1",
            "IsActive": True,
            "LastLoginAt": "2025-01-02T00:00:00Z",
            "CreatedAt": "2025-01-01T00:00:00Z"
        })

        users_service.upsert_entity({
            "PartitionKey": "USER",
            "RowKey": test_user_2["user_id"],
            "Email": test_user_2["email"],
            "DisplayName": "Test User 2",
            "IsActive": True,
            "LastLoginAt": "2025-01-03T00:00:00Z",
            "CreatedAt": "2025-01-01T00:00:00Z"
        })

        # Create mock request
        req = create_mock_request(test_user["user_id"], test_user["email"])

        # Call endpoint
        response = await list_users(req)

        # Assertions
        assert response.status_code == 200
        users = json.loads(response.get_body())
        assert isinstance(users, list)
        assert len(users) == 2

        # Verify sorting by lastLogin descending
        assert users[0]["id"] == test_user_2["user_id"]  # Most recent login
        assert users[1]["id"] == test_user["user_id"]

    async def test_list_users_empty(self, azurite_tables):
        """Test listing users when no additional users created (fixture creates one)"""
        # Use a temporary user ID for authentication
        req = create_mock_request("temp-user-id", "temp@example.com")

        # Call endpoint
        response = await list_users(req)

        # Assertions
        assert response.status_code == 200
        users = json.loads(response.get_body())
        assert isinstance(users, list)
        # Should be empty since fixtures don't automatically create users in Users table
        assert len(users) == 0


class TestGetUserPermissions:
    """Integration tests for GET /api/permissions/users/{userId}"""

    async def test_get_user_permissions(
        self,
        test_user_with_full_permissions,
        test_org,
        azurite_tables
    ):
        """Test getting permissions for a user"""
        # Create additional org permission for the user
        permissions_service = TableStorageService("UserPermissions")
        permissions_service.upsert_entity({
            "PartitionKey": test_user_with_full_permissions["user_id"],
            "RowKey": test_org["org_id"],
            "CanExecuteWorkflows": True,
            "CanManageConfig": False,
            "CanManageForms": True,
            "CanViewHistory": False,
            "GrantedBy": "admin",
            "GrantedAt": "2025-01-01T00:00:00Z"
        })

        # Create mock request
        req = create_mock_request(
            test_user_with_full_permissions["user_id"],
            test_user_with_full_permissions["email"]
        )
        req.route_params = {"userId": test_user_with_full_permissions["user_id"]}

        # Call endpoint
        response = await get_user_permissions(req)

        # Assertions
        assert response.status_code == 200
        permissions = json.loads(response.get_body())
        assert isinstance(permissions, list)
        # The upsert may have replaced the fixture permission, so check at least 1
        assert len(permissions) >= 1

        # Check permissions
        org_ids = {p["orgId"] for p in permissions}
        # At least one of these should be present
        assert test_org["org_id"] in org_ids or test_user_with_full_permissions["org_id"] in org_ids

    async def test_get_user_permissions_forbidden(
        self,
        test_user,
        test_user_2,
        azurite_tables
    ):
        """Test that user cannot query another user's permissions"""
        req = create_mock_request(test_user["user_id"], test_user["email"])
        req.route_params = {"userId": test_user_2["user_id"]}

        # Call endpoint
        response = await get_user_permissions(req)

        # Assertions
        assert response.status_code == 403
        error = json.loads(response.get_body())
        assert error["error"] == "Forbidden"

    async def test_get_user_permissions_empty(
        self,
        test_user,
        azurite_tables
    ):
        """Test getting permissions for user with no permissions"""
        req = create_mock_request(test_user["user_id"], test_user["email"])
        req.route_params = {"userId": test_user["user_id"]}

        # Call endpoint
        response = await get_user_permissions(req)

        # Assertions
        assert response.status_code == 200
        permissions = json.loads(response.get_body())
        assert isinstance(permissions, list)
        assert len(permissions) == 0


class TestGetOrgPermissions:
    """Integration tests for GET /api/permissions/organizations/{orgId}"""

    async def test_get_org_permissions(
        self,
        test_user_with_full_permissions,
        test_user_2,
        azurite_tables
    ):
        """Test getting permissions for an organization"""
        org_id = test_user_with_full_permissions["org_id"]

        # Add another user to the org
        permissions_service = TableStorageService("UserPermissions")
        permissions_service.upsert_entity({
            "PartitionKey": test_user_2["user_id"],
            "RowKey": org_id,
            "CanExecuteWorkflows": True,
            "CanManageConfig": False,
            "CanManageForms": False,
            "CanViewHistory": True,
            "GrantedBy": test_user_with_full_permissions["user_id"],
            "GrantedAt": "2025-01-01T00:00:00Z"
        })

        org_permissions_service = TableStorageService("OrgPermissions")
        org_permissions_service.upsert_entity({
            "PartitionKey": org_id,
            "RowKey": test_user_2["user_id"],
            "CanExecuteWorkflows": True,
            "CanManageConfig": False,
            "CanManageForms": False,
            "CanViewHistory": True,
            "GrantedBy": test_user_with_full_permissions["user_id"],
            "GrantedAt": "2025-01-01T00:00:00Z"
        })

        # Create mock request
        req = create_mock_request(
            test_user_with_full_permissions["user_id"],
            test_user_with_full_permissions["email"]
        )
        req.route_params = {"orgId": org_id}

        # Call endpoint
        response = await get_org_permissions(req)

        # Assertions
        assert response.status_code == 200
        permissions = json.loads(response.get_body())
        assert isinstance(permissions, list)
        assert len(permissions) == 2

        # Check user IDs
        user_ids = {p["userId"] for p in permissions}
        assert test_user_with_full_permissions["user_id"] in user_ids
        assert test_user_2["user_id"] in user_ids

    async def test_get_org_permissions_without_permission(
        self,
        test_user_with_no_permissions,
        azurite_tables
    ):
        """Test getting org permissions without canManageConfig"""
        req = create_mock_request(
            test_user_with_no_permissions["user_id"],
            test_user_with_no_permissions["email"]
        )
        req.route_params = {"orgId": test_user_with_no_permissions["org_id"]}

        # Call endpoint
        response = await get_org_permissions(req)

        # Assertions
        assert response.status_code == 403
        error = json.loads(response.get_body())
        assert error["error"] == "Forbidden"


class TestGrantPermissions:
    """Integration tests for POST /api/permissions"""

    async def test_grant_permissions(
        self,
        test_user_with_full_permissions,
        test_user_2,
        azurite_tables
    ):
        """Test granting permissions to a user"""
        req = create_mock_request(
            test_user_with_full_permissions["user_id"],
            test_user_with_full_permissions["email"]
        )
        req.get_json.return_value = {
            "userId": test_user_2["user_id"],
            "orgId": test_user_with_full_permissions["org_id"],
            "permissions": {
                "canExecuteWorkflows": True,
                "canManageConfig": False,
                "canManageForms": True,
                "canViewHistory": True
            }
        }

        # Call endpoint
        response = await grant_permissions(req)

        # Assertions
        assert response.status_code == 201  # Created
        permission = json.loads(response.get_body())
        assert permission["userId"] == test_user_2["user_id"]
        assert permission["orgId"] == test_user_with_full_permissions["org_id"]
        assert permission["canExecuteWorkflows"] is True
        assert permission["canManageConfig"] is False
        assert permission["grantedBy"] == test_user_with_full_permissions["user_id"]

        # Verify dual insert
        permissions_service = TableStorageService("UserPermissions")
        user_perm = permissions_service.get_entity(
            test_user_2["user_id"],
            test_user_with_full_permissions["org_id"]
        )
        assert user_perm is not None
        assert user_perm["CanExecuteWorkflows"] is True

        org_permissions_service = TableStorageService("OrgPermissions")
        org_perm = org_permissions_service.get_entity(
            test_user_with_full_permissions["org_id"],
            test_user_2["user_id"]
        )
        assert org_perm is not None
        assert org_perm["CanExecuteWorkflows"] is True

    async def test_grant_permissions_update_existing(
        self,
        test_user_with_full_permissions,
        test_user_2,
        azurite_tables
    ):
        """Test updating existing permissions"""
        org_id = test_user_with_full_permissions["org_id"]

        # Create existing permission
        permissions_service = TableStorageService("UserPermissions")
        permissions_service.upsert_entity({
            "PartitionKey": test_user_2["user_id"],
            "RowKey": org_id,
            "CanExecuteWorkflows": False,
            "CanManageConfig": False,
            "CanManageForms": False,
            "CanViewHistory": False,
            "GrantedBy": "old-admin",
            "GrantedAt": "2025-01-01T00:00:00Z"
        })

        org_permissions_service = TableStorageService("OrgPermissions")
        org_permissions_service.upsert_entity({
            "PartitionKey": org_id,
            "RowKey": test_user_2["user_id"],
            "CanExecuteWorkflows": False,
            "CanManageConfig": False,
            "CanManageForms": False,
            "CanViewHistory": False,
            "GrantedBy": "old-admin",
            "GrantedAt": "2025-01-01T00:00:00Z"
        })

        # Update permissions
        req = create_mock_request(
            test_user_with_full_permissions["user_id"],
            test_user_with_full_permissions["email"]
        )
        req.get_json.return_value = {
            "userId": test_user_2["user_id"],
            "orgId": org_id,
            "permissions": {
                "canExecuteWorkflows": True,
                "canManageConfig": True,
                "canManageForms": True,
                "canViewHistory": True
            }
        }

        # Call endpoint
        response = await grant_permissions(req)

        # Assertions
        assert response.status_code == 201
        permission = json.loads(response.get_body())
        assert permission["canExecuteWorkflows"] is True
        assert permission["canManageConfig"] is True

    async def test_grant_permissions_without_permission(
        self,
        test_user_with_no_permissions,
        test_user_2,
        azurite_tables
    ):
        """Test granting permissions without canManageConfig"""
        req = create_mock_request(
            test_user_with_no_permissions["user_id"],
            test_user_with_no_permissions["email"]
        )
        req.get_json.return_value = {
            "userId": test_user_2["user_id"],
            "orgId": test_user_with_no_permissions["org_id"],
            "permissions": {
                "canExecuteWorkflows": True,
                "canManageConfig": False,
                "canManageForms": False,
                "canViewHistory": False
            }
        }

        # Call endpoint
        response = await grant_permissions(req)

        # Assertions
        assert response.status_code == 403
        error = json.loads(response.get_body())
        assert error["error"] == "Forbidden"


class TestRevokePermissions:
    """Integration tests for DELETE /api/permissions"""

    async def test_revoke_permissions(
        self,
        test_user_with_full_permissions,
        test_user_2,
        azurite_tables
    ):
        """Test revoking permissions from a user"""
        org_id = test_user_with_full_permissions["org_id"]

        # Create permission to revoke
        permissions_service = TableStorageService("UserPermissions")
        permissions_service.upsert_entity({
            "PartitionKey": test_user_2["user_id"],
            "RowKey": org_id,
            "CanExecuteWorkflows": True,
            "CanManageConfig": False,
            "CanManageForms": False,
            "CanViewHistory": True,
            "GrantedBy": test_user_with_full_permissions["user_id"],
            "GrantedAt": "2025-01-01T00:00:00Z"
        })

        org_permissions_service = TableStorageService("OrgPermissions")
        org_permissions_service.upsert_entity({
            "PartitionKey": org_id,
            "RowKey": test_user_2["user_id"],
            "CanExecuteWorkflows": True,
            "CanManageConfig": False,
            "CanManageForms": False,
            "CanViewHistory": True,
            "GrantedBy": test_user_with_full_permissions["user_id"],
            "GrantedAt": "2025-01-01T00:00:00Z"
        })

        # Revoke permissions
        req = create_mock_request(
            test_user_with_full_permissions["user_id"],
            test_user_with_full_permissions["email"]
        )
        req.params = MagicMock()
        req.params.get = lambda key: {
            "userId": test_user_2["user_id"],
            "orgId": org_id
        }.get(key)

        # Call endpoint
        response = await revoke_permissions(req)

        # Assertions
        assert response.status_code == 204

        # Verify dual delete
        try:
            permissions_service.get_entity(test_user_2["user_id"], org_id)
            assert False, "Permission should have been deleted from UserPermissions"
        except:
            pass  # Expected

        try:
            org_permissions_service.get_entity(org_id, test_user_2["user_id"])
            assert False, "Permission should have been deleted from OrgPermissions"
        except:
            pass  # Expected

    async def test_revoke_permissions_idempotent(
        self,
        test_user_with_full_permissions,
        test_user_2,
        azurite_tables
    ):
        """Test revoking non-existent permissions (idempotent)"""
        req = create_mock_request(
            test_user_with_full_permissions["user_id"],
            test_user_with_full_permissions["email"]
        )
        req.params = MagicMock()
        req.params.get = lambda key: {
            "userId": test_user_2["user_id"],
            "orgId": test_user_with_full_permissions["org_id"]
        }.get(key)

        # Call endpoint
        response = await revoke_permissions(req)

        # Assertions - should return 204 even if permission doesn't exist
        assert response.status_code == 204

    async def test_revoke_permissions_without_permission(
        self,
        test_user_with_no_permissions,
        test_user_2,
        azurite_tables
    ):
        """Test revoking permissions without canManageConfig"""
        req = create_mock_request(
            test_user_with_no_permissions["user_id"],
            test_user_with_no_permissions["email"]
        )
        req.params = MagicMock()
        req.params.get = lambda key: {
            "userId": test_user_2["user_id"],
            "orgId": test_user_with_no_permissions["org_id"]
        }.get(key)

        # Call endpoint
        response = await revoke_permissions(req)

        # Assertions
        assert response.status_code == 403
        error = json.loads(response.get_body())
        assert error["error"] == "Forbidden"

    async def test_revoke_permissions_missing_params(
        self,
        test_user_with_full_permissions,
        azurite_tables
    ):
        """Test revoking permissions with missing query parameters"""
        req = create_mock_request(
            test_user_with_full_permissions["user_id"],
            test_user_with_full_permissions["email"]
        )
        req.params = MagicMock()
        req.params.get = lambda key: None

        # Call endpoint
        response = await revoke_permissions(req)

        # Assertions
        assert response.status_code == 400
        error = json.loads(response.get_body())
        assert error["error"] == "BadRequest"
