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
