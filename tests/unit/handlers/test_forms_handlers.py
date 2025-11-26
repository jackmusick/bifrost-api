"""Unit tests for forms_handlers module - validates workflow parameter business logic"""

from unittest.mock import MagicMock, patch

from shared.handlers.forms_handlers import (
    validate_launch_workflow_params,
)


class TestValidateLaunchWorkflowParams:
    """Test validate_launch_workflow_params function"""

    def test_no_launch_workflow_returns_none(self):
        """Should return None when no launch workflow configured"""
        result = validate_launch_workflow_params(None, None, None, [])
        assert result is None

    @patch('shared.discovery.load_workflow')
    def test_workflow_not_found_returns_error(self, mock_load_workflow):
        """Should return error message when workflow not found"""
        mock_load_workflow.return_value = None

        result = validate_launch_workflow_params(
            launch_workflow_id="missing_workflow",
            default_launch_params=None,
            allowed_query_params=None,
            form_schema_fields=[]
        )

        assert "not found" in result

    @patch('shared.discovery.load_workflow')
    def test_missing_required_params_returns_error(self, mock_load_workflow):
        """Should return error when required params missing"""
        mock_param = MagicMock()
        mock_param.name = "required_param"
        mock_param.required = True

        mock_workflow = MagicMock()
        mock_workflow.parameters = [mock_param]

        mock_func = MagicMock()
        mock_load_workflow.return_value = (mock_func, mock_workflow)

        result = validate_launch_workflow_params(
            launch_workflow_id="test_workflow",
            default_launch_params=None,
            allowed_query_params=None,
            form_schema_fields=[]
        )

        assert "required_param" in result
        assert "no default values" in result

    @patch('shared.discovery.load_workflow')
    def test_params_with_defaults_pass_validation(self, mock_load_workflow):
        """Should pass validation when required params have defaults"""
        mock_param = MagicMock()
        mock_param.name = "param1"
        mock_param.required = True

        mock_workflow = MagicMock()
        mock_workflow.parameters = [mock_param]

        mock_func = MagicMock()
        mock_load_workflow.return_value = (mock_func, mock_workflow)

        result = validate_launch_workflow_params(
            launch_workflow_id="test_workflow",
            default_launch_params={"param1": "value1"},
            allowed_query_params=None,
            form_schema_fields=[]
        )

        assert result is None
