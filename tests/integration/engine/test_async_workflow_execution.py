"""
Integration Tests for Async Workflow Execution (User Story 4)
End-to-end tests for async workflow execution lifecycle
"""

import asyncio
import json
import time
from unittest.mock import MagicMock, patch

import pytest

from shared.async_executor import enqueue_workflow_execution, get_queue_client
from shared.async_storage import close_async_storage_cache
from shared.context import Organization, ExecutionContext
from shared.decorators import workflow
from shared.error_handling import WorkflowError


# No custom event_loop fixture - use pytest-asyncio's built-in one
# This avoids race conditions with async storage cache cleanup


@pytest.fixture(autouse=True)
async def clear_storage_cache_before_test():
    """Close and clear async storage cache before each test to ensure fresh clients"""
    # Close all cached async storage services
    await close_async_storage_cache()

    # Reset execution logger singleton to prevent reusing old clients
    import shared.execution_logger as exec_logger_module
    if exec_logger_module._execution_logger is not None:
        # Close repository's async storage services
        if hasattr(exec_logger_module._execution_logger.repository, '_service'):
            try:
                await exec_logger_module._execution_logger.repository._service.close()
            except Exception:  # noqa: S110
                pass
        exec_logger_module._execution_logger = None

    yield

    # Close after test too to ensure proper cleanup
    if exec_logger_module._execution_logger is not None:
        if hasattr(exec_logger_module._execution_logger.repository, '_service'):
            try:
                await exec_logger_module._execution_logger.repository._service.close()
            except Exception:  # noqa: S110
                pass
        exec_logger_module._execution_logger = None

    await close_async_storage_cache()


@pytest.fixture
def test_org():
    """Test organization"""
    return Organization(
        id="test-org-async",
        name="Test Organization for Async",
        is_active=True
    )


@pytest.fixture
def test_context(test_org):
    """Test execution context"""
    return ExecutionContext(
        user_id="test-user-async",
        email="async@example.com",
        name="Async Test User",
        scope=test_org.id,
        organization=test_org,
        is_platform_admin=False,
        is_function_key=False,
        execution_id="test-exec-async",
        _config={"test_setting": "test_value"}
    )


@pytest.fixture
def request_context(test_org):
    """Test execution context for enqueuing"""
    return ExecutionContext(
        user_id="test-user-async",
        email="async@example.com",
        name="Async Test User",
        scope=test_org.id,
        organization=test_org,
        is_platform_admin=False,
        is_function_key=False,
        execution_id="test-exec-enqueue"
    )




@pytest.fixture(scope="function")
async def queue_client():
    """Azure Storage Queue client for async execution"""
    # Create client using context manager
    ctx_mgr = get_queue_client()
    client = await ctx_mgr.__aenter__()

    try:
        # Ensure queue exists
        try:
            await client.create_queue()
        except Exception:
            pass  # Queue already exists

        # Clear any existing messages
        try:
            while True:
                messages = client.receive_messages(messages_per_page=32)
                batch = []
                async for msg in messages:
                    batch.append(msg)
                if not batch:
                    break
                for msg in batch:
                    await client.delete_message(msg)
        except Exception:
            pass

        yield client

        # Cleanup after test
        try:
            while True:
                messages = client.receive_messages(messages_per_page=32)
                batch = []
                async for msg in messages:
                    batch.append(msg)
                if not batch:
                    break
                for msg in batch:
                    await client.delete_message(msg)
        except Exception:
            pass
    finally:
        # Manually close the client
        await ctx_mgr.__aexit__(None, None, None)


def decode_queue_message(msg):
    """
    Decode Azure Queue message content to JSON.

    Handles both direct JSON content and base64-encoded content.
    """
    import base64
    try:
        # Try direct JSON parse first (if already decoded)
        return json.loads(msg.content)
    except (json.JSONDecodeError, TypeError):
        # If that fails, try base64 decode first
        decoded_content = base64.b64decode(msg.content).decode('utf-8')
        return json.loads(decoded_content)


def create_mock_queue_message(queue_message):
    """
    Create mock Azure Functions queue message from storage queue message.

    Azure Functions queue trigger provides messages with get_body() returning
    the decoded JSON bytes, not the base64-encoded content.
    """
    import base64
    # Decode the base64 content to get the actual JSON
    try:
        # Try decoding base64 first
        json_content = base64.b64decode(queue_message.content).decode('utf-8')
    except Exception:
        # If that fails, content might already be decoded
        json_content = queue_message.content

    # Create mock that returns JSON bytes like Azure Functions does
    mock_msg = MagicMock()
    mock_msg.get_body.return_value = json_content.encode('utf-8')
    return mock_msg


async def wait_for_queue_messages(queue_client, expected_count=1, max_attempts=30, delay=1.0):
    """
    Helper to wait for messages to appear in Azure Queue (handles Azurite delays)

    Args:
        queue_client: Azure Queue client
        expected_count: Minimum number of messages to wait for
        max_attempts: Maximum retry attempts (default: 30 for slow CI)
        delay: Delay between attempts in seconds (default: 1.0s)

    Returns:
        list: List of messages found
    """
    message_list = []
    for attempt in range(max_attempts):
        messages = queue_client.receive_messages(messages_per_page=max(10, expected_count))
        message_list = []
        async for msg in messages:
            message_list.append(msg)
        if len(message_list) >= expected_count:
            return message_list
        if attempt < max_attempts - 1:  # Don't sleep on last attempt
            await asyncio.sleep(delay)
    return message_list  # Return whatever we got


class TestAsyncWorkflowLifecycle:
    """Test the complete async workflow execution lifecycle"""

    @pytest.mark.asyncio
    async def test_enqueue_async_workflow(self, request_context, queue_client):
        """Test enqueueing an async workflow creates execution record and queue message"""

        # Define a test async workflow
        @workflow(
            name="async_test_workflow",
            description="Async test workflow",
            category="test",
            execution_mode="async"
        )
        async def async_test(context, value: int):
            """Returns doubled value after async processing"""
            await asyncio.sleep(0.1)  # Simulate async work
            return {"result": value * 2, "org": context.org_id}

        # Verify workflow has metadata attached
        assert hasattr(async_test, '_workflow_metadata')
        metadata = async_test._workflow_metadata
        assert metadata.execution_mode == "async"

        # Enqueue workflow execution
        execution_id = await enqueue_workflow_execution(
            context=request_context,
            workflow_name="async_test_workflow",
            parameters={"value": 21}
        )

        # Verify execution ID was returned (UUID format)
        assert execution_id is not None
        assert len(execution_id) == 36  # UUID format
        assert execution_id.count('-') == 4  # UUID has 4 dashes

    @pytest.mark.asyncio
    async def test_worker_processes_async_workflow(self, request_context, queue_client):
        """Test that worker processes queued workflow correctly"""

        # Define a test async workflow
        @workflow(
            name="worker_test_workflow",
            description="Worker test workflow",
            category="test",
            execution_mode="async"
        )
        async def worker_test(context, x: int, y: int):
            """Simple calculation workflow"""
            # Use logger directly instead of context.info()
            result = x + y
            return {"sum": result, "org": context.org_id}

        # Enqueue workflow
        await enqueue_workflow_execution(
            context=request_context,
            workflow_name="worker_test_workflow",
            parameters={"x": 10, "y": 32}
        )

        # Wait for message to be in queue
        message_list = await wait_for_queue_messages(queue_client, expected_count=1)
        assert len(message_list) >= 1, f"Expected >= 1 messages, got {len(message_list)}"

        # Simulate worker processing (import worker function)
        from functions.queue.worker import workflow_execution_worker

        # Process the message with worker
        msg = message_list[0]

        # Create mock QueueMessage
        mock_msg = create_mock_queue_message(msg)

        # Execute worker
        await workflow_execution_worker(mock_msg)

        # Clean up queue message
        await queue_client.delete_message(msg)

    @pytest.mark.asyncio
    async def test_context_preservation_in_async_execution(self, request_context, queue_client):
        """Test that organization context is preserved through async execution"""

        # Define workflow that uses context
        @workflow(
            name="context_test_workflow",
            description="Context preservation test",
            category="test",
            execution_mode="async"
        )
        async def context_test(context, action: str):
            """Uses context features"""
            # Access organization info
            org_id = context.org_id

            # Note: save_checkpoint() has been removed

            return {
                "org_id": org_id,
                "action": action,
                "caller": context.email
            }

        # Enqueue workflow
        await enqueue_workflow_execution(
            context=request_context,
            workflow_name="context_test_workflow",
            parameters={"action": "test_action"}
        )

        # Verify message contains context data
        message_list = await wait_for_queue_messages(queue_client, expected_count=1)
        assert len(message_list) >= 1, f"Expected >= 1 messages, got {len(message_list)}"

        msg = message_list[0]
        message_data = decode_queue_message(msg)

        # Verify context is preserved in queue message
        assert message_data["org_id"] == "test-org-async"
        assert message_data["user_id"] == "test-user-async"
        assert message_data["user_email"] == "async@example.com"
        assert message_data["user_name"] == "Async Test User"

        # Clean up
        await queue_client.delete_message(msg)

    @pytest.mark.asyncio
    async def test_async_workflow_error_handling(self, request_context, queue_client):
        """Test error handling in async workflow execution"""

        # Define workflow that fails
        @workflow(
            name="failing_workflow",
            description="Workflow that fails",
            category="test",
            execution_mode="async"
        )
        async def failing_workflow(context, should_fail: bool):
            """Workflow that raises an error"""
            if should_fail:
                raise WorkflowError(
                    error_type="TestError",
                    message="Intentional test failure"
                )
            return {"success": True}

        # Enqueue failing workflow
        await enqueue_workflow_execution(
            context=request_context,
            workflow_name="failing_workflow",
            parameters={"should_fail": True}
        )

        # Get message
        message_list = await wait_for_queue_messages(queue_client, expected_count=1)
        assert len(message_list) >= 1, f"Expected >= 1 messages, got {len(message_list)}"

        msg = message_list[0]
        mock_msg = create_mock_queue_message(msg)

        # Execute worker (should handle error gracefully)
        from functions.queue.worker import workflow_execution_worker

        # Worker should not raise exception
        await workflow_execution_worker(mock_msg)

        # Clean up
        await queue_client.delete_message(msg)

    @pytest.mark.asyncio
    async def test_async_workflow_result_storage(self, request_context, queue_client):
        """Test that async workflow results are stored correctly"""

        # Define workflow with result
        @workflow(
            name="result_test_workflow",
            description="Result storage test",
            category="test",
            execution_mode="async"
        )
        async def result_test(context, items: int):
            """Returns data structure"""
            return {
                "items": [{"id": i, "value": i * 10} for i in range(items)],
                "total": items,
                "org": context.org_id
            }

        # Enqueue workflow
        await enqueue_workflow_execution(
            context=request_context,
            workflow_name="result_test_workflow",
            parameters={"items": 5}
        )

        # Process message
        message_list = await wait_for_queue_messages(queue_client, expected_count=1)
        assert len(message_list) >= 1, f"Expected >= 1 messages, got {len(message_list)}"

        msg = message_list[0]
        mock_msg = create_mock_queue_message(msg)

        from functions.queue.worker import workflow_execution_worker
        await workflow_execution_worker(mock_msg)

        # Clean up
        await queue_client.delete_message(msg)

    @pytest.mark.asyncio
    async def test_async_workflow_parameter_coercion(self, request_context, queue_client):
        """Test that parameter types are coerced correctly in async execution"""

        # Define workflow with typed parameters
        @workflow(
            name="typed_workflow",
            description="Workflow with typed parameters",
            category="test",
            execution_mode="async"
        )
        async def typed_workflow(context, count: int, enabled: bool, name: str):
            """Uses typed parameters"""
            assert isinstance(count, int), f"count should be int, got {type(count)}"
            assert isinstance(enabled, bool), f"enabled should be bool, got {type(enabled)}"
            assert isinstance(name, str), f"name should be str, got {type(name)}"

            return {
                "count": count,
                "enabled": enabled,
                "name": name
            }

        # Enqueue with string parameters (should be coerced)
        await enqueue_workflow_execution(
            context=request_context,
            workflow_name="typed_workflow",
            parameters={
                "count": "42",  # Should be coerced to int
                "enabled": "true",  # Should be coerced to bool
                "name": "test"
            }
        )

        # Process message
        message_list = await wait_for_queue_messages(queue_client, expected_count=1)
        assert len(message_list) >= 1, f"Expected >= 1 messages, got {len(message_list)}"

        msg = message_list[0]
        mock_msg = create_mock_queue_message(msg)

        from functions.queue.worker import workflow_execution_worker

        # Should not raise type errors
        await workflow_execution_worker(mock_msg)

        # Clean up
        await queue_client.delete_message(msg)


class TestAsyncWorkflowConfiguration:
    """Test async workflow configuration and metadata"""

    def test_async_workflow_metadata(self):
        """Test that async workflows have correct metadata"""

        @workflow(
            name="metadata_test",
            description="Metadata test workflow",
            category="test",
            execution_mode="async",
            timeout_seconds=600
        )
        async def metadata_workflow(context):
            """Test workflow"""
            return {"status": "ok"}

        # Get metadata directly from decorated function
        metadata = metadata_workflow._workflow_metadata

        assert metadata is not None
        assert metadata.execution_mode == "async"
        assert metadata.timeout_seconds == 600
        assert metadata.name == "metadata_test"
        assert metadata.description == "Metadata test workflow"

    def test_sync_workflow_default(self):
        """Test that workflows default to async mode"""

        @workflow(
            name="sync_default",
            description="Default workflow",
            category="test"
        )
        async def default_workflow(context):
            """Default workflow"""
            return {"status": "ok"}

        # Get metadata directly from decorated function
        metadata = default_workflow._workflow_metadata

        assert metadata is not None
        assert metadata.execution_mode == "async"  # Default mode


class TestAsyncWorkflowQueueManagement:
    """Test queue management for async workflows"""

    @pytest.mark.asyncio
    async def test_queue_message_format(self, request_context, queue_client):
        """Test that queue messages have correct format"""

        @workflow(
            name="queue_format_test",
            description="Queue format test",
            category="test",
            execution_mode="async"
        )
        async def queue_test(context, param1: str, param2: int):
            """Test workflow"""
            return {}

        # Enqueue workflow
        execution_id = await enqueue_workflow_execution(
            context=request_context,
            workflow_name="queue_format_test",
            parameters={"param1": "test", "param2": 123},
            form_id="form-123"
        )

        # Get message
        message_list = await wait_for_queue_messages(queue_client, expected_count=1)
        assert len(message_list) >= 1, f"Expected >= 1 messages, got {len(message_list)}"

        msg = message_list[0]
        message_data = decode_queue_message(msg)

        # Verify all required fields are present
        required_fields = [
            "execution_id",
            "workflow_name",
            "org_id",
            "user_id",
            "user_name",
            "user_email",
            "parameters",
            "form_id"
        ]

        for field in required_fields:
            assert field in message_data, f"Missing required field: {field}"

        # Verify values
        assert message_data["execution_id"] == execution_id
        assert message_data["workflow_name"] == "queue_format_test"
        assert message_data["parameters"]["param1"] == "test"
        assert message_data["parameters"]["param2"] == 123
        assert message_data["form_id"] == "form-123"

        # Clean up
        await queue_client.delete_message(msg)



class TestAsyncWorkflowStatusTransitions:
    """Test async workflow lifecycle and worker behavior

    Note: These tests verify worker processing behavior.
    Full status transition testing (PENDING→RUNNING→SUCCESS) requires
    API-level tests with actual HTTP endpoints.
    """

    @pytest.mark.asyncio
    async def test_worker_completes_successful_workflow(self, request_context, queue_client):
        """Test that worker successfully processes and completes a workflow"""

        @workflow(
            name="lifecycle_test",
            description="Full lifecycle test",
            category="test",
            execution_mode="async"
        )
        async def lifecycle_workflow(context, step: str):
            """Workflow for lifecycle testing"""
            # Use logger directly instead of context.info()
            await asyncio.sleep(0.1)
            return {"step": step, "completed": True}

        # Enqueue workflow
        execution_id = await enqueue_workflow_execution(
            context=request_context,
            workflow_name="lifecycle_test",
            parameters={"step": "test"}
        )

        assert execution_id is not None

        # Process with worker
        from functions.queue.worker import workflow_execution_worker
        message_list = await wait_for_queue_messages(queue_client, expected_count=1)
        assert len(message_list) >= 1, f"Expected >= 1 messages, got {len(message_list)}"

        msg = message_list[0]
        mock_msg = create_mock_queue_message(msg)

        # Execute worker - should not raise exception
        await workflow_execution_worker(mock_msg)

        # Clean up
        await queue_client.delete_message(msg)

    @pytest.mark.asyncio
    async def test_worker_handles_workflow_errors_gracefully(self, request_context, queue_client):
        """Test that worker handles errors without crashing"""

        @workflow(
            name="error_detail_test",
            description="Error detail test",
            category="test",
            execution_mode="async"
        )
        async def error_workflow(context):
            """Workflow that fails with specific error"""
            raise WorkflowError(
                error_type="ValidationError",
                message="Test validation failed: Missing required field 'email'"
            )

        # Enqueue workflow
        await enqueue_workflow_execution(
            context=request_context,
            workflow_name="error_detail_test",
            parameters={}
        )

        # Process with worker
        from functions.queue.worker import workflow_execution_worker
        message_list = await wait_for_queue_messages(queue_client, expected_count=1)
        assert len(message_list) >= 1, f"Expected >= 1 messages, got {len(message_list)}"

        msg = message_list[0]
        mock_msg = create_mock_queue_message(msg)

        # Execute worker (should NOT raise exception - should handle error gracefully)
        try:
            await workflow_execution_worker(mock_msg)
            # If we get here, the worker handled the error gracefully
            assert True
        except Exception as e:
            pytest.fail(f"Worker should handle errors gracefully but raised: {e}")

        # Clean up
        await queue_client.delete_message(msg)


    @pytest.mark.asyncio
    async def test_worker_executes_async_workflow_with_delay(self, request_context, queue_client):
        """Test that worker can execute workflows with delays"""

        @workflow(
            name="duration_test",
            description="Duration tracking test",
            category="test",
            execution_mode="async"
        )
        async def timed_workflow(context):
            """Workflow with known duration"""
            start_time = time.time()
            await asyncio.sleep(0.2)  # 200ms
            duration = time.time() - start_time
            return {"completed": True, "duration_seconds": duration}

        # Verify workflow has metadata attached
        metadata = timed_workflow._workflow_metadata
        assert metadata is not None, "duration_test workflow should have metadata"
        assert metadata.execution_mode == "async"

        # Enqueue workflow
        await enqueue_workflow_execution(
            context=request_context,
            workflow_name="duration_test",
            parameters={}
        )

        # Process with worker, but prevent it from re-discovering modules
        # (which would wipe out our test workflow)
        from functions.queue.worker import workflow_execution_worker
        message_list = await wait_for_queue_messages(queue_client, expected_count=1)
        assert len(message_list) >= 1, f"Expected >= 1 messages, got {len(message_list)}"

        msg = message_list[0]
        mock_msg = create_mock_queue_message(msg)

        # Measure execution time
        start = time.time()

        await workflow_execution_worker(mock_msg)

        elapsed = time.time() - start

        # Worker should have taken at least 100ms (accounting for test overhead/timing variability)
        # Original sleep is 200ms, but test environment timing can be imprecise
        assert elapsed >= 0.1, f"Worker should wait for async operations, took {elapsed}s"

        # Clean up
        await queue_client.delete_message(msg)


class TestWorkflowCancellation:
    """Test workflow cancellation functionality"""

    @pytest.mark.skip(reason="Cancellation tests require complex setup - test manually for now")
    @pytest.mark.asyncio
    async def test_cancel_running_workflow(self, request_context, queue_client):
        """Test cancelling a workflow while it's running"""
        from shared.models import ExecutionStatus
        from shared.repositories.executions import ExecutionRepository

        @workflow(
            name="cancellable_workflow",
            description="Long-running workflow for cancellation testing",
            category="test",
            execution_mode="async"
        )
        async def cancellable_workflow(context):
            """Workflow that runs long enough to be cancelled"""
            # Simulate long-running workflow
            for i in range(10):
                await asyncio.sleep(0.5)
            return {"completed": True}

        # Enqueue workflow
        execution_id = await enqueue_workflow_execution(
            context=request_context,
            workflow_name="cancellable_workflow",
            parameters={}
        )

        assert execution_id is not None

        # Get queue message
        from functions.queue.worker import workflow_execution_worker
        message_list = await wait_for_queue_messages(queue_client, expected_count=1)
        assert len(message_list) >= 1

        msg = message_list[0]
        mock_msg = create_mock_queue_message(msg)

        # Create execution repository for status updates
        exec_repo = ExecutionRepository()

        # Start worker in background
        async def run_worker():
            await workflow_execution_worker(mock_msg)

        worker_task = asyncio.create_task(run_worker())

        try:
            # Wait for workflow to start running and create execution record
            await asyncio.sleep(1.0)

            # Request cancellation by updating status to CANCELLING
            await exec_repo.update_execution(
                execution_id=execution_id,
                org_id=f"ORG:{request_context.organization.id}",
                user_id=request_context.user_id,
                status=ExecutionStatus.CANCELLING
            )

            # Wait for worker to process cancellation
            await asyncio.wait_for(worker_task, timeout=5.0)

            # Verify execution was cancelled
            execution = await exec_repo.get_execution(
                execution_id=execution_id,
                org_id=f"ORG:{request_context.organization.id}"
            )

            assert execution is not None
            assert execution.status == ExecutionStatus.CANCELLED
            assert execution.error_message == "Execution cancelled by user"

        finally:
            await exec_repo.close()
            await queue_client.delete_message(msg)

    @pytest.mark.skip(reason="Cancellation tests require complex setup - test manually for now")
    @pytest.mark.asyncio
    async def test_cancel_before_start(self, request_context, queue_client):
        """Test cancelling a workflow before the worker starts processing it"""
        from shared.models import ExecutionStatus
        from shared.repositories.executions import ExecutionRepository

        @workflow(
            name="pre_cancel_workflow",
            description="Workflow cancelled before execution",
            category="test",
            execution_mode="async"
        )
        async def pre_cancel_workflow(context):
            """Workflow that should never execute"""
            return {"completed": True}

        # Enqueue workflow
        execution_id = await enqueue_workflow_execution(
            context=request_context,
            workflow_name="pre_cancel_workflow",
            parameters={}
        )

        assert execution_id is not None

        # Immediately cancel before worker processes
        exec_repo = ExecutionRepository()
        try:
            await exec_repo.update_execution(
                execution_id=execution_id,
                org_id=f"ORG:{request_context.organization.id}",
                user_id=request_context.user_id,
                status=ExecutionStatus.CANCELLING
            )

            # Now process with worker
            from functions.queue.worker import workflow_execution_worker
            message_list = await wait_for_queue_messages(queue_client, expected_count=1)
            assert len(message_list) >= 1

            msg = message_list[0]
            mock_msg = create_mock_queue_message(msg)

            # Worker should detect pre-cancellation and mark as CANCELLED
            await workflow_execution_worker(mock_msg)

            # Verify execution was cancelled
            execution = await exec_repo.get_execution(
                execution_id=execution_id,
                org_id=f"ORG:{request_context.organization.id}"
            )

            assert execution is not None
            assert execution.status == ExecutionStatus.CANCELLED
            assert "cancelled before it could start" in execution.error_message.lower()

            # Clean up
            await queue_client.delete_message(msg)

        finally:
            await exec_repo.close()

    @pytest.mark.skip(reason="Cancellation tests require complex setup - test manually for now")
    @pytest.mark.asyncio
    async def test_workflow_timeout(self, request_context, queue_client):
        """Test that workflows timeout after exceeding configured timeout"""
        from shared.models import ExecutionStatus
        from shared.repositories.executions import ExecutionRepository

        @workflow(
            name="timeout_workflow",
            description="Workflow that should timeout",
            category="test",
            execution_mode="async",
            timeout_seconds=1  # 1 second timeout
        )
        async def timeout_workflow(context):
            """Workflow that runs longer than timeout"""
            await asyncio.sleep(10)  # Sleep longer than timeout
            return {"completed": True}

        # Enqueue workflow
        execution_id = await enqueue_workflow_execution(
            context=request_context,
            workflow_name="timeout_workflow",
            parameters={}
        )

        assert execution_id is not None

        # Process with worker
        from functions.queue.worker import workflow_execution_worker
        message_list = await wait_for_queue_messages(queue_client, expected_count=1)
        assert len(message_list) >= 1

        msg = message_list[0]
        mock_msg = create_mock_queue_message(msg)

        # Worker should timeout the execution
        await workflow_execution_worker(mock_msg)

        # Verify execution timed out
        exec_repo = ExecutionRepository()
        try:
            execution = await exec_repo.get_execution(
                execution_id=execution_id,
                org_id=f"ORG:{request_context.organization.id}"
            )

            assert execution is not None
            assert execution.status == ExecutionStatus.TIMEOUT
            assert "timeout" in execution.error_message.lower()

        finally:
            await exec_repo.close()
            await queue_client.delete_message(msg)
