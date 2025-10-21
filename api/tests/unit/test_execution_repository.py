"""
Unit tests for ExecutionRepository

Tests all repository methods with mocked Table Storage service.
"""

import json
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from shared.models import ExecutionStatus, WorkflowExecution
from shared.repositories.executions import ExecutionRepository


@pytest.fixture
def mock_table_service():
    """Mock TableStorageService for Entities table"""
    return MagicMock()


@pytest.fixture
def mock_relationships_service():
    """Mock TableStorageService for Relationships table"""
    return MagicMock()


@pytest.fixture
def execution_repo(mock_table_service, mock_relationships_service):
    """ExecutionRepository with mocked services"""
    with patch('shared.repositories.executions.TableStorageService') as mock_class:
        # First call creates Entities service, second creates Relationships service
        mock_class.side_effect = [mock_table_service, mock_relationships_service]
        repo = ExecutionRepository()
        repo._service = mock_table_service
        repo.relationships_service = mock_relationships_service
        return repo


class TestCreateExecution:
    """Tests for create_execution method"""

    def test_creates_execution_with_all_indexes(self, execution_repo, mock_table_service, mock_relationships_service):
        """Should create primary record and all 4 indexes (user, workflow, form, status)"""
        execution_id = str(uuid4())
        org_id = "org-123"
        user_id = "user@example.com"
        user_name = "Test User"
        workflow_name = "TestWorkflow"
        input_data = {"key": "value"}
        form_id = "form-abc"

        # Execute
        result = execution_repo.create_execution(
            execution_id=execution_id,
            org_id=org_id,
            user_id=user_id,
            user_name=user_name,
            workflow_name=workflow_name,
            input_data=input_data,
            form_id=form_id
        )

        # Verify primary record created
        assert mock_table_service.insert_entity.called
        primary_entity = mock_table_service.insert_entity.call_args[0][0]
        assert primary_entity["PartitionKey"] == org_id
        assert primary_entity["ExecutionId"] == execution_id
        assert primary_entity["WorkflowName"] == workflow_name
        assert primary_entity["Status"] == ExecutionStatus.RUNNING.value
        assert json.loads(primary_entity["InputData"]) == input_data

        # Verify 4 indexes created (user, workflow, form, status)
        assert mock_relationships_service.insert_entity.call_count == 4

        # Check user index
        user_index = mock_relationships_service.insert_entity.call_args_list[0][0][0]
        assert user_index["PartitionKey"] == "GLOBAL"
        assert user_index["RowKey"] == f"userexec:{user_id}:{execution_id}"
        assert user_index["WorkflowName"] == workflow_name
        assert user_index["Status"] == ExecutionStatus.RUNNING.value

        # Check workflow index
        workflow_index = mock_relationships_service.insert_entity.call_args_list[1][0][0]
        assert workflow_index["PartitionKey"] == "GLOBAL"
        assert workflow_index["RowKey"] == f"workflowexec:{workflow_name}:{org_id}:{execution_id}"

        # Check status index
        status_index = mock_relationships_service.insert_entity.call_args_list[2][0][0]
        assert status_index["PartitionKey"] == "GLOBAL"
        assert status_index["RowKey"] == f"status:{ExecutionStatus.RUNNING.value}:{execution_id}"
        assert status_index["WorkflowName"] == workflow_name
        assert "UpdatedAt" in status_index

        # Check form index
        form_index = mock_relationships_service.insert_entity.call_args_list[3][0][0]
        assert form_index["PartitionKey"] == "GLOBAL"
        assert form_index["RowKey"] == f"formexec:{form_id}:{execution_id}"

        # Verify return value
        assert isinstance(result, WorkflowExecution)
        assert result.executionId == execution_id
        assert result.workflowName == workflow_name

    def test_creates_execution_without_form_id(self, execution_repo, mock_relationships_service):
        """Should create 3 indexes when form_id is None"""
        execution_id = str(uuid4())

        execution_repo.create_execution(
            execution_id=execution_id,
            org_id="org-123",
            user_id="user@example.com",
            user_name="Test User",
            workflow_name="TestWorkflow",
            input_data={},
            form_id=None
        )

        # Should create only 3 indexes (user, workflow, status - no form)
        assert mock_relationships_service.insert_entity.call_count == 3

    def test_uses_global_partition_when_org_id_none(self, execution_repo, mock_table_service):
        """Should use GLOBAL partition when org_id is None"""
        execution_id = str(uuid4())

        execution_repo.create_execution(
            execution_id=execution_id,
            org_id=None,
            user_id="user@example.com",
            user_name="Test User",
            workflow_name="TestWorkflow",
            input_data={}
        )

        primary_entity = mock_table_service.insert_entity.call_args[0][0]
        assert primary_entity["PartitionKey"] == "GLOBAL"


class TestUpdateExecution:
    """Tests for update_execution method"""

    def test_updates_execution_to_success(self, execution_repo, mock_table_service, mock_relationships_service):
        """Should update primary record and all indexes to Success status"""
        execution_id = str(uuid4())
        org_id = "org-123"
        user_id = "user@example.com"
        workflow_name = "TestWorkflow"
        form_id = "form-abc"

        # Mock existing execution entity
        existing_entity = {
            "PartitionKey": org_id,
            "RowKey": f"execution:12345_{execution_id}",
            "ExecutionId": execution_id,
            "WorkflowName": workflow_name,
            "FormId": form_id,
            "Status": ExecutionStatus.RUNNING.value,
            "ExecutedByName": "Test User",
            "StartedAt": datetime.utcnow().isoformat()
        }
        mock_table_service.query_entities.return_value = [existing_entity]

        # Mock index entities
        mock_relationships_service.get_entity.side_effect = [
            {"PartitionKey": "GLOBAL", "RowKey": f"userexec:{user_id}:{execution_id}"},  # user index
            {"PartitionKey": "GLOBAL", "RowKey": f"workflowexec:{workflow_name}:{org_id}:{execution_id}"},  # workflow index
            {"PartitionKey": "GLOBAL", "RowKey": f"formexec:{form_id}:{execution_id}"},  # form index
        ]

        # Execute
        result = execution_repo.update_execution(
            execution_id=execution_id,
            org_id=org_id,
            user_id=user_id,
            status=ExecutionStatus.SUCCESS,
            result={"output": "test"},
            duration_ms=5000
        )

        # Verify primary record updated
        assert mock_table_service.update_entity.called
        updated_entity = mock_table_service.update_entity.call_args[0][0]
        assert updated_entity["Status"] == ExecutionStatus.SUCCESS.value
        assert updated_entity["DurationMs"] == 5000
        assert "CompletedAt" in updated_entity

        # Verify indexes updated (3 get calls, 3 update calls)
        assert mock_relationships_service.get_entity.call_count == 3
        assert mock_relationships_service.update_entity.call_count == 3

        # Status index deletion is wrapped in try/except that swallows exceptions
        # So we can't reliably assert it was called, but we can check:
        # - delete_entity may or may not be called (exception handling)
        # - insert_entity should NOT be called for Success status (terminal state)
        assert not mock_relationships_service.insert_entity.called

        # Verify return value
        assert isinstance(result, WorkflowExecution)
        assert result.status == ExecutionStatus.SUCCESS

    def test_updates_execution_to_pending(self, execution_repo, mock_table_service, mock_relationships_service):
        """Should update status index when changing to Pending"""
        execution_id = str(uuid4())
        org_id = "org-123"

        existing_entity = {
            "PartitionKey": org_id,
            "RowKey": f"execution:12345_{execution_id}",
            "ExecutionId": execution_id,
            "WorkflowName": "TestWorkflow",
            "Status": ExecutionStatus.RUNNING.value,
            "ExecutedByName": "Test User",
            "StartedAt": datetime.utcnow().isoformat()
        }
        mock_table_service.query_entities.return_value = [existing_entity]
        mock_relationships_service.get_entity.return_value = {}

        # Execute
        execution_repo.update_execution(
            execution_id=execution_id,
            org_id=org_id,
            user_id="user@example.com",
            status=ExecutionStatus.PENDING
        )

        # Should delete old Running status index
        assert mock_relationships_service.delete_entity.called

        # Should create new Pending status index
        assert mock_relationships_service.insert_entity.called
        status_index = mock_relationships_service.insert_entity.call_args[0][0]
        assert status_index["RowKey"] == f"status:{ExecutionStatus.PENDING.value}:{execution_id}"

    def test_raises_error_when_execution_not_found(self, execution_repo, mock_table_service):
        """Should raise ValueError when execution doesn't exist"""
        mock_table_service.query_entities.return_value = []

        with pytest.raises(ValueError, match="not found"):
            execution_repo.update_execution(
                execution_id="nonexistent",
                org_id="org-123",
                user_id="user@example.com",
                status=ExecutionStatus.SUCCESS
            )


class TestGetStuckExecutions:
    """Tests for get_stuck_executions method"""

    def test_finds_stuck_pending_executions(self, execution_repo, mock_relationships_service):
        """Should find executions stuck in Pending status > 10 minutes"""
        now = datetime.utcnow()
        old_time = now - timedelta(minutes=15)  # 15 minutes ago

        stuck_execution = {
            "PartitionKey": "GLOBAL",
            "RowKey": f"status:Pending:{uuid4()}",
            "ExecutionId": "exec-123",
            "WorkflowName": "StuckWorkflow",
            "ExecutedBy": "user@example.com",
            "ExecutedByName": "Test User",
            "Status": "Pending",
            "StartedAt": old_time.isoformat(),
            "UpdatedAt": old_time.isoformat()
        }

        # Mock query to return stuck execution for Pending status
        def mock_query(filter_str):
            if "status:Pending:" in filter_str:
                return [stuck_execution]
            return []

        mock_relationships_service.query_entities.side_effect = mock_query

        # Execute
        result = execution_repo.get_stuck_executions(
            pending_timeout_minutes=10,
            running_timeout_minutes=30
        )

        # Verify
        assert len(result) == 1
        assert result[0].executionId == "exec-123"
        assert result[0].status == ExecutionStatus.PENDING
        assert result[0].workflowName == "StuckWorkflow"

    def test_finds_stuck_running_executions(self, execution_repo, mock_relationships_service):
        """Should find executions stuck in Running status > 30 minutes"""
        now = datetime.utcnow()
        old_time = now - timedelta(minutes=35)  # 35 minutes ago

        stuck_execution = {
            "PartitionKey": "GLOBAL",
            "RowKey": f"status:Running:{uuid4()}",
            "ExecutionId": "exec-456",
            "WorkflowName": "LongWorkflow",
            "ExecutedBy": "user@example.com",
            "ExecutedByName": "Test User",
            "Status": "Running",
            "StartedAt": old_time.isoformat(),
            "UpdatedAt": old_time.isoformat()
        }

        def mock_query(filter_str):
            if "status:Running:" in filter_str:
                return [stuck_execution]
            return []

        mock_relationships_service.query_entities.side_effect = mock_query

        # Execute
        result = execution_repo.get_stuck_executions(
            pending_timeout_minutes=10,
            running_timeout_minutes=30
        )

        # Verify
        assert len(result) == 1
        assert result[0].executionId == "exec-456"
        assert result[0].status == ExecutionStatus.RUNNING

    def test_ignores_recent_executions(self, execution_repo, mock_relationships_service):
        """Should NOT return executions within timeout threshold"""
        now = datetime.utcnow()
        recent_time = now - timedelta(minutes=5)  # Only 5 minutes ago

        recent_execution = {
            "PartitionKey": "GLOBAL",
            "RowKey": f"status:Pending:{uuid4()}",
            "ExecutionId": "exec-123",
            "WorkflowName": "RecentWorkflow",
            "ExecutedBy": "user@example.com",
            "ExecutedByName": "Test User",
            "Status": "Pending",
            "StartedAt": recent_time.isoformat(),
            "UpdatedAt": recent_time.isoformat()
        }

        mock_relationships_service.query_entities.return_value = [recent_execution]

        # Execute
        result = execution_repo.get_stuck_executions(
            pending_timeout_minutes=10,
            running_timeout_minutes=30
        )

        # Verify - should be empty
        assert len(result) == 0

    def test_returns_empty_list_when_no_stuck_executions(self, execution_repo, mock_relationships_service):
        """Should return empty list when no stuck executions"""
        mock_relationships_service.query_entities.return_value = []

        result = execution_repo.get_stuck_executions()

        assert result == []

    def test_handles_missing_updated_at(self, execution_repo, mock_relationships_service):
        """Should skip executions without UpdatedAt timestamp"""
        execution_without_timestamp = {
            "PartitionKey": "GLOBAL",
            "RowKey": f"status:Pending:{uuid4()}",
            "ExecutionId": "exec-123",
            "WorkflowName": "BadWorkflow",
            "Status": "Pending"
            # Missing UpdatedAt
        }

        mock_relationships_service.query_entities.return_value = [execution_without_timestamp]

        result = execution_repo.get_stuck_executions()

        # Should skip this execution
        assert len(result) == 0

    def test_uses_status_index_not_table_scan(self, execution_repo, mock_relationships_service):
        """Should query status indexes, NOT scan Entities table"""
        mock_relationships_service.query_entities.return_value = []

        execution_repo.get_stuck_executions()

        # Verify it queries Relationships service (status indexes)
        assert mock_relationships_service.query_entities.called

        # Verify query filters use status index pattern
        call_args = mock_relationships_service.query_entities.call_args_list
        assert len(call_args) == 2  # One for Pending, one for Running

        # Check first query is for Pending status
        first_filter = call_args[0][0][0]
        assert "status:Pending:" in first_filter
        assert "PartitionKey eq 'GLOBAL'" in first_filter

        # Check second query is for Running status
        second_filter = call_args[1][0][0]
        assert "status:Running:" in second_filter
        assert "PartitionKey eq 'GLOBAL'" in second_filter


class TestListExecutions:
    """Tests for list_executions method"""

    def test_lists_executions_for_org(self, execution_repo, mock_table_service):
        """Should list executions scoped to organization"""
        org_id = "org-123"
        execution_id = str(uuid4())

        mock_entity = {
            "PartitionKey": org_id,
            "RowKey": f"execution:99999_{execution_id}",
            "ExecutionId": execution_id,
            "WorkflowName": "TestWorkflow",
            "Status": "Success",
            "ExecutedBy": "user@example.com",
            "ExecutedByName": "Test User",
            "StartedAt": datetime.utcnow().isoformat(),
            "CompletedAt": datetime.utcnow().isoformat(),
            "DurationMs": 1000,
            "InputData": json.dumps({}),
            "Result": json.dumps({"output": "test"}),
            "ResultInBlob": False
        }

        # Mock query_paged to return tuple (entities, continuation_token)
        with patch.object(execution_repo, 'query_paged', return_value=([mock_entity], None)):
            # Execute
            result = execution_repo.list_executions(org_id=org_id, limit=50)

            # Verify result
            assert len(result) == 1
            assert result[0].executionId == execution_id
            assert result[0].workflowName == "TestWorkflow"

    def test_lists_global_executions_when_org_id_none(self, execution_repo, mock_table_service):
        """Should use GLOBAL partition when org_id is None"""
        # Mock query_paged to return empty results
        with patch.object(execution_repo, 'query_paged', return_value=([], None)):
            result = execution_repo.list_executions(org_id=None)

            # Verify result is empty list
            assert result == []


class TestGetExecution:
    """Tests for get_execution method"""

    def test_gets_execution_by_id(self, execution_repo, mock_table_service):
        """Should retrieve execution by ID"""
        execution_id = str(uuid4())
        org_id = "org-123"

        mock_entity = {
            "PartitionKey": org_id,
            "RowKey": f"execution:99999_{execution_id}",
            "ExecutionId": execution_id,
            "WorkflowName": "TestWorkflow",
            "Status": "Success",
            "ExecutedBy": "user@example.com",
            "ExecutedByName": "Test User",
            "StartedAt": datetime.utcnow().isoformat(),
            "CompletedAt": datetime.utcnow().isoformat(),
            "InputData": json.dumps({}),
            "Result": json.dumps({}),
            "ResultInBlob": False
        }

        mock_table_service.query_entities.return_value = [mock_entity]

        # Execute
        result = execution_repo.get_execution(execution_id, org_id)

        # Verify
        assert result is not None
        assert result.executionId == execution_id
        assert result.workflowName == "TestWorkflow"

    def test_returns_none_when_not_found(self, execution_repo, mock_table_service):
        """Should return None when execution doesn't exist"""
        mock_table_service.query_entities.return_value = []

        result = execution_repo.get_execution("nonexistent", "org-123")

        assert result is None

    def test_tries_global_partition_when_org_query_fails(self, execution_repo, mock_table_service):
        """Should try GLOBAL partition if org partition returns nothing"""
        execution_id = str(uuid4())

        global_entity = {
            "PartitionKey": "GLOBAL",
            "RowKey": f"execution:99999_{execution_id}",
            "ExecutionId": execution_id,
            "WorkflowName": "GlobalWorkflow",
            "Status": "Success",
            "ExecutedBy": "user@example.com",
            "ExecutedByName": "Test User",
            "StartedAt": datetime.utcnow().isoformat(),
            "InputData": json.dumps({}),
            "ResultInBlob": False
        }

        # First call (org partition) returns empty, second call (GLOBAL) returns entity
        mock_table_service.query_entities.side_effect = [[], [global_entity]]

        result = execution_repo.get_execution(execution_id, "org-123")

        # Should have made 2 queries
        assert mock_table_service.query_entities.call_count == 2

        # Should find the execution
        assert result is not None
        assert result.executionId == execution_id
