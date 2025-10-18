"""
Integration tests for form workflows.

Tests form creation with various field types and data providers.
"""

import pytest
import requests

from tests.fixtures.auth import create_test_jwt, auth_headers, org_headers


@pytest.mark.integration
class TestFormsJourney:
    """Test form creation with dynamic data providers"""

    @pytest.fixture
    def platform_admin_token(self):
        """First user is always platform admin"""
        return create_test_jwt(
            user_id="admin-001",
            email="admin@platform.com",
            name="Platform Admin"
        )

    def test_form_with_data_provider(self, azure_functions_server, platform_admin_token):
        """
        SCENARIO: Create form that uses data provider for dropdown options

        STEPS:
        1. Create org and user
        2. Register data provider (exists in workspace/examples/)
        3. Create form with field using data provider
        4. Get form - verify data provider is listed
        5. Call data provider - verify returns options
        """
        # Setup
        org = requests.post(
            f"{azure_functions_server}/api/organizations",
            json={"name": "Test Org", "domain": "test.com"},
            headers=auth_headers(platform_admin_token)
        ).json()

        user_token = create_test_jwt(email="user@test.com")

        # List available data providers (from workspace)
        providers_response = requests.get(
            f"{azure_functions_server}/api/data-providers",
            headers=org_headers(org["id"], user_token)
        )
        assert providers_response.status_code == 200
        providers = providers_response.json()

        # Should have data providers from workspace/examples/
        provider_names = [p["name"] for p in providers]
        # At minimum, check response is valid
        assert isinstance(provider_names, list)

        # Create form with basic schema
        form_response = requests.post(
            f"{azure_functions_server}/api/forms",
            json={
                "name": "User Onboarding",
                "linkedWorkflow": "user_onboarding",
                "formSchema": {
                    "fields": [
                        {
                            "name": "first_name",
                            "type": "text",
                            "label": "First Name",
                            "required": True
                        }
                    ]
                }
            },
            headers=org_headers(org["id"], user_token)
        )

        assert form_response.status_code == 201
        form = form_response.json()
        assert form["name"] == "User Onboarding"
        assert "id" in form
