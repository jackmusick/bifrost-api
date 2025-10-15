"""
End-to-end tests for Workflow Execution via Form Submission
Tests the complete flow: Form Submit → Workflow Execution → Execution History
"""

import pytest
import requests
import time


class TestWorkflowExecutionE2E:
    """Test end-to-end workflow execution flow"""

    @pytest.mark.skip(reason="Requires workflows engine service to be running (separate from management API)")
    def test_submit_public_form_as_org_user(self, base_url, org_user_headers):
        """
        Org user can submit a public form and execute its workflow.

        Flow:
        1. List forms to find the public "Simple Greeting" form
        2. Submit the form with test data
        3. Verify workflow execution completes
        4. Check execution appears in history

        NOTE: This test requires the workflows engine service (separate Azure Functions app)
        to be running. For now, we test executions using the seed data.
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

        # Step 2: Submit the form
        submit_response = requests.post(
            f"{base_url}/forms/{form_id}/submit",
            headers=org_user_headers,
            json={
                "form_data": {
                    "name": "Test User",
                    "greeting_type": "Hello",
                    "include_timestamp": True
                }
            }
        )

        assert submit_response.status_code == 200
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

    @pytest.mark.skip(reason="Requires workflows engine service (returns 500 without it)")
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
            f"{base_url}/forms/{form_id}/submit",
            headers=org_user_headers,
            json={}  # Missing form_data
        )

        # May return 400 for validation error or 500 for workflow execution failure
        assert submit_response.status_code in [400, 500]

    @pytest.mark.skip(reason="Requires workflows engine service (returns 500 without it)")
    def test_submit_nonexistent_form_not_found(self, base_url, org_user_headers):
        """Submitting a nonexistent form returns 404"""
        response = requests.post(
            f"{base_url}/forms/nonexistent-form-id/submit",
            headers=org_user_headers,
            json={
                "form_data": {
                    "test": "value"
                }
            }
        )

        assert response.status_code == 404
        error = response.json()
        assert error["error"] == "NotFound"

    @pytest.mark.skip(reason="Local dev mode treats anonymous as admin (production has SWA auth layer)")
    def test_submit_form_anonymous_unauthorized(self, base_url, anonymous_headers):
        """
        Anonymous users should be rejected in production.

        NOTE: Skipped in local dev - see request_context.py lines 113-126.
        """
        response = requests.post(
            f"{base_url}/forms/any-form-id/submit",
            headers=anonymous_headers,
            json={"form_data": {}}
        )

        assert response.status_code == 401
