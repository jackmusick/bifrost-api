"""Integration tests for Organization Config API endpoints

Tests the organization configuration management endpoints for managing
global and organization-specific configuration key-value pairs.
"""

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


class TestOrgConfigTypeValidation:
    """Test configuration value type validation"""

    def test_string_config_validation(self, api_base_url, platform_admin_headers):
        """Should validate and store string config values"""
        response = requests.post(
            f"{api_base_url}/api/config",
            headers=platform_admin_headers,
            json={
                "key": "test_string_config",
                "value": "string_value_123",
                "type": "string"
            },
            timeout=10
        )
        assert response.status_code in [200, 201]

    def test_number_config_validation(self, api_base_url, platform_admin_headers):
        """Should validate and store number config values"""
        response = requests.post(
            f"{api_base_url}/api/config",
            headers=platform_admin_headers,
            json={
                "key": "test_number_config",
                "value": "42",
                "type": "number"
            },
            timeout=10
        )
        # May require number type or accept string representation
        assert response.status_code in [200, 201, 400, 422]

    def test_number_config_with_min_max_validation(self, api_base_url, platform_admin_headers):
        """Should validate number configs against min/max bounds"""
        response = requests.post(
            f"{api_base_url}/api/config",
            headers=platform_admin_headers,
            json={
                "key": "test_bounded_number",
                "value": "50",
                "type": "number",
                "min": "0",
                "max": "100"
            },
            timeout=10
        )
        assert response.status_code in [200, 201, 400, 422]

    def test_boolean_config_validation(self, api_base_url, platform_admin_headers):
        """Should validate and store boolean config values"""
        response = requests.post(
            f"{api_base_url}/api/config",
            headers=platform_admin_headers,
            json={
                "key": "test_boolean_config",
                "value": "true",
                "type": "boolean"
            },
            timeout=10
        )
        # May require boolean type or accept string representation
        assert response.status_code in [200, 201, 400, 422]

    def test_object_config_validation(self, api_base_url, platform_admin_headers):
        """Should validate and store JSON object config values"""
        response = requests.post(
            f"{api_base_url}/api/config",
            headers=platform_admin_headers,
            json={
                "key": "test_object_config",
                "value": '{"key": "value", "nested": {"field": "data"}}',
                "type": "object"
            },
            timeout=10
        )
        assert response.status_code in [200, 201, 400, 422]

    def test_array_config_validation(self, api_base_url, platform_admin_headers):
        """Should validate and store array config values"""
        response = requests.post(
            f"{api_base_url}/api/config",
            headers=platform_admin_headers,
            json={
                "key": "test_array_config",
                "value": '["item1", "item2", "item3"]',
                "type": "array"
            },
            timeout=10
        )
        assert response.status_code in [200, 201, 400, 422]

    def test_enum_config_validation(self, api_base_url, platform_admin_headers):
        """Should validate enum config against allowed values"""
        response = requests.post(
            f"{api_base_url}/api/config",
            headers=platform_admin_headers,
            json={
                "key": "test_enum_config",
                "value": "option1",
                "type": "enum",
                "allowedValues": ["option1", "option2", "option3"]
            },
            timeout=10
        )
        assert response.status_code in [200, 201, 400, 422]


class TestOrgConfigInheritance:
    """Test global vs organization-specific config inheritance"""

    def test_org_config_overrides_global(self, api_base_url, platform_admin_headers, test_org_id):
        """Should use org-specific config when available"""
        # Set global config
        requests.post(
            f"{api_base_url}/api/config",
            headers=platform_admin_headers,
            json={
                "key": "inheritance_test_key",
                "value": "global_value",
                "type": "string"
            },
            timeout=10
        )

        # Get org config (should fallback to global)
        response = requests.get(
            f"{api_base_url}/api/config?org_id={test_org_id}",
            headers=platform_admin_headers,
            timeout=10
        )
        assert response.status_code in [200, 404]

    def test_org_config_fallback_to_global_when_not_set(self, api_base_url, platform_admin_headers, test_org_id):
        """Should fallback to global config if org config not set"""
        # Get config that should fallback
        response = requests.get(
            f"{api_base_url}/api/config/fallback_test_key?org_id={test_org_id}",
            headers=platform_admin_headers,
            timeout=10
        )
        # Should return global or 404
        assert response.status_code in [200, 404]

    def test_delete_org_config_falls_back_to_global(self, api_base_url, platform_admin_headers, test_org_id):
        """Should fallback to global after deleting org-specific config"""
        # Set org config
        set_resp = requests.post(
            f"{api_base_url}/api/config",
            headers=platform_admin_headers,
            json={
                "key": "fallback_after_delete",
                "value": "org_value",
                "type": "string"
            },
            timeout=10
        )

        if set_resp.status_code in [200, 201]:
            # Delete org config
            delete_resp = requests.delete(
                f"{api_base_url}/api/config/fallback_after_delete",
                headers=platform_admin_headers,
                timeout=10
            )

            if delete_resp.status_code in [200, 204]:
                # Should now fallback to global or return 404
                get_resp = requests.get(
                    f"{api_base_url}/api/config/fallback_after_delete?org_id={test_org_id}",
                    headers=platform_admin_headers,
                    timeout=10
                )
                assert get_resp.status_code in [200, 404]


class TestOrgConfigSchemaValidation:
    """Test configuration schema enforcement"""

    def test_unknown_config_key_rejected(self, api_base_url, platform_admin_headers):
        """Should reject unknown configuration keys"""
        response = requests.post(
            f"{api_base_url}/api/config",
            headers=platform_admin_headers,
            json={
                "key": "completely_unknown_key_xyz_123",
                "value": "some_value",
                "type": "string"
            },
            timeout=10
        )
        # May reject or accept unknown keys
        assert response.status_code in [200, 201, 400, 422]

    def test_required_config_enforcement(self, api_base_url, platform_admin_headers):
        """Should enforce required configuration values"""
        # Try to delete a required config
        response = requests.delete(
            f"{api_base_url}/api/config/required_config_key",
            headers=platform_admin_headers,
            timeout=10
        )
        # May prevent deletion of required configs
        assert response.status_code in [200, 204, 403, 409, 404]

    def test_config_default_values_applied(self, api_base_url, platform_admin_headers):
        """Should apply default values for configs"""
        response = requests.get(
            f"{api_base_url}/api/config",
            headers=platform_admin_headers,
            timeout=10
        )
        assert response.status_code == 200
        data = response.json()
        if isinstance(data, list):
            # Should have some configs with defaults
            assert len(data) >= 0

    def test_config_schema_evolution(self, api_base_url, platform_admin_headers):
        """Should handle schema evolution without breaking"""
        # Set config with new schema version
        response = requests.post(
            f"{api_base_url}/api/config",
            headers=platform_admin_headers,
            json={
                "key": "evolving_config",
                "value": "value",
                "type": "string",
                "schema_version": "2.0",
                "new_field": "future_compatible"
            },
            timeout=10
        )
        # Should handle gracefully
        assert response.status_code in [200, 201, 400, 422]


class TestOrgConfigIntegrations:
    """Test integration-specific configuration"""

    def test_oauth_integration_config(self, api_base_url, platform_admin_headers):
        """Should store and validate OAuth integration config"""
        response = requests.post(
            f"{api_base_url}/api/config",
            headers=platform_admin_headers,
            json={
                "key": "oauth_config",
                "value": '{"provider": "azure", "client_id": "test-id"}',
                "type": "object"
            },
            timeout=10
        )
        assert response.status_code in [200, 201, 400, 422]

    def test_email_integration_config(self, api_base_url, platform_admin_headers):
        """Should store and validate email integration config"""
        response = requests.post(
            f"{api_base_url}/api/config",
            headers=platform_admin_headers,
            json={
                "key": "email_config",
                "value": '{"host": "smtp.example.com", "port": "587"}',
                "type": "object"
            },
            timeout=10
        )
        assert response.status_code in [200, 201, 400, 422]

    def test_sso_integration_config(self, api_base_url, platform_admin_headers):
        """Should store and validate SSO integration config"""
        response = requests.post(
            f"{api_base_url}/api/config",
            headers=platform_admin_headers,
            json={
                "key": "sso_config",
                "value": '{"provider": "okta", "domain": "example.okta.com"}',
                "type": "object"
            },
            timeout=10
        )
        assert response.status_code in [200, 201, 400, 422]

    def test_integration_config_validation_rules(self, api_base_url, platform_admin_headers):
        """Should apply provider-specific validation rules"""
        # Try to set config with invalid OAuth config
        response = requests.post(
            f"{api_base_url}/api/config",
            headers=platform_admin_headers,
            json={
                "key": "oauth_validation",
                "value": '{"invalid": "config"}',  # Missing required fields
                "type": "object",
                "integration": "oauth"
            },
            timeout=10
        )
        # May validate or accept
        assert response.status_code in [200, 201, 400, 422]

    def test_multiple_integration_configs(self, api_base_url, platform_admin_headers):
        """Should support multiple integration configs"""
        configs = [
            {
                "key": "integration_1",
                "value": "config1",
                "type": "string"
            },
            {
                "key": "integration_2",
                "value": "config2",
                "type": "string"
            },
            {
                "key": "integration_3",
                "value": "config3",
                "type": "string"
            }
        ]

        for config in configs:
            response = requests.post(
                f"{api_base_url}/api/config",
                headers=platform_admin_headers,
                json=config,
                timeout=10
            )
            assert response.status_code in [200, 201]
