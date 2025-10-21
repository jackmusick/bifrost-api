"""
Unit tests for workflows_handlers
Tests workflow execution logic - focused on unit-testable portions
"""

import json
import pytest
from unittest.mock import Mock, patch

import azure.functions as func

from shared.handlers.workflows_handlers import execute_workflow_handler


class TestExecuteWorkflowHandlerBasic:
    """Test basic execute_workflow_handler error cases"""

    @pytest.mark.asyncio
    async def test_execute_workflow_not_found(self):
        """Test executing non-existent workflow"""
        mock_req = Mock(spec=func.HttpRequest)
        mock_req.route_params = {"workflowName": "nonexistent"}
        mock_req.get_json.return_value = {}
        mock_req.org_context = Mock(
            caller=Mock(user_id="user-123"),
        )

        with patch('shared.handlers.workflows_handlers.get_registry') as mock_reg:
            registry = mock_reg.return_value
            registry.get_workflow.return_value = None

            with patch('function_app.discover_workspace_modules'):
                response = await execute_workflow_handler(mock_req)

                assert response.status_code == 404
                data = json.loads(response.get_body())
                assert data["error"] == "NotFound"

    @pytest.mark.asyncio
    async def test_execute_workflow_invalid_json_body(self):
        """Test workflow execution with invalid JSON body"""
        mock_req = Mock(spec=func.HttpRequest)
        mock_req.route_params = {"workflowName": "test_workflow"}
        mock_req.get_json.return_value = "not a dict"  # Invalid
        mock_req.org_context = Mock(
            caller=Mock(user_id="user-123"),
        )

        with patch('function_app.discover_workspace_modules'):
            response = await execute_workflow_handler(mock_req)

            assert response.status_code == 400
            data = json.loads(response.get_body())
            assert data["error"] == "BadRequest"

    @pytest.mark.asyncio
    async def test_execute_workflow_parse_error(self):
        """Test workflow execution with JSON parsing error"""
        mock_req = Mock(spec=func.HttpRequest)
        mock_req.route_params = {"workflowName": "test_workflow"}
        mock_req.get_json.side_effect = ValueError("Invalid JSON")
        mock_req.org_context = Mock(
            caller=Mock(user_id="user-123"),
        )

        with patch('function_app.discover_workspace_modules'):
            response = await execute_workflow_handler(mock_req)

            assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_execute_workflow_missing_workflow_name(self):
        """Test execution without workflow name in route"""
        mock_req = Mock(spec=func.HttpRequest)
        mock_req.route_params = {}  # No workflowName
        mock_req.org_context = Mock(
            caller=Mock(user_id="user-123"),
        )

        with patch('function_app.discover_workspace_modules'):
            response = await execute_workflow_handler(mock_req)

            assert response.status_code == 500
            data = json.loads(response.get_body())
            assert data["error"] == "InternalError"
