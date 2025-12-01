"""
Unit tests for org_config_handlers
Tests config and integration management business logic
"""

import json
import pytest
from unittest.mock import AsyncMock, Mock, patch

import azure.functions as func

from shared.handlers.org_config_handlers import (
    delete_config_handler,
    delete_integration_handler,
    get_config_handler,
    get_integrations_handler,
    mask_sensitive_value,
    set_config_handler,
    set_integration_handler,
)
from shared.models import IntegrationType


class TestMaskSensitiveValue:
    """Test sensitive value masking"""

    def test_mask_password_key(self):
        """Test masking values for password keys"""
        result = mask_sensitive_value("db_password", "super_secret_123", "string")
        assert result == "supe***_123"
        assert "secret" not in result

    def test_mask_token_key(self):
        """Test masking values for token keys"""
        result = mask_sensitive_value("api_token", "abc123defghijk456", "string")
        assert result == "abc1***k456"

    def test_mask_secret_key(self):
        """Test masking values for secret keys"""
        result = mask_sensitive_value("oauth_client_secret", "mysecretvalue", "string")
        assert result == "myse***alue"

    def test_no_mask_secret_ref(self):
        """Test that secret_ref types are not masked"""
        result = mask_sensitive_value("config_secret_ref", "keyvault-secret-name", "secret_ref")
        assert result == "keyvault-secret-name"

    def test_mask_short_value(self):
        """Test masking short sensitive values"""
        result = mask_sensitive_value("key", "short", "string")
        assert result == "***"

    def test_no_mask_non_sensitive(self):
        """Test non-sensitive keys are not masked"""
        result = mask_sensitive_value("feature_flag", "true", "string")
        assert result == "true"


class TestGetConfigHandler:
    """Test get_config_handler"""

    @pytest.mark.asyncio
    async def test_get_config_error(self):
        """Test error handling in get_config"""
        mock_req = Mock(spec=func.HttpRequest)
        mock_req.context = Mock(user_id="user-123", scope="org-123")

        with patch('shared.handlers.org_config_handlers.ConfigRepository') as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.list_config.side_effect = Exception("Database error")

            response = await get_config_handler(mock_req)

            assert response.status_code == 500
            data = json.loads(response.get_body())
            assert data["error"] == "InternalServerError"


class TestSetConfigHandler:
    """Test set_config_handler"""

    @pytest.mark.asyncio
    async def test_set_config_json_parse_error(self):
        """Test JSON parsing error"""
        mock_req = Mock(spec=func.HttpRequest)
        mock_req.get_json.side_effect = ValueError("Invalid JSON")
        mock_req.context = Mock(user_id="user-123", scope="org-123")

        response = await set_config_handler(mock_req)

        assert response.status_code == 400
        data = json.loads(response.get_body())
        assert data["error"] == "BadRequest"


class TestDeleteConfigHandler:
    """Test delete_config_handler"""

    @pytest.mark.asyncio
    async def test_delete_config_success(self):
        """Test successful config deletion"""
        mock_req = Mock(spec=func.HttpRequest)
        mock_req.route_params = {"key": "api_endpoint"}
        mock_req.context = Mock(user_id="user-123", scope="org-123")

        with patch('shared.handlers.org_config_handlers.ConfigRepository') as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.delete_config = AsyncMock(return_value=True)

            response = await delete_config_handler(mock_req)

            assert response.status_code == 204
            mock_repo.delete_config.assert_called_once_with("api_endpoint")


    @pytest.mark.asyncio
    async def test_delete_config_error(self):
        """Test error handling in delete_config"""
        mock_req = Mock(spec=func.HttpRequest)
        mock_req.route_params = {"key": "api_endpoint"}
        mock_req.context = Mock(user_id="user-123", scope="org-123")

        with patch('shared.handlers.org_config_handlers.ConfigRepository') as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.delete_config.side_effect = Exception("Database error")

            response = await delete_config_handler(mock_req)

            assert response.status_code == 500


class TestGetIntegrationsHandler:
    """Test get_integrations_handler"""

    @pytest.mark.asyncio
    async def test_get_integrations_success(self):
        """Test successful integrations retrieval"""
        mock_req = Mock(spec=func.HttpRequest)
        mock_req.route_params = {"orgId": "org-123"}
        mock_req.context = Mock(user_id="user-123", scope="org-123")

        integrations = [
            Mock(type=IntegrationType.MSGRAPH, model_dump=Mock(return_value={"type": "msgraph"})),
            Mock(type=IntegrationType.HALOPSA, model_dump=Mock(return_value={"type": "halopsa"})),
        ]

        with patch('shared.handlers.org_config_handlers.ConfigRepository') as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.list_integrations = AsyncMock(return_value=integrations)

            response = await get_integrations_handler(mock_req)

            assert response.status_code == 200
            data = json.loads(response.get_body())
            assert len(data) == 2

    @pytest.mark.asyncio
    async def test_get_integrations_empty(self):
        """Test getting integrations when none exist"""
        mock_req = Mock(spec=func.HttpRequest)
        mock_req.route_params = {"orgId": "org-123"}
        mock_req.context = Mock(user_id="user-123", scope="org-123")

        with patch('shared.handlers.org_config_handlers.ConfigRepository') as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.list_integrations = AsyncMock(return_value=[])

            response = await get_integrations_handler(mock_req)

            assert response.status_code == 200
            data = json.loads(response.get_body())
            assert data == []

    @pytest.mark.asyncio
    async def test_get_integrations_error(self):
        """Test error handling in get_integrations"""
        mock_req = Mock(spec=func.HttpRequest)
        mock_req.route_params = {"orgId": "org-123"}
        mock_req.context = Mock(user_id="user-123", scope="org-123")

        with patch('shared.handlers.org_config_handlers.ConfigRepository') as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.list_integrations.side_effect = Exception("Database error")

            response = await get_integrations_handler(mock_req)

            assert response.status_code == 500


class TestSetIntegrationHandler:
    """Test set_integration_handler"""

    @pytest.mark.asyncio
    async def test_set_integration_json_error(self):
        """Test JSON parsing error in set_integration"""
        mock_req = Mock(spec=func.HttpRequest)
        mock_req.get_json.side_effect = ValueError("Invalid JSON")
        mock_req.route_params = {"orgId": "org-123"}
        mock_req.context = Mock(user_id="user-123", scope="org-123")

        response = await set_integration_handler(mock_req)

        assert response.status_code == 400
        data = json.loads(response.get_body())
        assert data["error"] == "BadRequest"


class TestDeleteIntegrationHandler:
    """Test delete_integration_handler"""

    @pytest.mark.asyncio
    async def test_delete_integration_success(self):
        """Test successful integration deletion"""
        mock_req = Mock(spec=func.HttpRequest)
        mock_req.route_params = {"orgId": "org-123", "type": "msgraph"}
        mock_req.context = Mock(user_id="user-123", scope="org-123")

        with patch('shared.handlers.org_config_handlers.ConfigRepository') as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.delete_integration = AsyncMock(return_value=True)

            response = await delete_integration_handler(mock_req)

            assert response.status_code == 204

    @pytest.mark.asyncio
    async def test_delete_integration_error(self):
        """Test error handling in delete_integration"""
        mock_req = Mock(spec=func.HttpRequest)
        mock_req.route_params = {"orgId": "org-123", "type": "msgraph"}
        mock_req.context = Mock(user_id="user-123", scope="org-123")

        with patch('shared.handlers.org_config_handlers.ConfigRepository') as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.delete_integration.side_effect = Exception("Database error")

            response = await delete_integration_handler(mock_req)

            assert response.status_code == 500
