"""
Unit tests for roles_handlers
Tests role CRUD operations and user/form assignments
"""

import json
import pytest
from unittest.mock import Mock, AsyncMock, patch
import azure.functions as func
from pydantic import ValidationError

from shared.handlers.roles_handlers import (
    assign_forms_to_role_handler,
    assign_users_to_role_handler,
    create_role_handler,
    delete_role_handler,
    get_role_forms_handler,
    get_role_users_handler,
    list_roles_handler,
    remove_form_from_role_handler,
    remove_user_from_role_handler,
    update_role_handler,
)


class TestListRolesHandler:
    """Test list_roles_handler"""

    @pytest.mark.asyncio
    async def test_list_roles_success(self):
        """Test successful roles listing"""
        mock_req = Mock(spec=func.HttpRequest)
        mock_req.context = Mock(user_id="admin-123", org_id="GLOBAL")

        role1 = Mock(
            createdAt="2024-01-01T00:00:00Z",
            model_dump=Mock(return_value={"id": "role-1", "name": "Admin"})
        )
        role2 = Mock(
            createdAt="2024-01-02T00:00:00Z",
            model_dump=Mock(return_value={"id": "role-2", "name": "User"})
        )

        with patch('shared.handlers.roles_handlers.RoleRepository') as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.list_roles.return_value = [role1, role2]

            response = await list_roles_handler(mock_req)

            assert response.status_code == 200
            data = json.loads(response.get_body())
            assert len(data) == 2
            mock_repo.list_roles.assert_called_once_with(org_id="GLOBAL", active_only=True)

    @pytest.mark.asyncio
    async def test_list_roles_empty(self):
        """Test listing when no roles exist"""
        mock_req = Mock(spec=func.HttpRequest)
        mock_req.context = Mock(user_id="admin-123", org_id="GLOBAL")

        with patch('shared.handlers.roles_handlers.RoleRepository') as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.list_roles.return_value = []

            response = await list_roles_handler(mock_req)

            assert response.status_code == 200
            data = json.loads(response.get_body())
            assert data == []

    @pytest.mark.asyncio
    async def test_list_roles_error(self):
        """Test error handling in list_roles"""
        mock_req = Mock(spec=func.HttpRequest)
        mock_req.context = Mock(user_id="admin-123", org_id="GLOBAL")

        with patch('shared.handlers.roles_handlers.RoleRepository') as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.list_roles.side_effect = Exception("Database error")

            response = await list_roles_handler(mock_req)

            assert response.status_code == 500
            data = json.loads(response.get_body())
            assert data["error"] == "InternalServerError"


class TestCreateRoleHandler:
    """Test create_role_handler"""

    @pytest.mark.asyncio
    async def test_create_role_success(self):
        """Test successful role creation"""
        mock_req = Mock(spec=func.HttpRequest)
        mock_req.get_json.return_value = {"name": "Test Role", "description": "Test"}
        mock_req.context = Mock(user_id="admin-123", org_id="GLOBAL")

        role = Mock(
            id="role-new",
            name="Test Role",
            model_dump=Mock(return_value={"id": "role-new", "name": "Test Role"})
        )

        with patch('shared.handlers.roles_handlers.RoleRepository') as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.create_role.return_value = role

            response = await create_role_handler(mock_req)

            assert response.status_code == 201
            data = json.loads(response.get_body())
            assert data["id"] == "role-new"
            mock_repo.create_role.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_role_validation_error(self):
        """Test role creation with invalid data"""
        mock_req = Mock(spec=func.HttpRequest)
        mock_req.get_json.return_value = {"name": ""}  # Invalid: empty name
        mock_req.context = Mock(user_id="admin-123", org_id="GLOBAL")

        with patch('shared.handlers.roles_handlers.CreateRoleRequest') as MockModel:
            MockModel.side_effect = ValidationError.from_exception_data(
                "CreateRoleRequest", []
            )

            response = await create_role_handler(mock_req)

            assert response.status_code == 400
            data = json.loads(response.get_body())
            assert data["error"] == "ValidationError"

    @pytest.mark.asyncio
    async def test_create_role_json_error(self):
        """Test role creation with invalid JSON"""
        mock_req = Mock(spec=func.HttpRequest)
        mock_req.get_json.side_effect = ValueError("Invalid JSON")
        mock_req.context = Mock(user_id="admin-123", org_id="GLOBAL")

        response = await create_role_handler(mock_req)

        assert response.status_code == 400
        data = json.loads(response.get_body())
        assert data["error"] == "BadRequest"

    @pytest.mark.asyncio
    async def test_create_role_error(self):
        """Test error handling in create_role"""
        mock_req = Mock(spec=func.HttpRequest)
        mock_req.get_json.return_value = {"name": "Test Role"}
        mock_req.context = Mock(user_id="admin-123", org_id="GLOBAL")

        with patch('shared.handlers.roles_handlers.RoleRepository') as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.create_role.side_effect = Exception("Database error")

            response = await create_role_handler(mock_req)

            assert response.status_code == 500
            data = json.loads(response.get_body())
            assert data["error"] == "InternalServerError"


class TestUpdateRoleHandler:
    """Test update_role_handler"""

    @pytest.mark.asyncio
    async def test_update_role_success(self):
        """Test successful role update"""
        mock_req = Mock(spec=func.HttpRequest)
        mock_req.get_json.return_value = {"name": "Updated Role"}
        mock_req.context = Mock(user_id="admin-123", org_id="GLOBAL")

        role = Mock(
            id="role-1",
            name="Updated Role",
            model_dump=Mock(return_value={"id": "role-1", "name": "Updated Role"})
        )

        with patch('shared.handlers.roles_handlers.RoleRepository') as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.update_role.return_value = role

            response = await update_role_handler(mock_req, role_id="role-1")

            assert response.status_code == 200
            data = json.loads(response.get_body())
            assert data["name"] == "Updated Role"
            mock_repo.update_role.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_role_validation_error(self):
        """Test role update with invalid data"""
        mock_req = Mock(spec=func.HttpRequest)
        mock_req.get_json.return_value = {"name": ""}
        mock_req.context = Mock(user_id="admin-123", org_id="GLOBAL")

        with patch('shared.handlers.roles_handlers.UpdateRoleRequest') as MockModel:
            MockModel.side_effect = ValidationError.from_exception_data(
                "UpdateRoleRequest", []
            )

            response = await update_role_handler(mock_req, role_id="role-1")

            assert response.status_code == 400
            data = json.loads(response.get_body())
            assert data["error"] == "ValidationError"

    @pytest.mark.asyncio
    async def test_update_role_error(self):
        """Test error handling in update_role"""
        mock_req = Mock(spec=func.HttpRequest)
        mock_req.get_json.return_value = {"name": "Updated Role"}
        mock_req.context = Mock(user_id="admin-123", org_id="GLOBAL")

        with patch('shared.handlers.roles_handlers.RoleRepository') as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.update_role.side_effect = Exception("Database error")

            response = await update_role_handler(mock_req, role_id="role-1")

            assert response.status_code == 500
            data = json.loads(response.get_body())
            assert data["error"] == "InternalServerError"


class TestDeleteRoleHandler:
    """Test delete_role_handler"""

    @pytest.mark.asyncio
    async def test_delete_role_success(self):
        """Test successful role deletion"""
        mock_req = Mock(spec=func.HttpRequest)
        mock_req.context = Mock(user_id="admin-123", org_id="GLOBAL")

        with patch('shared.handlers.roles_handlers.RoleRepository') as MockRepo:
            mock_repo = MockRepo.return_value

            response = await delete_role_handler(mock_req, role_id="role-1")

            assert response.status_code == 204
            mock_repo.delete_role.assert_called_once_with("role-1", "GLOBAL")

    @pytest.mark.asyncio
    async def test_delete_role_error(self):
        """Test error handling in delete_role"""
        mock_req = Mock(spec=func.HttpRequest)
        mock_req.context = Mock(user_id="admin-123", org_id="GLOBAL")

        with patch('shared.handlers.roles_handlers.RoleRepository') as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.delete_role.side_effect = Exception("Database error")

            response = await delete_role_handler(mock_req, role_id="role-1")

            assert response.status_code == 500
            data = json.loads(response.get_body())
            assert data["error"] == "InternalServerError"


class TestGetRoleUsersHandler:
    """Test get_role_users_handler"""

    @pytest.mark.asyncio
    async def test_get_role_users_success(self):
        """Test successful get role users"""
        mock_req = Mock(spec=func.HttpRequest)
        mock_req.context = Mock(user_id="admin-123", org_id="GLOBAL")

        with patch('shared.handlers.roles_handlers.RoleRepository') as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.get_role_user_ids.return_value = ["user-1", "user-2"]

            response = await get_role_users_handler(mock_req, role_id="role-1")

            assert response.status_code == 200
            data = json.loads(response.get_body())
            assert data["userIds"] == ["user-1", "user-2"]
            mock_repo.get_role_user_ids.assert_called_once_with("role-1")

    @pytest.mark.asyncio
    async def test_get_role_users_empty(self):
        """Test get role users when none assigned"""
        mock_req = Mock(spec=func.HttpRequest)
        mock_req.context = Mock(user_id="admin-123", org_id="GLOBAL")

        with patch('shared.handlers.roles_handlers.RoleRepository') as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.get_role_user_ids.return_value = []

            response = await get_role_users_handler(mock_req, role_id="role-1")

            assert response.status_code == 200
            data = json.loads(response.get_body())
            assert data["userIds"] == []

    @pytest.mark.asyncio
    async def test_get_role_users_error(self):
        """Test error handling in get_role_users"""
        mock_req = Mock(spec=func.HttpRequest)
        mock_req.context = Mock(user_id="admin-123", org_id="GLOBAL")

        with patch('shared.handlers.roles_handlers.RoleRepository') as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.get_role_user_ids.side_effect = Exception("Database error")

            response = await get_role_users_handler(mock_req, role_id="role-1")

            assert response.status_code == 500
            data = json.loads(response.get_body())
            assert data["error"] == "InternalServerError"


class TestAssignUsersToRoleHandler:
    """Test assign_users_to_role_handler"""

    @pytest.mark.asyncio
    async def test_assign_users_success(self):
        """Test successful user assignment"""
        mock_req = Mock(spec=func.HttpRequest)
        mock_req.get_json.return_value = {"userIds": ["user-1", "user-2"]}
        mock_req.context = Mock(user_id="admin-123", org_id="GLOBAL")

        role = Mock(id="role-1")
        user1 = Mock(isPlatformAdmin=False)
        user2 = Mock(isPlatformAdmin=False)

        with patch('shared.handlers.roles_handlers.RoleRepository') as MockRepo:
            with patch('shared.handlers.roles_handlers.UserRepository') as MockUserRepo:
                mock_repo = MockRepo.return_value
                mock_user_repo = MockUserRepo.return_value

                mock_repo.get_role.return_value = role
                mock_user_repo.get_user.side_effect = [user1, user2]

                response = await assign_users_to_role_handler(mock_req, role_id="role-1")

                assert response.status_code == 200
                data = json.loads(response.get_body())
                assert "Assigned 2 users" in data["message"]
                mock_repo.assign_users_to_role.assert_called_once()

    @pytest.mark.asyncio
    async def test_assign_users_role_not_found(self):
        """Test assignment when role doesn't exist"""
        mock_req = Mock(spec=func.HttpRequest)
        mock_req.get_json.return_value = {"userIds": ["user-1"]}
        mock_req.context = Mock(user_id="admin-123", org_id="GLOBAL")

        with patch('shared.handlers.roles_handlers.RoleRepository') as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.get_role.return_value = None

            response = await assign_users_to_role_handler(mock_req, role_id="role-1")

            assert response.status_code == 404
            data = json.loads(response.get_body())
            assert data["error"] == "NotFound"

    @pytest.mark.asyncio
    async def test_assign_users_user_not_found(self):
        """Test assignment when user doesn't exist"""
        mock_req = Mock(spec=func.HttpRequest)
        mock_req.get_json.return_value = {"userIds": ["user-1"]}
        mock_req.context = Mock(user_id="admin-123", org_id="GLOBAL")

        role = Mock(id="role-1")

        with patch('shared.handlers.roles_handlers.RoleRepository') as MockRepo:
            with patch('shared.handlers.roles_handlers.UserRepository') as MockUserRepo:
                mock_repo = MockRepo.return_value
                mock_user_repo = MockUserRepo.return_value

                mock_repo.get_role.return_value = role
                mock_user_repo.get_user.return_value = None

                response = await assign_users_to_role_handler(mock_req, role_id="role-1")

                assert response.status_code == 400
                data = json.loads(response.get_body())
                assert data["error"] == "BadRequest"

    @pytest.mark.asyncio
    async def test_assign_users_platform_admin_not_allowed(self):
        """Test that platform admins cannot be assigned roles"""
        mock_req = Mock(spec=func.HttpRequest)
        mock_req.get_json.return_value = {"userIds": ["user-1"]}
        mock_req.context = Mock(user_id="admin-123", org_id="GLOBAL")

        role = Mock(id="role-1")
        platform_admin = Mock(isPlatformAdmin=True)

        with patch('shared.handlers.roles_handlers.RoleRepository') as MockRepo:
            with patch('shared.handlers.roles_handlers.UserRepository') as MockUserRepo:
                mock_repo = MockRepo.return_value
                mock_user_repo = MockUserRepo.return_value

                mock_repo.get_role.return_value = role
                mock_user_repo.get_user.return_value = platform_admin

                response = await assign_users_to_role_handler(mock_req, role_id="role-1")

                assert response.status_code == 400
                data = json.loads(response.get_body())
                assert "Platform Administrator" in data["message"]

    @pytest.mark.asyncio
    async def test_assign_users_validation_error(self):
        """Test assignment with invalid request"""
        mock_req = Mock(spec=func.HttpRequest)
        mock_req.get_json.return_value = {}  # Missing userIds
        mock_req.context = Mock(user_id="admin-123", org_id="GLOBAL")

        with patch('shared.handlers.roles_handlers.AssignUsersToRoleRequest') as MockModel:
            MockModel.side_effect = ValidationError.from_exception_data(
                "AssignUsersToRoleRequest", []
            )

            response = await assign_users_to_role_handler(mock_req, role_id="role-1")

            assert response.status_code == 400
            data = json.loads(response.get_body())
            assert data["error"] == "ValidationError"


class TestRemoveUserFromRoleHandler:
    """Test remove_user_from_role_handler"""

    @pytest.mark.asyncio
    async def test_remove_user_success(self):
        """Test successful user removal"""
        mock_req = Mock(spec=func.HttpRequest)
        mock_req.context = Mock(user_id="admin-123", org_id="GLOBAL")

        with patch('shared.handlers.roles_handlers.RoleRepository') as MockRepo:
            mock_repo = MockRepo.return_value

            response = await remove_user_from_role_handler(
                mock_req, role_id="role-1", user_id="user-1"
            )

            assert response.status_code == 204
            mock_repo.remove_user_from_role.assert_called_once_with("role-1", "user-1")

    @pytest.mark.asyncio
    async def test_remove_user_missing_role_id(self):
        """Test removal with missing role ID"""
        mock_req = Mock(spec=func.HttpRequest)
        mock_req.context = Mock(user_id="admin-123", org_id="GLOBAL")

        response = await remove_user_from_role_handler(
            mock_req, role_id="", user_id="user-1"
        )

        assert response.status_code == 400
        data = json.loads(response.get_body())
        assert "Role ID is required" in data["message"]

    @pytest.mark.asyncio
    async def test_remove_user_missing_user_id(self):
        """Test removal with missing user ID"""
        mock_req = Mock(spec=func.HttpRequest)
        mock_req.context = Mock(user_id="admin-123", org_id="GLOBAL")

        response = await remove_user_from_role_handler(
            mock_req, role_id="role-1", user_id=""
        )

        assert response.status_code == 400
        data = json.loads(response.get_body())
        assert "User ID is required" in data["message"]

    @pytest.mark.asyncio
    async def test_remove_user_error(self):
        """Test error handling in remove_user"""
        mock_req = Mock(spec=func.HttpRequest)
        mock_req.context = Mock(user_id="admin-123", org_id="GLOBAL")

        with patch('shared.handlers.roles_handlers.RoleRepository') as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.remove_user_from_role.side_effect = Exception("Database error")

            response = await remove_user_from_role_handler(
                mock_req, role_id="role-1", user_id="user-1"
            )

            assert response.status_code == 500
            data = json.loads(response.get_body())
            assert data["error"] == "InternalServerError"


class TestGetRoleFormsHandler:
    """Test get_role_forms_handler"""

    @pytest.mark.asyncio
    async def test_get_role_forms_success(self):
        """Test successful get role forms"""
        mock_req = Mock(spec=func.HttpRequest)
        mock_req.context = Mock(user_id="admin-123", org_id="GLOBAL")

        with patch('shared.handlers.roles_handlers.RoleRepository') as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.get_role_form_ids.return_value = ["form-1", "form-2"]

            response = await get_role_forms_handler(mock_req, role_id="role-1")

            assert response.status_code == 200
            data = json.loads(response.get_body())
            assert data["formIds"] == ["form-1", "form-2"]
            mock_repo.get_role_form_ids.assert_called_once_with("role-1")

    @pytest.mark.asyncio
    async def test_get_role_forms_empty(self):
        """Test get role forms when none assigned"""
        mock_req = Mock(spec=func.HttpRequest)
        mock_req.context = Mock(user_id="admin-123", org_id="GLOBAL")

        with patch('shared.handlers.roles_handlers.RoleRepository') as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.get_role_form_ids.return_value = []

            response = await get_role_forms_handler(mock_req, role_id="role-1")

            assert response.status_code == 200
            data = json.loads(response.get_body())
            assert data["formIds"] == []

    @pytest.mark.asyncio
    async def test_get_role_forms_error(self):
        """Test error handling in get_role_forms"""
        mock_req = Mock(spec=func.HttpRequest)
        mock_req.context = Mock(user_id="admin-123", org_id="GLOBAL")

        with patch('shared.handlers.roles_handlers.RoleRepository') as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.get_role_form_ids.side_effect = Exception("Database error")

            response = await get_role_forms_handler(mock_req, role_id="role-1")

            assert response.status_code == 500
            data = json.loads(response.get_body())
            assert data["error"] == "InternalServerError"


class TestAssignFormsToRoleHandler:
    """Test assign_forms_to_role_handler"""

    @pytest.mark.asyncio
    async def test_assign_forms_success(self):
        """Test successful form assignment"""
        mock_req = Mock(spec=func.HttpRequest)
        mock_req.get_json.return_value = {"formIds": ["form-1", "form-2"]}
        mock_req.context = Mock(user_id="admin-123", org_id="GLOBAL")

        role = Mock(id="role-1")

        with patch('shared.handlers.roles_handlers.RoleRepository') as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.get_role.return_value = role

            response = await assign_forms_to_role_handler(mock_req, role_id="role-1")

            assert response.status_code == 200
            data = json.loads(response.get_body())
            assert "Assigned 2 forms" in data["message"]
            mock_repo.assign_forms_to_role.assert_called_once()

    @pytest.mark.asyncio
    async def test_assign_forms_role_not_found(self):
        """Test assignment when role doesn't exist"""
        mock_req = Mock(spec=func.HttpRequest)
        mock_req.get_json.return_value = {"formIds": ["form-1"]}
        mock_req.context = Mock(user_id="admin-123", org_id="GLOBAL")

        with patch('shared.handlers.roles_handlers.RoleRepository') as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.get_role.return_value = None

            response = await assign_forms_to_role_handler(mock_req, role_id="role-1")

            assert response.status_code == 404
            data = json.loads(response.get_body())
            assert data["error"] == "NotFound"

    @pytest.mark.asyncio
    async def test_assign_forms_validation_error(self):
        """Test assignment with invalid request"""
        mock_req = Mock(spec=func.HttpRequest)
        mock_req.get_json.return_value = {}  # Missing formIds
        mock_req.context = Mock(user_id="admin-123", org_id="GLOBAL")

        with patch('shared.handlers.roles_handlers.AssignFormsToRoleRequest') as MockModel:
            MockModel.side_effect = ValidationError.from_exception_data(
                "AssignFormsToRoleRequest", []
            )

            response = await assign_forms_to_role_handler(mock_req, role_id="role-1")

            assert response.status_code == 400
            data = json.loads(response.get_body())
            assert data["error"] == "ValidationError"

    @pytest.mark.asyncio
    async def test_assign_forms_error(self):
        """Test error handling in assign_forms"""
        mock_req = Mock(spec=func.HttpRequest)
        mock_req.get_json.return_value = {"formIds": ["form-1"]}
        mock_req.context = Mock(user_id="admin-123", org_id="GLOBAL")

        role = Mock(id="role-1")

        with patch('shared.handlers.roles_handlers.RoleRepository') as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.get_role.return_value = role
            mock_repo.assign_forms_to_role.side_effect = Exception("Database error")

            response = await assign_forms_to_role_handler(mock_req, role_id="role-1")

            assert response.status_code == 500
            data = json.loads(response.get_body())
            assert data["error"] == "InternalServerError"


class TestRemoveFormFromRoleHandler:
    """Test remove_form_from_role_handler"""

    @pytest.mark.asyncio
    async def test_remove_form_success(self):
        """Test successful form removal"""
        mock_req = Mock(spec=func.HttpRequest)
        mock_req.context = Mock(user_id="admin-123", org_id="GLOBAL")

        with patch('shared.handlers.roles_handlers.RoleRepository') as MockRepo:
            mock_repo = MockRepo.return_value

            response = await remove_form_from_role_handler(
                mock_req, role_id="role-1", form_id="form-1"
            )

            assert response.status_code == 204
            mock_repo.remove_form_from_role.assert_called_once_with("role-1", "form-1")

    @pytest.mark.asyncio
    async def test_remove_form_missing_role_id(self):
        """Test removal with missing role ID"""
        mock_req = Mock(spec=func.HttpRequest)
        mock_req.context = Mock(user_id="admin-123", org_id="GLOBAL")

        response = await remove_form_from_role_handler(
            mock_req, role_id="", form_id="form-1"
        )

        assert response.status_code == 400
        data = json.loads(response.get_body())
        assert "Role ID is required" in data["message"]

    @pytest.mark.asyncio
    async def test_remove_form_missing_form_id(self):
        """Test removal with missing form ID"""
        mock_req = Mock(spec=func.HttpRequest)
        mock_req.context = Mock(user_id="admin-123", org_id="GLOBAL")

        response = await remove_form_from_role_handler(
            mock_req, role_id="role-1", form_id=""
        )

        assert response.status_code == 400
        data = json.loads(response.get_body())
        assert "Form ID is required" in data["message"]

    @pytest.mark.asyncio
    async def test_remove_form_error(self):
        """Test error handling in remove_form"""
        mock_req = Mock(spec=func.HttpRequest)
        mock_req.context = Mock(user_id="admin-123", org_id="GLOBAL")

        with patch('shared.handlers.roles_handlers.RoleRepository') as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.remove_form_from_role.side_effect = Exception("Database error")

            response = await remove_form_from_role_handler(
                mock_req, role_id="role-1", form_id="form-1"
            )

            assert response.status_code == 500
            data = json.loads(response.get_body())
            assert data["error"] == "InternalServerError"
