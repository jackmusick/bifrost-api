"""
Contract Tests for Workflow Execution API
Tests request/response models for workflow execution endpoint
"""

import pytest
from pydantic import ValidationError
from datetime import datetime

from shared.models import (
    WorkflowExecutionRequest,
    WorkflowExecutionResponse,
    ExecutionStatus,
    ErrorResponse
)


class TestWorkflowExecutionRequest:
    """Test WorkflowExecutionRequest validation"""

    def test_valid_execution_request(self):
        """Test valid execution request with all fields"""
        request = WorkflowExecutionRequest(
            workflowName="user_onboarding",
            formId="form-123",
            inputData={
                "email": "test@example.com",
                "first_name": "Test",
                "last_name": "User"
            }
        )

        assert request.workflowName == "user_onboarding"
        assert request.formId == "form-123"
        assert request.inputData["email"] == "test@example.com"

    def test_execution_request_minimal(self):
        """Test execution request with only required fields"""
        request = WorkflowExecutionRequest(
            workflowName="test_workflow",
            inputData={}
        )

        assert request.workflowName == "test_workflow"
        assert request.formId is None
        assert request.inputData == {}

    def test_execution_request_missing_workflow_name(self):
        """Test that workflow name is required"""
        with pytest.raises(ValidationError) as exc_info:
            WorkflowExecutionRequest(
                inputData={"key": "value"}
            )

        errors = exc_info.value.errors()
        assert any(e['loc'] == ('workflowName',) for e in errors)

    def test_execution_request_missing_input_data(self):
        """Test that input data is required"""
        with pytest.raises(ValidationError) as exc_info:
            WorkflowExecutionRequest(
                workflowName="test_workflow"
            )

        errors = exc_info.value.errors()
        assert any(e['loc'] == ('inputData',) for e in errors)


class TestWorkflowExecutionResponse:
    """Test WorkflowExecutionResponse validation"""

    def test_success_response(self):
        """Test successful execution response"""
        response = WorkflowExecutionResponse(
            executionId="exec-123",
            status=ExecutionStatus.SUCCESS,
            message="Workflow executed successfully"
        )

        assert response.executionId == "exec-123"
        assert response.status == ExecutionStatus.SUCCESS
        assert response.message == "Workflow executed successfully"

    def test_failed_response(self):
        """Test failed execution response"""
        response = WorkflowExecutionResponse(
            executionId="exec-789",
            status=ExecutionStatus.FAILED,
            message="Validation failed"
        )

        assert response.executionId == "exec-789"
        assert response.status == ExecutionStatus.FAILED
        assert response.message == "Validation failed"

    def test_running_response(self):
        """Test running/pending response"""
        response = WorkflowExecutionResponse(
            executionId="exec-999",
            status=ExecutionStatus.RUNNING,
            message="Workflow is running"
        )

        assert response.executionId == "exec-999"
        assert response.status == ExecutionStatus.RUNNING
        assert response.message == "Workflow is running"

    def test_response_required_fields(self):
        """Test that executionId and status are required"""
        with pytest.raises(ValidationError) as exc_info:
            WorkflowExecutionResponse(
                executionId="exec-123"
            )

        errors = exc_info.value.errors()
        assert any(e['loc'] == ('status',) for e in errors)


class TestErrorResponse:
    """Test ErrorResponse model"""

    def test_error_response_basic(self):
        """Test basic error response"""
        error = ErrorResponse(
            error="NotFound",
            message="Workflow not found"
        )

        assert error.error == "NotFound"
        assert error.message == "Workflow not found"
        assert error.details is None

    def test_error_response_with_details(self):
        """Test error response with details"""
        error = ErrorResponse(
            error="ValidationError",
            message="Invalid input parameters",
            details={
                "field": "email",
                "issue": "Invalid email format"
            }
        )

        assert error.error == "ValidationError"
        assert error.details["field"] == "email"

    def test_error_response_required_fields(self):
        """Test that error and message are required"""
        with pytest.raises(ValidationError) as exc_info:
            ErrorResponse(error="NotFound")

        errors = exc_info.value.errors()
        assert any(e['loc'] == ('message',) for e in errors)


class TestExecutionStatus:
    """Test ExecutionStatus enum"""

    def test_execution_status_values(self):
        """Test all execution status values"""
        assert ExecutionStatus.PENDING == "Pending"
        assert ExecutionStatus.RUNNING == "Running"
        assert ExecutionStatus.SUCCESS == "Success"
        assert ExecutionStatus.FAILED == "Failed"

    def test_execution_status_in_response(self):
        """Test using ExecutionStatus in response"""
        response = WorkflowExecutionResponse(
            executionId="exec-123",
            status=ExecutionStatus.SUCCESS,
            message="Success"
        )

        assert response.status == "Success"
        assert isinstance(response.status, ExecutionStatus)
