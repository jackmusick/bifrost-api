"""
Integration tests for OAuth API
Tests OAuth connection CRUD operations by calling Azure Functions directly (no HTTP)
"""

import pytest

from functions.oauth_api import (
    create_oauth_connection,
    delete_oauth_connection,
    get_oauth_connection,
    get_oauth_credentials,
    list_oauth_connections,
    update_oauth_connection,
)
from tests.helpers.http_helpers import (
    create_mock_request,
    create_org_user_headers,
    create_platform_admin_headers,
    parse_response,
)


class TestOAuthConnectionsIntegration:
    """Test OAuth connection CRUD operations"""

    @pytest.mark.asyncio
    async def test_list_oauth_connections_as_org_user(self):
        """Org user cannot list OAuth connections (platform admin only)"""
        req = create_mock_request(
            method="GET",
            url="/api/oauth/connections",
            headers=create_org_user_headers(),
        )

        response = await list_oauth_connections(req)
        status, body = parse_response(response)

        # Should return 403 (forbidden) - OAuth connections are platform admin only
        assert status == 403

    @pytest.mark.asyncio
    async def test_create_oauth_connection_as_platform_admin(self):
        """Platform admin can create OAuth connections"""
        req = create_mock_request(
            method="POST",
            url="/api/oauth/connections",
            headers=create_platform_admin_headers(),
            body={
                "connection_name": "test_oauth_connection_integration",
                "description": "Test OAuth connection for integration testing",
                "oauth_flow_type": "authorization_code",
                "authorization_url": "https://accounts.google.com/o/oauth2/v2/auth",
                "token_url": "https://oauth2.googleapis.com/token",
                "scopes": "https://www.googleapis.com/auth/userinfo.profile",
                "client_id": "test-client-id-12345",
                "client_secret_value": "test-secret-value-xyz",
                "redirect_uri": "/oauth/callback/test_oauth_connection_integration",
            },
        )

        response = await create_oauth_connection(req)
        status, body = parse_response(response)

        # May return 201 (created) or 409 (already exists from previous runs)
        assert status in [201, 409]

        if status == 201:
            assert body is not None
            assert body["connection_name"] == "test_oauth_connection_integration"
            assert body["status"] == "not_connected"
            assert body["oauth_flow_type"] == "authorization_code"
            # client_secret should be masked in response
            assert "client_secret_value" not in body

    @pytest.mark.asyncio
    async def test_get_oauth_connection_by_name_as_org_user(self):
        """Org user cannot get OAuth connection by name (platform admin only)"""
        # First create a connection to ensure we have one to test with
        create_req = create_mock_request(
            method="POST",
            url="/api/oauth/connections",
            headers=create_platform_admin_headers(),
            body={
                "connection_name": "test_get_by_name_connection",
                "oauth_flow_type": "authorization_code",
                "authorization_url": "https://test.example.com/auth",
                "token_url": "https://test.example.com/token",
                "scopes": "read",
                "client_id": "test-client",
                "client_secret_value": "test-secret",
                "redirect_uri": "/oauth/callback/test_get_by_name_connection",
            },
        )

        create_response = await create_oauth_connection(create_req)
        create_status, _ = parse_response(create_response)

        # Should succeed (201) or already exist (409)
        assert create_status in [
            201, 409], f"Failed to create OAuth connection: {create_status}"

        # Try to get specific connection as org user (should fail)
        get_req = create_mock_request(
            method="GET",
            url="/api/oauth/connections/test_get_by_name_connection",
            headers=create_org_user_headers(),
            route_params={"connection_name": "test_get_by_name_connection"},
        )

        response = await get_oauth_connection(get_req)
        status, body = parse_response(response)

        # Should return 403 (forbidden) - OAuth connections are platform admin only
        assert status == 403

    @pytest.mark.asyncio
    async def test_get_nonexistent_oauth_connection_not_found(self):
        """Getting nonexistent OAuth connection returns 404"""
        req = create_mock_request(
            method="GET",
            url="/api/oauth/connections/nonexistent_connection",
            headers=create_platform_admin_headers(),
            route_params={"connection_name": "nonexistent_connection"},
        )

        response = await get_oauth_connection(req)
        status, body = parse_response(response)

        assert status == 404
        assert body["error"] == "NotFound"

    @pytest.mark.asyncio
    async def test_update_oauth_connection(self):
        """Platform admin can update OAuth connections"""
        # First create a connection to update
        create_req = create_mock_request(
            method="POST",
            url="/api/oauth/connections",
            headers=create_platform_admin_headers(),
            body={
                "connection_name": "test_update_connection_integration",
                "description": "Original description",
                "oauth_flow_type": "authorization_code",
                "authorization_url": "https://test.example.com/auth",
                "token_url": "https://test.example.com/token",
                "scopes": "read",
                "client_id": "test-client",
                "client_secret_value": "test-secret",
                "redirect_uri": "/oauth/callback/test_update_connection_integration",
            },
        )

        create_response = await create_oauth_connection(create_req)
        create_status, _ = parse_response(create_response)

        # May already exist from previous runs
        assert create_status in [201, 409]

        # Update it
        update_req = create_mock_request(
            method="PUT",
            url="/api/oauth/connections/test_update_connection_integration",
            headers=create_platform_admin_headers(),
            route_params={
                "connection_name": "test_update_connection_integration"},
            body={"description": "Updated description for integration testing"},
        )

        response = await update_oauth_connection(update_req)
        status, body = parse_response(response)

        assert status == 200
        assert body["connection_name"] == "test_update_connection_integration"

    @pytest.mark.asyncio
    async def test_delete_oauth_connection(self):
        """Platform admin can delete OAuth connections"""
        # First create a connection to delete
        create_req = create_mock_request(
            method="POST",
            url="/api/oauth/connections",
            headers=create_platform_admin_headers(),
            body={
                "connection_name": "test_delete_connection_integration",
                "oauth_flow_type": "authorization_code",
                "authorization_url": "https://test.example.com/auth",
                "token_url": "https://test.example.com/token",
                "scopes": "read",
                "client_id": "test-client",
                "client_secret_value": "test-secret",
                "redirect_uri": "/oauth/callback/test_delete_connection_integration",
            },
        )

        await create_oauth_connection(create_req)

        # Delete it (idempotent)
        delete_req = create_mock_request(
            method="DELETE",
            url="/api/oauth/connections/test_delete_connection_integration",
            headers=create_platform_admin_headers(),
            route_params={
                "connection_name": "test_delete_connection_integration"},
        )

        response = await delete_oauth_connection(delete_req)
        status, _ = parse_response(response)

        assert status == 204

        # Verify it's gone
        get_req = create_mock_request(
            method="GET",
            url="/api/oauth/connections/test_delete_connection_integration",
            headers=create_platform_admin_headers(),
            route_params={
                "connection_name": "test_delete_connection_integration"},
        )

        response = await get_oauth_connection(get_req)
        status, _ = parse_response(response)
        assert status == 404

    @pytest.mark.asyncio
    async def test_create_oauth_connection_validation_error(self):
        """Creating OAuth connection without required fields returns 400"""
        req = create_mock_request(
            method="POST",
            url="/api/oauth/connections",
            headers=create_platform_admin_headers(),
            body={
                "connection_name": "incomplete_connection"
                # Missing: oauth_flow_type, urls, scopes, etc.
            },
        )

        response = await create_oauth_connection(req)
        status, body = parse_response(response)

        assert status == 400
        assert body["error"] == "ValidationError"

    @pytest.mark.asyncio
    async def test_create_duplicate_oauth_connection_conflict(self):
        """Creating duplicate OAuth connection returns 409"""
        connection_data = {
            "connection_name": "duplicate_connection_test_integration",
            "oauth_flow_type": "authorization_code",
            "authorization_url": "https://test.example.com/auth",
            "token_url": "https://test.example.com/token",
            "scopes": "read",
            "client_id": "test-client",
            "client_secret_value": "test-secret",
            "redirect_uri": "/oauth/callback/duplicate_connection_test_integration",
        }

        # First creation
        first_req = create_mock_request(
            method="POST",
            url="/api/oauth/connections",
            headers=create_platform_admin_headers(),
            body=connection_data,
        )

        first_response = await create_oauth_connection(first_req)
        first_status, _ = parse_response(first_response)

        # Should succeed (201) or already exist (409)
        assert first_status in [201, 409]

        # Second creation with same name
        second_req = create_mock_request(
            method="POST",
            url="/api/oauth/connections",
            headers=create_platform_admin_headers(),
            body=connection_data,
        )

        second_response = await create_oauth_connection(second_req)
        second_status, body = parse_response(second_response)

        assert second_status == 409
        assert body["error"] == "Conflict"


class TestOAuthCredentialsIntegration:
    """Test OAuth credentials retrieval"""

    @pytest.mark.asyncio
    async def test_get_oauth_credentials_not_connected(self):
        """
        Getting credentials for not_connected connection returns null credentials.

        This test verifies the API behavior for connections that haven't
        completed OAuth authorization yet.
        """
        # Create a connection (will be in not_connected status)
        create_req = create_mock_request(
            method="POST",
            url="/api/oauth/connections",
            headers=create_platform_admin_headers(),
            body={
                "connection_name": "test_credentials_not_connected",
                "oauth_flow_type": "authorization_code",
                "authorization_url": "https://test.example.com/auth",
                "token_url": "https://test.example.com/token",
                "scopes": "read",
                "client_id": "test-client",
                "client_secret_value": "test-secret",
                "redirect_uri": "/oauth/callback/test_credentials_not_connected",
            },
        )

        create_response = await create_oauth_connection(create_req)
        create_status, _ = parse_response(create_response)

        # May already exist
        assert create_status in [201, 409]

        # Try to get credentials (should return null credentials)
        credentials_req = create_mock_request(
            method="GET",
            url="/api/oauth/credentials/test_credentials_not_connected",
            headers=create_platform_admin_headers(),
            route_params={"connection_name": "test_credentials_not_connected"},
        )

        response = await get_oauth_credentials(credentials_req)
        status, body = parse_response(response)

        assert status == 200
        assert body["status"] == "not_connected"
        assert body["credentials"] is None

    @pytest.mark.asyncio
    async def test_get_oauth_credentials_nonexistent_connection(self):
        """Getting credentials for nonexistent connection returns 404"""
        req = create_mock_request(
            method="GET",
            url="/api/oauth/credentials/nonexistent_connection",
            headers=create_platform_admin_headers(),
            route_params={"connection_name": "nonexistent_connection"},
        )

        response = await get_oauth_credentials(req)
        status, body = parse_response(response)

        assert status == 404
        assert body["error"] == "NotFound"
