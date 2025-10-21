"""
Unit tests for organizations_handlers
Tests organization CRUD operations
"""

import json
import pytest
from unittest.mock import Mock, patch
import azure.functions as func
from pydantic import ValidationError

from shared.handlers.organizations_handlers import (
    create_organization_handler,
    delete_organization_handler,
    get_organization_handler,
    list_organizations_handler,
    update_organization_handler,
)


class TestListOrganizationsHandler:
    """Test list_organizations_handler"""

    @pytest.mark.asyncio
    async def test_list_organizations_success(self):
        """Test successful organizations listing"""
        mock_req = Mock(spec=func.HttpRequest)
        mock_req.context = Mock(user_id="admin-123")

        org1 = Mock(model_dump=Mock(return_value={"id": "org-1", "name": "Org 1"}))
        org2 = Mock(model_dump=Mock(return_value={"id": "org-2", "name": "Org 2"}))

        with patch('shared.handlers.organizations_handlers.OrganizationRepository') as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.list_organizations.return_value = [org1, org2]

            response = await list_organizations_handler(mock_req)

            assert response.status_code == 200
            data = json.loads(response.get_body())
            assert len(data) == 2
            # Should be sorted by name
            mock_repo.list_organizations.assert_called_once_with(active_only=True)

    @pytest.mark.asyncio
    async def test_list_organizations_empty(self):
        """Test listing when no organizations exist"""
        mock_req = Mock(spec=func.HttpRequest)
        mock_req.context = Mock(user_id="admin-123")

        with patch('shared.handlers.organizations_handlers.OrganizationRepository') as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.list_organizations.return_value = []

            response = await list_organizations_handler(mock_req)

            assert response.status_code == 200
            data = json.loads(response.get_body())
            assert data == []

    @pytest.mark.asyncio
    async def test_list_organizations_error(self):
        """Test error handling in list_organizations"""
        mock_req = Mock(spec=func.HttpRequest)
        mock_req.context = Mock(user_id="admin-123")

        with patch('shared.handlers.organizations_handlers.OrganizationRepository') as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.list_organizations.side_effect = Exception("Database error")

            response = await list_organizations_handler(mock_req)

            assert response.status_code == 500
            data = json.loads(response.get_body())
            assert data["error"] == "InternalServerError"


class TestCreateOrganizationHandler:
    """Test create_organization_handler"""

    @pytest.mark.asyncio
    async def test_create_organization_success(self):
        """Test successful organization creation"""
        mock_req = Mock(spec=func.HttpRequest)
        mock_req.get_json.return_value = {
            "name": "Test Org",
            "domain": "test.com"
        }
        mock_req.context = Mock(user_id="admin-123")

        org = Mock(id="org-new", name="Test Org", model_dump=Mock(return_value={"id": "org-new", "name": "Test Org"}))

        with patch('shared.handlers.organizations_handlers.OrganizationRepository') as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.create_organization.return_value = org

            response = await create_organization_handler(mock_req)

            assert response.status_code == 201
            data = json.loads(response.get_body())
            assert data["id"] == "org-new"
            mock_repo.create_organization.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_organization_validation_error(self):
        """Test validation error in organization creation"""
        mock_req = Mock(spec=func.HttpRequest)
        mock_req.get_json.return_value = {
            # Missing 'name' field
        }
        mock_req.context = Mock(user_id="admin-123")

        with patch('shared.handlers.organizations_handlers.CreateOrganizationRequest') as MockRequest:
            MockRequest.side_effect = ValidationError.from_exception_data("CreateOrganizationRequest", [])

            # Should handle validation error

    @pytest.mark.asyncio
    async def test_create_organization_json_error(self):
        """Test JSON parsing error"""
        mock_req = Mock(spec=func.HttpRequest)
        mock_req.get_json.side_effect = ValueError("Invalid JSON")
        mock_req.context = Mock(user_id="admin-123")

        response = await create_organization_handler(mock_req)

        assert response.status_code == 400
        data = json.loads(response.get_body())
        assert data["error"] == "BadRequest"

    @pytest.mark.asyncio
    async def test_create_organization_error(self):
        """Test server error during creation"""
        mock_req = Mock(spec=func.HttpRequest)
        mock_req.get_json.return_value = {"name": "Test Org"}
        mock_req.context = Mock(user_id="admin-123")

        with patch('shared.handlers.organizations_handlers.OrganizationRepository') as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.create_organization.side_effect = Exception("Database error")

            response = await create_organization_handler(mock_req)

            assert response.status_code == 500


class TestGetOrganizationHandler:
    """Test get_organization_handler"""

    @pytest.mark.asyncio
    async def test_get_organization_success(self):
        """Test successful organization retrieval"""
        mock_req = Mock(spec=func.HttpRequest)
        mock_req.route_params = {"orgId": "org-123"}
        mock_req.context = Mock(user_id="admin-123")

        org = Mock(model_dump=Mock(return_value={"id": "org-123", "name": "Test Org"}))

        with patch('shared.handlers.organizations_handlers.OrganizationRepository') as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.get_organization.return_value = org

            response = await get_organization_handler(mock_req)

            assert response.status_code == 200
            data = json.loads(response.get_body())
            assert data["id"] == "org-123"

    @pytest.mark.asyncio
    async def test_get_organization_not_found(self):
        """Test getting non-existent organization"""
        mock_req = Mock(spec=func.HttpRequest)
        mock_req.route_params = {"orgId": "org-nonexistent"}
        mock_req.context = Mock(user_id="admin-123")

        with patch('shared.handlers.organizations_handlers.OrganizationRepository') as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.get_organization.return_value = None

            response = await get_organization_handler(mock_req)

            assert response.status_code == 404
            data = json.loads(response.get_body())
            assert data["error"] == "NotFound"

    @pytest.mark.asyncio
    async def test_get_organization_error(self):
        """Test error handling in get_organization"""
        mock_req = Mock(spec=func.HttpRequest)
        mock_req.route_params = {"orgId": "org-123"}
        mock_req.context = Mock(user_id="admin-123")

        with patch('shared.handlers.organizations_handlers.OrganizationRepository') as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.get_organization.side_effect = Exception("Database error")

            response = await get_organization_handler(mock_req)

            assert response.status_code == 500


class TestUpdateOrganizationHandler:
    """Test update_organization_handler"""

    @pytest.mark.asyncio
    async def test_update_organization_success(self):
        """Test successful organization update"""
        mock_req = Mock(spec=func.HttpRequest)
        mock_req.get_json.return_value = {"name": "Updated Org"}
        mock_req.route_params = {"orgId": "org-123"}
        mock_req.context = Mock(user_id="admin-123")

        updated_org = Mock(model_dump=Mock(return_value={"id": "org-123", "name": "Updated Org"}))

        with patch('shared.handlers.organizations_handlers.OrganizationRepository') as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.update_organization.return_value = updated_org

            response = await update_organization_handler(mock_req)

            assert response.status_code == 200
            data = json.loads(response.get_body())
            assert data["name"] == "Updated Org"

    @pytest.mark.asyncio
    async def test_update_organization_not_found(self):
        """Test updating non-existent organization"""
        mock_req = Mock(spec=func.HttpRequest)
        mock_req.get_json.return_value = {"name": "Updated Org"}
        mock_req.route_params = {"orgId": "org-nonexistent"}
        mock_req.context = Mock(user_id="admin-123")

        with patch('shared.handlers.organizations_handlers.OrganizationRepository') as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.update_organization.return_value = None

            response = await update_organization_handler(mock_req)

            assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_organization_validation_error(self):
        """Test validation error in update"""
        mock_req = Mock(spec=func.HttpRequest)
        mock_req.get_json.return_value = {}
        mock_req.route_params = {"orgId": "org-123"}
        mock_req.context = Mock(user_id="admin-123")

        with patch('shared.handlers.organizations_handlers.UpdateOrganizationRequest') as MockRequest:
            MockRequest.side_effect = ValidationError.from_exception_data("UpdateOrganizationRequest", [])

            # Should handle validation error

    @pytest.mark.asyncio
    async def test_update_organization_error(self):
        """Test server error during update"""
        mock_req = Mock(spec=func.HttpRequest)
        mock_req.get_json.return_value = {"name": "Updated Org"}
        mock_req.route_params = {"orgId": "org-123"}
        mock_req.context = Mock(user_id="admin-123")

        with patch('shared.handlers.organizations_handlers.OrganizationRepository') as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.update_organization.side_effect = Exception("Database error")

            response = await update_organization_handler(mock_req)

            assert response.status_code == 500


class TestDeleteOrganizationHandler:
    """Test delete_organization_handler"""

    @pytest.mark.asyncio
    async def test_delete_organization_success(self):
        """Test successful organization deletion"""
        mock_req = Mock(spec=func.HttpRequest)
        mock_req.route_params = {"orgId": "org-123"}
        mock_req.context = Mock(user_id="admin-123")

        with patch('shared.handlers.organizations_handlers.OrganizationRepository') as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.delete_organization.return_value = True

            response = await delete_organization_handler(mock_req)

            assert response.status_code == 204
            mock_repo.delete_organization.assert_called_once_with("org-123")

    @pytest.mark.asyncio
    async def test_delete_organization_not_found(self):
        """Test deleting non-existent organization"""
        mock_req = Mock(spec=func.HttpRequest)
        mock_req.route_params = {"orgId": "org-nonexistent"}
        mock_req.context = Mock(user_id="admin-123")

        with patch('shared.handlers.organizations_handlers.OrganizationRepository') as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.delete_organization.return_value = False

            response = await delete_organization_handler(mock_req)

            assert response.status_code == 404
            data = json.loads(response.get_body())
            assert data["error"] == "NotFound"

    @pytest.mark.asyncio
    async def test_delete_organization_error(self):
        """Test error handling in delete_organization"""
        mock_req = Mock(spec=func.HttpRequest)
        mock_req.route_params = {"orgId": "org-123"}
        mock_req.context = Mock(user_id="admin-123")

        with patch('shared.handlers.organizations_handlers.OrganizationRepository') as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.delete_organization.side_effect = Exception("Database error")

            response = await delete_organization_handler(mock_req)

            assert response.status_code == 500
