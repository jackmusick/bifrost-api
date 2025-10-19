"""
Unit tests for endpoints_handlers
Tests workflow endpoint execution logic - focused on unit-testable portions
"""

import json
import pytest
import uuid
from unittest.mock import Mock, AsyncMock, patch

import azure.functions as func

from shared.handlers.endpoints_handlers import (
    execute_workflow_endpoint_handler,
    parse_input_data,
    _execute_async,
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


class TestExecuteWorkflowEndpointHandlerBasic:
    """Test basic execute_workflow_endpoint_handler error cases"""

    @pytest.mark.asyncio
    async def test_workflow_not_found(self):
        """Test executing non-existent workflow"""
        mock_context = Mock()
        mock_context.org_id = "org-123"
        mock_context.caller = Mock(user_id="user-123", name="Test User")

        with patch('shared.handlers.endpoints_handlers.get_registry') as mock_reg:
            registry = mock_reg.return_value
            registry.get_workflow.return_value = None

            response, status = await execute_workflow_endpoint_handler(
                context=mock_context,
                workflow_name="nonexistent",
                http_method="POST",
                input_data={}
            )

            assert status == 404
            data = json.loads(response.get_body())
            assert data["error"] == "NotFound"
            assert "not found" in data["message"].lower()

    @pytest.mark.asyncio
    async def test_endpoint_not_enabled(self):
        """Test executing workflow with endpoint disabled"""
        mock_context = Mock()
        mock_workflow = Mock()
        mock_workflow.endpoint_enabled = False

        with patch('shared.handlers.endpoints_handlers.get_registry') as mock_reg:
            registry = mock_reg.return_value
            registry.get_workflow.return_value = mock_workflow

            response, status = await execute_workflow_endpoint_handler(
                context=mock_context,
                workflow_name="test_workflow",
                http_method="POST",
                input_data={}
            )

            assert status == 404
            data = json.loads(response.get_body())
            assert data["error"] == "NotFound"
            assert "not enabled" in data["message"].lower()

    @pytest.mark.asyncio
    async def test_http_method_not_allowed(self):
        """Test executing workflow with disallowed HTTP method"""
        mock_context = Mock()
        mock_workflow = Mock()
        mock_workflow.endpoint_enabled = True
        mock_workflow.allowed_methods = ["POST", "PUT"]

        with patch('shared.handlers.endpoints_handlers.get_registry') as mock_reg:
            registry = mock_reg.return_value
            registry.get_workflow.return_value = mock_workflow

            response, status = await execute_workflow_endpoint_handler(
                context=mock_context,
                workflow_name="test_workflow",
                http_method="GET",
                input_data={}
            )

            assert status == 405
            data = json.loads(response.get_body())
            assert data["error"] == "MethodNotAllowed"
            assert "GET" in data["message"]

    @pytest.mark.asyncio
    async def test_http_method_allowed_default_post(self):
        """Test that POST is default allowed method"""
        mock_context = Mock()
        mock_workflow = Mock()
        mock_workflow.endpoint_enabled = True
        mock_workflow.allowed_methods = None  # Should default to ['POST']

        with patch('shared.handlers.endpoints_handlers.get_registry') as mock_reg:
            registry = mock_reg.return_value
            registry.get_workflow.return_value = mock_workflow

            with patch('shared.handlers.endpoints_handlers._execute_sync') as mock_sync:
                mock_sync.return_value = (Mock(), 200)

                await execute_workflow_endpoint_handler(
                    context=mock_context,
                    workflow_name="test_workflow",
                    http_method="POST",
                    input_data={}
                )

                mock_sync.assert_called_once()

    @pytest.mark.asyncio
    async def test_http_method_not_allowed_default(self):
        """Test that non-POST methods are rejected when allowed_methods is None"""
        mock_context = Mock()
        mock_workflow = Mock()
        mock_workflow.endpoint_enabled = True
        mock_workflow.allowed_methods = None  # Should default to ['POST']

        with patch('shared.handlers.endpoints_handlers.get_registry') as mock_reg:
            registry = mock_reg.return_value
            registry.get_workflow.return_value = mock_workflow

            response, status = await execute_workflow_endpoint_handler(
                context=mock_context,
                workflow_name="test_workflow",
                http_method="GET",
                input_data={}
            )

            assert status == 405
            data = json.loads(response.get_body())
            assert data["error"] == "MethodNotAllowed"


class TestExecuteAsync:
    """Test async workflow execution"""

    @pytest.mark.asyncio
    async def test_async_execution_enqueued(self):
        """Test that async workflows are properly enqueued"""
        mock_context = Mock()
        mock_context.org_id = "org-123"

        execution_id = str(uuid.uuid4())

        with patch('shared.handlers.endpoints_handlers.enqueue_workflow_execution') as mock_enqueue:
            mock_enqueue.return_value = execution_id

            response, status = await _execute_async(
                context=mock_context,
                workflow_name="async_workflow",
                input_data={"param": "value"}
            )

            assert status == 202
            data = json.loads(response.get_body())
            assert data["executionId"] == execution_id
            assert data["status"] == "Pending"
            assert "queued" in data["message"].lower()

            mock_enqueue.assert_called_once_with(
                context=mock_context,
                workflow_name="async_workflow",
                parameters={"param": "value"},
                form_id=None
            )


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

        mock_exec_logger = AsyncMock()

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

        mock_exec_logger = AsyncMock()

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

        mock_exec_logger = AsyncMock()

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

        mock_exec_logger = AsyncMock()

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


class TestExecuteWorkflowEndpointHandlerIntegration:
    """Integration tests for execute_workflow_endpoint_handler"""

    @pytest.mark.asyncio
    async def test_handler_dispatches_to_async(self):
        """Test that async workflows are dispatched correctly"""
        mock_context = Mock()
        mock_context.org_id = "org-123"

        mock_workflow = Mock()
        mock_workflow.endpoint_enabled = True
        mock_workflow.allowed_methods = ["POST"]
        mock_workflow.execution_mode = "async"

        with patch('shared.handlers.endpoints_handlers.get_registry') as mock_reg:
            registry = mock_reg.return_value
            registry.get_workflow.return_value = mock_workflow

            with patch('shared.handlers.endpoints_handlers._execute_async') as mock_async:
                mock_async.return_value = (Mock(), 202)

                response, status = await execute_workflow_endpoint_handler(
                    context=mock_context,
                    workflow_name="async_workflow",
                    http_method="POST",
                    input_data={}
                )

                assert status == 202
                mock_async.assert_called_once()

    @pytest.mark.asyncio
    async def test_handler_dispatches_to_sync(self):
        """Test that sync workflows are dispatched correctly"""
        mock_context = Mock()
        mock_context.org_id = "org-123"

        mock_workflow = Mock()
        mock_workflow.endpoint_enabled = True
        mock_workflow.allowed_methods = ["POST"]
        mock_workflow.execution_mode = "sync"

        with patch('shared.handlers.endpoints_handlers.get_registry') as mock_reg:
            registry = mock_reg.return_value
            registry.get_workflow.return_value = mock_workflow

            with patch('shared.handlers.endpoints_handlers._execute_sync') as mock_sync:
                mock_sync.return_value = (Mock(), 200)

                response, status = await execute_workflow_endpoint_handler(
                    context=mock_context,
                    workflow_name="sync_workflow",
                    http_method="POST",
                    input_data={}
                )

                assert status == 200
                mock_sync.assert_called_once_with(
                    context=mock_context,
                    workflow_name="sync_workflow",
                    http_method="POST",
                    input_data={},
                    workflow_metadata=mock_workflow
                )
