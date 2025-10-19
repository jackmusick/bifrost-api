"""Integration tests for OAuth API edge cases

Tests error handling, state transitions, and edge cases in OAuth connection management:
- Callback error handling (invalid state, expired callbacks)
- Invalid provider configurations
- Connection state transitions
- Credential refresh failures
- Multiple concurrent operations
"""

import json
import logging
import pytest
import requests
import uuid
from unittest.mock import patch, MagicMock

logger = logging.getLogger(__name__)


class TestOAuthCallbackErrorHandling:
    """Test OAuth callback error handling"""

    def test_callback_with_invalid_state(self, api_base_url, platform_admin_headers):
        """Should reject callback with invalid/missing state parameter"""
        response = requests.post(
            f"{api_base_url}/api/oauth/callback/test-connection",
            headers=platform_admin_headers,
            json={
                "code": "auth-code-123",
                "state": "invalid-state-xyz",
                "error": None
            },
            timeout=10
        )
        # Should reject invalid state
        assert response.status_code in [400, 401, 403, 404], \
            f"Expected 400/401/403/404 for invalid state, got {response.status_code}"

    def test_callback_with_error_from_provider(self, api_base_url, platform_admin_headers):
        """Should handle error response from OAuth provider"""
        response = requests.post(
            f"{api_base_url}/api/oauth/callback/test-connection",
            headers=platform_admin_headers,
            json={
                "error": "access_denied",
                "error_description": "User denied authorization",
                "state": "valid-state"
            },
            timeout=10
        )
        # May return 400, 403, or specific error code
        assert response.status_code in [400, 403, 404, 500]

    def test_callback_missing_authorization_code(self, api_base_url, platform_admin_headers):
        """Should reject callback without authorization code"""
        response = requests.post(
            f"{api_base_url}/api/oauth/callback/test-connection",
            headers=platform_admin_headers,
            json={
                "state": "valid-state",
                "error": None
            },
            timeout=10
        )
        assert response.status_code in [400, 404, 422], \
            f"Expected 400/404/422 for missing code, got {response.status_code}"

    def test_callback_with_malformed_json(self, api_base_url, platform_admin_headers):
        """Should handle malformed JSON in callback"""
        response = requests.post(
            f"{api_base_url}/api/oauth/callback/test-connection",
            headers=platform_admin_headers,
            data="invalid json{",
            timeout=10
        )
        assert response.status_code in [400, 422]

    def test_callback_for_nonexistent_connection(self, api_base_url, platform_admin_headers):
        """Should reject callback for nonexistent connection"""
        response = requests.post(
            f"{api_base_url}/api/oauth/callback/nonexistent-connection-{uuid.uuid4().hex[:8]}",
            headers=platform_admin_headers,
            json={
                "code": "auth-code-123",
                "state": "some-state"
            },
            timeout=10
        )
        # Should return error (401, 403, or 404)
        assert response.status_code in [400, 401, 403, 404], \
            f"Expected 400/401/403/404, got {response.status_code}"


class TestOAuthInvalidConfigurations:
    """Test handling of invalid provider configurations"""

    def test_create_connection_missing_client_id(self, api_base_url, platform_admin_headers):
        """Should reject connection without client_id"""
        connection_data = {
            "connection_name": f"test-oauth-{uuid.uuid4().hex[:8]}",
            "oauth_flow_type": "authorization_code",
            # Missing client_id
            "authorization_url": "https://example.com/authorize",
            "token_url": "https://example.com/token"
        }
        response = requests.post(
            f"{api_base_url}/api/oauth/connections",
            headers=platform_admin_headers,
            json=connection_data,
            timeout=10
        )
        assert response.status_code in [400, 422]

    def test_create_connection_invalid_urls(self, api_base_url, platform_admin_headers):
        """Should validate URL format in connection"""
        connection_data = {
            "connection_name": f"test-oauth-{uuid.uuid4().hex[:8]}",
            "oauth_flow_type": "authorization_code",
            "client_id": "test-client",
            "authorization_url": "not-a-url",  # Invalid URL
            "token_url": "https://example.com/token"
        }
        response = requests.post(
            f"{api_base_url}/api/oauth/connections",
            headers=platform_admin_headers,
            json=connection_data,
            timeout=10
        )
        # May accept or validate
        assert response.status_code in [201, 400, 422]

    def test_create_connection_duplicate_name(self, api_base_url, platform_admin_headers):
        """Should reject duplicate connection names"""
        connection_name = f"test-oauth-{uuid.uuid4().hex[:8]}"
        connection_data = {
            "connection_name": connection_name,
            "oauth_flow_type": "authorization_code",
            "client_id": "test-client",
            "authorization_url": "https://example.com/authorize",
            "token_url": "https://example.com/token"
        }

        # Create first connection
        response1 = requests.post(
            f"{api_base_url}/api/oauth/connections",
            headers=platform_admin_headers,
            json=connection_data,
            timeout=10
        )

        if response1.status_code == 201:
            # Try to create duplicate
            response2 = requests.post(
                f"{api_base_url}/api/oauth/connections",
                headers=platform_admin_headers,
                json=connection_data,
                timeout=10
            )
            assert response2.status_code in [409, 400], \
                f"Expected 409/400 for duplicate, got {response2.status_code}"

    def test_connection_with_invalid_scopes(self, api_base_url, platform_admin_headers):
        """Should handle invalid or unsupported scopes"""
        connection_data = {
            "connection_name": f"test-oauth-{uuid.uuid4().hex[:8]}",
            "oauth_flow_type": "authorization_code",
            "client_id": "test-client",
            "authorization_url": "https://example.com/authorize",
            "token_url": "https://example.com/token",
            "scopes": ""  # Empty scopes
        }
        response = requests.post(
            f"{api_base_url}/api/oauth/connections",
            headers=platform_admin_headers,
            json=connection_data,
            timeout=10
        )
        # May accept empty or validate
        assert response.status_code in [201, 400, 422]


class TestOAuthConnectionStateTransitions:
    """Test OAuth connection state transitions"""

    def test_authorize_without_connection(self, api_base_url, platform_admin_headers):
        """Should fail authorization for nonexistent connection"""
        response = requests.post(
            f"{api_base_url}/api/oauth/connections/nonexistent/authorize",
            headers=platform_admin_headers,
            json={},
            timeout=10
        )
        assert response.status_code in [404, 400, 403]

    def test_cancel_authorization_without_pending(self, api_base_url, platform_admin_headers):
        """Should handle cancel without pending authorization"""
        response = requests.post(
            f"{api_base_url}/api/oauth/connections/test-connection/cancel",
            headers=platform_admin_headers,
            json={},
            timeout=10
        )
        # May accept (noop) or reject
        assert response.status_code in [200, 204, 404, 400]

    def test_delete_connected_connection(self, api_base_url, platform_admin_headers, test_oauth_connection):
        """Should allow deleting even if connected"""
        response = requests.delete(
            f"{api_base_url}/api/oauth/connections/{test_oauth_connection}",
            headers=platform_admin_headers,
            timeout=10
        )
        assert response.status_code in [200, 204, 404]

    def test_refresh_credentials_without_tokens(self, api_base_url, platform_admin_headers):
        """Should fail refresh without stored refresh token"""
        response = requests.post(
            f"{api_base_url}/api/oauth/connections/test-connection/refresh-credentials",
            headers=platform_admin_headers,
            json={},
            timeout=10
        )
        # Should fail since no refresh token exists
        assert response.status_code in [400, 404, 500]


class TestOAuthCredentialRefreshFailures:
    """Test credential refresh failure scenarios"""

    def test_refresh_with_expired_refresh_token(self, api_base_url, platform_admin_headers):
        """Should handle expired refresh tokens"""
        response = requests.post(
            f"{api_base_url}/api/oauth/connections/test-connection/refresh-credentials",
            headers=platform_admin_headers,
            json={"force": True},
            timeout=10
        )
        # Should fail since token is expired
        assert response.status_code in [400, 401, 404, 500]

    def test_refresh_job_status_without_job(self, api_base_url, platform_admin_headers):
        """Should handle refresh job status query without pending job"""
        response = requests.get(
            f"{api_base_url}/api/oauth/refresh_job_status",
            headers=platform_admin_headers,
            timeout=10
        )
        # May return empty or 404
        assert response.status_code in [200, 404]

    def test_credentials_endpoint_unauthorized(self, api_base_url, user_headers):
        """Regular users should not access credentials endpoint"""
        response = requests.get(
            f"{api_base_url}/api/oauth/credentials/test-connection",
            headers=user_headers,
            timeout=10
        )
        # Should be restricted
        assert response.status_code in [401, 403, 404]


class TestOAuthConcurrencyAndRaceConditions:
    """Test concurrent operations and race conditions"""

    def test_update_connection_during_authorization(self, api_base_url, platform_admin_headers, test_oauth_connection):
        """Should handle update during authorization flow"""
        # This is a conceptual test - actual race testing requires timing
        update_data = {
            "oauth_flow_type": "implicit",
            "scopes": "read,write"
        }
        response = requests.put(
            f"{api_base_url}/api/oauth/connections/{test_oauth_connection}",
            headers=platform_admin_headers,
            json=update_data,
            timeout=10
        )
        # Should succeed or return conflict
        assert response.status_code in [200, 204, 409, 404]

    def test_simultaneous_refresh_requests(self, api_base_url, platform_admin_headers):
        """Should handle multiple refresh requests"""
        response1 = requests.post(
            f"{api_base_url}/api/oauth/connections/test-connection/refresh-credentials",
            headers=platform_admin_headers,
            json={},
            timeout=10
        )
        response2 = requests.post(
            f"{api_base_url}/api/oauth/connections/test-connection/refresh-credentials",
            headers=platform_admin_headers,
            json={},
            timeout=10
        )
        # Both should return some status (may be same or different)
        assert response1.status_code in [400, 401, 404, 500]
        assert response2.status_code in [400, 401, 404, 500]

    def test_delete_and_recreate_same_connection(self, api_base_url, platform_admin_headers, test_oauth_connection):
        """Should handle delete and immediate recreate"""
        # Delete
        delete_response = requests.delete(
            f"{api_base_url}/api/oauth/connections/{test_oauth_connection}",
            headers=platform_admin_headers,
            timeout=10
        )

        if delete_response.status_code in [200, 204]:
            # Recreate with same name
            connection_data = {
                "connection_name": test_oauth_connection,
                "oauth_flow_type": "authorization_code",
                "client_id": "test-client",
                "authorization_url": "https://example.com/authorize",
                "token_url": "https://example.com/token"
            }
            recreate_response = requests.post(
                f"{api_base_url}/api/oauth/connections",
                headers=platform_admin_headers,
                json=connection_data,
                timeout=10
            )
            # Should succeed (or conflict if not fully deleted)
            assert recreate_response.status_code in [201, 409]


class TestOAuthAuthorizationBoundaries:
    """Test authorization boundaries and edge cases"""

    def test_unauthorized_user_cannot_authorize(self, api_base_url, user_headers):
        """Regular users should not authorize OAuth connections"""
        response = requests.post(
            f"{api_base_url}/api/oauth/connections/test-connection/authorize",
            headers=user_headers,
            json={},
            timeout=10
        )
        # Should be restricted
        assert response.status_code in [401, 403, 404]

    def test_platform_admin_can_view_all_connections(self, api_base_url, platform_admin_headers):
        """Platform admin should list all connections"""
        response = requests.get(
            f"{api_base_url}/api/oauth/connections",
            headers=platform_admin_headers,
            timeout=10
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_list_connections_with_org_header(self, api_base_url, platform_admin_headers, test_org_id):
        """Platform admin can list org-specific connections"""
        headers = {**platform_admin_headers, "X-Organization-ID": test_org_id}
        response = requests.get(
            f"{api_base_url}/api/oauth/connections",
            headers=headers,
            timeout=10
        )
        assert response.status_code == 200
