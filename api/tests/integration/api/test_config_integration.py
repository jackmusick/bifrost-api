"""
Integration tests for Config API
Tests configuration management by calling Azure Functions directly (no HTTP)
"""

import pytest

from functions.org_config import (
    delete_config,
    delete_integration,
    get_config,
    get_integrations,
    set_config,
    set_integration,
)
from tests.helpers.http_helpers import (
    create_mock_request,
    create_org_user_headers,
    create_platform_admin_headers,
    parse_response,
)


class TestConfigIntegration:
    """Test Config API endpoints"""

    @pytest.mark.asyncio
    async def test_get_global_config_as_platform_admin(self):
        """Platform admin can retrieve global configuration"""
        req = create_mock_request(
            method="GET",
            url="/api/config?scope=global",
            headers=create_platform_admin_headers(),
            query_params={"scope": "global"},
        )

        response = await get_config(req)
        status, body = parse_response(response)

        assert status == 200
        configs = body
        assert isinstance(configs, list)

        # Should include seed data configs
        # Check for system configs from seed data
        if len(configs) > 0:
            # Verify structure
            assert "key" in configs[0]
            assert "value" in configs[0]
            assert "type" in configs[0]

    @pytest.mark.asyncio
    async def test_create_global_config(self):
        """Platform admin can create global configuration"""
        req = create_mock_request(
            method="POST",
            url="/api/config",
            headers=create_platform_admin_headers(),
            body={
                "key": "test_global_config",
                "value": "test_value",
                "type": "string",
                "description": "Test global configuration"
            },
        )

        response = await set_config(req)
        status, body = parse_response(response)

        # API uses upsert semantics: 201 for new, 200 for update
        assert status in [200, 201]
        config = body
        assert config["key"] == "test_global_config"
        assert config["value"] == "test_value"
        assert config["type"] == "string"
        assert config["scope"] == "GLOBAL"

        # Verify we can retrieve it
        get_req = create_mock_request(
            method="GET",
            url="/api/config?scope=global",
            headers=create_platform_admin_headers(),
            query_params={"scope": "global"},
        )

        get_response = await get_config(get_req)
        get_status, get_body = parse_response(get_response)
        assert get_status == 200
        configs = get_body
        test_config = next((c for c in configs if c["key"] == "test_global_config"), None)
        assert test_config is not None

    @pytest.mark.asyncio
    async def test_update_global_config(self):
        """Platform admin can update global configuration"""
        # First create a config
        create_req = create_mock_request(
            method="POST",
            url="/api/config",
            headers=create_platform_admin_headers(),
            body={
                "key": "test_update_config",
                "value": "original_value",
                "type": "string"
            },
        )

        create_response = await set_config(create_req)
        create_status, _ = parse_response(create_response)
        assert create_status in [200, 201]

        # Update it
        update_req = create_mock_request(
            method="POST",
            url="/api/config",
            headers=create_platform_admin_headers(),
            body={
                "key": "test_update_config",
                "value": "updated_value",
                "type": "string"
            },
        )

        response = await set_config(update_req)
        status, body = parse_response(response)

        assert status == 200
        updated_config = body
        assert updated_config["value"] == "updated_value"

    @pytest.mark.asyncio
    async def test_delete_global_config(self):
        """Platform admin can delete global configuration"""
        # First create a config to delete
        create_req = create_mock_request(
            method="POST",
            url="/api/config",
            headers=create_platform_admin_headers(),
            body={
                "key": "test_delete_config",
                "value": "to_be_deleted",
                "type": "string"
            },
        )

        await set_config(create_req)

        # Delete it (scope determined by absence of X-Organization-Id header)
        delete_req = create_mock_request(
            method="DELETE",
            url="/api/config/test_delete_config",
            headers=create_platform_admin_headers(),
            route_params={"key": "test_delete_config"},
        )

        response = await delete_config(delete_req)
        status, _ = parse_response(response)

        assert status == 204

        # Verify it's gone
        get_req = create_mock_request(
            method="GET",
            url="/api/config?scope=global",
            headers=create_platform_admin_headers(),
            query_params={"scope": "global"},
        )

        get_response = await get_config(get_req)
        get_status, get_body = parse_response(get_response)
        assert get_status == 200
        configs = get_body
        deleted_config = next((c for c in configs if c["key"] == "test_delete_config"), None)
        assert deleted_config is None

    @pytest.mark.asyncio
    async def test_create_org_config(self):
        """Platform admin can create org-specific configuration"""
        # Use the Covi Development org from seed data
        org_id = "546478ea-fc38-4bf7-a524-35f522f90b0e"

        # Add X-Organization-Id header to specify org scope
        org_headers = {**create_platform_admin_headers(), "X-Organization-Id": org_id}

        req = create_mock_request(
            method="POST",
            url="/api/config",
            headers=org_headers,
            body={
                "key": "test_org_config",
                "value": "org_value",
                "type": "string",
                "description": "Test org configuration"
            },
        )

        response = await set_config(req)
        status, body = parse_response(response)

        assert status in [200, 201]
        config = body
        assert config["key"] == "test_org_config"
        assert config["value"] == "org_value"
        assert config["scope"] == "org"
        assert config["orgId"] == org_id

    @pytest.mark.asyncio
    async def test_get_org_config(self):
        """Platform admin can retrieve org-specific configuration"""
        org_id = "546478ea-fc38-4bf7-a524-35f522f90b0e"

        # Add X-Organization-Id header to specify org scope
        org_headers = {**create_platform_admin_headers(), "X-Organization-Id": org_id}

        req = create_mock_request(
            method="GET",
            url="/api/config",
            headers=org_headers,
        )

        response = await get_config(req)
        status, body = parse_response(response)

        assert status == 200
        configs = body
        assert isinstance(configs, list)

        # Should include seed data org configs
        if len(configs) > 0:
            assert "key" in configs[0]
            assert configs[0].get("orgId") == org_id

    @pytest.mark.asyncio
    async def test_config_with_secret_ref_type(self):
        """
        Create config with secret_ref type (points to Key Vault secret).

        This tests the integration between Config API and Key Vault:
        1. Config stores the secret reference name
        2. Actual secret value is in Key Vault
        3. secret_ref values are NOT masked in responses (just the reference name)
        """
        req = create_mock_request(
            method="POST",
            url="/api/config",
            headers=create_platform_admin_headers(),
            body={
                "key": "test_secret_reference",
                "value": "my-keyvault-secret-name",  # This is the Key Vault secret name
                "type": "secret_ref",
                "description": "Reference to Key Vault secret"
            },
        )

        response = await set_config(req)
        status, body = parse_response(response)

        assert status in [200, 201]
        config = body
        assert config["type"] == "secret_ref"
        # secret_ref types should NOT be masked (it's just a reference name)
        assert config["value"] == "my-keyvault-secret-name"

    @pytest.mark.asyncio
    async def test_config_sensitive_value_masking(self):
        """
        Sensitive config values (not secret_ref) are masked in API responses.

        Keys containing 'secret', 'password', 'token', 'key', 'credential' are masked.
        """
        req = create_mock_request(
            method="POST",
            url="/api/config",
            headers=create_platform_admin_headers(),
            body={
                "key": "api_secret_key",  # Contains 'secret' keyword
                "value": "my-very-secret-value-12345",
                "type": "string"  # NOT secret_ref
            },
        )

        response = await set_config(req)
        status, body = parse_response(response)

        assert status in [200, 201]
        config = body
        # Sensitive string values should be masked: "my-v***2345"
        assert "***" in config["value"]
        assert len(config["value"]) < len("my-very-secret-value-12345")

    @pytest.mark.asyncio
    async def test_config_validation_error(self):
        """Creating config without required fields returns validation error"""
        req = create_mock_request(
            method="POST",
            url="/api/config",
            headers=create_platform_admin_headers(),
            body={
                "key": "incomplete_config"
                # Missing: value, type, scope
            },
        )

        response = await set_config(req)
        status, body = parse_response(response)

        assert status == 400
        error = body
        assert error["error"] == "ValidationError"

    @pytest.mark.asyncio
    async def test_config_org_user_forbidden(self):
        """Org users cannot access config endpoints (platform admin only)"""
        req = create_mock_request(
            method="GET",
            url="/api/config?scope=global",
            headers=create_org_user_headers(),
            query_params={"scope": "global"},
        )

        response = await get_config(req)
        status, _ = parse_response(response)

        assert status == 403


class TestIntegrationConfigIntegration:
    """Test Integration Config API endpoints"""

    @pytest.mark.asyncio
    async def test_get_integrations_for_org(self):
        """Platform admin can retrieve integrations for an organization"""
        org_id = "546478ea-fc38-4bf7-a524-35f522f90b0e"

        req = create_mock_request(
            method="GET",
            url=f"/api/organizations/{org_id}/integrations",
            headers=create_platform_admin_headers(),
            route_params={"orgId": org_id},
        )

        response = await get_integrations(req)
        status, body = parse_response(response)

        assert status == 200
        integrations = body
        assert isinstance(integrations, list)

        # Should include seed data integrations (msgraph)
        if len(integrations) > 0:
            integration = integrations[0]
            assert "type" in integration
            assert "enabled" in integration
            assert "settings" in integration

    @pytest.mark.asyncio
    async def test_create_integration_config(self):
        """Platform admin can create integration configuration"""
        org_id = "546478ea-fc38-4bf7-a524-35f522f90b0e"

        req = create_mock_request(
            method="POST",
            url=f"/api/organizations/{org_id}/integrations",
            headers=create_platform_admin_headers(),
            route_params={"orgId": org_id},
            body={
                "type": "halopsa",
                "enabled": True,
                "settings": {
                    "api_url": "https://test.halopsa.com",
                    "client_id": "test-client-id",
                    "api_key_ref": "test-api-key-ref"  # Reference to Key Vault secret
                }
            },
        )

        response = await set_integration(req)
        status, body = parse_response(response)

        assert status in [200, 201]
        integration = body
        assert integration["type"] == "halopsa"
        assert integration["enabled"] is True
        assert integration["settings"]["api_url"] == "https://test.halopsa.com"

    @pytest.mark.asyncio
    async def test_update_integration_config(self):
        """Platform admin can update integration configuration"""
        org_id = "546478ea-fc38-4bf7-a524-35f522f90b0e"

        # Use msgraph type (valid IntegrationType)
        # First create with required fields
        create_req = create_mock_request(
            method="POST",
            url=f"/api/organizations/{org_id}/integrations",
            headers=create_platform_admin_headers(),
            route_params={"orgId": org_id},
            body={
                "type": "msgraph",
                "enabled": True,
                "settings": {
                    "tenant_id": "test-tenant-id",
                    "client_id": "test-client-id",
                    "client_secret_ref": "test-secret-ref"
                }
            },
        )

        create_response = await set_integration(create_req)
        create_status, _ = parse_response(create_response)
        assert create_status in [200, 201]

        # Update it
        update_req = create_mock_request(
            method="POST",
            url=f"/api/organizations/{org_id}/integrations",
            headers=create_platform_admin_headers(),
            route_params={"orgId": org_id},
            body={
                "type": "msgraph",
                "enabled": False,
                "settings": {
                    "tenant_id": "updated-tenant-id",
                    "client_id": "updated-client-id",
                    "client_secret_ref": "updated-secret-ref"
                }
            },
        )

        response = await set_integration(update_req)
        status, body = parse_response(response)

        assert status == 200
        updated_integration = body
        assert updated_integration["enabled"] is False
        assert updated_integration["settings"]["tenant_id"] == "updated-tenant-id"

    @pytest.mark.asyncio
    async def test_delete_integration_config(self):
        """Platform admin can delete integration configuration"""
        org_id = "546478ea-fc38-4bf7-a524-35f522f90b0e"

        # First create
        create_req = create_mock_request(
            method="POST",
            url=f"/api/organizations/{org_id}/integrations",
            headers=create_platform_admin_headers(),
            route_params={"orgId": org_id},
            body={
                "type": "to_delete_integration",
                "enabled": True,
                "settings": {}
            },
        )

        await set_integration(create_req)

        # Delete
        delete_req = create_mock_request(
            method="DELETE",
            url=f"/api/organizations/{org_id}/integrations/to_delete_integration",
            headers=create_platform_admin_headers(),
            route_params={"orgId": org_id, "type": "to_delete_integration"},
        )

        response = await delete_integration(delete_req)
        status, _ = parse_response(response)

        assert status == 204

        # Verify it's gone
        get_req = create_mock_request(
            method="GET",
            url=f"/api/organizations/{org_id}/integrations",
            headers=create_platform_admin_headers(),
            route_params={"orgId": org_id},
        )

        get_response = await get_integrations(get_req)
        get_status, get_body = parse_response(get_response)
        assert get_status == 200
        integrations = get_body
        deleted_integration = next(
            (i for i in integrations if i["type"] == "to_delete_integration"),
            None
        )
        assert deleted_integration is None
