"""
Unit tests for endpoints_handlers
Tests workflow endpoint execution logic - focused on unit-testable portions
"""

import json
import pytest
from unittest.mock import Mock, AsyncMock, patch

import azure.functions as func

from shared.handlers.endpoints_handlers import (
    parse_input_data,
    _execute_sync,
)
from shared.models import ExecutionStatus
from shared.error_handling import WorkflowError


class TestParseInputData:
    """Test parse_input_data utility function"""

    def test_parse_input_data_query_params_only(self):
        """Test parsing query parameters only"""
        mock_req = Mock(spec=func.HttpRequest)
        mock_req.params = {"key1": "value1", "key2": "value2"}
        mock_req.get_json.return_value = {}

        result = parse_input_data(mock_req)

        assert result == {"key1": "value1", "key2": "value2"}

    def test_parse_input_data_body_only(self):
        """Test parsing JSON body only"""
        mock_req = Mock(spec=func.HttpRequest)
        mock_req.params = {}
        mock_req.get_json.return_value = {"bodyKey": "bodyValue"}

        result = parse_input_data(mock_req)

        assert result == {"bodyKey": "bodyValue"}

    def test_parse_input_data_merged_body_precedence(self):
        """Test that body parameters take precedence over query params"""
        mock_req = Mock(spec=func.HttpRequest)
        mock_req.params = {"key": "query_value", "other": "other_value"}
        mock_req.get_json.return_value = {"key": "body_value"}

        result = parse_input_data(mock_req)

        assert result["key"] == "body_value"
        assert result["other"] == "other_value"

    def test_parse_input_data_no_json_body(self):
        """Test parsing when get_json returns None"""
        mock_req = Mock(spec=func.HttpRequest)
        mock_req.params = {"key": "value"}
        mock_req.get_json.return_value = None

        result = parse_input_data(mock_req)

        assert result == {"key": "value"}

    def test_parse_input_data_json_error(self):
        """Test that JSON parsing errors are raised"""
        mock_req = Mock(spec=func.HttpRequest)
        mock_req.params = {}
        mock_req.get_json.side_effect = ValueError("Invalid JSON")

        with pytest.raises(ValueError, match="Invalid JSON body"):
            parse_input_data(mock_req)


class TestExecuteSync:
    """Test sync workflow execution"""

    @pytest.mark.asyncio
    async def test_sync_execution_success(self):
        """Test successful sync workflow execution"""
        mock_context = Mock()
        mock_context.org_id = "org-123"
        mock_context.caller = Mock(user_id="user-123", name="Test User")
        mock_context.set_variable = Mock()

        mock_workflow_func = AsyncMock(return_value={"result": "success"})

        param = Mock()
        param.name = "param1"
        param.type = "string"

        mock_workflow = Mock()
        mock_workflow.function = mock_workflow_func
        mock_workflow.parameters = [param]

        mock_exec_logger = Mock()

        with patch('shared.handlers.endpoints_handlers.get_execution_logger') as mock_logger_factory:
            mock_logger_factory.return_value = mock_exec_logger

            with patch('shared.handlers.endpoints_handlers.coerce_parameter_types') as mock_coerce:
                mock_coerce.return_value = {"param1": "value1"}

                with patch('shared.handlers.endpoints_handlers.separate_workflow_params') as mock_separate:
                    mock_separate.return_value = ({"param1": "value1"}, {})

                    with patch('shared.handlers.endpoints_handlers.record_workflow_execution_result') as mock_record:
                        response_obj = Mock()
                        response_obj.model_dump.return_value = {
                            "executionId": "exec-123",
                            "status": "Success",
                            "durationMs": 100
                        }
                        mock_record.return_value = response_obj

                        response, status = await _execute_sync(
                            context=mock_context,
                            workflow_name="test_workflow",
                            http_method="POST",
                            input_data={"param1": "value1"},
                            workflow_metadata=mock_workflow
                        )

                        assert status == 200
                        data = json.loads(response.get_body())
                        assert data["executionId"] == "exec-123"
                        assert data["status"] == "Success"

                        mock_exec_logger.create_execution.assert_called_once()
                        mock_workflow_func.assert_called_once()
                        mock_record.assert_called_once()

    @pytest.mark.asyncio
    async def test_sync_execution_workflow_error(self):
        """Test sync execution with WorkflowError"""
        mock_context = Mock()
        mock_context.org_id = "org-123"
        mock_context.caller = Mock(user_id="user-123", name="Test User")
        mock_context.set_variable = Mock()

        mock_workflow_func = AsyncMock(side_effect=WorkflowError("ValidationError", "Workflow failed"))

        param = Mock()
        param.name = "param1"

        mock_workflow = Mock()
        mock_workflow.function = mock_workflow_func
        mock_workflow.parameters = [param]

        mock_exec_logger = Mock()

        with patch('shared.handlers.endpoints_handlers.get_execution_logger') as mock_logger_factory:
            mock_logger_factory.return_value = mock_exec_logger

            with patch('shared.handlers.endpoints_handlers.coerce_parameter_types') as mock_coerce:
                mock_coerce.return_value = {"param1": "value1"}

                with patch('shared.handlers.endpoints_handlers.separate_workflow_params') as mock_separate:
                    mock_separate.return_value = ({"param1": "value1"}, {})

                    with patch('shared.handlers.endpoints_handlers.record_workflow_execution_result') as mock_record:
                        response_obj = Mock()
                        response_obj.model_dump.return_value = {
                            "executionId": "exec-123",
                            "status": "Failed",
                            "error": "Workflow failed",
                            "durationMs": 100
                        }
                        mock_record.return_value = response_obj

                        response, status = await _execute_sync(
                            context=mock_context,
                            workflow_name="test_workflow",
                            http_method="POST",
                            input_data={"param1": "value1"},
                            workflow_metadata=mock_workflow
                        )

                        assert status == 200
                        data = json.loads(response.get_body())
                        assert data["status"] == "Failed"

                        # Verify record was called with FAILED status
                        call_kwargs = mock_record.call_args.kwargs
                        assert call_kwargs["status"] == ExecutionStatus.FAILED
                        assert call_kwargs["context"] == mock_context

    @pytest.mark.asyncio
    async def test_sync_execution_unexpected_error(self):
        """Test sync execution with unexpected error"""
        mock_context = Mock()
        mock_context.org_id = "org-123"
        mock_context.caller = Mock(user_id="user-123", name="Test User")
        mock_context.set_variable = Mock()

        mock_workflow_func = AsyncMock(side_effect=RuntimeError("Unexpected error"))

        param = Mock()
        param.name = "param1"

        mock_workflow = Mock()
        mock_workflow.function = mock_workflow_func
        mock_workflow.parameters = [param]

        mock_exec_logger = Mock()

        with patch('shared.handlers.endpoints_handlers.get_execution_logger') as mock_logger_factory:
            mock_logger_factory.return_value = mock_exec_logger

            with patch('shared.handlers.endpoints_handlers.coerce_parameter_types') as mock_coerce:
                mock_coerce.return_value = {"param1": "value1"}

                with patch('shared.handlers.endpoints_handlers.separate_workflow_params') as mock_separate:
                    mock_separate.return_value = ({"param1": "value1"}, {})

                    with patch('shared.handlers.endpoints_handlers.record_workflow_execution_result') as mock_record:
                        response_obj = Mock()
                        response_obj.model_dump.return_value = {
                            "executionId": "exec-123",
                            "status": "Failed",
                            "error": "Unexpected error",
                            "durationMs": 100
                        }
                        mock_record.return_value = response_obj

                        response, status = await _execute_sync(
                            context=mock_context,
                            workflow_name="test_workflow",
                            http_method="POST",
                            input_data={"param1": "value1"},
                            workflow_metadata=mock_workflow
                        )

                        assert status == 200
                        data = json.loads(response.get_body())
                        assert data["status"] == "Failed"

    @pytest.mark.asyncio
    async def test_sync_execution_with_extra_variables(self):
        """Test sync execution with extra variables injected into context"""
        mock_context = Mock()
        mock_context.org_id = "org-123"
        mock_context.caller = Mock(user_id="user-123", name="Test User")
        mock_context.set_variable = Mock()

        mock_workflow_func = AsyncMock(return_value={"result": "success"})

        param = Mock()
        param.name = "param1"

        mock_workflow = Mock()
        mock_workflow.function = mock_workflow_func
        mock_workflow.parameters = [param]

        mock_exec_logger = Mock()

        with patch('shared.handlers.endpoints_handlers.get_execution_logger') as mock_logger_factory:
            mock_logger_factory.return_value = mock_exec_logger

            with patch('shared.handlers.endpoints_handlers.coerce_parameter_types') as mock_coerce:
                mock_coerce.return_value = {"param1": "value1", "extra_var": "extra_value"}

                with patch('shared.handlers.endpoints_handlers.separate_workflow_params') as mock_separate:
                    mock_separate.return_value = (
                        {"param1": "value1"},
                        {"extra_var": "extra_value"}
                    )

                    with patch('shared.handlers.endpoints_handlers.record_workflow_execution_result') as mock_record:
                        response_obj = Mock()
                        response_obj.model_dump.return_value = {
                            "executionId": "exec-123",
                            "status": "Success",
                            "durationMs": 100
                        }
                        mock_record.return_value = response_obj

                        response, status = await _execute_sync(
                            context=mock_context,
                            workflow_name="test_workflow",
                            http_method="POST",
                            input_data={"param1": "value1", "extra_var": "extra_value"},
                            workflow_metadata=mock_workflow
                        )

                        assert status == 200

                        # Verify extra variables were set
                        mock_context.set_variable.assert_called_with("extra_var", "extra_value")
