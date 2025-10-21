"""
Unit tests for permissions_handlers
Tests user permissions and roles business logic
"""

import json
import pytest
from unittest.mock import Mock, patch

from shared.handlers.permissions_handlers import (
    list_users_handler,
    get_user_handler,
    get_user_permissions_handler,
    get_org_permissions_handler,
    grant_permissions_handler,
    revoke_permissions_handler,
    get_user_roles_handler,
    get_user_forms_handler,
)


class TestListUsersHandler:
    """Test list_users_handler"""

    @pytest.mark.asyncio
    async def test_list_users_success(self):
        """Test successful users listing"""
        mock_context = Mock(user_id="admin-123")

        user_entity1 = {
            "RowKey": "user:user1@example.com",
            "Email": "user1@example.com",
            "DisplayName": "User One",
            "UserType": "PLATFORM",
            "IsPlatformAdmin": True,
            "IsActive": True,
            "LastLogin": "2024-10-19T12:00:00",
            "CreatedAt": "2024-01-01T00:00:00"
        }
        user_entity2 = {
            "RowKey": "user:user2@example.com",
            "Email": "user2@example.com",
            "DisplayName": "User Two",
            "UserType": "ORG",
            "IsPlatformAdmin": False,
            "IsActive": True,
            "LastLogin": "2024-10-18T12:00:00",
            "CreatedAt": "2024-02-01T00:00:00"
        }

        with patch('shared.handlers.permissions_handlers.get_table_service') as mock_get_service:
            mock_service = Mock()
            mock_get_service.return_value = mock_service
            mock_service.query_entities.return_value = [user_entity1, user_entity2]

            response = await list_users_handler(mock_context)

            assert response.status_code == 200
            data = json.loads(response.get_body())
            assert len(data) == 2
            # Should be sorted by lastLogin descending
            assert data[0]["email"] == "user1@example.com"

    @pytest.mark.asyncio
    async def test_list_users_with_platform_filter(self):
        """Test listing with platform user type filter"""
        mock_context = Mock(user_id="admin-123")

        user_entity = {
            "RowKey": "user:user1@example.com",
            "Email": "user1@example.com",
            "DisplayName": "User One",
            "UserType": "PLATFORM",
            "IsPlatformAdmin": True,
            "IsActive": True,
            "LastLogin": "2024-10-19T12:00:00",
            "CreatedAt": "2024-01-01T00:00:00"
        }

        with patch('shared.handlers.permissions_handlers.get_table_service') as mock_get_service:
            mock_service = Mock()
            mock_get_service.return_value = mock_service
            mock_service.query_entities.return_value = [user_entity]

            response = await list_users_handler(mock_context, user_type_filter="platform")

            assert response.status_code == 200
            data = json.loads(response.get_body())
            assert len(data) == 1
            assert data[0]["userType"] == "PLATFORM"

    @pytest.mark.asyncio
    async def test_list_users_with_org_filter(self):
        """Test listing with org user type filter"""
        mock_context = Mock(user_id="admin-123")

        user_entity = {
            "RowKey": "user:user2@example.com",
            "Email": "user2@example.com",
            "DisplayName": "User Two",
            "UserType": "ORG",
            "IsPlatformAdmin": False,
            "IsActive": True,
            "LastLogin": None,
            "CreatedAt": "2024-02-01T00:00:00"
        }

        with patch('shared.handlers.permissions_handlers.get_table_service') as mock_get_service:
            mock_service = Mock()
            mock_get_service.return_value = mock_service
            mock_service.query_entities.return_value = [user_entity]

            response = await list_users_handler(mock_context, user_type_filter="org")

            assert response.status_code == 200
            data = json.loads(response.get_body())
            assert len(data) == 1
            assert data[0]["userType"] == "ORG"

    @pytest.mark.asyncio
    async def test_list_users_empty(self):
        """Test listing when no users exist"""
        mock_context = Mock(user_id="admin-123")

        with patch('shared.handlers.permissions_handlers.get_table_service') as mock_get_service:
            mock_service = Mock()
            mock_get_service.return_value = mock_service
            mock_service.query_entities.return_value = []

            response = await list_users_handler(mock_context)

            assert response.status_code == 200
            data = json.loads(response.get_body())
            assert data == []

    @pytest.mark.asyncio
    async def test_list_users_error(self):
        """Test error handling"""
        mock_context = Mock(user_id="admin-123")

        with patch('shared.handlers.permissions_handlers.get_table_service') as mock_get_service:
            mock_service = Mock()
            mock_get_service.return_value = mock_service
            mock_service.query_entities.side_effect = Exception("Database error")

            response = await list_users_handler(mock_context)

            assert response.status_code == 500
            data = json.loads(response.get_body())
            assert data["error"] == "InternalServerError"

    @pytest.mark.asyncio
    async def test_list_users_sorts_by_last_login(self):
        """Test that users are sorted by lastLogin descending"""
        mock_context = Mock(user_id="admin-123")

        user_entity1 = {
            "RowKey": "user:old@example.com",
            "Email": "old@example.com",
            "DisplayName": "Old",
            "UserType": "PLATFORM",
            "IsPlatformAdmin": False,
            "IsActive": True,
            "LastLogin": "2024-01-01T00:00:00",
            "CreatedAt": "2024-01-01T00:00:00"
        }
        user_entity2 = {
            "RowKey": "user:recent@example.com",
            "Email": "recent@example.com",
            "DisplayName": "Recent",
            "UserType": "PLATFORM",
            "IsPlatformAdmin": False,
            "IsActive": True,
            "LastLogin": "2024-10-19T12:00:00",
            "CreatedAt": "2024-02-01T00:00:00"
        }
        user_entity3 = {
            "RowKey": "user:never@example.com",
            "Email": "never@example.com",
            "DisplayName": "Never",
            "UserType": "PLATFORM",
            "IsPlatformAdmin": False,
            "IsActive": True,
            "LastLogin": None,
            "CreatedAt": "2024-03-01T00:00:00"
        }

        with patch('shared.handlers.permissions_handlers.get_table_service') as mock_get_service:
            mock_service = Mock()
            mock_get_service.return_value = mock_service
            # Return in random order to test sorting
            mock_service.query_entities.return_value = [user_entity1, user_entity3, user_entity2]

            response = await list_users_handler(mock_context)

            data = json.loads(response.get_body())
            assert len(data) == 3
            # Most recent first
            assert data[0]["email"] == "recent@example.com"
            # Oldest second
            assert data[1]["email"] == "old@example.com"
            # Never logged in last
            assert data[2]["email"] == "never@example.com"


class TestGetUserHandler:
    """Test get_user_handler"""

    @pytest.mark.asyncio
    async def test_get_user_success(self):
        """Test successful user retrieval"""
        mock_context = Mock(user_id="admin-123")
        user_id = "user@example.com"

        user_entity = {
            "RowKey": "user:user@example.com",
            "Email": "user@example.com",
            "DisplayName": "Test User",
            "UserType": "PLATFORM",
            "IsPlatformAdmin": True,
            "IsActive": True,
            "LastLogin": "2024-10-19T12:00:00",
            "CreatedAt": "2024-01-01T00:00:00"
        }

        with patch('shared.handlers.permissions_handlers.get_table_service') as mock_get_service:
            mock_service = Mock()
            mock_get_service.return_value = mock_service
            mock_service.get_entity.return_value = user_entity

            response = await get_user_handler(mock_context, user_id)

            assert response.status_code == 200
            data = json.loads(response.get_body())
            assert data["email"] == "user@example.com"
            assert data["displayName"] == "Test User"
            assert data["isPlatformAdmin"] is True

    @pytest.mark.asyncio
    async def test_get_user_not_found(self):
        """Test retrieving non-existent user"""
        mock_context = Mock(user_id="admin-123")
        user_id = "nonexistent@example.com"

        with patch('shared.handlers.permissions_handlers.get_table_service') as mock_get_service:
            mock_service = Mock()
            mock_get_service.return_value = mock_service
            mock_service.get_entity.side_effect = Exception("Not found")

            response = await get_user_handler(mock_context, user_id)

            assert response.status_code == 404
            data = json.loads(response.get_body())
            assert data["error"] == "NotFound"



class TestGetUserPermissionsHandler:
    """Test get_user_permissions_handler"""

    @pytest.mark.asyncio
    async def test_get_user_permissions_returns_empty(self):
        """Test that deprecated endpoint returns empty list"""
        mock_context = Mock(user_id="admin-123")
        user_id = "user@example.com"

        response = await get_user_permissions_handler(mock_context, user_id)

        assert response.status_code == 200
        data = json.loads(response.get_body())
        assert data == []


class TestGetOrgPermissionsHandler:
    """Test get_org_permissions_handler"""

    @pytest.mark.asyncio
    async def test_get_org_permissions_returns_empty(self):
        """Test that deprecated endpoint returns empty list"""
        mock_context = Mock(user_id="admin-123")
        org_id = "org-123"

        response = await get_org_permissions_handler(mock_context, org_id)

        assert response.status_code == 200
        data = json.loads(response.get_body())
        assert data == []


class TestGrantPermissionsHandler:
    """Test grant_permissions_handler"""

    @pytest.mark.asyncio
    async def test_grant_permissions_returns_not_implemented(self):
        """Test that deprecated endpoint returns 501"""
        mock_context = Mock(user_id="admin-123")

        response = await grant_permissions_handler(mock_context)

        assert response.status_code == 501
        data = json.loads(response.get_body())
        assert data["error"] == "NotImplemented"
        assert "deprecated" in data["message"].lower()


class TestRevokePermissionsHandler:
    """Test revoke_permissions_handler"""

    @pytest.mark.asyncio
    async def test_revoke_permissions_returns_not_implemented(self):
        """Test that deprecated endpoint returns 501"""
        mock_context = Mock(user_id="admin-123")

        response = await revoke_permissions_handler(
            mock_context,
            user_id="user@example.com",
            org_id="org-123"
        )

        assert response.status_code == 501
        data = json.loads(response.get_body())
        assert data["error"] == "NotImplemented"
        assert "deprecated" in data["message"].lower()


class TestGetUserRolesHandler:
    """Test get_user_roles_handler"""

    @pytest.mark.asyncio
    async def test_get_user_roles_success(self):
        """Test successful roles retrieval"""
        mock_context = Mock(user_id="admin-123")
        user_id = "user@example.com"

        role_entity1 = {
            "RowKey": "userrole:user@example.com:role-1"
        }
        role_entity2 = {
            "RowKey": "userrole:user@example.com:role-2"
        }

        with patch('shared.handlers.permissions_handlers.get_table_service') as mock_get_service:
            mock_service = Mock()
            mock_get_service.return_value = mock_service
            mock_service.query_entities.return_value = [role_entity1, role_entity2]

            response = await get_user_roles_handler(mock_context, user_id)

            assert response.status_code == 200
            data = json.loads(response.get_body())
            assert "roleIds" in data
            assert len(data["roleIds"]) == 2
            assert "role-1" in data["roleIds"]
            assert "role-2" in data["roleIds"]

    @pytest.mark.asyncio
    async def test_get_user_roles_no_roles(self):
        """Test user with no roles"""
        mock_context = Mock(user_id="admin-123")
        user_id = "user@example.com"

        with patch('shared.handlers.permissions_handlers.get_table_service') as mock_get_service:
            mock_service = Mock()
            mock_get_service.return_value = mock_service
            mock_service.query_entities.return_value = []

            response = await get_user_roles_handler(mock_context, user_id)

            assert response.status_code == 200
            data = json.loads(response.get_body())
            assert data["roleIds"] == []

    @pytest.mark.asyncio
    async def test_get_user_roles_error(self):
        """Test error handling"""
        mock_context = Mock(user_id="admin-123")
        user_id = "user@example.com"

        with patch('shared.handlers.permissions_handlers.get_table_service') as mock_get_service:
            mock_service = Mock()
            mock_get_service.return_value = mock_service
            mock_service.query_entities.side_effect = Exception("Database error")

            response = await get_user_roles_handler(mock_context, user_id)

            assert response.status_code == 500
            data = json.loads(response.get_body())
            assert data["error"] == "InternalServerError"


class TestGetUserFormsHandler:
    """Test get_user_forms_handler"""

    @pytest.mark.asyncio
    async def test_get_user_forms_platform_admin(self):
        """Test platform admin has access to all forms"""
        mock_context = Mock(user_id="admin-123")
        user_id = "admin@example.com"

        user_entity = {
            "RowKey": "user:admin@example.com",
            "Email": "admin@example.com",
            "DisplayName": "Admin",
            "UserType": "PLATFORM",
            "IsPlatformAdmin": True,
            "IsActive": True,
            "LastLogin": "2024-10-19T12:00:00",
            "CreatedAt": "2024-01-01T00:00:00"
        }

        with patch('shared.handlers.permissions_handlers.get_table_service') as mock_get_service:
            mock_service = Mock()
            mock_get_service.return_value = mock_service
            mock_service.get_entity.return_value = user_entity

            response = await get_user_forms_handler(mock_context, user_id)

            assert response.status_code == 200
            data = json.loads(response.get_body())
            assert data["userType"] == "PLATFORM"
            assert data["hasAccessToAllForms"] is True
            assert data["formIds"] == []

    @pytest.mark.asyncio
    async def test_get_user_forms_user_not_found(self):
        """Test retrieving forms for non-existent user"""
        mock_context = Mock(user_id="admin-123")
        user_id = "nonexistent@example.com"

        with patch('shared.handlers.permissions_handlers.get_table_service') as mock_get_service:
            mock_service = Mock()
            mock_get_service.return_value = mock_service
            mock_service.get_entity.side_effect = Exception("Not found")

            response = await get_user_forms_handler(mock_context, user_id)

            assert response.status_code == 404
            data = json.loads(response.get_body())
            assert data["error"] == "NotFound"

    @pytest.mark.asyncio
    async def test_get_user_forms_user_with_roles(self):
        """Test regular user with role assignments"""
        mock_context = Mock(user_id="admin-123")
        user_id = "user@example.com"

        user_entity = {
            "RowKey": "user:user@example.com",
            "Email": "user@example.com",
            "DisplayName": "User",
            "UserType": "ORG",
            "IsPlatformAdmin": False,
            "IsActive": True,
            "LastLogin": "2024-10-19T12:00:00",
            "CreatedAt": "2024-01-01T00:00:00"
        }

        role_entity = {
            "RowKey": "userrole:user@example.com:role-1"
        }

        form_entity1 = {
            "RowKey": "roleform:role-1:form-1"
        }
        form_entity2 = {
            "RowKey": "roleform:role-1:form-2"
        }

        with patch('shared.handlers.permissions_handlers.get_table_service') as mock_get_service:
            mock_service = Mock()
            mock_get_service.return_value = mock_service
            # First call: get user entity
            # Second call: get user roles
            # Third call: get forms for role-1
            mock_service.get_entity.return_value = user_entity
            mock_service.query_entities.side_effect = [
                [role_entity],  # user roles query
                [form_entity1, form_entity2]  # forms for role-1
            ]

            response = await get_user_forms_handler(mock_context, user_id)

            assert response.status_code == 200
            data = json.loads(response.get_body())
            assert data["userType"] == "ORG"
            assert data["hasAccessToAllForms"] is False
            assert len(data["formIds"]) == 2
            assert "form-1" in data["formIds"]
            assert "form-2" in data["formIds"]

    @pytest.mark.asyncio
    async def test_get_user_forms_no_roles(self):
        """Test regular user with no role assignments"""
        mock_context = Mock(user_id="admin-123")
        user_id = "user@example.com"

        user_entity = {
            "RowKey": "user:user@example.com",
            "Email": "user@example.com",
            "DisplayName": "User",
            "UserType": "ORG",
            "IsPlatformAdmin": False,
            "IsActive": True,
            "LastLogin": None,
            "CreatedAt": "2024-01-01T00:00:00"
        }

        with patch('shared.handlers.permissions_handlers.get_table_service') as mock_get_service:
            mock_service = Mock()
            mock_get_service.return_value = mock_service
            mock_service.get_entity.return_value = user_entity
            mock_service.query_entities.return_value = []

            response = await get_user_forms_handler(mock_context, user_id)

            assert response.status_code == 200
            data = json.loads(response.get_body())
            assert data["userType"] == "ORG"
            assert data["hasAccessToAllForms"] is False
            assert data["formIds"] == []

    @pytest.mark.asyncio
    async def test_get_user_forms_multiple_roles(self):
        """Test user with multiple roles and forms"""
        mock_context = Mock(user_id="admin-123")
        user_id = "user@example.com"

        user_entity = {
            "RowKey": "user:user@example.com",
            "Email": "user@example.com",
            "DisplayName": "User",
            "UserType": "ORG",
            "IsPlatformAdmin": False,
            "IsActive": True,
            "LastLogin": None,
            "CreatedAt": "2024-01-01T00:00:00"
        }

        role_entity1 = {
            "RowKey": "userrole:user@example.com:role-1"
        }
        role_entity2 = {
            "RowKey": "userrole:user@example.com:role-2"
        }

        form_entity1 = {
            "RowKey": "roleform:role-1:form-1"
        }
        form_entity2 = {
            "RowKey": "roleform:role-1:form-2"
        }
        form_entity3 = {
            "RowKey": "roleform:role-2:form-2"  # Duplicate form in another role
        }
        form_entity4 = {
            "RowKey": "roleform:role-2:form-3"
        }

        with patch('shared.handlers.permissions_handlers.get_table_service') as mock_get_service:
            mock_service = Mock()
            mock_get_service.return_value = mock_service
            mock_service.get_entity.return_value = user_entity
            # Mock query_entities for: user roles, forms for role-1, forms for role-2
            mock_service.query_entities.side_effect = [
                [role_entity1, role_entity2],  # user roles
                [form_entity1, form_entity2],  # forms for role-1
                [form_entity3, form_entity4]   # forms for role-2
            ]

            response = await get_user_forms_handler(mock_context, user_id)

            assert response.status_code == 200
            data = json.loads(response.get_body())
            assert data["userType"] == "ORG"
            assert data["hasAccessToAllForms"] is False
            # Should have 3 unique forms (form-2 appears in both roles)
            assert len(data["formIds"]) == 3
            assert "form-1" in data["formIds"]
            assert "form-2" in data["formIds"]
            assert "form-3" in data["formIds"]

