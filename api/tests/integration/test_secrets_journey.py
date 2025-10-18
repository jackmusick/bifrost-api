"""
Integration tests for secrets management workflows.

Tests org secret isolation and secret access patterns.
"""

import pytest
import requests

from tests.fixtures.auth import create_test_jwt, auth_headers, org_headers


@pytest.mark.integration
class TestSecretsJourney:
    """Test secrets management and isolation"""

    @pytest.fixture
    def platform_admin_token(self):
        """First user is always platform admin"""
        return create_test_jwt(
            user_id="admin-001",
            email="admin@platform.com",
            name="Platform Admin"
        )

    def test_org_secrets_isolated(self, azure_functions_server, platform_admin_token):
        """
        SCENARIO: Org secrets are isolated between organizations

        STEPS:
        1. Create two orgs
        2. Each org creates secret with same key name
        3. Each org can only see their own secret
        """
        # Create Org A
        org_a = requests.post(
            f"{azure_functions_server}/api/organizations",
            json={"name": "Org A", "domain": "orga.com"},
            headers=auth_headers(platform_admin_token)
        ).json()

        # Create Org B
        org_b = requests.post(
            f"{azure_functions_server}/api/organizations",
            json={"name": "Org B", "domain": "orgb.com"},
            headers=auth_headers(platform_admin_token)
        ).json()

        # Org A creates secret
        org_a_token = create_test_jwt(email="user@orga.com")
        requests.post(
            f"{azure_functions_server}/api/secrets",
            json={
                "key": "api_key",
                "value": "secret-a-value",
                "organizationId": org_a["id"]
            },
            headers=org_headers(org_a["id"], org_a_token)
        )

        # Org B creates secret with SAME key
        org_b_token = create_test_jwt(email="user@orgb.com")
        requests.post(
            f"{azure_functions_server}/api/secrets",
            json={
                "key": "api_key",
                "value": "secret-b-value",
                "organizationId": org_b["id"]
            },
            headers=org_headers(org_b["id"], org_b_token)
        )

        # Org A gets their secret
        get_a = requests.get(
            f"{azure_functions_server}/api/secrets/api_key",
            headers=org_headers(org_a["id"], org_a_token)
        )
        assert get_a.status_code == 200
        assert get_a.json()["value"] == "secret-a-value"

        # Org B gets their secret
        get_b = requests.get(
            f"{azure_functions_server}/api/secrets/api_key",
            headers=org_headers(org_b["id"], org_b_token)
        )
        assert get_b.status_code == 200
        assert get_b.json()["value"] == "secret-b-value"
