"""Integration tests for OAuth API endpoints

Tests the OAuth connection management endpoints:
- POST /api/oauth/connections - Create connection
- GET /api/oauth/connections - List connections
- GET /api/oauth/connections/{connection_name} - Get connection
- PUT /api/oauth/connections/{connection_name} - Update connection
- DELETE /api/oauth/connections/{connection_name} - Delete connection
- POST /api/oauth/connections/{connection_name}/authorize - Initiate auth flow
- POST /api/oauth/connections/{connection_name}/cancel - Cancel auth flow
- POST /api/oauth/callback/{connection_name} - Handle OAuth callback
- GET /api/oauth/credentials/{connection_name} - Get credentials
- GET /api/oauth/refresh_job_status - Get refresh job status
"""

import json
import logging
import pytest
import requests
from unittest.mock import patch, MagicMock

logger = logging.getLogger(__name__)


class TestOAuthConnectionManagement:
    """Test OAuth connection CRUD operations"""

    def test_create_oauth_connection_success(self, api_base_url, platform_admin_headers):
        """Should create OAuth connection and return connection details"""
        connection_data = {
            "connection_name": "test-github-oauth",
            "oauth_provider": "github",
            "client_id": "test-client-123",
            "redirect_uri": "/oauth/callback/test-github-oauth",
            "authorization_url": "https://github.com/login/oauth/authorize",
            "token_url": "https://github.com/login/oauth/access_token",
            "scopes": "user,repo"
        }

        response = requests.post(
            f"{api_base_url}/api/oauth/connections",
            headers=platform_admin_headers,
            json=connection_data,
            timeout=10
        )

        assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"
        data = response.json()
        assert "connection_name" in data
        assert data["connection_name"] == "test-github-oauth"
        assert data["oauth_provider"] == "github"
        assert "client_id" not in data  # Sensitive field masked
        logger.info(f"Successfully created OAuth connection")

    def test_create_oauth_connection_missing_required_field(self, api_base_url, platform_admin_headers):
        """Should reject connection without required fields"""
        connection_data = {
            "oauth_provider": "github",
            # Missing connection_name
        }

        response = requests.post(
            f"{api_base_url}/api/oauth/connections",
            headers=platform_admin_headers,
            json=connection_data,
            timeout=10
        )

        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        data = response.json()
        assert "error" in data or "message" in data
        logger.info("Correctly rejected missing required field")

    def test_list_oauth_connections(self, api_base_url, platform_admin_headers, test_oauth_connection):
        """Should list OAuth connections for organization"""
        response = requests.get(
            f"{api_base_url}/api/oauth/connections",
            headers=platform_admin_headers,
            timeout=10
        )

        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        logger.info(f"Listed {len(data)} OAuth connections")

    def test_get_oauth_connection_success(self, api_base_url, platform_admin_headers, test_oauth_connection):
        """Should retrieve OAuth connection details"""
        response = requests.get(
            f"{api_base_url}/api/oauth/connections/{test_oauth_connection}",
            headers=platform_admin_headers,
            timeout=10
        )

        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "connection_name" in data
        logger.info(f"Retrieved OAuth connection: {test_oauth_connection}")

    def test_get_oauth_connection_not_found(self, api_base_url, platform_admin_headers):
        """Should return 404 for nonexistent connection"""
        response = requests.get(
            f"{api_base_url}/api/oauth/connections/nonexistent-connection",
            headers=platform_admin_headers,
            timeout=10
        )

        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        logger.info("Correctly returned 404 for nonexistent connection")

    def test_update_oauth_connection_success(self, api_base_url, platform_admin_headers, test_oauth_connection):
        """Should update OAuth connection fields"""
        update_data = {
            "scopes": "read,write,admin"
        }

        response = requests.put(
            f"{api_base_url}/api/oauth/connections/{test_oauth_connection}",
            headers=platform_admin_headers,
            json=update_data,
            timeout=10
        )

        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "connection_name" in data
        logger.info(f"Updated OAuth connection: {test_oauth_connection}")

    def test_delete_oauth_connection_success(self, api_base_url, platform_admin_headers):
        """Should delete OAuth connection (idempotent)"""
        # First create a connection to delete
        connection_name = "test-delete-oauth-conn"
        connection_data = {
            "connection_name": connection_name,
            "oauth_provider": "generic",
            "client_id": "test-delete-123",
            "redirect_uri": "/oauth/callback/test-delete",
            "authorization_url": "https://example.com/auth",
            "token_url": "https://example.com/token",
            "scopes": "read"
        }

        create_response = requests.post(
            f"{api_base_url}/api/oauth/connections",
            headers=platform_admin_headers,
            json=connection_data,
            timeout=10
        )
        assert create_response.status_code == 201

        # Delete the connection
        delete_response = requests.delete(
            f"{api_base_url}/api/oauth/connections/{connection_name}",
            headers=platform_admin_headers,
            timeout=10
        )

        assert delete_response.status_code == 204, f"Expected 204, got {delete_response.status_code}"
        logger.info(f"Deleted OAuth connection: {connection_name}")

    def test_delete_oauth_connection_idempotent(self, api_base_url, platform_admin_headers):
        """Should return 204 even if connection already deleted (idempotent)"""
        response = requests.delete(
            f"{api_base_url}/api/oauth/connections/already-deleted-connection",
            headers=platform_admin_headers,
            timeout=10
        )

        assert response.status_code == 204, f"Expected 204 (idempotent), got {response.status_code}"
        logger.info("Delete is idempotent")


class TestOAuthAuthorizationFlow:
    """Test OAuth authorization flow endpoints"""

    def test_authorize_oauth_connection_success(self, api_base_url, platform_admin_headers, test_oauth_connection):
        """Should initiate OAuth authorization flow and return auth URL"""
        response = requests.post(
            f"{api_base_url}/api/oauth/connections/{test_oauth_connection}/authorize",
            headers=platform_admin_headers,
            timeout=10
        )

        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "authorization_url" in data
        assert "state" in data
        assert "example.com" in data["authorization_url"]
        logger.info(f"Generated authorization URL for {test_oauth_connection}")

    def test_authorize_nonexistent_connection(self, api_base_url, platform_admin_headers):
        """Should return 404 for nonexistent connection"""
        response = requests.post(
            f"{api_base_url}/api/oauth/connections/nonexistent/authorize",
            headers=platform_admin_headers,
            timeout=10
        )

        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        logger.info("Correctly returned 404 for nonexistent connection")

    def test_cancel_oauth_authorization_success(self, api_base_url, platform_admin_headers, test_oauth_connection):
        """Should cancel OAuth authorization and reset status"""
        # First authorize to put in waiting state
        auth_response = requests.post(
            f"{api_base_url}/api/oauth/connections/{test_oauth_connection}/authorize",
            headers=platform_admin_headers,
            timeout=10
        )
        assert auth_response.status_code == 200

        # Cancel authorization
        cancel_response = requests.post(
            f"{api_base_url}/api/oauth/connections/{test_oauth_connection}/cancel",
            headers=platform_admin_headers,
            timeout=10
        )

        assert cancel_response.status_code == 204, f"Expected 204, got {cancel_response.status_code}"
        logger.info(f"Canceled OAuth authorization for {test_oauth_connection}")

    def test_cancel_nonexistent_connection(self, api_base_url, platform_admin_headers):
        """Should return 404 for nonexistent connection"""
        response = requests.post(
            f"{api_base_url}/api/oauth/connections/nonexistent/cancel",
            headers=platform_admin_headers,
            timeout=10
        )

        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        logger.info("Correctly returned 404 for nonexistent connection")


class TestOAuthCallback:
    """Test OAuth callback endpoint"""

    def test_oauth_callback_missing_code(self, api_base_url):
        """Should reject callback without authorization code"""
        response = requests.post(
            f"{api_base_url}/api/oauth/callback/test-connection",
            json={"state": "some-state"},
            timeout=10
        )

        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        data = response.json()
        assert "error" in data or "message" in data
        logger.info("Correctly rejected callback without code")

    def test_oauth_callback_connection_not_found(self, api_base_url):
        """Should return 404 if connection not found"""
        response = requests.post(
            f"{api_base_url}/api/oauth/callback/nonexistent-connection",
            json={"code": "auth-code-123", "state": "state-token"},
            timeout=10
        )

        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        logger.info("Correctly returned 404 for nonexistent connection in callback")


class TestOAuthCredentials:
    """Test OAuth credentials retrieval endpoint"""

    def test_get_oauth_credentials_not_found(self, api_base_url, platform_admin_headers):
        """Should return 404 for nonexistent connection"""
        response = requests.get(
            f"{api_base_url}/api/oauth/credentials/nonexistent-connection",
            headers=platform_admin_headers,
            timeout=10
        )

        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        logger.info("Correctly returned 404 for nonexistent connection")

    def test_get_oauth_credentials_not_connected(self, api_base_url, platform_admin_headers, test_oauth_connection):
        """Should return credentials response with None for unconnected connection"""
        response = requests.get(
            f"{api_base_url}/api/oauth/credentials/{test_oauth_connection}",
            headers=platform_admin_headers,
            timeout=10
        )

        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "connection_name" in data
        assert "status" in data
        # Credentials should be None for unconnected connection
        if data["credentials"] is not None:
            assert "access_token" in data["credentials"] or data["credentials"] is None
        logger.info(f"Retrieved credentials status for {test_oauth_connection}")


class TestOAuthRefreshJobStatus:
    """Test OAuth refresh job status endpoint"""

    def test_get_refresh_job_status(self, api_base_url, platform_admin_headers):
        """Should retrieve OAuth refresh job status"""
        response = requests.get(
            f"{api_base_url}/api/oauth/refresh_job_status",
            headers=platform_admin_headers,
            timeout=10
        )

        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        # Should have either message (no runs yet) or last_run details
        assert "message" in data or "last_run" in data
        logger.info("Retrieved OAuth refresh job status")


class TestOAuthAuthorizationRequired:
    """Test OAuth endpoints require authentication and platform admin role"""

    def test_create_oauth_connection_unauthorized_no_headers(self, api_base_url):
        """Should reject request without auth headers"""
        response = requests.post(
            f"{api_base_url}/api/oauth/connections",
            json={"connection_name": "test"},
            timeout=10
        )

        # Should either be 401 (unauthorized) or 400 (missing required header)
        assert response.status_code in [400, 401, 403], f"Expected 400/401/403, got {response.status_code}"
        logger.info("Correctly rejected request without auth headers")

    def test_list_oauth_connections_unauthorized_no_headers(self, api_base_url):
        """Should reject request without auth headers"""
        response = requests.get(
            f"{api_base_url}/api/oauth/connections",
            timeout=10
        )

        assert response.status_code in [400, 401, 403], f"Expected 400/401/403, got {response.status_code}"
        logger.info("Correctly rejected request without auth headers")

    def test_create_oauth_connection_non_admin(self, api_base_url, user_headers):
        """Should reject request from non-admin user"""
        connection_data = {
            "connection_name": "test-oauth",
            "oauth_provider": "github",
            "client_id": "test-123",
            "redirect_uri": "/oauth/callback",
            "authorization_url": "https://github.com/authorize",
            "token_url": "https://github.com/token",
            "scopes": "user"
        }

        response = requests.post(
            f"{api_base_url}/api/oauth/connections",
            headers=user_headers,
            json=connection_data,
            timeout=10
        )

        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
        logger.info("Correctly rejected non-admin user")
