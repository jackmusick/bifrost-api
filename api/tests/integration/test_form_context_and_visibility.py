"""
Integration tests for Form Context System (User Story 1)
Tests workflow execution on form load, query parameter handling, and context propagation

NOTE: This tests the BACKEND parts of form context:
- Storing launch workflow configuration in Forms table
- Validating form submissions
- Storing query parameter configuration

The ACTUAL context generation, visibility evaluation, and field show/hide logic
happens 100% CLIENT-SIDE in React. See research.md for architecture rationale.
"""

import pytest

from functions.forms import create_form, get_form
from tests.helpers.http_helpers import (
    create_mock_request,
    create_platform_admin_headers,
    parse_response,
)


@pytest.fixture(scope="module", autouse=True)
def ensure_test_workflows_loaded():
    """
    Ensure test workflows are loaded before running these tests.
    This is needed because some unit tests (test_registry.py) clear the registry.
    """
    from shared.registry import get_registry
    import importlib
    import sys

    registry = get_registry()

    # Check if workflows need to be reloaded
    if not registry.has_workflow("workflows.load_customer_licenses"):
        # Import and reload to ensure workflows are registered
        try:
            # Check if already imported
            if "workspace.examples.test_form_workflows" in sys.modules:
                importlib.reload(sys.modules["workspace.examples.test_form_workflows"])
            else:
                import workspace.examples.test_form_workflows  # noqa: F401
        except ImportError:
            pass

    yield


class TestFormContextConfiguration:
    """Test backend storage and validation of form context configuration"""

    @pytest.mark.asyncio
    async def test_create_form_with_launch_workflow(self, test_platform_admin_user):
        """Test creating a form with launch workflow configuration"""
        req = create_mock_request(
            method="POST",
            url="/api/forms",
            headers=create_platform_admin_headers(user_email=test_platform_admin_user["email"]),
            body={
                "name": "Form with Launch Workflow",
                "description": "Form that executes workflow on load",
                "linkedWorkflow": "workflows.process_form_submission",
                "formSchema": {
                    "fields": [
                        {
                            "name": "customer_name",
                            "label": "Customer Name",
                            "type": "text",
                            "required": True
                        },
                        {
                            "name": "license_type",
                            "label": "License Type",
                            "type": "select",
                            "required": True,
                            "dataProvider": "get_available_licenses"
                        }
                    ]
                },
                "launchWorkflowId": "workflows.load_customer_licenses",
                "isGlobal": True
            }
        )

        response = await create_form(req)
        status, body = parse_response(response)

        assert status == 201
        form = body
        assert form["name"] == "Form with Launch Workflow"
        assert form["launchWorkflowId"] == "workflows.load_customer_licenses"
        assert "id" in form

        # Verify we can retrieve it with launch workflow intact
        form_id = form["id"]
        get_req = create_mock_request(
            method="GET",
            url=f"/api/forms/{form_id}",
            headers=create_platform_admin_headers(),
            route_params={"formId": form_id},
        )

        get_response = await get_form(get_req)
        get_status, retrieved_form = parse_response(get_response)

        assert get_status == 200
        assert retrieved_form["launchWorkflowId"] == "workflows.load_customer_licenses"

    @pytest.mark.asyncio
    async def test_create_form_with_allowed_query_params(self, test_platform_admin_user):
        """Test creating a form with allowed query parameters"""
        req = create_mock_request(
            method="POST",
            url="/api/forms",
            headers=create_platform_admin_headers(user_email=test_platform_admin_user["email"]),
            body={
                "name": "Form with Query Params",
                "description": "Form that accepts URL parameters",
                "linkedWorkflow": "workflows.process_form",
                "formSchema": {
                    "fields": [
                        {
                            "name": "ticket_id",
                            "label": "Ticket ID",
                            "type": "text",
                            "required": True
                        }
                    ]
                },
                "allowedQueryParams": ["customer_id", "ticket_id", "source"],
                "isGlobal": True
            }
        )

        response = await create_form(req)
        status, body = parse_response(response)

        assert status == 201
        form = body
        assert form["name"] == "Form with Query Params"
        assert form["allowedQueryParams"] == ["customer_id", "ticket_id", "source"]
        assert len(form["allowedQueryParams"]) == 3

        # Verify query params persist on retrieval
        form_id = form["id"]
        get_req = create_mock_request(
            method="GET",
            url=f"/api/forms/{form_id}",
            headers=create_platform_admin_headers(),
            route_params={"formId": form_id},
        )

        get_response = await get_form(get_req)
        get_status, retrieved_form = parse_response(get_response)

        assert get_status == 200
        assert retrieved_form["allowedQueryParams"] == ["customer_id", "ticket_id", "source"]

    @pytest.mark.asyncio
    async def test_create_form_with_full_context_configuration(self, test_platform_admin_user):
        """Test creating a form with both launch workflow and query params"""
        req = create_mock_request(
            method="POST",
            url="/api/forms",
            headers=create_platform_admin_headers(user_email=test_platform_admin_user["email"]),
            body={
                "name": "Full Context Form",
                "description": "Form with complete context configuration",
                "linkedWorkflow": "workflows.process_submission",
                "formSchema": {
                    "fields": [
                        {
                            "name": "user_info",
                            "label": "User Info",
                            "type": "text",
                            "required": True,
                            "visibilityExpression": "context.workflow.user_exists === true"
                        },
                        {
                            "name": "new_user_form",
                            "label": "New User Form",
                            "type": "text",
                            "required": False,
                            "visibilityExpression": "context.workflow.user_exists === false"
                        }
                    ]
                },
                "launchWorkflowId": "workflows.check_user_exists",
                "allowedQueryParams": ["user_id", "email"],
                "isGlobal": True
            }
        )

        response = await create_form(req)
        status, body = parse_response(response)

        assert status == 201
        form = body
        assert form["launchWorkflowId"] == "workflows.check_user_exists"
        assert form["allowedQueryParams"] == ["user_id", "email"]
        assert len(form["formSchema"]["fields"]) == 2

        # Verify visibility expressions are stored
        fields = form["formSchema"]["fields"]
        assert fields[0]["visibilityExpression"] == "context.workflow.user_exists === true"
        assert fields[1]["visibilityExpression"] == "context.workflow.user_exists === false"


class TestFormFieldVisibilityConfiguration:
    """Test backend storage of field visibility expressions"""

    @pytest.mark.asyncio
    async def test_create_form_with_visibility_expressions(self, test_platform_admin_user):
        """Test creating a form with conditional field visibility"""
        req = create_mock_request(
            method="POST",
            url="/api/forms",
            headers=create_platform_admin_headers(user_email=test_platform_admin_user["email"]),
            body={
                "name": "Conditional Visibility Form",
                "linkedWorkflow": "workflows.process_conditional_form",
                "formSchema": {
                    "fields": [
                        {
                            "name": "show_advanced",
                            "label": "Show Advanced Options",
                            "type": "checkbox",
                            "required": False
                        },
                        {
                            "name": "advanced_field_1",
                            "label": "Advanced Field 1",
                            "type": "text",
                            "required": False,
                            "visibilityExpression": "context.field.show_advanced === true"
                        },
                        {
                            "name": "advanced_field_2",
                            "label": "Advanced Field 2",
                            "type": "number",
                            "required": False,
                            "visibilityExpression": "context.field.show_advanced === true"
                        },
                        {
                            "name": "always_visible",
                            "label": "Always Visible",
                            "type": "text",
                            "required": True
                            # No visibilityExpression = always visible
                        }
                    ]
                },
                "isGlobal": True
            }
        )

        response = await create_form(req)
        status, body = parse_response(response)

        assert status == 201
        form = body
        fields = form["formSchema"]["fields"]

        # First field has no visibility expression (checkbox control)
        assert fields[0]["name"] == "show_advanced"
        assert "visibilityExpression" not in fields[0] or fields[0]["visibilityExpression"] is None

        # Next two fields have conditional visibility
        assert fields[1]["visibilityExpression"] == "context.field.show_advanced === true"
        assert fields[2]["visibilityExpression"] == "context.field.show_advanced === true"

        # Last field is always visible
        assert "visibilityExpression" not in fields[3] or fields[3]["visibilityExpression"] is None

    @pytest.mark.asyncio
    async def test_form_with_query_param_visibility(self, test_platform_admin_user):
        """Test field visibility based on query parameters"""
        req = create_mock_request(
            method="POST",
            url="/api/forms",
            headers=create_platform_admin_headers(user_email=test_platform_admin_user["email"]),
            body={
                "name": "Query Param Visibility Form",
                "linkedWorkflow": "workflows.process_form",
                "formSchema": {
                    "fields": [
                        {
                            "name": "crm_field",
                            "label": "CRM Field",
                            "type": "text",
                            "required": False,
                            "visibilityExpression": "context.query.source === 'crm'"
                        },
                        {
                            "name": "ticket_field",
                            "label": "Ticket Field",
                            "type": "text",
                            "required": False,
                            "visibilityExpression": "context.query.source === 'ticketing'"
                        }
                    ]
                },
                "allowedQueryParams": ["source", "id"],
                "isGlobal": True
            }
        )

        response = await create_form(req)
        status, body = parse_response(response)

        assert status == 201
        form = body
        assert form["allowedQueryParams"] == ["source", "id"]

        fields = form["formSchema"]["fields"]
        assert fields[0]["visibilityExpression"] == "context.query.source === 'crm'"
        assert fields[1]["visibilityExpression"] == "context.query.source === 'ticketing'"

    @pytest.mark.asyncio
    async def test_form_with_workflow_result_visibility(self, test_platform_admin_user):
        """Test field visibility based on launch workflow results"""
        req = create_mock_request(
            method="POST",
            url="/api/forms",
            headers=create_platform_admin_headers(user_email=test_platform_admin_user["email"]),
            body={
                "name": "Workflow Result Visibility Form",
                "linkedWorkflow": "workflows.process_form",
                "formSchema": {
                    "fields": [
                        {
                            "name": "license_field",
                            "label": "Select License",
                            "type": "select",
                            "required": True,
                            "visibilityExpression": "context.workflow.has_available_licenses === true",
                            "dataProvider": "get_available_licenses"
                        },
                        {
                            "name": "no_licenses_message",
                            "label": "No Licenses Available",
                            "type": "markdown",
                            "required": False,
                            "visibilityExpression": "context.workflow.has_available_licenses === false",
                            "content": "## No Licenses Available\n\nPlease contact your administrator."
                        }
                    ]
                },
                "launchWorkflowId": "workflows.check_available_licenses",
                "isGlobal": True
            }
        )

        response = await create_form(req)
        status, body = parse_response(response)

        assert status == 201
        form = body
        assert form["launchWorkflowId"] == "workflows.check_available_licenses"

        fields = form["formSchema"]["fields"]
        assert fields[0]["visibilityExpression"] == "context.workflow.has_available_licenses === true"
        assert fields[1]["visibilityExpression"] == "context.workflow.has_available_licenses === false"
        assert fields[1]["content"] is not None

    @pytest.mark.asyncio
    async def test_form_with_complex_visibility_expressions(self, test_platform_admin_user):
        """Test complex boolean visibility expressions"""
        req = create_mock_request(
            method="POST",
            url="/api/forms",
            headers=create_platform_admin_headers(user_email=test_platform_admin_user["email"]),
            body={
                "name": "Complex Visibility Form",
                "linkedWorkflow": "workflows.process_form",
                "formSchema": {
                    "fields": [
                        {
                            "name": "admin_only_field",
                            "label": "Admin Only",
                            "type": "text",
                            "required": False,
                            "visibilityExpression": "context.workflow.user_type === 'admin' && context.field.enable_admin_mode === true"
                        },
                        {
                            "name": "conditional_field",
                            "label": "Conditional Field",
                            "type": "text",
                            "required": False,
                            "visibilityExpression": "(context.query.mode === 'advanced' || context.field.show_all) && context.workflow.feature_enabled"
                        }
                    ]
                },
                "launchWorkflowId": "workflows.check_user_permissions",
                "allowedQueryParams": ["mode"],
                "isGlobal": True
            }
        )

        response = await create_form(req)
        status, body = parse_response(response)

        assert status == 201
        form = body

        fields = form["formSchema"]["fields"]
        # Backend should store expressions as-is (validation happens client-side)
        assert fields[0]["visibilityExpression"] == "context.workflow.user_type === 'admin' && context.field.enable_admin_mode === true"
        assert fields[1]["visibilityExpression"] == "(context.query.mode === 'advanced' || context.field.show_all) && context.workflow.feature_enabled"


class TestFormContextValidation:
    """Test backend validation for form context configuration"""

    @pytest.mark.asyncio
    async def test_create_form_without_context_config(self, test_platform_admin_user):
        """Test that launchWorkflowId and allowedQueryParams are optional"""
        req = create_mock_request(
            method="POST",
            url="/api/forms",
            headers=create_platform_admin_headers(user_email=test_platform_admin_user["email"]),
            body={
                "name": "Simple Form",
                "linkedWorkflow": "workflows.process_simple_form",
                "formSchema": {
                    "fields": [
                        {
                            "name": "basic_field",
                            "label": "Basic Field",
                            "type": "text",
                            "required": True
                        }
                    ]
                },
                "isGlobal": True
            }
        )

        response = await create_form(req)
        status, body = parse_response(response)

        assert status == 201
        form = body
        # These should be None/null when not provided
        assert form.get("launchWorkflowId") is None
        assert form.get("allowedQueryParams") is None

    @pytest.mark.asyncio
    async def test_create_form_with_empty_allowed_query_params(self, test_platform_admin_user):
        """Test that empty allowedQueryParams array is valid"""
        req = create_mock_request(
            method="POST",
            url="/api/forms",
            headers=create_platform_admin_headers(user_email=test_platform_admin_user["email"]),
            body={
                "name": "No Query Params Form",
                "linkedWorkflow": "workflows.process_form",
                "formSchema": {"fields": []},
                "allowedQueryParams": [],  # Explicitly empty
                "isGlobal": True
            }
        )

        response = await create_form(req)
        status, body = parse_response(response)

        assert status == 201
        form = body
        assert form["allowedQueryParams"] == []

    @pytest.mark.asyncio
    async def test_field_without_visibility_expression(self, test_platform_admin_user):
        """Test that visibilityExpression is optional (field is always visible)"""
        req = create_mock_request(
            method="POST",
            url="/api/forms",
            headers=create_platform_admin_headers(user_email=test_platform_admin_user["email"]),
            body={
                "name": "Always Visible Form",
                "linkedWorkflow": "workflows.process_form",
                "formSchema": {
                    "fields": [
                        {
                            "name": "always_visible_field",
                            "label": "Always Visible",
                            "type": "text",
                            "required": True
                            # No visibilityExpression
                        }
                    ]
                },
                "isGlobal": True
            }
        )

        response = await create_form(req)
        status, body = parse_response(response)

        assert status == 201
        form = body
        field = form["formSchema"]["fields"][0]
        # visibilityExpression should be absent or null
        assert "visibilityExpression" not in field or field["visibilityExpression"] is None


# NOTE: We do NOT test actual expression evaluation here.
# Expression evaluation (parsing, validation, execution) happens 100% CLIENT-SIDE in React.
# The backend only:
# 1. Stores the configuration (launchWorkflowId, allowedQueryParams, visibilityExpression)
# 2. Validates submitted form data against schema
# 3. Executes the linked workflow with submitted parameters
#
# See research.md for full architecture rationale.
