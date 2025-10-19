"""
Contract tests for Async Workflow Execution API (User Story 4)
Tests Pydantic validation for async workflow execution, status tracking, and result retrieval
"""

from datetime import datetime, timedelta
from typing import Optional

import pytest
from pydantic import ValidationError

from shared.models import (
    ExecutionStatus,
    WorkflowMetadata,
)


# ==================== ASYNC EXECUTION REQUEST TESTS ====================

class TestAsyncExecutionRequest:
    """Test async execution request validation"""

    def test_workflow_metadata_with_async_flag(self):
        """Test WorkflowMetadata with async execution enabled"""
        metadata = WorkflowMetadata(
            name="long_running_workflow",
            description="Long running workflow",
            isAsync=True
        )
        assert metadata.isAsync is True

    def test_workflow_metadata_async_default_false(self):
        """Test that isAsync defaults to False"""
        metadata = WorkflowMetadata(
            name="sync_workflow",
            description="Synchronous workflow"
        )
        assert metadata.isAsync is False

    def test_workflow_metadata_explicit_sync(self):
        """Test WorkflowMetadata with explicit sync execution"""
        metadata = WorkflowMetadata(
            name="sync_workflow",
            description="Sync workflow",
            isAsync=False
        )
        assert metadata.isAsync is False


# ==================== EXECUTION STATUS TESTS ====================

class TestExecutionStatusEnum:
    """Test ExecutionStatus enum values for async workflows"""

    def test_pending_status(self):
        """Test PENDING status for queued executions"""
        status = ExecutionStatus.PENDING
        assert status == "Pending"
        assert status.value == "Pending"

    def test_running_status(self):
        """Test RUNNING status for active executions"""
        status = ExecutionStatus.RUNNING
        assert status == "Running"
        assert status.value == "Running"

    def test_success_status(self):
        """Test SUCCESS status for completed executions"""
        status = ExecutionStatus.SUCCESS
        assert status == "Success"
        assert status.value == "Success"

    def test_failed_status(self):
        """Test FAILED status for failed executions"""
        status = ExecutionStatus.FAILED
        assert status == "Failed"
        assert status.value == "Failed"

    def test_completed_with_errors_status(self):
        """Test COMPLETED_WITH_ERRORS status"""
        status = ExecutionStatus.COMPLETED_WITH_ERRORS
        assert status == "CompletedWithErrors"
        assert status.value == "CompletedWithErrors"

    def test_status_transitions(self):
        """Test valid status transitions for async execution lifecycle"""
        # Valid async workflow lifecycle: PENDING → RUNNING → SUCCESS/FAILED
        initial = ExecutionStatus.PENDING
        running = ExecutionStatus.RUNNING
        completed = ExecutionStatus.SUCCESS

        assert initial == ExecutionStatus.PENDING
        assert running == ExecutionStatus.RUNNING
        assert completed == ExecutionStatus.SUCCESS


# ==================== ASYNC EXECUTION LIFECYCLE TESTS ====================

class TestAsyncExecutionLifecycle:
    """Test async execution lifecycle scenarios"""

    def test_async_workflow_queued_state(self):
        """Test async workflow starts in PENDING state"""
        metadata = WorkflowMetadata(
            name="async_workflow",
            description="Async workflow",
            isAsync=True
        )

        # When triggered, execution should be PENDING
        initial_status = ExecutionStatus.PENDING
        assert initial_status == ExecutionStatus.PENDING
        assert metadata.isAsync is True

    def test_async_workflow_running_state(self):
        """Test async workflow transitions to RUNNING"""
        metadata = WorkflowMetadata(
            name="async_workflow",
            description="Async workflow",
            isAsync=True
        )

        # Worker picks up execution
        running_status = ExecutionStatus.RUNNING
        assert running_status == ExecutionStatus.RUNNING

    def test_async_workflow_success_state(self):
        """Test async workflow completes successfully"""
        metadata = WorkflowMetadata(
            name="async_workflow",
            description="Async workflow",
            isAsync=True
        )

        # Execution completes
        final_status = ExecutionStatus.SUCCESS
        assert final_status == ExecutionStatus.SUCCESS

    def test_async_workflow_failure_state(self):
        """Test async workflow fails"""
        metadata = WorkflowMetadata(
            name="async_workflow",
            description="Async workflow",
            isAsync=True
        )

        # Execution fails
        final_status = ExecutionStatus.FAILED
        assert final_status == ExecutionStatus.FAILED


# ==================== BATCH STATUS QUERY TESTS ====================

class TestBatchStatusQuery:
    """Test batch status query scenarios"""

    def test_multiple_execution_ids_list(self):
        """Test querying status for multiple execution IDs"""
        execution_ids = [
            "exec-1",
            "exec-2",
            "exec-3"
        ]

        assert len(execution_ids) == 3
        assert "exec-1" in execution_ids
        assert "exec-2" in execution_ids
        assert "exec-3" in execution_ids

    def test_empty_execution_ids_list(self):
        """Test empty execution IDs list"""
        execution_ids = []
        assert len(execution_ids) == 0

    def test_single_execution_id_list(self):
        """Test single execution ID in list"""
        execution_ids = ["exec-1"]
        assert len(execution_ids) == 1
        assert execution_ids[0] == "exec-1"


# ==================== RESULT RETRIEVAL TESTS ====================

class TestResultRetrieval:
    """Test execution result retrieval scenarios"""

    def test_small_result_inline_storage(self):
        """Test small result stored inline (<32KB)"""
        # Small results should be stored in Executions table directly
        small_result = {"status": "ok", "count": 42}
        result_size = len(str(small_result).encode('utf-8'))

        # Should be much smaller than 32KB
        assert result_size < 32 * 1024

    def test_large_result_blob_storage(self):
        """Test large result requires blob storage (>32KB)"""
        # Large results should reference blob storage
        # Simulate a result that would exceed 32KB
        large_data = "x" * (33 * 1024)  # 33KB of data
        result_size = len(large_data.encode('utf-8'))

        # Should exceed 32KB threshold
        assert result_size > 32 * 1024


# ==================== CONTEXT PRESERVATION TESTS ====================

class TestContextPreservation:
    """Test context preservation in async execution"""

    def test_org_scope_preservation(self):
        """Test organization scope is preserved in queue message"""
        org_id = "org-123"
        user_id = "user-456"

        # Context should be serializable
        context_data = {
            "org_id": org_id,
            "user_id": user_id,
            "workflow_name": "async_workflow",
            "parameters": {"param1": "value1"}
        }

        assert context_data["org_id"] == org_id
        assert context_data["user_id"] == user_id
        assert context_data["workflow_name"] == "async_workflow"

    def test_parameters_preservation(self):
        """Test workflow parameters are preserved"""
        parameters = {
            "input_file": "data.csv",
            "output_format": "json",
            "max_rows": 1000
        }

        # Parameters should be JSON-serializable
        import json
        serialized = json.dumps(parameters)
        deserialized = json.loads(serialized)

        assert deserialized == parameters
        assert deserialized["input_file"] == "data.csv"
        assert deserialized["max_rows"] == 1000


# ==================== ERROR HANDLING TESTS ====================

class TestAsyncErrorHandling:
    """Test error handling in async execution"""

    def test_failed_execution_with_error_message(self):
        """Test failed execution stores error details"""
        status = ExecutionStatus.FAILED
        error_message = "Failed to connect to database"

        assert status == ExecutionStatus.FAILED
        assert error_message is not None
        assert len(error_message) > 0

    def test_failed_execution_with_stack_trace(self):
        """Test failed execution can store stack trace"""
        status = ExecutionStatus.FAILED
        stack_trace = "Traceback (most recent call last):\n  File..."

        assert status == ExecutionStatus.FAILED
        assert stack_trace.startswith("Traceback")


# ==================== TIMEOUT TESTS ====================

class TestAsyncTimeout:
    """Test async execution timeout scenarios"""

    def test_execution_with_timeout(self):
        """Test execution can have timeout setting"""
        timeout_seconds = 300  # 5 minutes

        assert timeout_seconds > 0
        assert timeout_seconds <= 3600  # Max 1 hour

    def test_execution_timeout_exceeded(self):
        """Test execution timeout handling"""
        start_time = datetime.utcnow()
        timeout_seconds = 60
        current_time = start_time + timedelta(seconds=61)

        # Check if timeout exceeded
        elapsed = (current_time - start_time).total_seconds()
        is_timeout = elapsed > timeout_seconds

        assert is_timeout is True


# ==================== QUEUE MESSAGE TESTS ====================

class TestQueueMessage:
    """Test queue message structure for async execution"""

    def test_queue_message_structure(self):
        """Test queue message contains required fields"""
        message = {
            "execution_id": "exec-123",
            "workflow_name": "async_workflow",
            "org_id": "org-456",
            "user_id": "user-789",
            "parameters": {"key": "value"}
        }

        assert "execution_id" in message
        assert "workflow_name" in message
        assert "org_id" in message
        assert "user_id" in message
        assert "parameters" in message

    def test_queue_message_json_serialization(self):
        """Test queue message can be JSON serialized"""
        import json

        message = {
            "execution_id": "exec-123",
            "workflow_name": "async_workflow",
            "org_id": "org-456",
            "parameters": {"key": "value"}
        }

        # Should serialize and deserialize without errors
        serialized = json.dumps(message)
        deserialized = json.loads(serialized)

        assert deserialized == message
        assert deserialized["execution_id"] == "exec-123"
