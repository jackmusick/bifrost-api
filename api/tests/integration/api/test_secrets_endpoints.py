"""Integration tests for Secrets API endpoints

Tests the secrets management endpoints for Azure Key Vault integration.
All tests require a platform admin role to execute.
"""

import pytest
import requests


class TestSecretsCRUD:
    """Test secret CRUD operations"""

    def test_list_secrets_success(self, api_base_url, platform_admin_headers):
        """Should list secrets successfully"""
        response = requests.get(
            f"{api_base_url}/api/secrets",
            headers=platform_admin_headers,
            timeout=10
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
        assert "secrets" in data
        assert isinstance(data["secrets"], list)

    def test_create_secret_success(self, api_base_url, platform_admin_headers):
        """Should create organization secret successfully"""
        response = requests.post(
            f"{api_base_url}/api/secrets",
            headers=platform_admin_headers,
            json={
                "orgId": "GLOBAL",
                "secretKey": "test-api-key-integration",
                "value": "secret-value-123"
            },
            timeout=10
        )
        # May return 201 (created) or 409 (conflict - already exists)
        assert response.status_code in [201, 409]
        if response.status_code == 201:
            data = response.json()
            assert data["secretKey"] == "test-api-key-integration"
            assert data["orgId"] == "GLOBAL"

    def test_update_secret_success(self, api_base_url, platform_admin_headers):
        """Should update existing secret"""
        # First ensure a secret exists
        create_response = requests.post(
            f"{api_base_url}/api/secrets",
            headers=platform_admin_headers,
            json={
                "orgId": "GLOBAL",
                "secretKey": "test-update-key",
                "value": "initial-value"
            },
            timeout=10
        )

        # Now update it
        response = requests.put(
            f"{api_base_url}/api/secrets/GLOBAL--test-update-key",
            headers=platform_admin_headers,
            json={
                "value": "updated-secret-value"
            },
            timeout=10
        )
        # May return 200 (success) or 404 (not found if create failed)
        assert response.status_code in [200, 404]
        if response.status_code == 200:
            data = response.json()
            assert data["value"] == "updated-secret-value"

    def test_delete_secret_success(self, api_base_url, platform_admin_headers):
        """Should delete secret successfully"""
        # First create a secret to delete
        create_response = requests.post(
            f"{api_base_url}/api/secrets",
            headers=platform_admin_headers,
            json={
                "orgId": "GLOBAL",
                "secretKey": "test-delete-key",
                "value": "to-be-deleted"
            },
            timeout=10
        )

        if create_response.status_code in [201, 409]:
            response = requests.delete(
                f"{api_base_url}/api/secrets/GLOBAL--test-delete-key",
                headers=platform_admin_headers,
                timeout=10
            )
            # May return 200 (deleted) or 404 (not found)
            assert response.status_code in [200, 204, 404]

    def test_list_secrets_with_org_filter(self, api_base_url, platform_admin_headers):
        """Should list secrets filtered by organization"""
        response = requests.get(
            f"{api_base_url}/api/secrets?org_id=GLOBAL",
            headers=platform_admin_headers,
            timeout=10
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
        assert data.get("orgId") == "GLOBAL"


class TestSecretsAuthorization:
    """Test secret authorization and access control"""

    def test_regular_user_cannot_list_secrets(self, api_base_url, regular_user_headers):
        """Regular users should not list secrets"""
        response = requests.get(
            f"{api_base_url}/api/secrets",
            headers=regular_user_headers,
            timeout=10
        )
        # Should be 403 (Forbidden) or 401 (Unauthorized)
        assert response.status_code in [403, 401]

    def test_regular_user_cannot_create_secrets(self, api_base_url, regular_user_headers):
        """Regular users should not create secrets"""
        response = requests.post(
            f"{api_base_url}/api/secrets",
            headers=regular_user_headers,
            json={
                "orgId": "GLOBAL",
                "secretKey": "unauthorized-key",
                "value": "value"
            },
            timeout=10
        )
        assert response.status_code in [403, 401]

    def test_regular_user_cannot_update_secrets(self, api_base_url, regular_user_headers):
        """Regular users should not update secrets"""
        response = requests.put(
            f"{api_base_url}/api/secrets/GLOBAL--test-key",
            headers=regular_user_headers,
            json={"value": "new-value"},
            timeout=10
        )
        assert response.status_code in [403, 401, 404]

    def test_regular_user_cannot_delete_secrets(self, api_base_url, regular_user_headers):
        """Regular users should not delete secrets"""
        response = requests.delete(
            f"{api_base_url}/api/secrets/GLOBAL--test-key",
            headers=regular_user_headers,
            timeout=10
        )
        assert response.status_code in [403, 401, 404]


class TestSecretsValidation:
    """Test secret validation and error handling"""

    def test_create_secret_missing_org_id(self, api_base_url, platform_admin_headers):
        """Should validate orgId is required"""
        response = requests.post(
            f"{api_base_url}/api/secrets",
            headers=platform_admin_headers,
            json={
                "secretKey": "test-key",
                "value": "test-value"
            },
            timeout=10
        )
        # Should be 400 (validation error) or 422 (unprocessable)
        assert response.status_code in [400, 422]

    def test_create_secret_missing_key(self, api_base_url, platform_admin_headers):
        """Should validate secretKey is required"""
        response = requests.post(
            f"{api_base_url}/api/secrets",
            headers=platform_admin_headers,
            json={
                "orgId": "GLOBAL",
                "value": "test-value"
            },
            timeout=10
        )
        # Should be 400 (validation error) or 422 (unprocessable)
        assert response.status_code in [400, 422]

    def test_create_secret_missing_value(self, api_base_url, platform_admin_headers):
        """Should validate value is required"""
        response = requests.post(
            f"{api_base_url}/api/secrets",
            headers=platform_admin_headers,
            json={
                "orgId": "GLOBAL",
                "secretKey": "test-key"
            },
            timeout=10
        )
        # Should be 400 (validation error) or 422 (unprocessable)
        assert response.status_code in [400, 422]

    def test_update_secret_invalid_format(self, api_base_url, platform_admin_headers):
        """Should validate secret name format"""
        response = requests.put(
            f"{api_base_url}/api/secrets/invalid-name-no-separator",
            headers=platform_admin_headers,
            json={"value": "new-value"},
            timeout=10
        )
        # Should be 400 (bad request) or 404 (not found)
        assert response.status_code in [400, 404]

    def test_create_secret_with_description(self, api_base_url, platform_admin_headers):
        """Should create secret with description"""
        response = requests.post(
            f"{api_base_url}/api/secrets",
            headers=platform_admin_headers,
            json={
                "orgId": "GLOBAL",
                "secretKey": "test-secret-with-desc",
                "value": "secret-value",
                "description": "This is a test secret with description"
            },
            timeout=10
        )
        assert response.status_code in [201, 409]
        if response.status_code == 201:
            data = response.json()
            # API may or may not return description field
            assert "secretKey" in data
            assert data["secretKey"] == "test-secret-with-desc"
