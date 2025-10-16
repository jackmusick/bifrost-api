"""
Contract tests for Roles API
Tests request/response validation for role management endpoints
"""

import pytest
from pydantic import ValidationError

from shared.models import (
    AssignFormsToRoleRequest,
    AssignUsersToRoleRequest,
    CreateRoleRequest,
    Role,
    UpdateRoleRequest,
    UserType,
)


class TestCreateRoleRequest:
    """Test CreateRoleRequest validation"""

    def test_valid_request(self):
        """Valid role creation request should pass"""
        request = CreateRoleRequest(
            name="Field Technician",
            description="Technicians who perform on-site work"
        )
        assert request.name == "Field Technician"
        assert request.description == "Technicians who perform on-site work"

    def test_valid_request_minimal(self):
        """Valid request with only required fields"""
        request = CreateRoleRequest(name="Admin")
        assert request.name == "Admin"
        assert request.description is None

    def test_invalid_empty_name(self):
        """Empty name should fail validation"""
        with pytest.raises(ValidationError) as exc_info:
            CreateRoleRequest(name="")

        errors = exc_info.value.errors()
        assert any(error["type"] == "string_too_short" for error in errors)

    def test_invalid_name_too_long(self):
        """Name exceeding 100 characters should fail"""
        with pytest.raises(ValidationError):
            CreateRoleRequest(name="A" * 101)

    def test_invalid_missing_name(self):
        """Missing name should fail validation"""
        with pytest.raises(ValidationError) as exc_info:
            CreateRoleRequest()

        errors = exc_info.value.errors()
        assert any(error["loc"] == ("name",) for error in errors)


class TestUpdateRoleRequest:
    """Test UpdateRoleRequest validation"""

    def test_valid_update_name_only(self):
        """Update with only name should pass"""
        request = UpdateRoleRequest(name="Updated Role")
        assert request.name == "Updated Role"
        assert request.description is None

    def test_valid_update_description_only(self):
        """Update with only description should pass"""
        request = UpdateRoleRequest(description="New description")
        assert request.name is None
        assert request.description == "New description"

    def test_valid_update_both_fields(self):
        """Update with both fields should pass"""
        request = UpdateRoleRequest(
            name="New Name",
            description="New Description"
        )
        assert request.name == "New Name"
        assert request.description == "New Description"

    def test_valid_update_empty_request(self):
        """Update with no fields should pass (partial update)"""
        request = UpdateRoleRequest()
        assert request.name is None
        assert request.description is None

    def test_invalid_empty_name(self):
        """Empty name should fail validation"""
        with pytest.raises(ValidationError):
            UpdateRoleRequest(name="")

    def test_invalid_name_too_long(self):
        """Name exceeding 100 characters should fail"""
        with pytest.raises(ValidationError):
            UpdateRoleRequest(name="A" * 101)


class TestAssignUsersToRoleRequest:
    """Test AssignUsersToRoleRequest validation"""

    def test_valid_single_user(self):
        """Assign single user should pass"""
        request = AssignUsersToRoleRequest(userIds=["user-123"])
        assert len(request.userIds) == 1
        assert request.userIds[0] == "user-123"

    def test_valid_multiple_users(self):
        """Assign multiple users should pass"""
        request = AssignUsersToRoleRequest(
            userIds=["user-1", "user-2", "user-3"]
        )
        assert len(request.userIds) == 3

    def test_invalid_empty_list(self):
        """Empty user list should fail validation"""
        with pytest.raises(ValidationError) as exc_info:
            AssignUsersToRoleRequest(userIds=[])

        errors = exc_info.value.errors()
        assert any(error["type"] == "too_short" for error in errors)

    def test_invalid_missing_user_ids(self):
        """Missing userIds should fail validation"""
        with pytest.raises(ValidationError) as exc_info:
            AssignUsersToRoleRequest()

        errors = exc_info.value.errors()
        assert any(error["loc"] == ("userIds",) for error in errors)


class TestAssignFormsToRoleRequest:
    """Test AssignFormsToRoleRequest validation"""

    def test_valid_single_form(self):
        """Assign single form should pass"""
        request = AssignFormsToRoleRequest(formIds=["form-abc-123"])
        assert len(request.formIds) == 1
        assert request.formIds[0] == "form-abc-123"

    def test_valid_multiple_forms(self):
        """Assign multiple forms should pass"""
        request = AssignFormsToRoleRequest(
            formIds=["form-1", "form-2", "form-3", "form-4"]
        )
        assert len(request.formIds) == 4

    def test_invalid_empty_list(self):
        """Empty form list should fail validation"""
        with pytest.raises(ValidationError) as exc_info:
            AssignFormsToRoleRequest(formIds=[])

        errors = exc_info.value.errors()
        assert any(error["type"] == "too_short" for error in errors)

    def test_invalid_missing_form_ids(self):
        """Missing formIds should fail validation"""
        with pytest.raises(ValidationError) as exc_info:
            AssignFormsToRoleRequest()

        errors = exc_info.value.errors()
        assert any(error["loc"] == ("formIds",) for error in errors)


class TestRoleResponse:
    """Test Role response model validation"""

    def test_valid_role_response(self):
        """Valid role response should parse correctly"""
        from datetime import datetime

        role = Role(
            id="role-123",
            name="Manager",
            description="Management role",
            isActive=True,
            createdBy="admin@example.com",
            createdAt=datetime(2025, 1, 1, 12, 0, 0),
            updatedAt=datetime(2025, 1, 2, 14, 30, 0)
        )

        assert role.id == "role-123"
        assert role.name == "Manager"
        assert role.isActive is True

    def test_valid_role_minimal(self):
        """Role with minimal fields should work"""
        from datetime import datetime

        role = Role(
            id="role-456",
            name="Basic Role",
            description=None,
            isActive=True,
            createdBy="user@test.com",
            createdAt=datetime.utcnow(),
            updatedAt=datetime.utcnow()
        )

        assert role.description is None
        assert role.isActive is True


class TestUserTypeValidation:
    """Test UserType enum for role assignment validation"""

    def test_platform_user_type(self):
        """PLATFORM user type should be valid"""
        assert UserType.PLATFORM.value == "PLATFORM"

    def test_org_user_type(self):
        """ORG user type should be valid"""
        assert UserType.ORG.value == "ORG"

    def test_invalid_user_type(self):
        """Invalid user type should fail"""
        with pytest.raises(ValueError):
            UserType("INVALID")


# Integration-style contract tests (mocked API calls)
class TestRolesAPIContract:
    """Test the contract between API requests and responses"""

    def test_create_role_request_response_cycle(self):
        """Create role request should produce valid response"""
        from datetime import datetime

        # Request
        request = CreateRoleRequest(
            name="Support Team",
            description="Customer support specialists"
        )

        # Simulate response
        response = Role(
            id="role-789",
            name=request.name,
            description=request.description,
            isActive=True,
            createdBy="admin@example.com",
            createdAt=datetime.utcnow(),
            updatedAt=datetime.utcnow()
        )

        # Verify contract
        assert response.name == request.name
        assert response.description == request.description
        assert response.isActive is True

    def test_update_role_partial_request(self):
        """Partial update should only modify specified fields"""
        # Original role
        from datetime import datetime

        original = Role(
            id="role-100",
            name="Original Name",
            description="Original Description",
            isActive=True,
            createdBy="user@test.com",
            createdAt=datetime(2025, 1, 1),
            updatedAt=datetime(2025, 1, 1)
        )

        # Update request (name only)
        update_request = UpdateRoleRequest(name="New Name")

        # Simulated updated role
        updated = Role(
            id=original.id,
            name=update_request.name if update_request.name else original.name,
            description=update_request.description if update_request.description is not None else original.description,
            isActive=original.isActive,
            createdBy=original.createdBy,
            createdAt=original.createdAt,
            updatedAt=datetime.utcnow()
        )

        # Verify only name changed
        assert updated.name == "New Name"
        assert updated.description == "Original Description"
        assert updated.id == original.id

    def test_assign_users_validates_list(self):
        """Assign users request should validate user list"""
        # Valid request
        valid_request = AssignUsersToRoleRequest(
            userIds=["user-1", "user-2", "user-3"]
        )
        assert len(valid_request.userIds) == 3

        # Should reject duplicates in business logic (not validated by schema)
        request_with_dupes = AssignUsersToRoleRequest(
            userIds=["user-1", "user-1", "user-2"]
        )
        # Schema allows duplicates, but API should deduplicate
        unique_ids = list(set(request_with_dupes.userIds))
        assert len(unique_ids) == 2
