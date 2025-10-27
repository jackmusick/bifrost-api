"""
Unit tests for user management handlers
Tests create_user_handler and update_user_handler
"""

import json
import pytest
from unittest.mock import AsyncMock, Mock, patch
from datetime import datetime

from shared.handlers.permissions_handlers import (
    create_user_handler,
    update_user_handler,
    delete_user_handler,
)
from shared.models import UserType


class TestCreateUserHandler:
    """Test create_user_handler"""

    @pytest.mark.asyncio
    async def test_create_platform_admin_user_success(self):
        """Test creating a platform admin user successfully"""
        mock_context = Mock(user_id="admin@example.com")
        mock_req = Mock()
        mock_req.get_json.return_value = {
            "email": "newadmin@example.com",
            "displayName": "New Admin",
            "isPlatformAdmin": True,
            "orgId": None
        }

        with patch('shared.handlers.permissions_handlers.UserRepository') as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.get_user = AsyncMock(return_value=None)  # User doesn't exist
            mock_repo.create_user = AsyncMock(return_value=Mock(
                id="newadmin@example.com",
                email="newadmin@example.com",
                displayName="New Admin",
                userType=UserType.PLATFORM,
                isPlatformAdmin=True,
                isActive=True,
                lastLogin=None,
                createdAt=datetime.utcnow(),
                entraUserId=None,
                lastEntraIdSync=None,
                model_dump=lambda mode=None: {
                    "id": "newadmin@example.com",
                    "email": "newadmin@example.com",
                    "displayName": "New Admin",
                    "userType": "PLATFORM",
                    "isPlatformAdmin": True,
                    "isActive": True,
                    "lastLogin": None,
                    "createdAt": datetime.utcnow().isoformat(),
                    "entraUserId": None,
                    "lastEntraIdSync": None
                }
            ))

            response = await create_user_handler(mock_context, mock_req)

            assert response.status_code == 201
            data = json.loads(response.get_body())
            assert data["email"] == "newadmin@example.com"
            assert data["isPlatformAdmin"] is True
            assert data["userType"] == "PLATFORM"

            # Verify create_user was called correctly
            mock_repo.create_user.assert_called_once_with(
                email="newadmin@example.com",
                display_name="New Admin",
                user_type=UserType.PLATFORM,
                is_platform_admin=True
            )
            # Verify assign_user_to_org was NOT called for platform admin
            mock_repo.assign_user_to_org.assert_not_called()

    @pytest.mark.asyncio
    async def test_create_org_user_success(self):
        """Test creating an org user successfully"""
        mock_context = Mock(user_id="admin@example.com")
        mock_req = Mock()
        mock_req.get_json.return_value = {
            "email": "orguser@example.com",
            "displayName": "Org User",
            "isPlatformAdmin": False,
            "orgId": "org-123"
        }

        with patch('shared.handlers.permissions_handlers.UserRepository') as MockUserRepo, \
             patch('shared.handlers.permissions_handlers.OrganizationRepository') as MockOrgRepo:
            mock_user_repo = MockUserRepo.return_value
            mock_org_repo = MockOrgRepo.return_value

            mock_user_repo.get_user = AsyncMock(return_value=None)  # User doesn't exist
            mock_org_repo.get_by_id = AsyncMock(return_value={"id": "org-123"})  # Org exists
            mock_user_repo.create_user = AsyncMock(return_value=Mock(
                id="orguser@example.com",
                email="orguser@example.com",
                displayName="Org User",
                userType=UserType.ORG,
                isPlatformAdmin=False,
                isActive=True,
                lastLogin=None,
                createdAt=datetime.utcnow(),
                entraUserId=None,
                lastEntraIdSync=None,
                model_dump=lambda mode=None: {
                    "id": "orguser@example.com",
                    "email": "orguser@example.com",
                    "displayName": "Org User",
                    "userType": "ORG",
                    "isPlatformAdmin": False,
                    "isActive": True,
                    "lastLogin": None,
                    "createdAt": datetime.utcnow().isoformat(),
                    "entraUserId": None,
                    "lastEntraIdSync": None
                }
            ))
            mock_user_repo.assign_user_to_org = AsyncMock()

            response = await create_user_handler(mock_context, mock_req)

            assert response.status_code == 201
            data = json.loads(response.get_body())
            assert data["email"] == "orguser@example.com"
            assert data["isPlatformAdmin"] is False
            assert data["userType"] == "ORG"

            # Verify assign_user_to_org was called
            mock_user_repo.assign_user_to_org.assert_called_once_with(
                email="orguser@example.com",
                org_id="org-123",
                assigned_by="admin@example.com"
            )

    @pytest.mark.asyncio
    async def test_create_user_validation_error_missing_org(self):
        """Test validation error when creating org user without orgId"""
        mock_context = Mock(user_id="admin@example.com")
        mock_req = Mock()
        mock_req.get_json.return_value = {
            "email": "orguser@example.com",
            "displayName": "Org User",
            "isPlatformAdmin": False,
            "orgId": None  # Missing orgId for org user
        }

        response = await create_user_handler(mock_context, mock_req)

        assert response.status_code == 400
        data = json.loads(response.get_body())
        assert "ValidationError" in data["error"]
        assert "orgId is required" in data["message"]

    @pytest.mark.asyncio
    async def test_create_user_validation_error_platform_admin_with_org(self):
        """Test validation error when creating platform admin with orgId"""
        mock_context = Mock(user_id="admin@example.com")
        mock_req = Mock()
        mock_req.get_json.return_value = {
            "email": "admin@example.com",
            "displayName": "Admin",
            "isPlatformAdmin": True,
            "orgId": "org-123"  # Platform admin shouldn't have orgId
        }

        response = await create_user_handler(mock_context, mock_req)

        assert response.status_code == 400
        data = json.loads(response.get_body())
        assert "ValidationError" in data["error"]

    @pytest.mark.asyncio
    async def test_create_user_already_exists(self):
        """Test error when creating user that already exists"""
        mock_context = Mock(user_id="admin@example.com")
        mock_req = Mock()
        mock_req.get_json.return_value = {
            "email": "existing@example.com",
            "displayName": "Existing User",
            "isPlatformAdmin": False,
            "orgId": "org-123"
        }

        with patch('shared.handlers.permissions_handlers.UserRepository') as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.get_user = AsyncMock(return_value=Mock(email="existing@example.com"))

            response = await create_user_handler(mock_context, mock_req)

            assert response.status_code == 409
            data = json.loads(response.get_body())
            assert data["error"] == "Conflict"
            assert "already exists" in data["message"]

    @pytest.mark.asyncio
    async def test_create_user_org_not_found(self):
        """Test error when organization doesn't exist"""
        mock_context = Mock(user_id="admin@example.com")
        mock_req = Mock()
        mock_req.get_json.return_value = {
            "email": "newuser@example.com",
            "displayName": "New User",
            "isPlatformAdmin": False,
            "orgId": "nonexistent-org"
        }

        with patch('shared.handlers.permissions_handlers.UserRepository') as MockUserRepo, \
             patch('shared.handlers.permissions_handlers.OrganizationRepository') as MockOrgRepo:
            mock_user_repo = MockUserRepo.return_value
            mock_org_repo = MockOrgRepo.return_value

            mock_user_repo.get_user = AsyncMock(return_value=None)
            mock_org_repo.get_by_id = AsyncMock(return_value=None)  # Org doesn't exist

            response = await create_user_handler(mock_context, mock_req)

            assert response.status_code == 404
            data = json.loads(response.get_body())
            assert data["error"] == "NotFound"
            assert "Organization" in data["message"]


class TestUpdateUserHandler:
    """Test update_user_handler"""

    @pytest.mark.asyncio
    async def test_update_user_display_name(self):
        """Test updating user's display name"""
        mock_context = Mock(user_id="admin@example.com")
        user_id = "user@example.com"
        mock_req = Mock()
        mock_req.get_json.return_value = {
            "displayName": "Updated Name",
            "isActive": None,
            "isPlatformAdmin": None,
            "orgId": None
        }

        with patch('shared.handlers.permissions_handlers.UserRepository') as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.get_user = AsyncMock(return_value=Mock(email=user_id))
            mock_repo.update_user = AsyncMock(return_value=Mock(
                id=user_id,
                email=user_id,
                displayName="Updated Name",
                userType=UserType.ORG,
                isPlatformAdmin=False,
                isActive=True,
                lastLogin=None,
                createdAt=datetime.utcnow(),
                entraUserId=None,
                lastEntraIdSync=None,
                model_dump=lambda mode=None: {
                    "id": user_id,
                    "email": user_id,
                    "displayName": "Updated Name",
                    "userType": "ORG",
                    "isPlatformAdmin": False,
                    "isActive": True,
                    "lastLogin": None,
                    "createdAt": datetime.utcnow().isoformat(),
                    "entraUserId": None,
                    "lastEntraIdSync": None
                }
            ))

            response = await update_user_handler(mock_context, user_id, mock_req)

            assert response.status_code == 200
            data = json.loads(response.get_body())
            assert data["displayName"] == "Updated Name"

            mock_repo.update_user.assert_called_once_with(
                email=user_id,
                display_name="Updated Name",
                is_active=None,
                is_platform_admin=None,
                org_id=None,
                updated_by="admin@example.com"
            )

    @pytest.mark.asyncio
    async def test_promote_user_to_platform_admin(self):
        """Test promoting org user to platform admin"""
        mock_context = Mock(user_id="admin@example.com")
        user_id = "user@example.com"
        mock_req = Mock()
        mock_req.get_json.return_value = {
            "displayName": None,
            "isActive": None,
            "isPlatformAdmin": True,  # Promoting to admin
            "orgId": None
        }

        with patch('shared.handlers.permissions_handlers.UserRepository') as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.get_user = AsyncMock(return_value=Mock(
                email=user_id,
                isPlatformAdmin=False,
                userType=UserType.ORG
            ))
            mock_repo.update_user = AsyncMock(return_value=Mock(
                id=user_id,
                email=user_id,
                displayName="User",
                userType=UserType.PLATFORM,
                isPlatformAdmin=True,
                isActive=True,
                lastLogin=None,
                createdAt=datetime.utcnow(),
                entraUserId=None,
                lastEntraIdSync=None,
                model_dump=lambda mode=None: {
                    "id": user_id,
                    "email": user_id,
                    "displayName": "User",
                    "userType": "PLATFORM",
                    "isPlatformAdmin": True,
                    "isActive": True,
                    "lastLogin": None,
                    "createdAt": datetime.utcnow().isoformat(),
                    "entraUserId": None,
                    "lastEntraIdSync": None
                }
            ))

            response = await update_user_handler(mock_context, user_id, mock_req)

            assert response.status_code == 200
            data = json.loads(response.get_body())
            assert data["isPlatformAdmin"] is True
            assert data["userType"] == "PLATFORM"

    @pytest.mark.asyncio
    async def test_demote_platform_admin_to_org_user(self):
        """Test demoting platform admin to org user"""
        mock_context = Mock(user_id="admin@example.com")
        user_id = "user@example.com"
        mock_req = Mock()
        mock_req.get_json.return_value = {
            "displayName": None,
            "isActive": None,
            "isPlatformAdmin": False,  # Demoting from admin
            "orgId": "org-123"  # Required when demoting
        }

        with patch('shared.handlers.permissions_handlers.UserRepository') as MockUserRepo, \
             patch('shared.handlers.permissions_handlers.OrganizationRepository') as MockOrgRepo:
            mock_user_repo = MockUserRepo.return_value
            mock_org_repo = MockOrgRepo.return_value

            mock_user_repo.get_user = AsyncMock(return_value=Mock(
                email=user_id,
                isPlatformAdmin=True,
                userType=UserType.PLATFORM
            ))
            mock_org_repo.get_by_id = AsyncMock(return_value={"id": "org-123"})
            mock_user_repo.update_user = AsyncMock(return_value=Mock(
                id=user_id,
                email=user_id,
                displayName="User",
                userType=UserType.ORG,
                isPlatformAdmin=False,
                isActive=True,
                lastLogin=None,
                createdAt=datetime.utcnow(),
                entraUserId=None,
                lastEntraIdSync=None,
                model_dump=lambda mode=None: {
                    "id": user_id,
                    "email": user_id,
                    "displayName": "User",
                    "userType": "ORG",
                    "isPlatformAdmin": False,
                    "isActive": True,
                    "lastLogin": None,
                    "createdAt": datetime.utcnow().isoformat(),
                    "entraUserId": None,
                    "lastEntraIdSync": None
                }
            ))

            response = await update_user_handler(mock_context, user_id, mock_req)

            assert response.status_code == 200
            data = json.loads(response.get_body())
            assert data["isPlatformAdmin"] is False
            assert data["userType"] == "ORG"

    @pytest.mark.asyncio
    async def test_demote_without_org_id_fails(self):
        """Test that demoting to org user without orgId fails"""
        mock_context = Mock(user_id="admin@example.com")
        user_id = "user@example.com"
        mock_req = Mock()
        mock_req.get_json.return_value = {
            "displayName": None,
            "isActive": None,
            "isPlatformAdmin": False,  # Demoting from admin
            "orgId": None  # Missing required orgId
        }

        response = await update_user_handler(mock_context, user_id, mock_req)

        assert response.status_code == 400
        data = json.loads(response.get_body())
        assert "ValidationError" in data["error"]
        assert "orgId is required" in data["message"]

    @pytest.mark.asyncio
    async def test_update_user_not_found(self):
        """Test error when updating non-existent user"""
        mock_context = Mock(user_id="admin@example.com")
        user_id = "nonexistent@example.com"
        mock_req = Mock()
        mock_req.get_json.return_value = {
            "displayName": "Updated Name",
            "isActive": None,
            "isPlatformAdmin": None,
            "orgId": None
        }

        with patch('shared.handlers.permissions_handlers.UserRepository') as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.get_user = AsyncMock(return_value=None)

            response = await update_user_handler(mock_context, user_id, mock_req)

            assert response.status_code == 404
            data = json.loads(response.get_body())
            assert data["error"] == "NotFound"

    @pytest.mark.asyncio
    async def test_update_user_deactivate(self):
        """Test deactivating a user"""
        mock_context = Mock(user_id="admin@example.com")
        user_id = "user@example.com"
        mock_req = Mock()
        mock_req.get_json.return_value = {
            "displayName": None,
            "isActive": False,  # Deactivating user
            "isPlatformAdmin": None,
            "orgId": None
        }

        with patch('shared.handlers.permissions_handlers.UserRepository') as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.get_user = AsyncMock(return_value=Mock(email=user_id))
            mock_repo.update_user = AsyncMock(return_value=Mock(
                id=user_id,
                email=user_id,
                displayName="User",
                userType=UserType.ORG,
                isPlatformAdmin=False,
                isActive=False,
                lastLogin=None,
                createdAt=datetime.utcnow(),
                entraUserId=None,
                lastEntraIdSync=None,
                model_dump=lambda mode=None: {
                    "id": user_id,
                    "email": user_id,
                    "displayName": "User",
                    "userType": "ORG",
                    "isPlatformAdmin": False,
                    "isActive": False,
                    "lastLogin": None,
                    "createdAt": datetime.utcnow().isoformat(),
                    "entraUserId": None,
                    "lastEntraIdSync": None
                }
            ))

            response = await update_user_handler(mock_context, user_id, mock_req)

            assert response.status_code == 200
            data = json.loads(response.get_body())
            assert data["isActive"] is False


class TestDeleteUserHandler:
    """Test cases for delete_user_handler"""

    @pytest.mark.asyncio
    async def test_delete_user_success(self):
        """Test successfully deleting a user"""
        mock_context = Mock(user_id="admin@example.com")
        user_id = "user@example.com"

        with patch('shared.handlers.permissions_handlers.UserRepository') as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.get_user = AsyncMock(return_value=Mock(
                email=user_id,
                isPlatformAdmin=False
            ))
            mock_repo.delete_user = AsyncMock(return_value=None)
            mock_repo.delete = AsyncMock(return_value=None)
            mock_repo.get_user_org_id = AsyncMock(return_value="test-org-id")
            mock_repo.remove_user_from_org = AsyncMock(return_value=None)

            response = await delete_user_handler(mock_context, user_id)

            assert response.status_code == 204
            # Verify the user entity was deleted
            mock_repo.delete.assert_awaited_once_with("GLOBAL", f"user:{user_id}")
            # Verify org assignment cleanup
            mock_repo.get_user_org_id.assert_awaited_once_with(user_id)
            mock_repo.remove_user_from_org.assert_awaited_once_with(user_id, "test-org-id")

    @pytest.mark.asyncio
    async def test_delete_self_forbidden(self):
        """Test that users cannot delete themselves"""
        mock_context = Mock(user_id="admin@example.com")
        user_id = "admin@example.com"  # Same as context user

        response = await delete_user_handler(mock_context, user_id)

        assert response.status_code == 403
        data = json.loads(response.get_body())
        assert data["error"] == "Forbidden"
        assert "cannot delete your own user account" in data["message"]

    @pytest.mark.asyncio
    async def test_delete_user_not_found(self):
        """Test error when deleting non-existent user"""
        mock_context = Mock(user_id="admin@example.com")
        user_id = "nonexistent@example.com"

        with patch('shared.handlers.permissions_handlers.UserRepository') as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.get_user = AsyncMock(return_value=None)

            response = await delete_user_handler(mock_context, user_id)

            assert response.status_code == 404
            data = json.loads(response.get_body())
            assert data["error"] == "NotFound"
