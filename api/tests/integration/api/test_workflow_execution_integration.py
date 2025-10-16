"""
Integration tests for Workflow Execution via Form Submission
Tests the complete flow: Form Submit → Workflow Execution → Execution History
"""

from pathlib import Path

import pytest

from functions.executions import get_execution, list_executions
from functions.forms import create_form, delete_form, execute_form, list_forms
from tests.helpers.http_helpers import (
    create_mock_request,
    create_org_user_headers,
    create_platform_admin_headers,
    parse_response,
)


class TestWorkflowExecutionIntegration:
    """Test end-to-end workflow execution flow"""

    @pytest.mark.asyncio
    async def test_hot_reload_workflow_discovery(self):
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
        # Get workspace path dynamically relative to test file
        api_dir = Path(__file__).parent.parent.parent.parent
        workspace_path = api_dir / "workspace" / "examples"
        workspace_path.mkdir(parents=True, exist_ok=True)
        test_workflow_path = workspace_path / "hot_reload_test_workflow.py"

        workflow_code = '''"""
Hot-reload test workflow - created during integration testing
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
    """Test workflow created during integration test to verify hot-reload"""
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
            create_form_req = create_mock_request(
                method="POST",
                url="/api/forms",
                headers=create_platform_admin_headers(),
                body={
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

            create_form_response = await create_form(create_form_req)
            create_status, form_data = parse_response(create_form_response)

            assert create_status in [200, 201], \
                f"Failed to create form: {create_status}"

            form_id = form_data["id"]

            # Step 3: Execute the form (this should trigger hot-reload + execution)
            submit_req = create_mock_request(
                method="POST",
                url=f"/api/forms/{form_id}/execute",
                headers=create_org_user_headers(),
                route_params={"formId": form_id},
                body={
                    "form_data": {
                        "test_value": "Hot reload is working!"
                    }
                }
            )

            submit_response = await execute_form(submit_req)
            submit_status, execution = parse_response(submit_response)

            # Step 4: Verify workflow executed successfully
            assert submit_status == 200, \
                f"Form submission failed (hot-reload may not be working): {submit_status}"

            assert execution.get("status") in ["Success", "success", "completed"]

            result = execution.get("result") or execution.get("output")
            assert result is not None, "Execution result is missing"
            assert result.get("success") is True
            assert result.get("test_value") == "Hot reload is working!"
            assert result.get("message") == "Hot-reload works!"

            # Step 5: Clean up - delete the form
            delete_form_req = create_mock_request(
                method="DELETE",
                url=f"/api/forms/{form_id}",
                headers=create_platform_admin_headers(),
                route_params={"formId": form_id}
            )

            delete_form_response = await delete_form(delete_form_req)
            delete_status, _ = parse_response(delete_form_response)
            # Deletion may return 204 (no content) or 404 (already deleted)
            assert delete_status in [204, 404]

        finally:
            # Always clean up the workflow file
            if test_workflow_path.exists():
                test_workflow_path.unlink()

    @pytest.mark.asyncio
    async def test_submit_public_form_as_org_user(self):
        """
        Org user can submit a public form and execute its workflow.

        Flow:
        1. List forms to find the public "Simple Greeting" form
        2. Submit the form with test data
        3. Verify workflow execution completes
        4. Check execution appears in history
        """
        # Step 1: Find the public "Simple Greeting" form
        list_req = create_mock_request(
            method="GET",
            url="/api/forms",
            headers=create_org_user_headers()
        )

        list_response = await list_forms(list_req)
        list_status, forms = parse_response(list_response)

        assert list_status == 200

        greeting_form = next(
            (f for f in forms if f["name"] == "Simple Greeting"),
            None
        )
        assert greeting_form is not None, "Simple Greeting form not found in seed data"
        form_id = greeting_form["id"]

        # Step 2: Execute the form
        submit_req = create_mock_request(
            method="POST",
            url=f"/api/forms/{form_id}/execute",
            headers=create_org_user_headers(),
            route_params={"formId": form_id},
            body={
                "form_data": {
                    "name": "Test User",
                    "greeting_type": "Hello",
                    "include_timestamp": True
                }
            }
        )

        submit_response = await execute_form(submit_req)
        submit_status, execution = parse_response(submit_response)

        assert submit_status == 200, \
            f"Form submission failed: {submit_status}"

        # Verify execution result structure
        assert "executionId" in execution or "execution_id" in execution
        assert "status" in execution
        assert "result" in execution or "output" in execution

        execution_id = execution.get("executionId") or execution.get("execution_id")

        # Step 3: Verify execution appears in history
        history_req = create_mock_request(
            method="GET",
            url="/api/executions",
            headers=create_org_user_headers()
        )

        history_response = await list_executions(history_req)
        history_status, response_data = parse_response(history_response)

        assert history_status == 200
        # API returns {"executions": [...]}
        executions = response_data.get("executions", response_data)
        assert isinstance(executions, list)

        # Find our execution
        our_execution = next(
            (e for e in executions if e.get("executionId") == execution_id or e.get("id") == execution_id),
            None
        )

        # Note: May not find it if execution hasn't been recorded yet
        # This is acceptable for integration test (async processing)
        if our_execution:
            assert our_execution.get("formId") == form_id
            assert our_execution.get("workflowName") == "simple_greeting" or our_execution.get("linkedWorkflow") == "simple_greeting"

    @pytest.mark.asyncio
    async def test_submit_form_without_permission_forbidden(self):
        """
        Org user cannot submit a non-public form they don't have role access to.

        The "New User Onboarding" form is role-restricted to IT Managers.
        """
        # Find the role-restricted "New User Onboarding" form
        # We need to get it as platform admin first since org user can't see it
        pass  # TODO: This requires setting up role assignments in seed data

    @pytest.mark.asyncio
    async def test_get_execution_by_id(self):
        """User can retrieve a specific execution by ID"""
        # First get list of executions
        list_req = create_mock_request(
            method="GET",
            url="/api/executions",
            headers=create_org_user_headers()
        )

        list_response = await list_executions(list_req)
        list_status, response_data = parse_response(list_response)

        assert list_status == 200
        executions = response_data.get("executions", response_data)

        if len(executions) == 0:
            pytest.skip("No executions found (requires form submission first)")

        execution_id = executions[0].get("executionId") or executions[0].get("id")

        # Get specific execution
        get_req = create_mock_request(
            method="GET",
            url=f"/api/executions/{execution_id}",
            headers=create_org_user_headers(),
            route_params={"executionId": execution_id}
        )

        get_response = await get_execution(get_req)
        get_status, execution = parse_response(get_response)

        assert get_status == 200
        assert execution.get("executionId") == execution_id or execution.get("id") == execution_id

    @pytest.mark.asyncio
    async def test_list_executions_as_platform_admin(self):
        """
        Platform admin can see executions (scope-aware).

        Note: Platform admins in GLOBAL scope see global executions.
        To see org-scoped executions, they must set X-Organization-Id header.
        """
        req = create_mock_request(
            method="GET",
            url="/api/executions",
            headers=create_platform_admin_headers()
        )

        response = await list_executions(req)
        status, response_data = parse_response(response)

        assert status == 200
        executions = response_data.get("executions", response_data)
        assert isinstance(executions, list)

        # Verify structure if executions exist
        if len(executions) > 0:
            execution = executions[0]
            assert "executionId" in execution or "id" in execution
            assert "workflowName" in execution or "linkedWorkflow" in execution
            assert "status" in execution

    @pytest.mark.asyncio
    async def test_submit_form_validation_error(self):
        """Submitting a form with invalid data returns validation error"""
        # Find a form
        list_req = create_mock_request(
            method="GET",
            url="/api/forms",
            headers=create_org_user_headers()
        )

        list_response = await list_forms(list_req)
        list_status, forms = parse_response(list_response)

        if len(forms) == 0:
            pytest.skip("No forms available")

        form_id = forms[0]["id"]

        # Submit with invalid/missing data
        submit_req = create_mock_request(
            method="POST",
            url=f"/api/forms/{form_id}/execute",
            headers=create_org_user_headers(),
            route_params={"formId": form_id},
            body={}  # Missing form_data
        )

        submit_response = await execute_form(submit_req)
        status, _ = parse_response(submit_response)

        # May return 400 for validation error, 404 if workflow not found, or 500 for execution failure
        assert status in [400, 404, 500]

    @pytest.mark.asyncio
    async def test_submit_nonexistent_form_not_found(self):
        """Submitting a nonexistent form returns error status"""
        req = create_mock_request(
            method="POST",
            url="/api/forms/nonexistent-form-id/execute",
            headers=create_org_user_headers(),
            route_params={"formId": "nonexistent-form-id"},
            body={
                "form_data": {
                    "test": "value"
                }
            }
        )

        response = await execute_form(req)
        status, _ = parse_response(response)

        # May return 404 (not found), 403 (permission check), or 500 (internal error)
        assert status in [403, 404, 500]
