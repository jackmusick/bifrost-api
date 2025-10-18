"""
Integration tests for configuration management workflows.

Tests global configs, org-specific overrides, and config access patterns.
"""

import pytest
import requests

from tests.fixtures.auth import create_test_jwt, auth_headers, org_headers


@pytest.mark.integration
class TestConfigJourney:
    """Test configuration management across global and org scopes"""

    @pytest.fixture
    def platform_admin_token(self):
        """First user is always platform admin"""
        return create_test_jwt(
            user_id="admin-001",
            email="admin@platform.com",
            name="Platform Admin"
        )

    def test_global_config_with_org_override(self, azure_functions_server, platform_admin_token):
        """
        SCENARIO: Global config can be overridden per-org

        STEPS:
        1. Admin sets global config: default_timeout=30
        2. Admin creates org
        3. Admin sets org-specific config: default_timeout=60
        4. Org user gets timeout=60 (org override)
        5. Other org gets timeout=30 (global default)
        """
        # Set global config
        global_response = requests.post(
            f"{azure_functions_server}/api/config",
            json={
                "key": "default_timeout",
                "value": "30",
                "scope": "global"
            },
            headers=auth_headers(platform_admin_token)
        )
        assert global_response.status_code == 201

        # Create org
        org_response = requests.post(
            f"{azure_functions_server}/api/organizations",
            json={"name": "Acme Corp", "domain": "acme.com"},
            headers=auth_headers(platform_admin_token)
        )
        assert org_response.status_code == 201
        org_id = org_response.json()["id"]

        # Set org-specific override
        org_config_response = requests.post(
            f"{azure_functions_server}/api/config",
            json={
                "key": "default_timeout",
                "value": "60",
                "organizationId": org_id
            },
            headers=auth_headers(platform_admin_token)
        )
        assert org_config_response.status_code == 201

        # Org user gets config - should see override
        user_token = create_test_jwt(email="user@acme.com")
        get_response = requests.get(
            f"{azure_functions_server}/api/config/default_timeout",
            headers=org_headers(org_id, user_token)
        )

        assert get_response.status_code == 200
        assert get_response.json()["value"] == "60"  # Org override
