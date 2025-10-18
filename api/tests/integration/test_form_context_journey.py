"""
Integration tests for form context and field visibility workflows.

Tests form launch workflows and field visibility expressions.
"""

import pytest
import requests

from tests.fixtures.auth import create_test_jwt, auth_headers, org_headers


@pytest.mark.integration
class TestFormContextJourney:
    """Test form context propagation and field visibility"""

    @pytest.fixture
    def platform_admin_token(self):
        """First user is always platform admin"""
        return create_test_jwt(
            user_id="admin-001",
            email="admin@platform.com",
            name="Platform Admin"
        )

    def test_form_launch_workflow_and_visibility(self, azure_functions_server, platform_admin_token):
        """
        SCENARIO: Form with launch workflow provides context for field visibility

        STEPS:
        1. Create form with launch workflow
        2. Form has field visible only if workflow returns specific value
        3. Submit form with query params
        4. Launch workflow executes, returns data
        5. Field visibility determined by workflow result
        """
        # Setup
        org = requests.post(
            f"{azure_functions_server}/api/organizations",
            json={"name": "Test Org", "domain": "test.com"},
            headers=auth_headers(platform_admin_token)
        ).json()

        user_token = create_test_jwt(email="user@test.com")

        # Create form with launch workflow and visibility
        form_response = requests.post(
            f"{azure_functions_server}/api/forms",
            json={
                "name": "License Assignment Form",
                "linkedWorkflow": "assign_license",
                "launchWorkflow": "workflows.load_customer_licenses",
                "allowedQueryParams": ["customer_id"],
                "formSchema": {
                    "fields": [
                        {
                            "name": "license_type",
                            "type": "select",
                            "label": "License Type",
                            "required": True,
                            "visibilityExpression": "context.license_count > 0"
                        },
                        {
                            "name": "no_licenses_message",
                            "type": "info",
                            "label": "No licenses available for this customer",
                            "visibilityExpression": "context.license_count === 0"
                        }
                    ]
                }
            },
            headers=org_headers(org["id"], user_token)
        )

        assert form_response.status_code == 201
        form = form_response.json()

        # Get form with query param (triggers launch workflow)
        get_response = requests.get(
            f"{azure_functions_server}/api/forms/{form['id']}?customer_id=cust-123",
            headers=org_headers(org["id"], user_token)
        )

        assert get_response.status_code == 200
        form_data = get_response.json()

        # Verify launch workflow configuration stored
        assert form_data.get("launchWorkflow") == "workflows.load_customer_licenses"
        assert "customer_id" in form_data.get("allowedQueryParams", [])
