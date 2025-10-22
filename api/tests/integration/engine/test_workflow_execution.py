"""
Integration Tests for Workflow Execution
End-to-end tests for the workflow execution endpoint
"""

from unittest.mock import MagicMock, patch

import pytest

from shared.context import Caller, Organization, OrganizationContext
from shared.models import ExecutionStatus
from shared.registry import WorkflowRegistry


@pytest.fixture
def mock_org():
    """Mock organization for testing"""
    return Organization(
        org_id="test-org-123",
        name="Test Organization",
        is_active=True
    )


@pytest.fixture
def mock_caller():
    """Mock caller for testing"""
    return Caller(
        user_id="test-user-789",
        email="test@example.com",
        name="Test User"
    )


@pytest.fixture
def mock_context(mock_org, mock_caller):
    """Mock organization context"""
    return OrganizationContext(
        org=mock_org,
        config={
            "default_license": "O365_E3",
            "welcome_email_template": "welcome_v1"
        },
        caller=mock_caller,
        execution_id="test-exec-123"
    )


@pytest.fixture
def registry():
    """Fresh workflow registry for each test, restored afterward"""
    # Save current registry state
    old_instance = WorkflowRegistry._instance

    # Create fresh registry for test
    WorkflowRegistry._instance = None
    fresh = WorkflowRegistry()

    yield fresh

    # Restore old registry after test
    WorkflowRegistry._instance = old_instance


@pytest.fixture
def mock_table_storage():
    """Mock table storage service"""
    with patch('shared.storage.TableStorageService') as mock:
        instance = MagicMock()
        mock.return_value = instance
        yield instance


class TestWorkflowExecutionEndpoint:
    """Test the POST /workflows/{workflowName} endpoint components"""

    @pytest.mark.asyncio
    async def test_workflow_execution_flow(self, registry, mock_context):
        """Test complete workflow execution flow"""

        from shared.decorators import workflow

        # Register a simple test workflow
        @workflow(
            name="simple_test_workflow",
            description="Simple test workflow",
            category="test"
        )
        async def simple_workflow(context, value: int):
            """Returns doubled value"""
            return {"result": value * 2, "org": context.org_id}

        # Verify workflow was registered
        metadata = registry.get_workflow("simple_test_workflow")
        assert metadata is not None

        # Get and execute the workflow function
        result = await metadata.function(mock_context, value=21)

        assert result["result"] == 42
        assert result["org"] == "test-org-123"

    @pytest.mark.asyncio
    async def test_workflow_with_validation_error(self, registry, mock_context):
        """Test workflow that raises ValidationError"""

        from shared.decorators import workflow
        from shared.error_handling import ValidationError

        @workflow(
            name="validation_workflow",
            description="Workflow with validation",
            category="test"
        )
        async def validate_email(context, email: str):
            """Validates email format"""
            if '@' not in email:
                raise ValidationError("Invalid email format", field="email")
            return {"valid": True}

        # Test valid email
        metadata = registry.get_workflow("validation_workflow")
        result = await metadata.function(mock_context, email="test@example.com")
        assert result["valid"] is True

        # Test invalid email
        with pytest.raises(ValidationError) as exc_info:
            await metadata.function(mock_context, email="invalid")

        assert exc_info.value.error_type == "ValidationError"
        assert exc_info.value.details["field"] == "email"

    @pytest.mark.asyncio
    async def test_workflow_with_state_tracking(self, registry, mock_context):
        """Test that state tracking works correctly"""

        from shared.decorators import workflow

        @workflow(
            name="state_test_workflow",
            description="Workflow with state tracking",
            category="test"
        )
        async def track_state(context, step: str):
            """Uses state tracking features"""
            context.save_checkpoint("start", {"step": step})
            context.info("Processing", {"current_step": step})
            context.set_variable("last_step", step)
            return {"completed": True}

        # Execute workflow
        metadata = registry.get_workflow("state_test_workflow")
        result = await metadata.function(mock_context, step="validation")

        assert result["completed"] is True

        # Verify state was tracked
        assert len(mock_context._state_snapshots) == 1
        assert mock_context._state_snapshots[0]["name"] == "start"
        assert len(mock_context._logs) == 1
        assert mock_context._logs[0]["message"] == "Processing"
        assert mock_context.get_variable("last_step") == "validation"


class TestExecutionLogger:
    """Test the ExecutionLogger directly"""

    @pytest.mark.asyncio
    async def test_create_execution_dual_indexing(self, mock_table_storage):
        """Test that create_execution uses ExecutionRepository"""
        from shared.execution_logger import ExecutionLogger

        # Mock ExecutionRepository
        mock_exec_repo = MagicMock()

        with patch('shared.execution_logger.ExecutionRepository') as mock_repo_class:
            with patch('shared.execution_logger.get_blob_service') as mock_blob:
                mock_repo_class.return_value = mock_exec_repo
                mock_blob.return_value = MagicMock()

                logger = ExecutionLogger()

                logger.create_execution(
                    execution_id="test-exec-123",
                    org_id="org-456",
                    user_id="user-789",
                    user_name="Test User",
                    workflow_name="test_workflow",
                    input_data={"key": "value"},
                    form_id="form-abc"
                )

                # Verify repository was called
                mock_exec_repo.create_execution.assert_called_once()

                # Get the call args to verify execution parameters
                call_args = mock_exec_repo.create_execution.call_args
                assert call_args[1]['execution_id'] == 'test-exec-123'
                assert call_args[1]['org_id'] == 'org-456'
                assert call_args[1]['user_id'] == 'user-789'
                assert call_args[1]['workflow_name'] == 'test_workflow'
                assert call_args[1]['form_id'] == 'form-abc'

    @pytest.mark.asyncio
    async def test_update_execution_with_result(self):
        """Test updating execution with success result"""
        from shared.execution_logger import ExecutionLogger

        # Mock ExecutionRepository
        mock_exec_repo = MagicMock()

        with patch('shared.execution_logger.ExecutionRepository') as mock_repo_class:
            with patch('shared.execution_logger.get_blob_service') as mock_blob:
                mock_repo_class.return_value = mock_exec_repo
                mock_blob.return_value = MagicMock()

                logger = ExecutionLogger()

                logger.update_execution(
                    execution_id="test-exec-123",
                    org_id="org-456",
                    user_id="user-789",
                    status=ExecutionStatus.SUCCESS,
                    result={"user_id": "new-user-123"},
                    duration_ms=1500
                )

                # Verify repository was called
                mock_exec_repo.update_execution.assert_called_once()

                # Get the call args to verify update parameters
                call_args = mock_exec_repo.update_execution.call_args
                assert call_args[1]['execution_id'] == 'test-exec-123'
                assert call_args[1]['org_id'] == 'org-456'
                assert call_args[1]['status'] == ExecutionStatus.SUCCESS
                assert call_args[1]['duration_ms'] == 1500
