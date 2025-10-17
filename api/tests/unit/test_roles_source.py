"""
Unit tests for GetRoles endpoint (roles_source.py)
Tests automatic role assignment by Azure Static Web Apps
"""

import json
from unittest.mock import Mock, patch

import azure.functions as func
import pytest

from functions.roles_source import get_roles
from shared.storage import TableStorageService


class TestGetRoles:
    """Test GetRoles endpoint for SWA role assignment"""

    @pytest.fixture
    def mock_users_table(self, monkeypatch):
        """Mock Users table for user lookups"""
        mock_table = Mock(spec=TableStorageService)

        def mock_table_service_init(table_name):
            if table_name == "Users":
                return mock_table
            return Mock(spec=TableStorageService)

        monkeypatch.setattr("functions.roles_source.TableStorageService", mock_table_service_init)
        return mock_table

    def test_first_user_auto_promotion(self, mock_users_table):
        """First user in system auto-promoted to PlatformAdmin"""
        # Mock user doesn't exist
        mock_users_table.get_entity.return_value = None

        # Mock query_entities to return empty list (no users in system)
        mock_users_table.query_entities.return_value = iter([])

        # Mock successful insert
        mock_users_table.insert_entity.return_value = {
            "PartitionKey": "first@example.com",
            "RowKey": "user",
            "Email": "first@example.com",
            "DisplayName": "first",
            "UserType": "PLATFORM",
            "IsPlatformAdmin": True,
            "IsActive": True
        }

        # Create request from SWA
        req = Mock(spec=func.HttpRequest)
        req.get_json.return_value = {
            "userId": "user-id-123",
            "userDetails": "first@example.com",
            "identityProvider": "aad"
        }

        # Call GetRoles
        response = get_roles(req)

        # Verify response
        assert response.status_code == 200
        body = json.loads(response.get_body())
        assert "roles" in body
        assert "authenticated" in body["roles"]
        assert "PlatformAdmin" in body["roles"]

        # Verify user was created
        mock_users_table.insert_entity.assert_called_once()
        created_user = mock_users_table.insert_entity.call_args[0][0]
        assert created_user["Email"] == "first@example.com"
        assert created_user["UserType"] == "PLATFORM"
        assert created_user["IsPlatformAdmin"] is True

    def test_existing_platform_admin(self, mock_users_table):
        """Existing PlatformAdmin gets PlatformAdmin role"""
        # Mock existing platform admin user
        mock_users_table.get_entity.return_value = {
            "PartitionKey": "admin@example.com",
            "RowKey": "user",
            "Email": "admin@example.com",
            "DisplayName": "Admin",
            "UserType": "PLATFORM",
            "IsPlatformAdmin": True,
            "IsActive": True
        }

        # Create request from SWA
        req = Mock(spec=func.HttpRequest)
        req.get_json.return_value = {
            "userId": "admin-id-456",
            "userDetails": "admin@example.com",
            "identityProvider": "aad"
        }

        # Call GetRoles
        response = get_roles(req)

        # Verify response
        assert response.status_code == 200
        body = json.loads(response.get_body())
        assert "roles" in body
        assert "authenticated" in body["roles"]
        assert "PlatformAdmin" in body["roles"]

        # Verify no insert was called (user already exists)
        mock_users_table.insert_entity.assert_not_called()

    def test_existing_org_user(self, mock_users_table):
        """Existing org user gets OrgUser role"""
        # Mock existing org user
        mock_users_table.get_entity.return_value = {
            "PartitionKey": "user@example.com",
            "RowKey": "user",
            "Email": "user@example.com",
            "DisplayName": "User",
            "UserType": "ORG",
            "IsPlatformAdmin": False,
            "IsActive": True
        }

        # Create request from SWA
        req = Mock(spec=func.HttpRequest)
        req.get_json.return_value = {
            "userId": "user-id-789",
            "userDetails": "user@example.com",
            "identityProvider": "aad"
        }

        # Call GetRoles
        response = get_roles(req)

        # Verify response
        assert response.status_code == 200
        body = json.loads(response.get_body())
        assert "roles" in body
        assert "authenticated" in body["roles"]
        assert "OrgUser" in body["roles"]
        assert "PlatformAdmin" not in body["roles"]

    def test_non_first_user_not_found(self, mock_users_table):
        """Non-first user who doesn't exist gets anonymous role"""
        # Mock user doesn't exist
        mock_users_table.get_entity.return_value = None

        # Mock query_entities to return existing users (not first user)
        mock_users_table.query_entities.return_value = iter([
            {"PartitionKey": "existing@example.com", "RowKey": "user"}
        ])

        # Create request from SWA
        req = Mock(spec=func.HttpRequest)
        req.get_json.return_value = {
            "userId": "new-user-id",
            "userDetails": "newuser@example.com",
            "identityProvider": "aad"
        }

        # Call GetRoles
        response = get_roles(req)

        # Verify response
        assert response.status_code == 200
        body = json.loads(response.get_body())
        assert "roles" in body
        assert body["roles"] == ["anonymous"]

        # Verify user was NOT created
        mock_users_table.insert_entity.assert_not_called()

    def test_no_user_id_provided(self, mock_users_table):
        """Request without userId gets anonymous role"""
        # Create request without userId
        req = Mock(spec=func.HttpRequest)
        req.get_json.return_value = {
            "identityProvider": "aad"
        }

        # Call GetRoles
        response = get_roles(req)

        # Verify response
        assert response.status_code == 200
        body = json.loads(response.get_body())
        assert "roles" in body
        assert body["roles"] == ["anonymous"]

    def test_error_handling(self, mock_users_table):
        """Errors result in anonymous role for safety"""
        # Mock get_entity to raise exception
        mock_users_table.get_entity.side_effect = Exception("Database error")

        # Create request
        req = Mock(spec=func.HttpRequest)
        req.get_json.return_value = {
            "userId": "user-id",
            "userDetails": "user@example.com"
        }

        # Call GetRoles
        response = get_roles(req)

        # Verify response (should return anonymous on error)
        assert response.status_code == 200
        body = json.loads(response.get_body())
        assert "roles" in body
        assert body["roles"] == ["anonymous"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
