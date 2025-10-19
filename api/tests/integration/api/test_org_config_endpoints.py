"""Integration tests for Organization Config API endpoints

Tests the organization configuration management endpoints for managing
global and organization-specific configuration key-value pairs.
"""

import pytest
import requests


class TestOrgConfigCRUD:
    """Test organization configuration CRUD operations"""

    def test_get_config_success(self, api_base_url, platform_admin_headers):
        """Should retrieve organization config"""
        response = requests.get(
            f"{api_base_url}/api/config",
            headers=platform_admin_headers,
            timeout=10
        )
        assert response.status_code == 200
        data = response.json()
        # Response should be a list of config items
        assert isinstance(data, list)

    def test_set_config_success(self, api_base_url, platform_admin_headers):
        """Should set organization configuration"""
        response = requests.post(
            f"{api_base_url}/api/config",
            headers=platform_admin_headers,
            json={
                "key": "test_config_key_integration",
                "value": "test_value",
                "type": "string",
                "description": "Test configuration"
            },
            timeout=10
        )
        # Should return 201 (created) or 200 (updated)
        assert response.status_code in [200, 201]
        data = response.json()
        assert data["key"] == "test_config_key_integration"
        # Value may be masked for sensitive keys by the API
        assert data["value"] is not None

    def test_delete_config_success(self, api_base_url, platform_admin_headers):
        """Should delete configuration value"""
        # First set a config to delete
        set_response = requests.post(
            f"{api_base_url}/api/config",
            headers=platform_admin_headers,
            json={
                "key": "test_delete_config",
                "value": "to_be_deleted",
                "type": "string"
            },
            timeout=10
        )

        if set_response.status_code in [200, 201]:
            response = requests.delete(
                f"{api_base_url}/api/config/test_delete_config",
                headers=platform_admin_headers,
                timeout=10
            )
            # Should return 204 (no content) or 200 (success)
            assert response.status_code in [200, 204]

    def test_get_integrations_success(self, api_base_url, platform_admin_headers, test_org_id):
        """Should retrieve organization integrations"""
        response = requests.get(
            f"{api_base_url}/api/organizations/{test_org_id}/integrations",
            headers=platform_admin_headers,
            timeout=10
        )
        assert response.status_code == 200
        data = response.json()
        # Response should be a list or dict with integration configs
        assert isinstance(data, (list, dict))


class TestOrgConfigValidation:
    """Test organization configuration validation"""

    def test_set_config_missing_key(self, api_base_url, platform_admin_headers):
        """Should validate key is required"""
        response = requests.post(
            f"{api_base_url}/api/config",
            headers=platform_admin_headers,
            json={
                "value": "test_value",
                "type": "string"
            },
            timeout=10
        )
        # Should be 400 (validation error) or 422 (unprocessable)
        assert response.status_code in [400, 422]

    def test_set_config_missing_value(self, api_base_url, platform_admin_headers):
        """Should validate value is required"""
        response = requests.post(
            f"{api_base_url}/api/config",
            headers=platform_admin_headers,
            json={
                "key": "test_key",
                "type": "string"
            },
            timeout=10
        )
        # Should be 400 (validation error) or 422 (unprocessable)
        assert response.status_code in [400, 422]

    def test_set_config_missing_type(self, api_base_url, platform_admin_headers):
        """Should validate type is required"""
        response = requests.post(
            f"{api_base_url}/api/config",
            headers=platform_admin_headers,
            json={
                "key": "test_key",
                "value": "test_value"
            },
            timeout=10
        )
        # Should be 400 (validation error) or 422 (unprocessable)
        assert response.status_code in [400, 422]

    def test_set_config_invalid_json(self, api_base_url, platform_admin_headers):
        """Should reject malformed JSON"""
        response = requests.post(
            f"{api_base_url}/api/config",
            headers=platform_admin_headers,
            data="invalid json",
            timeout=10
        )
        # Should be 400 (bad request)
        assert response.status_code in [400, 422]

    def test_set_integration_missing_type(self, api_base_url, platform_admin_headers, test_org_id):
        """Should validate integration type is required"""
        response = requests.post(
            f"{api_base_url}/api/organizations/{test_org_id}/integrations",
            headers=platform_admin_headers,
            json={
                "config": {"key": "value"}
            },
            timeout=10
        )
        # Should be 400 (validation error) or 422 (unprocessable)
        assert response.status_code in [400, 422]

    def test_delete_nonexistent_config(self, api_base_url, platform_admin_headers):
        """Should handle deletion of non-existent config gracefully"""
        response = requests.delete(
            f"{api_base_url}/api/config/nonexistent_config_key_xyz",
            headers=platform_admin_headers,
            timeout=10
        )
        # Should return 204 (idempotent) or 404 (not found)
        assert response.status_code in [204, 200, 404]

    def test_regular_user_cannot_get_config(self, api_base_url, regular_user_headers):
        """Regular users should not list config"""
        response = requests.get(
            f"{api_base_url}/api/config",
            headers=regular_user_headers,
            timeout=10
        )
        assert response.status_code in [403, 401]

    def test_regular_user_cannot_set_config(self, api_base_url, regular_user_headers):
        """Regular users should not set config"""
        response = requests.post(
            f"{api_base_url}/api/config",
            headers=regular_user_headers,
            json={
                "key": "test_key",
                "value": "test_value",
                "type": "string"
            },
            timeout=10
        )
        assert response.status_code in [403, 401]

    def test_set_config_with_description(self, api_base_url, platform_admin_headers):
        """Should set config with description"""
        response = requests.post(
            f"{api_base_url}/api/config",
            headers=platform_admin_headers,
            json={
                "key": "test_config_with_desc",
                "value": "value",
                "type": "string",
                "description": "This is a test configuration"
            },
            timeout=10
        )
        assert response.status_code in [200, 201]

    def test_delete_integration_success(self, api_base_url, platform_admin_headers, test_org_id):
        """Should delete organization integration"""
        response = requests.delete(
            f"{api_base_url}/api/organizations/{test_org_id}/integrations/msgraph",
            headers=platform_admin_headers,
            timeout=10
        )
        # May return 204 (deleted) or 404 (not found)
        assert response.status_code in [200, 204, 404]
