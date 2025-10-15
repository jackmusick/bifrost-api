"""
End-to-end tests for Config API
Tests configuration management with Table Storage and Key Vault integration
"""

import pytest
import requests


class TestConfigE2E:
    """Test Config API endpoints"""

    def test_get_global_config_as_platform_admin(self, base_url, platform_admin_headers):
        """Platform admin can retrieve global configuration"""
        response = requests.get(
            f"{base_url}/config?scope=global",
            headers=platform_admin_headers
        )

        assert response.status_code == 200
        configs = response.json()
        assert isinstance(configs, list)

        # Should include seed data configs
        config_keys = [c["key"] for c in configs]
        # Check for system configs from seed data
        if len(configs) > 0:
            # Verify structure
            assert "key" in configs[0]
            assert "value" in configs[0]
            assert "type" in configs[0]

    def test_create_global_config(self, base_url, platform_admin_headers):
        """Platform admin can create global configuration"""
        response = requests.post(
            f"{base_url}/config",
            headers=platform_admin_headers,
            json={
                "key": "test_global_config",
                "value": "test_value",
                "type": "string",
                "scope": "GLOBAL",
                "description": "Test global configuration"
            }
        )

        # API uses upsert semantics: 201 for new, 200 for update
        assert response.status_code in [200, 201]
        config = response.json()
        assert config["key"] == "test_global_config"
        assert config["value"] == "test_value"
        assert config["type"] == "string"
        assert config["scope"] == "GLOBAL"

        # Verify we can retrieve it
        get_response = requests.get(
            f"{base_url}/config?scope=global",
            headers=platform_admin_headers
        )
        configs = get_response.json()
        test_config = next((c for c in configs if c["key"] == "test_global_config"), None)
        assert test_config is not None

    def test_update_global_config(self, base_url, platform_admin_headers):
        """Platform admin can update global configuration"""
        # First create a config
        create_response = requests.post(
            f"{base_url}/config",
            headers=platform_admin_headers,
            json={
                "key": "test_update_config",
                "value": "original_value",
                "type": "string",
                "scope": "GLOBAL"
            }
        )
        assert create_response.status_code in [200, 201]

        # Update it
        update_response = requests.post(
            f"{base_url}/config",
            headers=platform_admin_headers,
            json={
                "key": "test_update_config",
                "value": "updated_value",
                "type": "string",
                "scope": "GLOBAL"
            }
        )

        assert update_response.status_code == 200
        updated_config = update_response.json()
        assert updated_config["value"] == "updated_value"

    def test_delete_global_config(self, base_url, platform_admin_headers):
        """Platform admin can delete global configuration"""
        # First create a config to delete
        requests.post(
            f"{base_url}/config",
            headers=platform_admin_headers,
            json={
                "key": "test_delete_config",
                "value": "to_be_deleted",
                "type": "string",
                "scope": "GLOBAL"
            }
        )

        # Delete it
        delete_response = requests.delete(
            f"{base_url}/config/test_delete_config?scope=global",
            headers=platform_admin_headers
        )

        assert delete_response.status_code == 204

        # Verify it's gone
        get_response = requests.get(
            f"{base_url}/config?scope=global",
            headers=platform_admin_headers
        )
        configs = get_response.json()
        deleted_config = next((c for c in configs if c["key"] == "test_delete_config"), None)
        assert deleted_config is None

    def test_create_org_config(self, base_url, platform_admin_headers):
        """Platform admin can create org-specific configuration"""
        # Use the Covi Development org from seed data
        org_id = "546478ea-fc38-4bf7-a524-35f522f90b0e"

        response = requests.post(
            f"{base_url}/config?orgId={org_id}",
            headers=platform_admin_headers,
            json={
                "key": "test_org_config",
                "value": "org_value",
                "type": "string",
                "scope": "org",
                "description": "Test org configuration"
            }
        )

        assert response.status_code in [200, 201]
        config = response.json()
        assert config["key"] == "test_org_config"
        assert config["value"] == "org_value"
        assert config["scope"] == "org"
        assert config["orgId"] == org_id

    def test_get_org_config(self, base_url, platform_admin_headers):
        """Platform admin can retrieve org-specific configuration"""
        org_id = "546478ea-fc38-4bf7-a524-35f522f90b0e"

        response = requests.get(
            f"{base_url}/config?scope=org&orgId={org_id}",
            headers=platform_admin_headers
        )

        assert response.status_code == 200
        configs = response.json()
        assert isinstance(configs, list)

        # Should include seed data org configs
        if len(configs) > 0:
            assert "key" in configs[0]
            assert configs[0].get("orgId") == org_id

    def test_config_with_secret_ref_type(self, base_url, platform_admin_headers):
        """
        Create config with secret_ref type (points to Key Vault secret).

        This tests the integration between Config API and Key Vault:
        1. Config stores the secret reference name
        2. Actual secret value is in Key Vault
        3. secret_ref values are NOT masked in responses (just the reference name)
        """
        response = requests.post(
            f"{base_url}/config",
            headers=platform_admin_headers,
            json={
                "key": "test_secret_reference",
                "value": "my-keyvault-secret-name",  # This is the Key Vault secret name
                "type": "secret_ref",
                "scope": "GLOBAL",
                "description": "Reference to Key Vault secret"
            }
        )

        assert response.status_code in [200, 201]
        config = response.json()
        assert config["type"] == "secret_ref"
        # secret_ref types should NOT be masked (it's just a reference name)
        assert config["value"] == "my-keyvault-secret-name"

    def test_config_sensitive_value_masking(self, base_url, platform_admin_headers):
        """
        Sensitive config values (not secret_ref) are masked in API responses.

        Keys containing 'secret', 'password', 'token', 'key', 'credential' are masked.
        """
        response = requests.post(
            f"{base_url}/config",
            headers=platform_admin_headers,
            json={
                "key": "api_secret_key",  # Contains 'secret' keyword
                "value": "my-very-secret-value-12345",
                "type": "string",  # NOT secret_ref
                "scope": "GLOBAL"
            }
        )

        assert response.status_code in [200, 201]
        config = response.json()
        # Sensitive string values should be masked: "my-v***2345"
        assert "***" in config["value"]
        assert len(config["value"]) < len("my-very-secret-value-12345")

    def test_config_validation_error(self, base_url, platform_admin_headers):
        """Creating config without required fields returns validation error"""
        response = requests.post(
            f"{base_url}/config",
            headers=platform_admin_headers,
            json={
                "key": "incomplete_config"
                # Missing: value, type, scope
            }
        )

        assert response.status_code == 400
        error = response.json()
        assert error["error"] == "ValidationError"

    def test_config_org_user_forbidden(self, base_url, org_user_headers):
        """Org users cannot access config endpoints (platform admin only)"""
        response = requests.get(
            f"{base_url}/config?scope=global",
            headers=org_user_headers
        )

        assert response.status_code == 403

    @pytest.mark.skip(reason="Local dev mode treats anonymous as admin")
    def test_config_anonymous_unauthorized(self, base_url, anonymous_headers):
        """Anonymous users should be rejected in production"""
        response = requests.get(
            f"{base_url}/config?scope=global",
            headers=anonymous_headers
        )

        assert response.status_code == 401


class TestIntegrationConfigE2E:
    """Test Integration Config API endpoints"""

    def test_get_integrations_for_org(self, base_url, platform_admin_headers):
        """Platform admin can retrieve integrations for an organization"""
        org_id = "546478ea-fc38-4bf7-a524-35f522f90b0e"

        response = requests.get(
            f"{base_url}/organizations/{org_id}/integrations",
            headers=platform_admin_headers
        )

        assert response.status_code == 200
        integrations = response.json()
        assert isinstance(integrations, list)

        # Should include seed data integrations (msgraph)
        if len(integrations) > 0:
            integration = integrations[0]
            assert "type" in integration
            assert "enabled" in integration
            assert "settings" in integration

    def test_create_integration_config(self, base_url, platform_admin_headers):
        """Platform admin can create integration configuration"""
        org_id = "546478ea-fc38-4bf7-a524-35f522f90b0e"

        response = requests.post(
            f"{base_url}/organizations/{org_id}/integrations",
            headers=platform_admin_headers,
            json={
                "type": "halopsa",
                "enabled": True,
                "settings": {
                    "api_url": "https://test.halopsa.com",
                    "client_id": "test-client-id",
                    "api_key_ref": "test-api-key-ref"  # Reference to Key Vault secret
                }
            }
        )

        assert response.status_code in [200, 201]
        integration = response.json()
        assert integration["type"] == "halopsa"
        assert integration["enabled"] is True
        assert integration["settings"]["api_url"] == "https://test.halopsa.com"

    def test_update_integration_config(self, base_url, platform_admin_headers):
        """Platform admin can update integration configuration"""
        org_id = "546478ea-fc38-4bf7-a524-35f522f90b0e"

        # Use msgraph type (valid IntegrationType)
        # First create with required fields
        create_response = requests.post(
            f"{base_url}/organizations/{org_id}/integrations",
            headers=platform_admin_headers,
            json={
                "type": "msgraph",
                "enabled": True,
                "settings": {
                    "tenant_id": "test-tenant-id",
                    "client_id": "test-client-id",
                    "client_secret_ref": "test-secret-ref"
                }
            }
        )
        assert create_response.status_code in [200, 201]

        # Update it
        update_response = requests.post(
            f"{base_url}/organizations/{org_id}/integrations",
            headers=platform_admin_headers,
            json={
                "type": "msgraph",
                "enabled": False,
                "settings": {
                    "tenant_id": "updated-tenant-id",
                    "client_id": "updated-client-id",
                    "client_secret_ref": "updated-secret-ref"
                }
            }
        )

        assert update_response.status_code == 200
        updated_integration = update_response.json()
        assert updated_integration["enabled"] is False
        assert updated_integration["settings"]["tenant_id"] == "updated-tenant-id"

    def test_delete_integration_config(self, base_url, platform_admin_headers):
        """Platform admin can delete integration configuration"""
        org_id = "546478ea-fc38-4bf7-a524-35f522f90b0e"

        # First create
        requests.post(
            f"{base_url}/organizations/{org_id}/integrations",
            headers=platform_admin_headers,
            json={
                "type": "to_delete_integration",
                "enabled": True,
                "settings": {}
            }
        )

        # Delete
        delete_response = requests.delete(
            f"{base_url}/organizations/{org_id}/integrations/to_delete_integration",
            headers=platform_admin_headers
        )

        assert delete_response.status_code == 204

        # Verify it's gone
        get_response = requests.get(
            f"{base_url}/organizations/{org_id}/integrations",
            headers=platform_admin_headers
        )
        integrations = get_response.json()
        deleted_integration = next(
            (i for i in integrations if i["type"] == "to_delete_integration"),
            None
        )
        assert deleted_integration is None
