"""
Unit tests for OAuth handlers.
Tests handler business logic with mocked services.
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from azure.functions import HttpRequest, HttpResponse
from pydantic import ValidationError

from shared.handlers.oauth_handlers import (
    create_oauth_connection_handler,
    list_oauth_connections_handler,
    get_oauth_connection_handler,
    update_oauth_connection_handler,
    delete_oauth_connection_handler,
    authorize_oauth_connection_handler,
    cancel_oauth_authorization_handler,
    refresh_oauth_token_handler,
    oauth_callback_handler,
    get_oauth_credentials_handler,
    get_oauth_refresh_job_status_handler,
)
from shared.models import ErrorResponse


@pytest.fixture
def mock_request_context():
    """Mock request context."""
    context = MagicMock()
    context.scope = "org-123"
    context.email = "user@example.com"
    context.user_id = "user-123"
    return context


@pytest.fixture
def mock_http_request(mock_request_context):
    """Create a mock HTTP request."""
    request = MagicMock(spec=HttpRequest)

    def get_json_side_effect():
        return {}

    request.get_json = MagicMock(side_effect=get_json_side_effect)
    return request


@pytest.mark.asyncio
async def test_create_oauth_connection_validation_error(mock_http_request, mock_request_context):
    """Test OAuth connection creation with validation error."""
    mock_http_request.get_json.return_value = {}  # Invalid: missing required fields

    with patch("shared.handlers.oauth_handlers.get_context", return_value=mock_request_context):
        with patch("shared.handlers.oauth_handlers.OAuthStorageService") as mock_service:
            mock_instance = AsyncMock()
            mock_service.return_value = mock_instance

            response = await create_oauth_connection_handler(mock_http_request)

            assert response.status_code == 400
            data = json.loads(response.get_body())
            assert data["error"] == "ValidationError"


@pytest.mark.asyncio
async def test_create_oauth_connection_json_error(mock_http_request, mock_request_context):
    """Test OAuth connection creation with JSON parse error."""
    mock_http_request.get_json.side_effect = ValueError("Invalid JSON")

    with patch("shared.handlers.oauth_handlers.get_context", return_value=mock_request_context):
        with patch("shared.handlers.oauth_handlers.OAuthStorageService") as mock_service:
            mock_instance = AsyncMock()
            mock_service.return_value = mock_instance

            response = await create_oauth_connection_handler(mock_http_request)

            assert response.status_code == 400
            data = json.loads(response.get_body())
            assert data["error"] == "BadRequest"


@pytest.mark.asyncio
async def test_list_oauth_connections_success(mock_http_request, mock_request_context):
    """Test listing OAuth connections."""
    mock_connections = [MagicMock(), MagicMock()]
    for conn in mock_connections:
        conn.to_detail.return_value.model_dump.return_value = {"name": "conn"}

    with patch("shared.handlers.oauth_handlers.get_context", return_value=mock_request_context):
        with patch("shared.handlers.oauth_handlers.OAuthStorageService") as mock_service:
            mock_instance = AsyncMock()
            mock_instance.list_connections.return_value = mock_connections
            mock_service.return_value = mock_instance

            response = await list_oauth_connections_handler(mock_http_request)

            assert response.status_code == 200
            data = json.loads(response.get_body())
            assert len(data) == 2


@pytest.mark.asyncio
async def test_get_oauth_connection_success(mock_http_request, mock_request_context):
    """Test getting a specific OAuth connection."""
    mock_connection = MagicMock()
    mock_connection.to_detail.return_value.model_dump.return_value = {
        "name": "test-connection"
    }

    with patch("shared.handlers.oauth_handlers.get_context", return_value=mock_request_context):
        with patch("shared.handlers.oauth_handlers.get_route_param", return_value="test-connection"):
            with patch("shared.handlers.oauth_handlers.OAuthStorageService") as mock_service:
                mock_instance = AsyncMock()
                mock_instance.get_connection.return_value = mock_connection
                mock_service.return_value = mock_instance

                response = await get_oauth_connection_handler(mock_http_request)

                assert response.status_code == 200
                data = json.loads(response.get_body())
                assert data["name"] == "test-connection"


@pytest.mark.asyncio
async def test_get_oauth_connection_not_found(mock_http_request, mock_request_context):
    """Test getting non-existent OAuth connection."""
    with patch("shared.handlers.oauth_handlers.get_context", return_value=mock_request_context):
        with patch("shared.handlers.oauth_handlers.get_route_param", return_value="nonexistent"):
            with patch("shared.handlers.oauth_handlers.OAuthStorageService") as mock_service:
                mock_instance = AsyncMock()
                mock_instance.get_connection.return_value = None
                mock_service.return_value = mock_instance

                response = await get_oauth_connection_handler(mock_http_request)

                assert response.status_code == 404
                data = json.loads(response.get_body())
                assert data["error"] == "NotFound"


@pytest.mark.asyncio
async def test_update_oauth_connection_success(mock_http_request, mock_request_context):
    """Test updating OAuth connection."""
    request_data = {"provider": "oauth2_updated"}
    mock_http_request.get_json.return_value = request_data

    mock_connection = MagicMock()
    mock_updated = MagicMock()
    mock_updated.to_detail.return_value.model_dump.return_value = {
        "name": "test-connection",
        "provider": "oauth2_updated"
    }

    with patch("shared.handlers.oauth_handlers.get_context", return_value=mock_request_context):
        with patch("shared.handlers.oauth_handlers.get_route_param", return_value="test-connection"):
            with patch("shared.handlers.oauth_handlers.OAuthStorageService") as mock_service:
                mock_instance = AsyncMock()
                mock_instance.get_connection.return_value = mock_connection
                mock_instance.update_connection.return_value = mock_updated
                mock_service.return_value = mock_instance

                response = await update_oauth_connection_handler(mock_http_request)

                assert response.status_code == 200
                data = json.loads(response.get_body())
                assert data["provider"] == "oauth2_updated"


@pytest.mark.asyncio
async def test_delete_oauth_connection_success(mock_http_request, mock_request_context):
    """Test deleting OAuth connection."""
    mock_connection = MagicMock()

    with patch("shared.handlers.oauth_handlers.get_context", return_value=mock_request_context):
        with patch("shared.handlers.oauth_handlers.get_route_param", return_value="test-connection"):
            with patch("shared.handlers.oauth_handlers.OAuthStorageService") as mock_service:
                mock_instance = AsyncMock()
                mock_instance.get_connection.return_value = mock_connection
                mock_instance.delete_connection.return_value = None
                mock_service.return_value = mock_instance

                response = await delete_oauth_connection_handler(mock_http_request)

                # 204 No Content - successful delete with no response body
                assert response.status_code == 204


@pytest.mark.asyncio
async def test_authorize_oauth_connection_success(mock_http_request, mock_request_context):
    """Test authorizing OAuth connection."""
    mock_connection = MagicMock()

    with patch("shared.handlers.oauth_handlers.get_context", return_value=mock_request_context):
        with patch("shared.handlers.oauth_handlers.get_route_param", return_value="test-connection"):
            with patch("shared.handlers.oauth_handlers.OAuthStorageService") as mock_service:
                with patch("shared.handlers.oauth_handlers.OAuthProviderClient") as mock_provider:
                    mock_instance = AsyncMock()
                    mock_instance.get_connection.return_value = mock_connection
                    mock_service.return_value = mock_instance

                    mock_provider_instance = AsyncMock()
                    mock_provider_instance.get_authorization_url.return_value = "https://auth.example.com"
                    mock_provider.return_value = mock_provider_instance

                    response = await authorize_oauth_connection_handler(mock_http_request)

                    assert response.status_code == 200
                    data = json.loads(response.get_body())
                    assert "authorization_url" in data


@pytest.mark.asyncio
async def test_cancel_oauth_authorization_success(mock_http_request, mock_request_context):
    """Test canceling OAuth authorization."""
    mock_connection = MagicMock()

    with patch("shared.handlers.oauth_handlers.get_context", return_value=mock_request_context):
        with patch("shared.handlers.oauth_handlers.get_route_param", return_value="test-connection"):
            with patch("shared.handlers.oauth_handlers.OAuthStorageService") as mock_service:
                mock_instance = AsyncMock()
                mock_instance.get_connection.return_value = mock_connection
                mock_instance.cancel_authorization.return_value = None
                mock_service.return_value = mock_instance

                response = await cancel_oauth_authorization_handler(mock_http_request)

                assert response.status_code == 200
                data = json.loads(response.get_body())
                assert data["message"] == "Authorization canceled"


@pytest.mark.asyncio
async def test_refresh_oauth_token_success(mock_http_request, mock_request_context):
    """Test refreshing OAuth token."""
    mock_connection = MagicMock()

    with patch("shared.handlers.oauth_handlers.get_context", return_value=mock_request_context):
        with patch("shared.handlers.oauth_handlers.get_route_param", return_value="test-connection"):
            with patch("shared.handlers.oauth_handlers.OAuthStorageService") as mock_service:
                mock_instance = AsyncMock()
                mock_instance.get_connection.return_value = mock_connection
                mock_instance.refresh_token.return_value = True
                mock_service.return_value = mock_instance

                response = await refresh_oauth_token_handler(mock_http_request)

                assert response.status_code == 200
                data = json.loads(response.get_body())
                assert data["message"] == "Token refreshed"


@pytest.mark.asyncio
async def test_oauth_callback_validation_error(mock_http_request):
    """Test OAuth callback with validation error."""
    mock_http_request.get_json.return_value = {}  # Invalid: missing required fields

    response = await oauth_callback_handler(mock_http_request)

    assert response.status_code == 400
    data = json.loads(response.get_body())
    assert data["error"] == "ValidationError"


@pytest.mark.asyncio
async def test_get_oauth_credentials_not_found(mock_http_request, mock_request_context):
    """Test getting OAuth credentials when connection not found."""
    with patch("shared.handlers.oauth_handlers.get_context", return_value=mock_request_context):
        with patch("shared.handlers.oauth_handlers.get_route_param", return_value="nonexistent"):
            with patch("shared.handlers.oauth_handlers.OAuthStorageService") as mock_service:
                mock_instance = AsyncMock()
                mock_instance.get_connection.return_value = None
                mock_service.return_value = mock_instance

                response = await get_oauth_credentials_handler(mock_http_request)

                assert response.status_code == 404
                data = json.loads(response.get_body())
                assert data["error"] == "NotFound"


@pytest.mark.asyncio
async def test_get_oauth_refresh_job_status_success(mock_http_request, mock_request_context):
    """Test getting refresh job status (simplified implementation)."""
    with patch("shared.handlers.oauth_handlers.get_context", return_value=mock_request_context):
        response = await get_oauth_refresh_job_status_handler(mock_http_request)

        assert response.status_code == 200
        data = json.loads(response.get_body())
        # Simplified handler returns a message
        assert "message" in data
