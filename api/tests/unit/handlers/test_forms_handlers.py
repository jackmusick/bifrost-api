"""Unit tests for forms_handlers module - extracted handler business logic"""

import pytest
from unittest.mock import MagicMock, patch

from shared.handlers.forms_handlers import (
    validate_launch_workflow_params,
    list_forms_handler,
    create_form_handler,
    get_form_handler,
    update_form_handler,
    delete_form_handler,
    execute_form_startup_handler,
    execute_form_handler,
)
from shared.models import Form


class MockRequestContext:
    """Mock request context for testing"""
    def __init__(self, user_id="user123", org_id="org456", name="Test User"):
        self.user_id = user_id
        self.org_id = org_id
        self.name = name


class MockWorkflowContext:
    """Mock workflow context for testing"""
    def __init__(self):
        self.execution_id = "exec123"
        self._state_snapshots = []
        self._integration_calls = []
        self._logs = []
        self._variables = {}

    def set_variable(self, key, value):
        self._variables[key] = value


class TestValidateLaunchWorkflowParams:
    """Test validate_launch_workflow_params function"""

    def test_no_launch_workflow_returns_none(self):
        """Should return None when no launch workflow configured"""
        result = validate_launch_workflow_params(None, None, None, [])
        assert result is None

    @patch('shared.registry.get_registry')
    def test_workflow_not_found_returns_error(self, mock_get_registry):
        """Should return error message when workflow not found"""
        mock_registry = MagicMock()
        mock_registry.get_workflow.return_value = None
        mock_get_registry.return_value = mock_registry

        result = validate_launch_workflow_params(
            launch_workflow_id="missing_workflow",
            default_launch_params=None,
            allowed_query_params=None,
            form_schema_fields=[]
        )

        assert "not found in registry" in result

    @patch('shared.registry.get_registry')
    def test_missing_required_params_returns_error(self, mock_get_registry):
        """Should return error when required params missing"""
        mock_param = MagicMock()
        mock_param.name = "required_param"
        mock_param.required = True

        mock_workflow = MagicMock()
        mock_workflow.parameters = [mock_param]

        mock_registry = MagicMock()
        mock_registry.get_workflow.return_value = mock_workflow
        mock_get_registry.return_value = mock_registry

        result = validate_launch_workflow_params(
            launch_workflow_id="test_workflow",
            default_launch_params=None,
            allowed_query_params=None,
            form_schema_fields=[]
        )

        assert "required_param" in result
        assert "no default values" in result

    @patch('shared.registry.get_registry')
    def test_params_with_defaults_pass_validation(self, mock_get_registry):
        """Should pass validation when required params have defaults"""
        mock_param = MagicMock()
        mock_param.name = "param1"
        mock_param.required = True

        mock_workflow = MagicMock()
        mock_workflow.parameters = [mock_param]

        mock_registry = MagicMock()
        mock_registry.get_workflow.return_value = mock_workflow
        mock_get_registry.return_value = mock_registry

        result = validate_launch_workflow_params(
            launch_workflow_id="test_workflow",
            default_launch_params={"param1": "value1"},
            allowed_query_params=None,
            form_schema_fields=[]
        )

        assert result is None


@pytest.mark.asyncio
class TestListFormsHandler:
    """Test list_forms_handler function"""

    @patch('shared.handlers.forms_handlers.get_user_visible_forms')
    async def test_list_forms_success(self, mock_get_visible):
        """Should return list of forms and 200 status"""
        test_forms = [
            {"id": "form1", "name": "Form A"},
            {"id": "form2", "name": "Form B"}
        ]
        mock_get_visible.return_value = test_forms

        context = MockRequestContext()
        req = MagicMock()

        result, status = await list_forms_handler(req, context)

        assert status == 200
        assert len(result) == 2
        assert result[0]["name"] == "Form A"

    @patch('shared.handlers.forms_handlers.get_user_visible_forms')
    async def test_list_forms_error(self, mock_get_visible):
        """Should return 500 error on exception"""
        mock_get_visible.side_effect = Exception("Database error")

        context = MockRequestContext()
        req = MagicMock()

        result, status = await list_forms_handler(req, context)

        assert status == 500
        assert result["error"] == "InternalServerError"


@pytest.mark.asyncio
class TestCreateFormHandler:
    """Test create_form_handler function"""

    @patch('shared.handlers.forms_handlers.FormRepository')
    @patch('shared.handlers.forms_handlers.validate_launch_workflow_params')
    async def test_create_form_success(self, mock_validate, mock_repo_class):
        """Should create form and return 201"""
        mock_validate.return_value = None

        mock_form = MagicMock(spec=Form)
        mock_form.id = "form1"
        mock_form.orgId = "org1"
        mock_form.model_dump.return_value = {"id": "form1"}

        mock_repo = MagicMock()
        mock_repo.create_form.return_value = mock_form
        mock_repo_class.return_value = mock_repo

        request_body = {
            "name": "Test Form",
            "formSchema": {"fields": []},
            "linkedWorkflow": "test_workflow"
        }
        context = MockRequestContext()

        result, status = await create_form_handler(request_body, context)

        assert status == 201
        assert result["id"] == "form1"

    @patch('shared.handlers.forms_handlers.validate_launch_workflow_params')
    async def test_create_form_validation_error(self, mock_validate):
        """Should return 400 on launch workflow validation error"""
        mock_validate.return_value = "Workflow validation failed"

        request_body = {
            "name": "Test Form",
            "formSchema": {"fields": []},
            "linkedWorkflow": "test_workflow",
            "launchWorkflowId": "missing_workflow"
        }
        context = MockRequestContext()

        result, status = await create_form_handler(request_body, context)

        assert status == 400
        assert result["error"] == "ValidationError"

    async def test_create_form_invalid_json(self):
        """Should return 500 on invalid request body (not a dict)"""
        request_body = "invalid"
        context = MockRequestContext()

        result, status = await create_form_handler(request_body, context)

        # Returns 500 because unpacking a string raises TypeError, caught by general exception handler
        assert status == 500
        assert result["error"] == "InternalServerError"


@pytest.mark.asyncio
class TestGetFormHandler:
    """Test get_form_handler function"""

    @patch('shared.handlers.forms_handlers.can_user_view_form')
    @patch('shared.handlers.forms_handlers.FormRepository')
    async def test_get_form_success(self, mock_repo_class, mock_can_view):
        """Should return form and 200 status"""
        mock_can_view.return_value = True

        mock_form = MagicMock(spec=Form)
        mock_form.id = "form1"
        mock_form.isActive = True
        mock_form.model_dump.return_value = {"id": "form1", "name": "Test"}

        mock_repo = MagicMock()
        mock_repo.get_form.return_value = mock_form
        mock_repo_class.return_value = mock_repo

        context = MockRequestContext()

        result, status = await get_form_handler("form1", context)

        assert status == 200
        assert result["id"] == "form1"

    @patch('shared.handlers.forms_handlers.FormRepository')
    async def test_get_form_not_found(self, mock_repo_class):
        """Should return 404 when form not found"""
        mock_repo = MagicMock()
        mock_repo.get_form.return_value = None
        mock_repo_class.return_value = mock_repo

        context = MockRequestContext()

        result, status = await get_form_handler("missing_form", context)

        assert status == 404
        assert result["error"] == "NotFound"

    @patch('shared.handlers.forms_handlers.FormRepository')
    async def test_get_form_inactive(self, mock_repo_class):
        """Should return 404 for inactive form"""
        mock_form = MagicMock(spec=Form)
        mock_form.isActive = False

        mock_repo = MagicMock()
        mock_repo.get_form.return_value = mock_form
        mock_repo_class.return_value = mock_repo

        context = MockRequestContext()

        result, status = await get_form_handler("form1", context)

        assert status == 404
        assert result["error"] == "NotFound"

    @patch('shared.handlers.forms_handlers.can_user_view_form')
    @patch('shared.handlers.forms_handlers.FormRepository')
    async def test_get_form_forbidden(self, mock_repo_class, mock_can_view):
        """Should return 403 when user lacks permission"""
        mock_can_view.return_value = False

        mock_form = MagicMock(spec=Form)
        mock_form.isActive = True

        mock_repo = MagicMock()
        mock_repo.get_form.return_value = mock_form
        mock_repo_class.return_value = mock_repo

        context = MockRequestContext()

        result, status = await get_form_handler("form1", context)

        assert status == 403
        assert result["error"] == "Forbidden"


@pytest.mark.asyncio
class TestUpdateFormHandler:
    """Test update_form_handler function"""

    @patch('shared.handlers.forms_handlers.FormRepository')
    @patch('shared.handlers.forms_handlers.validate_launch_workflow_params')
    async def test_update_form_success(self, mock_validate, mock_repo_class):
        """Should update form and return 200"""
        mock_validate.return_value = None

        mock_existing = MagicMock(spec=Form)
        mock_existing.launchWorkflowId = None
        mock_existing.defaultLaunchParams = None
        mock_existing.allowedQueryParams = None
        mock_existing.formSchema = MagicMock()
        mock_existing.formSchema.fields = []

        mock_updated = MagicMock(spec=Form)
        mock_updated.model_dump.return_value = {"id": "form1"}

        mock_repo = MagicMock()
        mock_repo.get_form.return_value = mock_existing
        mock_repo.update_form.return_value = mock_updated
        mock_repo_class.return_value = mock_repo

        request_body = {"name": "Updated Form"}
        context = MockRequestContext()

        result, status = await update_form_handler("form1", request_body, context)

        assert status == 200
        assert result["id"] == "form1"

    @patch('shared.handlers.forms_handlers.FormRepository')
    async def test_update_form_not_found(self, mock_repo_class):
        """Should return 404 when form not found"""
        mock_repo = MagicMock()
        mock_repo.get_form.return_value = None
        mock_repo_class.return_value = mock_repo

        request_body = {"name": "Updated Form"}
        context = MockRequestContext()

        result, status = await update_form_handler("missing_form", request_body, context)

        assert status == 404
        assert result["error"] == "NotFound"


@pytest.mark.asyncio
class TestDeleteFormHandler:
    """Test delete_form_handler function"""

    @patch('shared.handlers.forms_handlers.FormRepository')
    async def test_delete_form_success(self, mock_repo_class):
        """Should return 204 on successful delete"""
        mock_repo = MagicMock()
        mock_repo.delete_form.return_value = True
        mock_repo_class.return_value = mock_repo

        context = MockRequestContext()

        result, status = await delete_form_handler("form1", context)

        assert status == 204
        assert result is None

    @patch('shared.handlers.forms_handlers.FormRepository')
    async def test_delete_form_not_found(self, mock_repo_class):
        """Should return 204 even if form not found (idempotent)"""
        mock_repo = MagicMock()
        mock_repo.delete_form.return_value = False
        mock_repo_class.return_value = mock_repo

        context = MockRequestContext()

        result, status = await delete_form_handler("missing_form", context)

        assert status == 204


@pytest.mark.asyncio
class TestExecuteFormStartupHandler:
    """Test execute_form_startup_handler function"""

    @patch('shared.handlers.forms_handlers.can_user_view_form')
    @patch('shared.handlers.forms_handlers.FormRepository')
    async def test_startup_no_launch_workflow(self, mock_repo_class, mock_can_view):
        """Should return empty result when no launch workflow"""
        mock_can_view.return_value = True

        mock_form = MagicMock(spec=Form)
        mock_form.isActive = True
        mock_form.launchWorkflowId = None

        mock_repo = MagicMock()
        mock_repo.get_form.return_value = mock_form
        mock_repo_class.return_value = mock_repo

        context = MockRequestContext()
        workflow_context = MockWorkflowContext()

        mock_req = MagicMock()
        mock_req.method = "GET"

        result, status = await execute_form_startup_handler("form1", mock_req, context, workflow_context)

        assert status == 200
        assert result == {"result": {}}

    @patch('shared.handlers.forms_handlers.can_user_view_form')
    async def test_startup_forbidden(self, mock_can_view):
        """Should return 403 when user lacks permission"""
        mock_can_view.return_value = False

        context = MockRequestContext()
        workflow_context = MockWorkflowContext()
        mock_req = MagicMock()

        result, status = await execute_form_startup_handler("form1", mock_req, context, workflow_context)

        assert status == 403
        assert result["error"] == "Forbidden"

    @patch('shared.handlers.forms_handlers.can_user_view_form')
    @patch('shared.handlers.forms_handlers.FormRepository')
    async def test_startup_form_not_found(self, mock_repo_class, mock_can_view):
        """Should return 404 when form not found"""
        mock_can_view.return_value = True

        mock_repo = MagicMock()
        mock_repo.get_form.return_value = None
        mock_repo_class.return_value = mock_repo

        context = MockRequestContext()
        workflow_context = MockWorkflowContext()
        mock_req = MagicMock()

        result, status = await execute_form_startup_handler("missing_form", mock_req, context, workflow_context)

        assert status == 404
        assert result["error"] == "NotFound"


@pytest.mark.asyncio
class TestExecuteFormHandler:
    """Test execute_form_handler function"""

    @patch('shared.handlers.forms_handlers.can_user_execute_form')
    async def test_execute_form_forbidden(self, mock_can_execute):
        """Should return 403 when user lacks permission"""
        mock_can_execute.return_value = False

        request_body = {"form_data": {}}
        context = MockRequestContext()
        workflow_context = MockWorkflowContext()

        result, status = await execute_form_handler("form1", request_body, context, workflow_context)

        assert status == 403
        assert result["error"] == "Forbidden"

    @patch('shared.handlers.forms_handlers.can_user_execute_form')
    @patch('shared.handlers.forms_handlers.FormRepository')
    async def test_execute_form_not_found(self, mock_repo_class, mock_can_execute):
        """Should return 404 when form not found"""
        mock_can_execute.return_value = True

        mock_repo = MagicMock()
        mock_repo.get_form.return_value = None
        mock_repo_class.return_value = mock_repo

        request_body = {"form_data": {}}
        context = MockRequestContext()
        workflow_context = MockWorkflowContext()

        result, status = await execute_form_handler("missing_form", request_body, context, workflow_context)

        assert status == 404
        assert result["error"] == "NotFound"

    @patch('shared.handlers.forms_handlers.can_user_execute_form')
    @patch('shared.handlers.forms_handlers.FormRepository')
    async def test_execute_form_no_linked_workflow(self, mock_repo_class, mock_can_execute):
        """Should return 500 when no linked workflow"""
        mock_can_execute.return_value = True

        mock_form = MagicMock(spec=Form)
        mock_form.isActive = True
        mock_form.linkedWorkflow = None

        mock_repo = MagicMock()
        mock_repo.get_form.return_value = mock_form
        mock_repo_class.return_value = mock_repo

        request_body = {"form_data": {}}
        context = MockRequestContext()
        workflow_context = MockWorkflowContext()

        result, status = await execute_form_handler("form1", request_body, context, workflow_context)

        assert status == 500
        assert result["error"] == "InternalServerError"
