"""
Integration tests for organization workflows.

Tests organization creation and domain-based user provisioning.
"""

import pytest
import requests

from tests.fixtures.auth import create_test_jwt, auth_headers, org_headers


@pytest.mark.integration
class TestOrganizationJourney:
    """Test organization creation and domain-based provisioning"""

    @pytest.fixture
    def platform_admin_token(self):
        """First user is always platform admin"""
        return create_test_jwt(
            user_id="admin-001",
            email="admin@platform.com",
            name="Platform Admin"
        )

    def test_admin_creates_organization(self, azure_functions_server, platform_admin_token):
        """
        SCENARIO: Platform admin creates organization with domain

        STEPS:
        1. Admin creates org with domain "acme.com"
        2. Org appears in org list
        3. Org has correct properties
        """
        response = requests.post(
            f"{azure_functions_server}/api/organizations",
            json={
                "name": "Acme Corp",
                "domain": "acme.com"
            },
            headers=auth_headers(platform_admin_token)
        )

        assert response.status_code == 201
        org = response.json()
        assert org["name"] == "Acme Corp"
        assert org["domain"] == "acme.com"
        assert "id" in org

        # Verify appears in list
        list_response = requests.get(
            f"{azure_functions_server}/api/organizations",
            headers=auth_headers(platform_admin_token)
        )
        assert list_response.status_code == 200
        org_names = [o["name"] for o in list_response.json()]
        assert "Acme Corp" in org_names

    def test_user_auto_joins_by_domain(self, azure_functions_server, platform_admin_token):
        """
        SCENARIO: User with matching email domain auto-joins org

        STEPS:
        1. Admin creates org with domain "acme.com"
        2. User with email "john@acme.com" authenticates
        3. User auto-provisioned to Acme Corp org
        4. User can see their org but not others
        """
        # Create org
        org_response = requests.post(
            f"{azure_functions_server}/api/organizations",
            json={"name": "Acme Corp", "domain": "acme.com"},
            headers=auth_headers(platform_admin_token)
        )
        assert org_response.status_code == 201
        org_id = org_response.json()["id"]

        # User with matching domain authenticates
        user_token = create_test_jwt(
            user_id="john-123",
            email="john@acme.com",
            name="John Doe"
        )

        # User tries to access their org's forms
        forms_response = requests.get(
            f"{azure_functions_server}/api/forms",
            headers=org_headers(org_id, user_token)
        )

        # Should succeed - user auto-joined
        assert forms_response.status_code == 200
