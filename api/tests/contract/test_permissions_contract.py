"""
Contract tests for Permissions API models
Tests Pydantic validation rules for request/response models
"""

import pytest
from datetime import datetime
from pydantic import ValidationError

from shared.models import (
    User,
    UserPermission,
    PermissionsData,
    GrantPermissionsRequest,
    ErrorResponse
)


class TestGrantPermissionsRequest:
    """Test validation for GrantPermissionsRequest model"""

    def test_valid_grant_permissions_request(self):
        """Test valid grant permissions request"""
        request = GrantPermissionsRequest(
            userId="user-123",
            orgId="org-456",
            permissions=PermissionsData(
                canExecuteWorkflows=True,
                canManageConfig=True,
                canManageForms=True,
                canViewHistory=True
            )
        )
        assert request.userId == "user-123"
        assert request.orgId == "org-456"
        assert request.permissions.canExecuteWorkflows is True
        assert request.permissions.canManageConfig is True
        assert request.permissions.canManageForms is True
        assert request.permissions.canViewHistory is True

    def test_grant_permissions_with_mixed_flags(self):
        """Test granting some permissions but not others"""
        request = GrantPermissionsRequest(
            userId="user-123",
            orgId="org-456",
            permissions=PermissionsData(
                canExecuteWorkflows=True,
                canManageConfig=False,
                canManageForms=True,
                canViewHistory=False
            )
        )
        assert request.permissions.canExecuteWorkflows is True
        assert request.permissions.canManageConfig is False
        assert request.permissions.canManageForms is True
        assert request.permissions.canViewHistory is False

    def test_grant_permissions_with_all_false(self):
        """Test granting no permissions (all false)"""
        request = GrantPermissionsRequest(
            userId="user-123",
            orgId="org-456",
            permissions=PermissionsData(
                canExecuteWorkflows=False,
                canManageConfig=False,
                canManageForms=False,
                canViewHistory=False
            )
        )
        assert request.permissions.canExecuteWorkflows is False
        assert request.permissions.canManageConfig is False
        assert request.permissions.canManageForms is False
        assert request.permissions.canViewHistory is False

    def test_missing_required_user_id(self):
        """Test that userId is required"""
        with pytest.raises(ValidationError) as exc_info:
            GrantPermissionsRequest(
                orgId="org-456",
                permissions=PermissionsData(
                    canExecuteWorkflows=True,
                    canManageConfig=True,
                    canManageForms=True,
                    canViewHistory=True
                )
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("userId",) and e["type"] == "missing" for e in errors)

    def test_missing_required_org_id(self):
        """Test that orgId is required"""
        with pytest.raises(ValidationError) as exc_info:
            GrantPermissionsRequest(
                userId="user-123",
                permissions=PermissionsData(
                    canExecuteWorkflows=True,
                    canManageConfig=True,
                    canManageForms=True,
                    canViewHistory=True
                )
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("orgId",) and e["type"] == "missing" for e in errors)

    def test_missing_required_permissions(self):
        """Test that permissions object is required"""
        with pytest.raises(ValidationError) as exc_info:
            GrantPermissionsRequest(
                userId="user-123",
                orgId="org-456"
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("permissions",) and e["type"] == "missing" for e in errors)


class TestPermissionsData:
    """Test validation for PermissionsData model"""

    def test_valid_permissions_data(self):
        """Test valid permissions data"""
        permissions = PermissionsData(
            canExecuteWorkflows=True,
            canManageConfig=False,
            canManageForms=True,
            canViewHistory=False
        )
        assert permissions.canExecuteWorkflows is True
        assert permissions.canManageConfig is False
        assert permissions.canManageForms is True
        assert permissions.canViewHistory is False

    def test_missing_can_execute_workflows(self):
        """Test that canExecuteWorkflows is required"""
        with pytest.raises(ValidationError) as exc_info:
            PermissionsData(
                canManageConfig=True,
                canManageForms=True,
                canViewHistory=True
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("canExecuteWorkflows",) and e["type"] == "missing" for e in errors)

    def test_missing_can_manage_config(self):
        """Test that canManageConfig is required"""
        with pytest.raises(ValidationError) as exc_info:
            PermissionsData(
                canExecuteWorkflows=True,
                canManageForms=True,
                canViewHistory=True
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("canManageConfig",) and e["type"] == "missing" for e in errors)

    def test_missing_can_manage_forms(self):
        """Test that canManageForms is required"""
        with pytest.raises(ValidationError) as exc_info:
            PermissionsData(
                canExecuteWorkflows=True,
                canManageConfig=True,
                canViewHistory=True
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("canManageForms",) and e["type"] == "missing" for e in errors)

    def test_missing_can_view_history(self):
        """Test that canViewHistory is required"""
        with pytest.raises(ValidationError) as exc_info:
            PermissionsData(
                canExecuteWorkflows=True,
                canManageConfig=True,
                canManageForms=True
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("canViewHistory",) and e["type"] == "missing" for e in errors)


class TestUserPermissionResponse:
    """Test UserPermission response model structure"""

    def test_valid_user_permission_response(self):
        """Test valid user permission response"""
        permission = UserPermission(
            userId="user-123",
            orgId="org-456",
            canExecuteWorkflows=True,
            canManageConfig=False,
            canManageForms=True,
            canViewHistory=False,
            grantedBy="admin-user",
            grantedAt=datetime.utcnow()
        )
        assert permission.userId == "user-123"
        assert permission.orgId == "org-456"
        assert permission.canExecuteWorkflows is True
        assert permission.canManageConfig is False
        assert permission.grantedBy == "admin-user"
        assert isinstance(permission.grantedAt, datetime)

    def test_user_permission_defaults_to_false(self):
        """Test that permission flags default to False"""
        permission = UserPermission(
            userId="user-123",
            orgId="org-456",
            grantedBy="admin-user",
            grantedAt=datetime.utcnow()
        )
        assert permission.canExecuteWorkflows is False
        assert permission.canManageConfig is False
        assert permission.canManageForms is False
        assert permission.canViewHistory is False

    def test_user_permission_missing_required_fields(self):
        """Test that all required fields must be present"""
        with pytest.raises(ValidationError) as exc_info:
            UserPermission(
                userId="user-123",
                orgId="org-456"
                # Missing: grantedBy, grantedAt
            )

        errors = exc_info.value.errors()
        required_fields = {"grantedBy", "grantedAt"}
        missing_fields = {e["loc"][0] for e in errors if e["type"] == "missing"}
        assert required_fields.issubset(missing_fields)

    def test_user_permission_serialization(self):
        """Test that user permission can be serialized to dict/JSON"""
        permission = UserPermission(
            userId="user-123",
            orgId="org-456",
            canExecuteWorkflows=True,
            canManageConfig=True,
            canManageForms=True,
            canViewHistory=True,
            grantedBy="admin-user",
            grantedAt=datetime.utcnow()
        )

        perm_dict = permission.model_dump()
        assert "userId" in perm_dict
        assert "orgId" in perm_dict
        assert "canExecuteWorkflows" in perm_dict
        assert "canManageConfig" in perm_dict
        assert "canManageForms" in perm_dict
        assert "canViewHistory" in perm_dict
        assert "grantedBy" in perm_dict
        assert "grantedAt" in perm_dict

    def test_user_permission_json_serialization(self):
        """Test that user permission can be serialized to JSON mode"""
        permission = UserPermission(
            userId="user-123",
            orgId="org-456",
            canExecuteWorkflows=True,
            canManageConfig=False,
            canManageForms=True,
            canViewHistory=False,
            grantedBy="admin-user",
            grantedAt=datetime.utcnow()
        )

        perm_dict = permission.model_dump(mode="json")
        assert isinstance(perm_dict["grantedAt"], str)  # datetime -> ISO string


class TestUserResponse:
    """Test User response model structure"""

    def test_valid_user_response(self):
        """Test valid user response"""
        user = User(
            id="user-123",
            email="user@example.com",
            displayName="Test User",
            isActive=True,
            lastLogin=datetime.utcnow(),
            createdAt=datetime.utcnow()
        )
        assert user.id == "user-123"
        assert user.email == "user@example.com"
        assert user.displayName == "Test User"
        assert user.isActive is True
        assert isinstance(user.lastLogin, datetime)
        assert isinstance(user.createdAt, datetime)

    def test_user_without_last_login(self):
        """Test user without lastLogin (new user)"""
        user = User(
            id="user-123",
            email="user@example.com",
            displayName="Test User",
            isActive=True,
            lastLogin=None,
            createdAt=datetime.utcnow()
        )
        assert user.lastLogin is None

    def test_user_is_active_defaults_to_true(self):
        """Test that isActive defaults to True"""
        user = User(
            id="user-123",
            email="user@example.com",
            displayName="Test User",
            createdAt=datetime.utcnow()
        )
        assert user.isActive is True

    def test_user_missing_required_fields(self):
        """Test that all required fields must be present"""
        with pytest.raises(ValidationError) as exc_info:
            User(
                id="user-123",
                email="user@example.com"
                # Missing: displayName, createdAt
            )

        errors = exc_info.value.errors()
        required_fields = {"displayName", "createdAt"}
        missing_fields = {e["loc"][0] for e in errors if e["type"] == "missing"}
        assert required_fields.issubset(missing_fields)

    def test_user_serialization(self):
        """Test that user can be serialized to dict/JSON"""
        user = User(
            id="user-123",
            email="user@example.com",
            displayName="Test User",
            isActive=True,
            lastLogin=datetime.utcnow(),
            createdAt=datetime.utcnow()
        )

        user_dict = user.model_dump()
        assert "id" in user_dict
        assert "email" in user_dict
        assert "displayName" in user_dict
        assert "isActive" in user_dict
        assert "lastLogin" in user_dict
        assert "createdAt" in user_dict
