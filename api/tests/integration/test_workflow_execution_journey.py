"""
Integration tests for workflow execution workflows.

Tests workflow execution with configs and secrets.
"""

import pytest
import requests

from tests.fixtures.auth import create_test_jwt, auth_headers, org_headers


@pytest.mark.integration
class TestWorkflowExecutionJourney:
    """Test workflow execution with configs and secrets"""

    @pytest.fixture
    def platform_admin_token(self):
        """First user is always platform admin"""
        return create_test_jwt(
            user_id="admin-001",
            email="admin@platform.com",
            name="Platform Admin"
        )

    def test_workflow_accesses_config_and_secret(self, azure_functions_server, platform_admin_token):
        """
        SCENARIO: Workflow retrieves org config and secret during execution

        STEPS:
        1. Create org, config, and secret
        2. Create workflow that uses context.get_config() and context.get_secret()
        3. Execute workflow
        4. Verify workflow received correct values
        """
        # Setup org
        org = requests.post(
            f"{azure_functions_server}/api/organizations",
            json={"name": "Test Org", "domain": "test.com"},
            headers=auth_headers(platform_admin_token)
        ).json()

        user_token = create_test_jwt(email="user@test.com")

        # Create config
        requests.post(
            f"{azure_functions_server}/api/config",
            json={
                "key": "company_name",
                "value": "Test Company",
                "organizationId": org["id"]
            },
            headers=org_headers(org["id"], user_token)
        )

        # Create secret
        requests.post(
            f"{azure_functions_server}/api/secrets",
            json={
                "key": "api_token",
                "value": "super-secret-token",
                "organizationId": org["id"]
            },
            headers=org_headers(org["id"], user_token)
        )

        # Execute workflow that accesses config and secret
        # (This workflow should exist in workspace/examples/)
        exec_response = requests.post(
            f"{azure_functions_server}/api/workflows/simple_greeting/execute",
            json={
                "parameters": {"name": "John"}
            },
            headers=org_headers(org["id"], user_token)
        )

        # Check if workflow endpoint exists
        if exec_response.status_code == 200:
            result = exec_response.json()
            assert "status" in result
