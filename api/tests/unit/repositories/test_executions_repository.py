"""
Unit tests for ExecutionRepository
"""

import json
import pytest
from datetime import datetime
from unittest.mock import patch

from shared.repositories.executions import ExecutionRepository
from shared.models import ExecutionStatus


class TestExecutionRepositoryCreate:
    """Test execution creation"""

    def test_create_execution_success(self, mock_table_service):
        """Test successful execution creation"""
        repo = ExecutionRepository()

        mock_table_service.insert_entity.return_value = None

        result = repo.create_execution(
            execution_id="exec-uuid-123",
            org_id="org-123",
            user_id="user@example.com",
            user_name="John Doe",
            workflow_name="CreateUserWorkflow",
            input_data={"email": "new@example.com"},
            form_id="form-456"
        )

        assert result.executionId == "exec-uuid-123"
        assert result.workflowName == "CreateUserWorkflow"
        assert result.status == ExecutionStatus.RUNNING
        assert result.startedAt is not None
        # Should create 5 indexes: primary + user + workflow + form + status
        assert mock_table_service.insert_entity.call_count == 5

    def test_create_execution_without_form(self, mock_table_service):
        """Test execution creation without form_id"""
        repo = ExecutionRepository()

        mock_table_service.insert_entity.return_value = None

        result = repo.create_execution(
            execution_id="exec-uuid-789",
            org_id="org-123",
            user_id="user@example.com",
            user_name="John Doe",
            workflow_name="BulkCreateUsers",
            input_data={"count": 10},
            form_id=None
        )

        assert result.formId is None
        # Should create 4 indexes: primary + user + workflow + status (no form)
        assert mock_table_service.insert_entity.call_count == 4

    def test_create_execution_global_scope(self, mock_table_service):
        """Test execution in GLOBAL scope"""
        repo = ExecutionRepository()

        mock_table_service.insert_entity.return_value = None

        result = repo.create_execution(
            execution_id="exec-global",
            org_id=None,
            user_id="user@example.com",
            user_name="Admin",
            workflow_name="AdminWorkflow",
            input_data={},
            form_id=None
        )

        # When org_id is None, the execution is global-scoped
        # Check that the execution was created successfully
        assert result.executionId == "exec-global"
        assert result.workflowName == "AdminWorkflow"
        # orgId may be None or "GLOBAL" depending on implementation
        assert result.orgId in [None, "GLOBAL"]


class TestExecutionRepositoryRead:
    """Test execution retrieval"""

    def test_get_execution_success(self, mock_table_service):
        """Test retrieving execution"""
        repo = ExecutionRepository()

        mock_table_service.query_entities.return_value = iter([{
            "PartitionKey": "org-123",
            "RowKey": "execution:9999999999999_exec-123",
            "ExecutionId": "exec-123",
            "WorkflowName": "CreateUserWorkflow",
            "FormId": "form-456",
            "ExecutedBy": "user@example.com",
            "ExecutedByName": "John Doe",
            "Status": "Success",
            "InputData": json.dumps({"email": "new@example.com"}),
            "Result": json.dumps({"userId": "123"}),
            "StartedAt": "2024-01-15T10:30:00",
            "CompletedAt": "2024-01-15T10:31:00",
            "DurationMs": 60000
        }])

        result = repo.get_execution("exec-123", "org-123")

        assert result is not None
        assert result.executionId == "exec-123"
        assert result.workflowName == "CreateUserWorkflow"

    def test_get_execution_not_found(self, mock_table_service):
        """Test retrieving non-existent execution"""
        repo = ExecutionRepository()

        mock_table_service.query_entities.return_value = iter([])

        result = repo.get_execution("nonexistent", "org-123")

        assert result is None

    def test_list_executions_by_user(self, mock_table_service):
        """Test listing executions for a user"""
        repo = ExecutionRepository()

        executions_data = [
            {
                "PartitionKey": "GLOBAL",
                "RowKey": "userexec:user@example.com:exec-1",
                "ExecutionId": "exec-1",
                "WorkflowName": "Workflow1",
                "Status": "Success",
                "StartedAt": "2024-01-15T10:30:00",
                "CompletedAt": "2024-01-15T10:31:00",
                "InputData": "{}"
            },
            {
                "PartitionKey": "GLOBAL",
                "RowKey": "userexec:user@example.com:exec-2",
                "ExecutionId": "exec-2",
                "WorkflowName": "Workflow2",
                "Status": "Running",
                "StartedAt": "2024-01-15T11:00:00",
                "CompletedAt": None,
                "InputData": "{}"
            }
        ]

        # Mock relationships_service.query_entities_paged to return tuple
        with patch.object(repo.relationships_service, 'query_entities_paged', return_value=(executions_data, None)):
            result = repo.list_executions_by_user("user@example.com", limit=50)

            assert len(result) == 2
            assert result[0].executionId == "exec-1"
            assert result[1].status == ExecutionStatus.RUNNING

    def test_list_executions_by_workflow(self, mock_table_service):
        """Test listing executions for a workflow"""
        repo = ExecutionRepository()

        executions_data = [
            {
                "PartitionKey": "GLOBAL",
                "RowKey": "workflowexec:CreateUserWorkflow:org-123:exec-1",
                "ExecutionId": "exec-1",
                "ExecutedBy": "user1@example.com",
                "Status": "Success",
                "StartedAt": "2024-01-15T10:30:00",
                "CompletedAt": "2024-01-15T10:31:00"
            }
        ]

        mock_table_service.query_entities.return_value = iter(executions_data)

        result = repo.list_executions_by_workflow("CreateUserWorkflow", "org-123", limit=100)

        assert len(result) == 1
        assert result[0].workflowName == "CreateUserWorkflow"

    def test_list_executions_by_form(self, mock_table_service):
        """Test listing executions for a form"""
        repo = ExecutionRepository()

        executions_data = [
            {
                "PartitionKey": "GLOBAL",
                "RowKey": "formexec:form-456:exec-1",
                "ExecutionId": "exec-1",
                "WorkflowName": "FormWorkflow",
                "ExecutedBy": "user@example.com",
                "Status": "Success",
                "StartedAt": "2024-01-15T10:30:00",
                "CompletedAt": "2024-01-15T10:31:00"
            }
        ]

        mock_table_service.query_entities.return_value = iter(executions_data)

        result = repo.list_executions_by_form("form-456", limit=100)

        assert len(result) == 1
        assert result[0].formId == "form-456"

    def test_list_executions_for_org(self, mock_table_service):
        """Test listing all executions for organization"""
        repo = ExecutionRepository()

        executions_data = [
            {
                "PartitionKey": "org-123",
                "RowKey": "execution:9999999999999_exec-1",
                "ExecutionId": "exec-1"
            },
            {
                "PartitionKey": "org-123",
                "RowKey": "execution:9999999999998_exec-2",
                "ExecutionId": "exec-2"
            }
        ]

        mock_table_service.query_entities.return_value = iter(executions_data)

        result = repo.list_executions_for_org("org-123", limit=100)

        assert len(result) == 2

    def test_list_executions_empty(self, mock_table_service):
        """Test listing executions when none exist"""
        repo = ExecutionRepository()

        # Mock query_paged to return empty tuple
        with patch.object(repo, 'query_paged', return_value=([], None)):
            result = repo.list_executions("org-123", limit=50)

            assert result == []


class TestExecutionRepositoryUpdate:
    """Test execution updates"""

    def test_update_execution_success(self, mock_table_service):
        """Test updating execution with completion data"""
        repo = ExecutionRepository()

        execution_data = {
            "PartitionKey": "org-123",
            "RowKey": "execution:9999999999999_exec-123",
            "ExecutionId": "exec-123",
            "WorkflowName": "CreateUserWorkflow",
            "FormId": "form-456",
            "Status": "Running",
            "StartedAt": "2024-01-15T10:30:00"
        }

        mock_table_service.query_entities.return_value = iter([execution_data])
        mock_table_service.update_entity.return_value = None
        mock_table_service.get_entity.return_value = None

        result = repo.update_execution(
            execution_id="exec-123",
            org_id="org-123",
            user_id="user@example.com",
            status=ExecutionStatus.SUCCESS,
            result={"userId": "new-user-123"},
            duration_ms=60000
        )

        assert result.status == ExecutionStatus.SUCCESS
        # Should update primary + indexes
        assert mock_table_service.update_entity.call_count >= 1

    def test_update_execution_not_found(self, mock_table_service):
        """Test update raises error when execution not found"""
        repo = ExecutionRepository()

        mock_table_service.query_entities.return_value = iter([])

        with pytest.raises(ValueError, match="not found"):
            repo.update_execution(
                execution_id="nonexistent",
                org_id="org-123",
                user_id="user@example.com",
                status=ExecutionStatus.SUCCESS
            )

    def test_update_execution_with_error(self, mock_table_service):
        """Test updating execution with error message"""
        repo = ExecutionRepository()

        execution_data = {
            "PartitionKey": "org-123",
            "RowKey": "execution:9999999999999_exec-123",
            "ExecutionId": "exec-123",
            "WorkflowName": "Workflow",
            "Status": "Running",
            "StartedAt": "2024-01-15T10:30:00"
        }

        mock_table_service.query_entities.return_value = iter([execution_data])
        mock_table_service.update_entity.return_value = None
        mock_table_service.get_entity.return_value = None

        result = repo.update_execution(
            execution_id="exec-123",
            org_id="org-123",
            user_id="user@example.com",
            status=ExecutionStatus.FAILED,
            error_message="API connection timeout",
            duration_ms=30000
        )

        assert result.status == ExecutionStatus.FAILED
        assert result.errorMessage == "API connection timeout"


class TestExecutionRepositoryHelpers:
    """Test helper methods"""

    def test_reverse_timestamp(self):
        """Test reverse timestamp generation"""
        repo = ExecutionRepository()

        dt = datetime(2024, 1, 15, 10, 30, 45)
        reverse_ts = repo._reverse_timestamp(dt)

        assert isinstance(reverse_ts, str)
        assert len(reverse_ts) > 0

    def test_execution_timestamps_parsed(self, mock_table_service):
        """Test that execution timestamps are parsed correctly"""
        repo = ExecutionRepository()

        mock_table_service.query_entities.return_value = iter([{
            "PartitionKey": "org-123",
            "RowKey": "execution:9999999999999_exec-123",
            "ExecutionId": "exec-123",
            "WorkflowName": "Workflow",
            "Status": "Success",
            "InputData": "{}",
            "Result": None,
            "StartedAt": "2024-01-15T10:30:45.123456",
            "CompletedAt": "2024-01-15T10:31:15.654321"
        }])

        result = repo.get_execution("exec-123", "org-123")

        assert result is not None
        assert result.startedAt is not None
        assert result.completedAt is not None
        assert result.completedAt > result.startedAt

    def test_execution_result_parsing_json(self, mock_table_service):
        """Test parsing JSON result"""
        repo = ExecutionRepository()

        result_json = {"userId": "123", "status": "created"}
        mock_table_service.query_entities.return_value = iter([{
            "PartitionKey": "org-123",
            "RowKey": "execution:9999999999999_exec-123",
            "ExecutionId": "exec-123",
            "WorkflowName": "Workflow",
            "Status": "Success",
            "InputData": "{}",
            "Result": json.dumps(result_json),
            "ResultInBlob": False,
            "StartedAt": "2024-01-15T10:30:00",
            "CompletedAt": "2024-01-15T10:31:00"
        }])

        result = repo.get_execution("exec-123", "org-123")

        assert result is not None
        assert result.result == result_json
        assert result.resultType == "json"

    def test_execution_result_parsing_html(self, mock_table_service):
        """Test parsing HTML result"""
        repo = ExecutionRepository()

        html_result = "<html><body>Success</body></html>"
        mock_table_service.query_entities.return_value = iter([{
            "PartitionKey": "org-123",
            "RowKey": "execution:9999999999999_exec-123",
            "ExecutionId": "exec-123",
            "WorkflowName": "Workflow",
            "Status": "Success",
            "InputData": "{}",
            "Result": html_result,
            "ResultInBlob": False,
            "StartedAt": "2024-01-15T10:30:00",
            "CompletedAt": "2024-01-15T10:31:00"
        }])

        result = repo.get_execution("exec-123", "org-123")

        assert result is not None
        assert result.result == html_result
        assert result.resultType == "html"

    def test_execution_status_enum(self, mock_table_service):
        """Test execution status enum parsing"""
        repo = ExecutionRepository()

        mock_table_service.query_entities.return_value = iter([{
            "PartitionKey": "org-123",
            "RowKey": "execution:9999999999999_exec-123",
            "ExecutionId": "exec-123",
            "WorkflowName": "Workflow",
            "Status": ExecutionStatus.PENDING.value,
            "InputData": "{}",
            "Result": None,
            "StartedAt": "2024-01-15T10:30:00",
            "CompletedAt": None
        }])

        result = repo.get_execution("exec-123", "org-123")

        assert result is not None
        assert result.status == ExecutionStatus.PENDING
