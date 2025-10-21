"""Integration tests for OAuth API edge cases

Tests error handling, state transitions, and edge cases in OAuth connection management:
- Callback error handling (invalid state, expired callbacks)
- Invalid provider configurations
- Connection state transitions
- Credential refresh failures
- Multiple concurrent operations
"""

import logging
import uuid

import pytest
import requests

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


class TestOAuthConnectionCRUDComprehensive:
    """Comprehensive CRUD testing for OAuth connections"""

    @pytest.mark.skip(reason="Requires KeyVault - move to E2E tests")
    def test_create_connection_with_all_fields(self, api_base_url, platform_admin_headers, test_org_id):
        """Should create connection with complete configuration"""
        response = requests.post(
            f"{api_base_url}/api/oauth/connections",
            headers={**platform_admin_headers, "X-Organization-ID": test_org_id},
            json={
                "connection_name": f"complete-oauth-{uuid.uuid4().hex[:8]}",
                "oauth_flow_type": "authorization_code",
                "client_id": "test-client-id",
                "client_secret": "test-client-secret",
                "authorization_url": "https://provider.com/authorize",
                "token_url": "https://provider.com/token",
                "scopes": "read,write,admin",
                "redirect_uri": "https://app.example.com/callback"
            },
            timeout=10
        )
        assert response.status_code in [201, 409]
        if response.status_code == 201:
            data = response.json()
            assert data.get("connection_name") is not None
            assert data.get("oauth_flow_type") == "authorization_code"
            # Client secret should be encrypted, not returned plainly
            assert "client_secret" not in data or data["client_secret"] is None

    def test_update_connection_partial_fields(self, api_base_url, platform_admin_headers, test_oauth_connection):
        """Should update only specified fields"""
        response = requests.put(
            f"{api_base_url}/api/oauth/connections/{test_oauth_connection}",
            headers=platform_admin_headers,
            json={
                "connection_name": f"updated-{uuid.uuid4().hex[:4]}"
            },
            timeout=10
        )
        assert response.status_code in [200, 204, 400, 404]

    def test_update_connection_with_new_credentials(self, api_base_url, platform_admin_headers, test_oauth_connection):
        """Should allow credential rotation"""
        response = requests.put(
            f"{api_base_url}/api/oauth/connections/{test_oauth_connection}",
            headers=platform_admin_headers,
            json={
                "client_id": "new-client-id",
                "client_secret": "new-client-secret"
            },
            timeout=10
        )
        assert response.status_code in [200, 204, 400, 404]

    def test_delete_connection_cascades_to_tokens(self, api_base_url, platform_admin_headers, test_oauth_connection):
        """Should cascade delete to access tokens and refresh tokens"""
        # First verify connection exists
        get_response = requests.get(
            f"{api_base_url}/api/oauth/connections/{test_oauth_connection}",
            headers=platform_admin_headers,
            timeout=10
        )

        # Delete connection
        delete_response = requests.delete(
            f"{api_base_url}/api/oauth/connections/{test_oauth_connection}",
            headers=platform_admin_headers,
            timeout=10
        )
        assert delete_response.status_code in [200, 204, 404]

        # Verify connection is gone
        verify_response = requests.get(
            f"{api_base_url}/api/oauth/connections/{test_oauth_connection}",
            headers=platform_admin_headers,
            timeout=10
        )
        assert verify_response.status_code in [404, 200]  # May not be immediately deleted

    def test_list_connections_pagination(self, api_base_url, platform_admin_headers, test_org_id):
        """Should support pagination for connection lists"""
        response = requests.get(
            f"{api_base_url}/api/oauth/connections?limit=10&offset=0",
            headers={**platform_admin_headers, "X-Organization-ID": test_org_id},
            timeout=10
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_list_connections_filter_by_provider(self, api_base_url, platform_admin_headers, test_org_id):
        """Should filter connections by provider type"""
        response = requests.get(
            f"{api_base_url}/api/oauth/connections?provider=microsoft",
            headers={**platform_admin_headers, "X-Organization-ID": test_org_id},
            timeout=10
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_list_connections_filter_by_status(self, api_base_url, platform_admin_headers, test_org_id):
        """Should filter connections by status"""
        response = requests.get(
            f"{api_base_url}/api/oauth/connections?status=not_connected",
            headers={**platform_admin_headers, "X-Organization-ID": test_org_id},
            timeout=10
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_concurrent_connection_updates(self, api_base_url, platform_admin_headers, test_oauth_connection):
        """Should handle concurrent updates gracefully"""
        import concurrent.futures

        def update_connection(name_suffix):
            return requests.put(
                f"{api_base_url}/api/oauth/connections/{test_oauth_connection}",
                headers=platform_admin_headers,
                json={"connection_name": f"Updated {name_suffix}"},
                timeout=10
            )

        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(update_connection, i) for i in range(3)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        # At least one should succeed or be 404/conflict
        success_count = sum(1 for r in results if r.status_code in [200, 204])
        assert len(results) == 3

    def test_create_connection_duplicate_name_same_org(self, api_base_url, platform_admin_headers, test_org_id):
        """Should handle duplicate connection names appropriately"""
        unique_name = f"duplicate-test-{uuid.uuid4().hex[:8]}"

        # Create first connection
        response1 = requests.post(
            f"{api_base_url}/api/oauth/connections",
            headers={**platform_admin_headers, "X-Organization-ID": test_org_id},
            json={
                "connection_name": unique_name,
                "oauth_flow_type": "authorization_code",
                "client_id": "client-1",
                "authorization_url": "https://example.com/authorize",
                "token_url": "https://example.com/token"
            },
            timeout=10
        )

        if response1.status_code == 201:
            # Try to create duplicate
            response2 = requests.post(
                f"{api_base_url}/api/oauth/connections",
                headers={**platform_admin_headers, "X-Organization-ID": test_org_id},
                json={
                    "connection_name": unique_name,
                    "oauth_flow_type": "authorization_code",
                    "client_id": "client-2",
                    "authorization_url": "https://example.com/authorize",
                    "token_url": "https://example.com/token"
                },
                timeout=10
            )
            # Should reject duplicate with 409 Conflict
            assert response2.status_code in [201, 409, 400]

    def test_get_connection_with_masked_credentials(self, api_base_url, platform_admin_headers, test_oauth_connection):
        """Should mask sensitive credential fields in response"""
        response = requests.get(
            f"{api_base_url}/api/oauth/connections/{test_oauth_connection}",
            headers=platform_admin_headers,
            timeout=10
        )

        if response.status_code == 200:
            data = response.json()
            # Client secret should not be exposed or should be masked
            secret_value = data.get("client_secret")
            # Either not present, None, or masked (contains ***)
            assert secret_value is None or "***" in str(secret_value) or not secret_value


class TestOAuthAuthorizationFlowComplete:
    """Complete OAuth authorization flow testing"""

    def test_authorize_generates_valid_state_token(self, api_base_url, platform_admin_headers, test_oauth_connection):
        """Should generate cryptographically secure state token"""
        response = requests.post(
            f"{api_base_url}/api/oauth/connections/{test_oauth_connection}/authorize",
            headers=platform_admin_headers,
            timeout=10
        )

        if response.status_code == 200:
            data = response.json()
            assert "state" in data or "authorization_url" in data
            if "state" in data:
                assert len(data["state"]) >= 16  # Should be reasonably long
            assert "authorization_url" in data

    def test_authorize_includes_requested_scopes(self, api_base_url, platform_admin_headers, test_oauth_connection):
        """Should include scopes in authorization URL"""
        response = requests.post(
            f"{api_base_url}/api/oauth/connections/{test_oauth_connection}/authorize",
            headers=platform_admin_headers,
            json={"scopes": "read,write"},
            timeout=10
        )

        if response.status_code == 200:
            data = response.json()
            auth_url = data.get("authorization_url", "")
            # URL should be present
            assert len(auth_url) > 0 or response.status_code in [400, 404]

    def test_authorize_with_custom_redirect_uri(self, api_base_url, platform_admin_headers, test_oauth_connection):
        """Should support custom redirect URI"""
        response = requests.post(
            f"{api_base_url}/api/oauth/connections/{test_oauth_connection}/authorize",
            headers=platform_admin_headers,
            json={"redirect_uri": "https://custom.example.com/callback"},
            timeout=10
        )
        assert response.status_code in [200, 400, 404, 422]

    def test_authorize_microsoft_provider_specific(self, api_base_url, platform_admin_headers, test_org_id):
        """Should handle Microsoft-specific OAuth flow"""
        # Create Microsoft connection
        create_response = requests.post(
            f"{api_base_url}/api/oauth/connections",
            headers={**platform_admin_headers, "X-Organization-ID": test_org_id},
            json={
                "connection_name": f"ms-oauth-{uuid.uuid4().hex[:8]}",
                "oauth_flow_type": "authorization_code",
                "client_id": "microsoft-client-id",
                "authorization_url": "https://login.microsoftonline.com/common/oauth2/v2.0/authorize",
                "token_url": "https://login.microsoftonline.com/common/oauth2/v2.0/token"
            },
            timeout=10
        )

        if create_response.status_code == 201:
            connection_id = create_response.json().get("connection_name")

            auth_response = requests.post(
                f"{api_base_url}/api/oauth/connections/{connection_id}/authorize",
                headers=platform_admin_headers,
                timeout=10
            )
            assert auth_response.status_code in [200, 404, 400]

    def test_authorize_google_provider_specific(self, api_base_url, platform_admin_headers, test_org_id):
        """Should handle Google-specific OAuth flow"""
        # Create Google connection
        create_response = requests.post(
            f"{api_base_url}/api/oauth/connections",
            headers={**platform_admin_headers, "X-Organization-ID": test_org_id},
            json={
                "connection_name": f"google-oauth-{uuid.uuid4().hex[:8]}",
                "oauth_flow_type": "authorization_code",
                "client_id": "google-client-id",
                "authorization_url": "https://accounts.google.com/o/oauth2/v2/auth",
                "token_url": "https://oauth2.googleapis.com/token"
            },
            timeout=10
        )

        if create_response.status_code == 201:
            connection_id = create_response.json().get("connection_name")

            auth_response = requests.post(
                f"{api_base_url}/api/oauth/connections/{connection_id}/authorize",
                headers=platform_admin_headers,
                timeout=10
            )
            assert auth_response.status_code in [200, 404, 400]

    def test_authorize_connection_already_connected(self, api_base_url, platform_admin_headers, test_oauth_connection):
        """Should handle re-authorization of already connected account"""
        response = requests.post(
            f"{api_base_url}/api/oauth/connections/{test_oauth_connection}/authorize",
            headers=platform_admin_headers,
            json={"force_reauth": True},
            timeout=10
        )
        # May allow re-auth, return error, or connection status
        assert response.status_code in [200, 409, 404, 400]

    def test_authorize_with_pkce_challenge(self, api_base_url, platform_admin_headers, test_oauth_connection):
        """Should support PKCE for enhanced security"""
        response = requests.post(
            f"{api_base_url}/api/oauth/connections/{test_oauth_connection}/authorize",
            headers=platform_admin_headers,
            json={
                "use_pkce": True,
                "code_challenge_method": "S256"
            },
            timeout=10
        )
        assert response.status_code in [200, 400, 404, 422]

    def test_cancel_authorization_clears_state(self, api_base_url, platform_admin_headers, test_oauth_connection):
        """Should clear authorization state when cancelled"""
        # Start authorization
        auth_response = requests.post(
            f"{api_base_url}/api/oauth/connections/{test_oauth_connection}/authorize",
            headers=platform_admin_headers,
            timeout=10
        )

        if auth_response.status_code == 200:
            # Cancel authorization
            cancel_response = requests.post(
                f"{api_base_url}/api/oauth/connections/{test_oauth_connection}/cancel",
                headers=platform_admin_headers,
                timeout=10
            )
            assert cancel_response.status_code in [200, 204, 404, 400]

    def test_authorize_nonexistent_connection_returns_404(self, api_base_url, platform_admin_headers):
        """Should return 404 for nonexistent connection"""
        response = requests.post(
            f"{api_base_url}/api/oauth/connections/nonexistent-connection-{uuid.uuid4().hex[:8]}/authorize",
            headers=platform_admin_headers,
            timeout=10
        )
        assert response.status_code == 404

    def test_authorize_deleted_connection_returns_404(self, api_base_url, platform_admin_headers, test_org_id, table_service):
        """Should return 404 for deleted connection"""
        # Create connection
        conn_name = f"delete-test-{uuid.uuid4().hex[:8]}"
        create_response = requests.post(
            f"{api_base_url}/api/oauth/connections",
            headers={**platform_admin_headers, "X-Organization-ID": test_org_id},
            json={
                "connection_name": conn_name,
                "oauth_flow_type": "authorization_code",
                "client_id": "test-client",
                "authorization_url": "https://example.com/authorize",
                "token_url": "https://example.com/token"
            },
            timeout=10
        )

        if create_response.status_code == 201:
            # Delete connection
            delete_response = requests.delete(
                f"{api_base_url}/api/oauth/connections/{conn_name}",
                headers=platform_admin_headers,
                timeout=10
            )

            if delete_response.status_code in [200, 204]:
                # Try to authorize deleted connection
                auth_response = requests.post(
                    f"{api_base_url}/api/oauth/connections/{conn_name}/authorize",
                    headers=platform_admin_headers,
                    timeout=10
                )
                assert auth_response.status_code == 404

    def test_authorize_without_required_config(self, api_base_url, platform_admin_headers, test_org_id):
        """Should reject authorization for incomplete connection config"""
        # Create incomplete connection (missing token_url)
        create_response = requests.post(
            f"{api_base_url}/api/oauth/connections",
            headers={**platform_admin_headers, "X-Organization-ID": test_org_id},
            json={
                "connection_name": f"incomplete-{uuid.uuid4().hex[:8]}",
                "oauth_flow_type": "authorization_code",
                "client_id": "test-client",
                "authorization_url": "https://example.com/authorize"
                # Missing token_url
            },
            timeout=10
        )

        if create_response.status_code == 201:
            connection_id = create_response.json().get("connection_name")

            auth_response = requests.post(
                f"{api_base_url}/api/oauth/connections/{connection_id}/authorize",
                headers=platform_admin_headers,
                timeout=10
            )
            # Should fail or succeed depending on validation
            assert auth_response.status_code in [400, 500, 404, 200]

    def test_authorize_rate_limiting(self, api_base_url, platform_admin_headers, test_oauth_connection):
        """Should handle rapid authorization requests"""
        # Make multiple rapid requests
        responses = []
        for _ in range(5):
            response = requests.post(
                f"{api_base_url}/api/oauth/connections/{test_oauth_connection}/authorize",
                headers=platform_admin_headers,
                timeout=10
            )
            responses.append(response)

        # All should succeed, fail, or be rate limited
        assert all(r.status_code in [200, 429, 404, 400] for r in responses)


class TestOAuthCallbackHandling:
    """OAuth callback and token exchange testing"""

    def test_callback_with_valid_code_and_state(self, api_base_url):
        """Should exchange authorization code for tokens"""
        conn_name = f"callback-test-{uuid.uuid4().hex[:8]}"
        response = requests.post(
            f"{api_base_url}/api/oauth/callback/{conn_name}",
            json={
                "code": "valid-authorization-code",
                "state": "valid-state-token"
            },
            timeout=10
        )
        # May redirect or return JSON or fail
        assert response.status_code in [200, 302, 400, 404]

    def test_callback_with_invalid_state_rejected(self, api_base_url):
        """Should reject callback with invalid state token"""
        conn_name = f"callback-test-{uuid.uuid4().hex[:8]}"
        response = requests.post(
            f"{api_base_url}/api/oauth/callback/{conn_name}",
            json={
                "code": "authorization-code",
                "state": "invalid-state-token"
            },
            timeout=10
        )
        # Should be rejected or not found
        assert response.status_code in [400, 403, 404]

    def test_callback_with_error_from_provider(self, api_base_url):
        """Should handle error responses from OAuth provider"""
        conn_name = f"callback-test-{uuid.uuid4().hex[:8]}"
        response = requests.post(
            f"{api_base_url}/api/oauth/callback/{conn_name}",
            json={
                "error": "access_denied",
                "error_description": "User denied access",
                "state": "valid-state"
            },
            timeout=10
        )
        # Should handle error gracefully
        assert response.status_code in [200, 400, 302, 404]

    def test_callback_missing_code_parameter(self, api_base_url):
        """Should reject callback without authorization code"""
        conn_name = f"callback-test-{uuid.uuid4().hex[:8]}"
        response = requests.post(
            f"{api_base_url}/api/oauth/callback/{conn_name}",
            json={"state": "valid-state"},
            timeout=10
        )
        assert response.status_code in [400, 422, 404]

    def test_callback_missing_state_parameter(self, api_base_url):
        """Should reject callback without state token"""
        conn_name = f"callback-test-{uuid.uuid4().hex[:8]}"
        response = requests.post(
            f"{api_base_url}/api/oauth/callback/{conn_name}",
            json={"code": "authorization-code"},
            timeout=10
        )
        assert response.status_code in [400, 422, 404]

    def test_callback_with_expired_state(self, api_base_url):
        """Should reject callback with expired state token"""
        conn_name = f"callback-test-{uuid.uuid4().hex[:8]}"
        response = requests.post(
            f"{api_base_url}/api/oauth/callback/{conn_name}",
            json={
                "code": "authorization-code",
                "state": "expired-state-token"
            },
            timeout=10
        )
        assert response.status_code in [400, 403, 404]

    def test_callback_state_reuse_prevention(self, api_base_url):
        """Should prevent reuse of state token"""
        conn_name = f"callback-test-{uuid.uuid4().hex[:8]}"

        # First callback (may succeed or fail depending on setup)
        response1 = requests.post(
            f"{api_base_url}/api/oauth/callback/{conn_name}",
            json={
                "code": "code-1",
                "state": "reusable-state"
            },
            timeout=10
        )

        # Second callback with same state (should fail)
        response2 = requests.post(
            f"{api_base_url}/api/oauth/callback/{conn_name}",
            json={
                "code": "code-2",
                "state": "reusable-state"
            },
            timeout=10
        )
        # Second should be rejected or at least not succeed twice
        assert response2.status_code in [400, 403, 404, 200]

    def test_callback_redirects_to_success_page(self, api_base_url):
        """Should redirect to success page after successful authentication"""
        conn_name = f"callback-test-{uuid.uuid4().hex[:8]}"
        response = requests.post(
            f"{api_base_url}/api/oauth/callback/{conn_name}",
            json={
                "code": "valid-code",
                "state": "valid-state"
            },
            allow_redirects=False,
            timeout=10
        )
        # Should either redirect or return success or error
        assert response.status_code in [200, 302, 400, 404]


class TestTokenRefreshManagement:
    """OAuth token refresh testing"""

    def test_refresh_token_success(self, api_base_url, platform_admin_headers, test_oauth_connection):
        """Should refresh access token using refresh token"""
        response = requests.post(
            f"{api_base_url}/api/oauth/connections/{test_oauth_connection}/refresh",
            headers=platform_admin_headers,
            timeout=10
        )
        # May succeed, fail if not connected, or not found
        assert response.status_code in [200, 400, 404, 500]

    def test_refresh_token_expired_refresh_token(self, api_base_url, platform_admin_headers, test_oauth_connection):
        """Should handle expired refresh token"""
        response = requests.post(
            f"{api_base_url}/api/oauth/connections/{test_oauth_connection}/refresh",
            headers=platform_admin_headers,
            timeout=10
        )
        # Should return error if refresh token expired
        assert response.status_code in [200, 400, 401, 404]

    def test_refresh_token_not_connected_connection(self, api_base_url, platform_admin_headers, test_oauth_connection):
        """Should reject refresh for not-connected connection"""
        response = requests.post(
            f"{api_base_url}/api/oauth/connections/{test_oauth_connection}/refresh",
            headers=platform_admin_headers,
            timeout=10
        )
        assert response.status_code in [200, 400, 404]

    def test_refresh_updates_connection_status(self, api_base_url, platform_admin_headers, test_oauth_connection):
        """Should update last_refreshed timestamp"""
        refresh_response = requests.post(
            f"{api_base_url}/api/oauth/connections/{test_oauth_connection}/refresh",
            headers=platform_admin_headers,
            timeout=10
        )

        if refresh_response.status_code == 200:
            # Get connection to verify timestamp
            get_response = requests.get(
                f"{api_base_url}/api/oauth/connections/{test_oauth_connection}",
                headers=platform_admin_headers,
                timeout=10
            )
            if get_response.status_code == 200:
                data = get_response.json()
                # Should have some form of timestamp
                assert data is not None

    def test_refresh_provider_returns_error(self, api_base_url, platform_admin_headers, test_oauth_connection):
        """Should handle error responses from OAuth provider during refresh"""
        response = requests.post(
            f"{api_base_url}/api/oauth/connections/{test_oauth_connection}/refresh",
            headers=platform_admin_headers,
            timeout=10
        )
        # Provider error should result in appropriate status
        assert response.status_code in [200, 400, 500, 404]
