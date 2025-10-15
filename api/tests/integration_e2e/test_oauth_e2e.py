"""
End-to-end tests for OAuth API
Tests OAuth connection CRUD operations with encrypted credentials
"""

import pytest
import requests


class TestOAuthConnectionsE2E:
    """Test OAuth connection CRUD endpoints"""

    def test_list_oauth_connections_as_org_user(self, base_url, org_user_headers):
        """Org user can list OAuth connections (org + GLOBAL)"""
        response = requests.get(
            f"{base_url}/oauth/connections",
            headers=org_user_headers
        )

        assert response.status_code == 200
        connections = response.json()
        assert isinstance(connections, list)

        # Verify structure if connections exist
        if len(connections) > 0:
            connection = connections[0]
            assert "connection_name" in connection
            assert "status" in connection
            # Should be summary view (no sensitive fields)
            assert "client_secret_ref" not in connection or connection.get("client_secret_ref") is None

    def test_create_oauth_connection_as_platform_admin(self, base_url, platform_admin_headers):
        """Platform admin can create OAuth connections"""
        response = requests.post(
            f"{base_url}/oauth/connections",
            headers=platform_admin_headers,
            json={
                "connection_name": "test_oauth_connection_e2e",
                "description": "Test OAuth connection for E2E testing",
                "oauth_flow_type": "authorization_code",
                "authorization_url": "https://accounts.google.com/o/oauth2/v2/auth",
                "token_url": "https://oauth2.googleapis.com/token",
                "scopes": "https://www.googleapis.com/auth/userinfo.profile",
                "client_id": "test-client-id-12345",
                "client_secret_value": "test-secret-value-xyz",  # Will be stored in Key Vault
                "redirect_uri": "/oauth/callback/test_oauth_connection_e2e"
            }
        )

        # May return 201 (created) or 409 (already exists from previous runs)
        assert response.status_code in [201, 409]

        if response.status_code == 201:
            connection = response.json()
            assert connection["connection_name"] == "test_oauth_connection_e2e"
            assert connection["status"] == "not_connected"
            assert connection["oauth_flow_type"] == "authorization_code"
            # client_secret should be masked in response
            assert "client_secret_value" not in connection

    def test_get_oauth_connection_by_name(self, base_url, org_user_headers):
        """User can get OAuth connection by name"""
        # First list to find an existing connection
        list_response = requests.get(
            f"{base_url}/oauth/connections",
            headers=org_user_headers
        )
        connections = list_response.json()

        if len(connections) == 0:
            pytest.skip("No OAuth connections available")

        connection_name = connections[0]["connection_name"]

        # Get specific connection
        response = requests.get(
            f"{base_url}/oauth/connections/{connection_name}",
            headers=org_user_headers
        )

        assert response.status_code == 200
        connection = response.json()
        assert connection["connection_name"] == connection_name
        assert "authorization_url" in connection
        assert "token_url" in connection
        # Sensitive fields should be masked
        assert "client_secret_value" not in connection

    def test_get_nonexistent_oauth_connection_not_found(self, base_url, platform_admin_headers):
        """Getting nonexistent OAuth connection returns 404"""
        response = requests.get(
            f"{base_url}/oauth/connections/nonexistent_connection",
            headers=platform_admin_headers
        )

        assert response.status_code == 404
        error = response.json()
        assert error["error"] == "NotFound"

    def test_update_oauth_connection(self, base_url, platform_admin_headers):
        """Platform admin can update OAuth connections"""
        # First create a connection to update
        create_response = requests.post(
            f"{base_url}/oauth/connections",
            headers=platform_admin_headers,
            json={
                "connection_name": "test_update_connection_e2e",
                "description": "Original description",
                "oauth_flow_type": "authorization_code",
                "authorization_url": "https://test.example.com/auth",
                "token_url": "https://test.example.com/token",
                "scopes": "read",
                "client_id": "test-client",
                "client_secret_value": "test-secret",
                "redirect_uri": "/oauth/callback/test_update_connection_e2e"
            }
        )

        # May already exist from previous runs
        if create_response.status_code == 409:
            # Connection already exists, can update it
            pass
        else:
            assert create_response.status_code == 201

        # Update it
        update_response = requests.put(
            f"{base_url}/oauth/connections/test_update_connection_e2e",
            headers=platform_admin_headers,
            json={
                "description": "Updated description for E2E testing"
            }
        )

        assert update_response.status_code == 200
        updated_connection = update_response.json()
        assert updated_connection["description"] == "Updated description for E2E testing"
        assert updated_connection["connection_name"] == "test_update_connection_e2e"

    def test_delete_oauth_connection(self, base_url, platform_admin_headers):
        """Platform admin can delete OAuth connections"""
        # First create a connection to delete
        requests.post(
            f"{base_url}/oauth/connections",
            headers=platform_admin_headers,
            json={
                "connection_name": "test_delete_connection_e2e",
                "oauth_flow_type": "authorization_code",
                "authorization_url": "https://test.example.com/auth",
                "token_url": "https://test.example.com/token",
                "scopes": "read",
                "client_id": "test-client",
                "client_secret_value": "test-secret",
                "redirect_uri": "/oauth/callback/test_delete_connection_e2e"
            }
        )

        # Delete it (idempotent)
        delete_response = requests.delete(
            f"{base_url}/oauth/connections/test_delete_connection_e2e",
            headers=platform_admin_headers
        )

        assert delete_response.status_code == 204

        # Verify it's gone
        get_response = requests.get(
            f"{base_url}/oauth/connections/test_delete_connection_e2e",
            headers=platform_admin_headers
        )
        assert get_response.status_code == 404

    def test_create_oauth_connection_validation_error(self, base_url, platform_admin_headers):
        """Creating OAuth connection without required fields returns 400"""
        response = requests.post(
            f"{base_url}/oauth/connections",
            headers=platform_admin_headers,
            json={
                "connection_name": "incomplete_connection"
                # Missing: oauth_flow_type, urls, scopes, etc.
            }
        )

        assert response.status_code == 400
        error = response.json()
        assert error["error"] == "ValidationError"

    def test_create_duplicate_oauth_connection_conflict(self, base_url, platform_admin_headers):
        """Creating duplicate OAuth connection returns 409"""
        connection_data = {
            "connection_name": "duplicate_connection_test",
            "oauth_flow_type": "authorization_code",
            "authorization_url": "https://test.example.com/auth",
            "token_url": "https://test.example.com/token",
            "scopes": "read",
            "client_id": "test-client",
            "client_secret_value": "test-secret",
            "redirect_uri": "/oauth/callback/duplicate_connection_test"
        }

        # First creation
        first_response = requests.post(
            f"{base_url}/oauth/connections",
            headers=platform_admin_headers,
            json=connection_data
        )

        # Should succeed (201) or already exist (409)
        assert first_response.status_code in [201, 409]

        # Second creation with same name
        second_response = requests.post(
            f"{base_url}/oauth/connections",
            headers=platform_admin_headers,
            json=connection_data
        )

        assert second_response.status_code == 409
        error = second_response.json()
        assert error["error"] == "Conflict"

    @pytest.mark.skip(reason="Local dev mode treats anonymous as admin")
    def test_list_oauth_connections_anonymous_unauthorized(self, base_url, anonymous_headers):
        """Anonymous users should be rejected in production"""
        response = requests.get(
            f"{base_url}/oauth/connections",
            headers=anonymous_headers
        )

        assert response.status_code == 401


class TestOAuthCredentialsE2E:
    """Test OAuth credentials retrieval endpoint"""

    @pytest.mark.skip(reason="Requires completed OAuth connection with tokens")
    def test_get_oauth_credentials(self, base_url, org_user_headers):
        """
        User can retrieve OAuth credentials for completed connections.

        NOTE: This test is skipped because it requires:
        1. A completed OAuth connection (status="completed")
        2. Valid tokens stored in Key Vault
        3. Full OAuth authorization flow to have been completed

        This would require mocking the OAuth provider or running actual OAuth flow.
        """
        response = requests.get(
            f"{base_url}/oauth/credentials/test_connection",
            headers=org_user_headers
        )

        assert response.status_code == 200
        credentials_response = response.json()
        assert "credentials" in credentials_response
        assert "status" in credentials_response

    def test_get_oauth_credentials_not_connected(self, base_url, platform_admin_headers):
        """
        Getting credentials for not_connected connection returns null credentials.

        This test verifies the API behavior for connections that haven't
        completed OAuth authorization yet.
        """
        # Create a connection (will be in not_connected status)
        create_response = requests.post(
            f"{base_url}/oauth/connections",
            headers=platform_admin_headers,
            json={
                "connection_name": "test_credentials_not_connected",
                "oauth_flow_type": "authorization_code",
                "authorization_url": "https://test.example.com/auth",
                "token_url": "https://test.example.com/token",
                "scopes": "read",
                "client_id": "test-client",
                "client_secret_value": "test-secret",
                "redirect_uri": "/oauth/callback/test_credentials_not_connected"
            }
        )

        # May already exist
        assert create_response.status_code in [201, 409]

        # Try to get credentials (should return null credentials)
        credentials_response = requests.get(
            f"{base_url}/oauth/credentials/test_credentials_not_connected",
            headers=platform_admin_headers
        )

        assert credentials_response.status_code == 200
        creds = credentials_response.json()
        assert creds["status"] == "not_connected"
        assert creds["credentials"] is None

    def test_get_oauth_credentials_nonexistent_connection(self, base_url, platform_admin_headers):
        """Getting credentials for nonexistent connection returns 404"""
        response = requests.get(
            f"{base_url}/oauth/credentials/nonexistent_connection",
            headers=platform_admin_headers
        )

        assert response.status_code == 404
        error = response.json()
        assert error["error"] == "NotFound"
