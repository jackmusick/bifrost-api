"""
Unit tests for RoleRepository

Tests role management with mocked TableStorageService.
"""

import pytest
from datetime import datetime
from unittest.mock import MagicMock
from azure.core.exceptions import ResourceNotFoundError

from shared.repositories.roles import RoleRepository
from shared.models import CreateRoleRequest, UpdateRoleRequest


class TestRoleRepositoryCreate:
    """Test role creation operations"""

    def test_create_role_success(self, mock_table_service, mock_context):
        """Test successful role creation"""
        repo = RoleRepository(mock_context)

        role_request = CreateRoleRequest(
            name="Manager",
            description="Can manage workflows"
        )

        mock_table_service.insert_entity.return_value = None

        result = repo.create_role(role_request, "org-123", "creator-user")

        assert result.name == "Manager"
        assert result.description == "Can manage workflows"
        assert result.id is not None
        assert result.isActive is True
        mock_table_service.insert_entity.assert_called_once()

    def test_create_role_sets_defaults(self, mock_table_service, mock_context):
        """Test that role defaults are set correctly"""
        repo = RoleRepository(mock_context)

        role_request = CreateRoleRequest(name="Viewer", description=None)
        mock_table_service.insert_entity.return_value = None

        result = repo.create_role(role_request, "org-123", "creator")

        assert result.isActive is True
        assert result.createdBy == "creator"
        assert result.createdAt is not None


class TestRoleRepositoryRead:
    """Test role retrieval operations"""

    def test_get_role_success(self, mock_table_service, mock_context):
        """Test retrieving an existing role"""
        repo = RoleRepository(mock_context)

        mock_table_service.get_entity.return_value = {
            "PartitionKey": "org-123",
            "RowKey": "role:role-uuid",
            "Name": "Manager",
            "Description": "Can manage",
            "IsActive": True,
            "CreatedBy": "admin",
            "CreatedAt": "2024-01-15T10:30:00",
            "UpdatedAt": "2024-01-15T10:30:00"
        }

        result = repo.get_role("role-uuid", "org-123")

        assert result is not None
        assert result.name == "Manager"
        assert result.id == "role-uuid"

    def test_get_role_not_found(self, mock_table_service, mock_context):
        """Test retrieving non-existent role"""
        repo = RoleRepository(mock_context)

        mock_table_service.get_entity.return_value = None

        result = repo.get_role("nonexistent", "org-123")

        assert result is None

    def test_list_roles_empty(self, mock_table_service, mock_context):
        """Test listing roles when none exist"""
        repo = RoleRepository(mock_context)

        mock_table_service.query_entities.return_value = iter([])

        result = repo.list_roles("org-123")

        assert result == []

    def test_list_roles_returns_multiple(self, mock_table_service, mock_context):
        """Test listing multiple roles"""
        repo = RoleRepository(mock_context)

        roles_data = [
            {
                "PartitionKey": "org-123",
                "RowKey": "role:role-1",
                "Name": "Admin",
                "IsActive": True,
                "CreatedBy": "system",
                "CreatedAt": "2024-01-15T10:30:00",
                "UpdatedAt": "2024-01-15T10:30:00"
            },
            {
                "PartitionKey": "org-123",
                "RowKey": "role:role-2",
                "Name": "Editor",
                "IsActive": True,
                "CreatedBy": "system",
                "CreatedAt": "2024-01-15T10:30:00",
                "UpdatedAt": "2024-01-15T10:30:00"
            }
        ]

        mock_table_service.query_entities.return_value = iter(roles_data)

        result = repo.list_roles("org-123")

        assert len(result) == 2
        assert result[0].name == "Admin"
        assert result[1].name == "Editor"

    def test_list_roles_excludes_inactive(self, mock_table_service, mock_context):
        """Test that inactive roles are excluded"""
        repo = RoleRepository(mock_context)

        mock_table_service.query_entities.return_value = iter([])

        repo.list_roles("org-123", active_only=True)

        call_args = mock_table_service.query_entities.call_args
        # query_entities is called with keyword arguments: filter=...
        filter_query = call_args[1].get("filter", call_args[0][0] if call_args[0] else "")
        assert "IsActive eq true" in filter_query


class TestRoleRepositoryUpdate:
    """Test role update operations"""

    def test_update_role_success(self, mock_table_service, mock_context):
        """Test successful role update"""
        repo = RoleRepository(mock_context)

        existing_role = {
            "PartitionKey": "org-123",
            "RowKey": "role:role-123",
            "Name": "Original Name",
            "Description": "Original",
            "IsActive": True,
            "CreatedBy": "creator",
            "CreatedAt": "2024-01-15T10:30:00",
            "UpdatedAt": "2024-01-15T10:30:00"
        }

        mock_table_service.get_entity.return_value = existing_role
        mock_table_service.update_entity.return_value = None

        updates = UpdateRoleRequest(name="Updated Name", description="Updated")

        result = repo.update_role("role-123", "org-123", updates)

        assert result.name == "Updated Name"
        assert result.description == "Updated"

    def test_update_role_not_found(self, mock_table_service, mock_context):
        """Test update raises error when role not found"""
        repo = RoleRepository(mock_context)

        mock_table_service.get_entity.return_value = None

        updates = UpdateRoleRequest(name="Updated")

        with pytest.raises(ValueError, match="not found"):
            repo.update_role("nonexistent", "org-123", updates)

    def test_update_role_partial_fields(self, mock_table_service, mock_context):
        """Test partial field updates"""
        repo = RoleRepository(mock_context)

        existing_role = {
            "PartitionKey": "org-123",
            "RowKey": "role:role-123",
            "Name": "Original Name",
            "Description": "Original Description",
            "IsActive": True,
            "CreatedBy": "creator",
            "CreatedAt": "2024-01-15T10:30:00",
            "UpdatedAt": "2024-01-15T10:30:00"
        }

        mock_table_service.get_entity.return_value = existing_role
        mock_table_service.update_entity.return_value = None

        updates = UpdateRoleRequest(name="New Name", description=None)

        result = repo.update_role("role-123", "org-123", updates)

        assert result.name == "New Name"
        assert result.description == "Original Description"


class TestRoleRepositoryAssignments:
    """Test role assignment operations"""

    def test_assign_users_to_role(self, mock_table_service, mock_context):
        """Test assigning users to a role"""
        repo = RoleRepository(mock_context)

        mock_table_service.insert_entity.return_value = None

        repo.assign_users_to_role("role-123", ["user1@example.com", "user2@example.com"], "admin")

        # Should create 2 relationships
        assert mock_table_service.insert_entity.call_count == 2

    def test_assign_forms_to_role(self, mock_table_service, mock_context):
        """Test assigning forms to a role"""
        repo = RoleRepository(mock_context)

        mock_table_service.insert_entity.return_value = None

        repo.assign_forms_to_role("role-123", ["form-1", "form-2"], "admin")

        # Should create 2 relationships
        assert mock_table_service.insert_entity.call_count == 2

    def test_get_user_role_ids(self, mock_table_service, mock_context):
        """Test retrieving role IDs for a user"""
        repo = RoleRepository(mock_context)

        mock_table_service.query_entities.return_value = iter([
            {"RowKey": "userrole:user@example.com:role-1"},
            {"RowKey": "userrole:user@example.com:role-2"}
        ])

        result = repo.get_user_role_ids("user@example.com")

        assert len(result) == 2
        assert "role-1" in result
        assert "role-2" in result

    def test_get_form_role_ids(self, mock_table_service, mock_context):
        """Test retrieving role IDs for a form"""
        repo = RoleRepository(mock_context)

        mock_table_service.query_entities.return_value = iter([
            {"RowKey": "formrole:form-1:role-1"},
            {"RowKey": "formrole:form-1:role-2"}
        ])

        result = repo.get_form_role_ids("form-1")

        assert len(result) == 2
        assert "role-1" in result
        assert "role-2" in result

    def test_get_role_user_ids(self, mock_table_service, mock_context):
        """Test retrieving user IDs for a role (reverse lookup)"""
        repo = RoleRepository(mock_context)

        mock_table_service.query_entities.return_value = iter([
            {"UserId": "user1@example.com"},
            {"UserId": "user2@example.com"}
        ])

        result = repo.get_role_user_ids("role-123")

        assert len(result) == 2
        assert "user1@example.com" in result
        assert "user2@example.com" in result

    def test_get_role_form_ids(self, mock_table_service, mock_context):
        """Test retrieving form IDs for a role"""
        repo = RoleRepository(mock_context)

        mock_table_service.query_entities.return_value = iter([
            {"FormId": "form-1"},
            {"FormId": "form-2"}
        ])

        result = repo.get_role_form_ids("role-123")

        assert len(result) == 2
        assert "form-1" in result
        assert "form-2" in result


class TestRoleRepositoryDelete:
    """Test role deletion operations"""

    def test_delete_role_success(self, mock_table_service, mock_context):
        """Test soft delete of role"""
        repo = RoleRepository(mock_context)

        existing_role = {
            "PartitionKey": "org-123",
            "RowKey": "role:role-123",
            "Name": "To Delete",
            "IsActive": True,
            "CreatedBy": "admin",
            "CreatedAt": "2024-01-15T10:30:00",
            "UpdatedAt": "2024-01-15T10:30:00"
        }

        mock_table_service.get_entity.return_value = existing_role
        mock_table_service.update_entity.return_value = None

        result = repo.delete_role("role-123", "org-123")

        assert result is True
        mock_table_service.update_entity.assert_called_once()

    def test_delete_role_not_found(self, mock_table_service, mock_context):
        """Test delete returns False when role not found"""
        repo = RoleRepository(mock_context)

        mock_table_service.get_entity.return_value = None

        result = repo.delete_role("nonexistent", "org-123")

        assert result is False

    def test_remove_user_from_role(self, mock_table_service, mock_context):
        """Test removing user from role"""
        repo = RoleRepository(mock_context)

        mock_table_service.delete_entity.return_value = True

        result = repo.remove_user_from_role("role-123", "user@example.com")

        assert result is True
        # Should attempt to delete both forward and reverse indexes
        assert mock_table_service.delete_entity.call_count >= 1

    def test_remove_form_from_role(self, mock_table_service, mock_context):
        """Test removing form from role"""
        repo = RoleRepository(mock_context)

        mock_table_service.delete_entity.return_value = True

        result = repo.remove_form_from_role("role-123", "form-1")

        assert result is True
        assert mock_table_service.delete_entity.call_count >= 1
