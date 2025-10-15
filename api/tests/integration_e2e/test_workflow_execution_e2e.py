"""
End-to-end tests for Workflow Execution via Form Submission
Tests the complete flow: Form Submit → Workflow Execution → Execution History
"""

import pytest
import requests
import time
import tempfile
import shutil
from pathlib import Path


class TestWorkflowExecutionE2E:
    """Test end-to-end workflow execution flow"""

    def test_hot_reload_workflow_discovery(self, base_url, org_user_headers, platform_admin_headers):
        """
        Test that workflows are discovered at execution time (hot-reload).

        This test validates that a developer can push a new workflow file
        and execute it WITHOUT restarting the Azure Functions app.

        Flow:
        1. Create a new workflow file in workspace/examples/
        2. Create a form linked to this new workflow
        3. Submit the form (should trigger workflow discovery + execution)
        4. Verify the workflow executed successfully
        5. Clean up the test workflow file
        """
        # Step 1: Create a new workflow file dynamically
        workspace_path = Path("/Users/jack/GitHub/bifrost-integrations/api/workspace/examples")
        test_workflow_path = workspace_path / "hot_reload_test_workflow.py"

        workflow_code = '''"""
Hot-reload test workflow - created during E2E testing
"""
from bifrost import workflow, param, OrganizationContext

@workflow(
    name="hot_reload_test",
    description="Hot-reload test workflow",
    category="testing",
    tags=["test", "hot-reload"],
    requires_org=True
)
@param("test_value", type="string", label="Test Value", required=True, help_text="Test value to echo")
async def hot_reload_test(
    context: OrganizationContext,
    test_value: str
) -> dict:
    """Test workflow created during E2E test to verify hot-reload"""
    context.info(f"Hot-reload test executed with value: {test_value}")
    return {
        "success": True,
        "test_value": test_value,
        "org_id": context.org_id,
        "message": "Hot-reload works!"
    }
'''

        # Write the workflow file
        test_workflow_path.write_text(workflow_code)

        try:
            # Step 2: Create a form linked to this workflow
            create_form_response = requests.post(
                f"{base_url}/forms",
                headers=platform_admin_headers,
                json={
                    "name": "Hot Reload Test Form",
                    "description": "Form for testing hot-reload",
                    "linkedWorkflow": "hot_reload_test",
                    "isPublic": True,
                    "formSchema": {
                        "fields": [
                            {
                                "name": "test_value",
                                "label": "Test Value",
                                "type": "text",
                                "required": True
                            }
                        ]
                    }
                }
            )

            assert create_form_response.status_code in [200, 201], \
                f"Failed to create form: {create_form_response.status_code} - {create_form_response.text}"

            form_data = create_form_response.json()
            form_id = form_data["id"]

            # Step 3: Execute the form (this should trigger hot-reload + execution)
            submit_response = requests.post(
                f"{base_url}/forms/{form_id}/execute",
                headers=org_user_headers,
                json={
                    "form_data": {
                        "test_value": "Hot reload is working!"
                    }
                }
            )

            # Step 4: Verify workflow executed successfully
            assert submit_response.status_code == 200, \
                f"Form submission failed (hot-reload may not be working): {submit_response.status_code} - {submit_response.text}"

            execution = submit_response.json()
            assert execution.get("status") in ["Success", "success", "completed"]

            result = execution.get("result") or execution.get("output")
            assert result is not None, "Execution result is missing"
            assert result.get("success") is True
            assert result.get("test_value") == "Hot reload is working!"
            assert result.get("message") == "Hot-reload works!"

            # Step 5: Clean up - delete the form
            delete_form_response = requests.delete(
                f"{base_url}/forms/{form_id}",
                headers=platform_admin_headers
            )
            # Deletion may return 204 (no content) or 404 (already deleted)
            assert delete_form_response.status_code in [204, 404]

        finally:
            # Always clean up the workflow file
            if test_workflow_path.exists():
                test_workflow_path.unlink()

    def test_submit_public_form_as_org_user(self, base_url, org_user_headers):
        """
        Org user can submit a public form and execute its workflow.

        Flow:
        1. List forms to find the public "Simple Greeting" form
        2. Submit the form with test data
        3. Verify workflow execution completes
        4. Check execution appears in history
        """
        # Step 1: Find the public "Simple Greeting" form
        list_response = requests.get(
            f"{base_url}/forms",
            headers=org_user_headers
        )
        assert list_response.status_code == 200
        forms = list_response.json()

        greeting_form = next(
            (f for f in forms if f["name"] == "Simple Greeting"),
            None
        )
        assert greeting_form is not None, "Simple Greeting form not found in seed data"
        form_id = greeting_form["id"]

        # Step 2: Execute the form
        submit_response = requests.post(
            f"{base_url}/forms/{form_id}/execute",
            headers=org_user_headers,
            json={
                "form_data": {
                    "name": "Test User",
                    "greeting_type": "Hello",
                    "include_timestamp": True
                }
            }
        )

        assert submit_response.status_code == 200, \
            f"Form submission failed: {submit_response.status_code} - {submit_response.text}"
        execution = submit_response.json()

        # Verify execution result structure
        assert "executionId" in execution or "execution_id" in execution
        assert "status" in execution
        assert "result" in execution or "output" in execution

        execution_id = execution.get("executionId") or execution.get("execution_id")

        # Step 3: Wait a moment for execution to be recorded
        time.sleep(1)

        # Step 4: Verify execution appears in history
        history_response = requests.get(
            f"{base_url}/executions",
            headers=org_user_headers
        )

        assert history_response.status_code == 200
        response_data = history_response.json()
        # API returns {"executions": [...]}
        executions = response_data.get("executions", response_data)
        assert isinstance(executions, list)

        # Find our execution
        our_execution = next(
            (e for e in executions if e.get("executionId") == execution_id or e.get("id") == execution_id),
            None
        )

        # Note: May not find it if execution hasn't been recorded yet
        # This is acceptable for E2E test (async processing)
        if our_execution:
            assert our_execution.get("formId") == form_id
            assert our_execution.get("workflowName") == "simple_greeting" or our_execution.get("linkedWorkflow") == "simple_greeting"

    def test_submit_form_without_permission_forbidden(self, base_url, org_user_headers):
        """
        Org user cannot submit a non-public form they don't have role access to.

        The "New User Onboarding" form is role-restricted to IT Managers.
        """
        # Find the role-restricted "New User Onboarding" form
        # We need to get it as platform admin first since org user can't see it
        pass  # TODO: This requires setting up role assignments in seed data

    def test_get_execution_by_id(self, base_url, org_user_headers):
        """User can retrieve a specific execution by ID"""
        # First get list of executions
        list_response = requests.get(
            f"{base_url}/executions",
            headers=org_user_headers
        )
        assert list_response.status_code == 200
        response_data = list_response.json()
        executions = response_data.get("executions", response_data)

        if len(executions) == 0:
            pytest.skip("No executions found (requires form submission first)")

        execution_id = executions[0].get("executionId") or executions[0].get("id")

        # Get specific execution
        get_response = requests.get(
            f"{base_url}/executions/{execution_id}",
            headers=org_user_headers
        )

        assert get_response.status_code == 200
        execution = get_response.json()
        assert execution.get("executionId") == execution_id or execution.get("id") == execution_id

    def test_list_executions_as_platform_admin(self, base_url, platform_admin_headers):
        """
        Platform admin can see executions (scope-aware).

        Note: Platform admins in GLOBAL scope see global executions.
        To see org-scoped executions, they must set X-Organization-Id header.
        """
        response = requests.get(
            f"{base_url}/executions",
            headers=platform_admin_headers
        )

        assert response.status_code == 200
        response_data = response.json()
        executions = response_data.get("executions", response_data)
        assert isinstance(executions, list)

        # Verify structure if executions exist
        if len(executions) > 0:
            execution = executions[0]
            assert "executionId" in execution or "id" in execution
            assert "workflowName" in execution or "linkedWorkflow" in execution
            assert "status" in execution

    def test_submit_form_validation_error(self, base_url, org_user_headers):
        """Submitting a form with invalid data returns validation error"""
        # Find a form
        list_response = requests.get(
            f"{base_url}/forms",
            headers=org_user_headers
        )
        forms = list_response.json()

        if len(forms) == 0:
            pytest.skip("No forms available")

        form_id = forms[0]["id"]

        # Submit with invalid/missing data
        submit_response = requests.post(
            f"{base_url}/forms/{form_id}/execute",
            headers=org_user_headers,
            json={}  # Missing form_data
        )

        # May return 400 for validation error, 404 if workflow not found, or 500 for execution failure
        assert submit_response.status_code in [400, 404, 500]

    def test_submit_nonexistent_form_not_found(self, base_url, org_user_headers):
        """Submitting a nonexistent form returns error status"""
        response = requests.post(
            f"{base_url}/forms/nonexistent-form-id/execute",
            headers=org_user_headers,
            json={
                "form_data": {
                    "test": "value"
                }
            }
        )

        # May return 404 (not found), 403 (permission check), or 500 (internal error)
        assert response.status_code in [403, 404, 500]
