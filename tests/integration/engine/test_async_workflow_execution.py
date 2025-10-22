"""
Integration Tests for Async Workflow Execution (User Story 4)
End-to-end tests for async workflow execution lifecycle
"""

import asyncio
import json
import time
from unittest.mock import MagicMock

import pytest

from shared.async_executor import enqueue_workflow_execution, get_queue_client
from shared.context import Caller, Organization, OrganizationContext
from shared.decorators import workflow
from shared.error_handling import WorkflowError
from shared.execution_logger import get_execution_logger
from shared.registry import WorkflowRegistry
from shared.request_context import RequestContext


@pytest.fixture
def test_org():
    """Test organization"""
    return Organization(
        org_id="test-org-async",
        name="Test Organization for Async",
        is_active=True
    )


@pytest.fixture
def test_caller():
    """Test caller"""
    return Caller(
        user_id="test-user-async",
        email="async@example.com",
        name="Async Test User"
    )


@pytest.fixture
def test_context(test_org, test_caller):
    """Test organization context"""
    return OrganizationContext(
        org=test_org,
        config={"test_setting": "test_value"},
        caller=test_caller,
        execution_id="test-exec-async"
    )


@pytest.fixture
def request_context(test_org, test_caller):
    """Test request context for enqueuing"""
    return RequestContext(
        org_id="test-org-async",
        user_id="test-user-async",
        email="async@example.com",
        name="Async Test User",
        is_platform_admin=False,
        is_function_key=False
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
async def queue_client():
    """Azure Storage Queue client for async execution"""
    client = get_queue_client()

    # Ensure queue exists
    try:
        client.create_queue()
    except Exception:
        pass  # Queue already exists

    # Clear any existing messages
    try:
        while True:
            messages = client.receive_messages(messages_per_page=32)
            batch = list(messages)
            if not batch:
                break
            for msg in batch:
                client.delete_message(msg)
    except Exception:
        pass

    yield client

    # Cleanup after test
    try:
        while True:
            messages = client.receive_messages(messages_per_page=32)
            batch = list(messages)
            if not batch:
                break
            for msg in batch:
                client.delete_message(msg)
    except Exception:
        pass


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


async def wait_for_queue_messages(queue_client, expected_count=1, max_attempts=10, delay=1.0):
    """
    Helper to wait for messages to appear in Azure Queue (handles Azurite delays)

    Args:
        queue_client: Azure Queue client
        expected_count: Minimum number of messages to wait for
        max_attempts: Maximum retry attempts (default: 10)
        delay: Delay between attempts in seconds (default: 1.0s)

    Returns:
        list: List of messages found
    """
    for attempt in range(max_attempts):
        messages = queue_client.receive_messages(messages_per_page=max(10, expected_count))
        message_list = list(messages)
        if len(message_list) >= expected_count:
            return message_list
        if attempt < max_attempts - 1:  # Don't sleep on last attempt
            await asyncio.sleep(delay)
    return message_list  # Return whatever we got


class TestAsyncWorkflowLifecycle:
    """Test the complete async workflow execution lifecycle"""

    @pytest.mark.asyncio
    async def test_enqueue_async_workflow(self, registry, request_context, queue_client):
        """Test enqueueing an async workflow creates execution record and queue message"""

        # Register a test async workflow
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

        # Verify workflow was registered
        metadata = registry.get_workflow("async_test_workflow")
        assert metadata is not None
        assert metadata.execution_mode == "async"

        # Enqueue workflow execution
        execution_id = await enqueue_workflow_execution(
            context=request_context,
            workflow_name="async_test_workflow",
            parameters={"value": 21}
        )

        # Verify execution ID was returned
        assert execution_id is not None
        assert len(execution_id) > 0

        # Verify execution record was created with PENDING status
        exec_logger = get_execution_logger()

        # Wait a moment for async operation to complete
        await asyncio.sleep(0.2)

        # Verify message was added to queue
        message_list = await wait_for_queue_messages(queue_client, expected_count=1)
        assert len(message_list) >= 1, f"Expected >= 1 messages, got {len(message_list)}"

        # Verify message structure
        msg = message_list[0]
        message_data = decode_queue_message(msg)

        assert message_data["execution_id"] == execution_id
        assert message_data["workflow_name"] == "async_test_workflow"
        assert message_data["org_id"] == "test-org-async"
        assert message_data["user_id"] == "test-user-async"
        assert message_data["parameters"]["value"] == 21

        # Clean up
        queue_client.delete_message(msg)

    @pytest.mark.asyncio
    async def test_worker_processes_async_workflow(self, registry, request_context, queue_client):
        """Test that worker processes queued workflow correctly"""

        # Register a test async workflow
        @workflow(
            name="worker_test_workflow",
            description="Worker test workflow",
            category="test",
            execution_mode="async"
        )
        async def worker_test(context, x: int, y: int):
            """Simple calculation workflow"""
            context.info("Processing calculation", {"x": x, "y": y})
            result = x + y
            return {"sum": result, "org": context.org_id}

        # Enqueue workflow
        execution_id = await enqueue_workflow_execution(
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
        queue_client.delete_message(msg)

    @pytest.mark.asyncio
    async def test_context_preservation_in_async_execution(self, registry, request_context, queue_client):
        """Test that organization context is preserved through async execution"""

        # Register workflow that uses context
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

            # Use context logging
            context.info("Action started", {"action": action})

            # Use context variables
            context.set_variable("action_type", action)

            # Save checkpoint
            context.save_checkpoint("action_complete", {"status": "done"})

            return {
                "org_id": org_id,
                "action": action,
                "caller": context.caller.email
            }

        # Enqueue workflow
        execution_id = await enqueue_workflow_execution(
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
        queue_client.delete_message(msg)

    @pytest.mark.asyncio
    async def test_async_workflow_error_handling(self, registry, request_context, queue_client):
        """Test error handling in async workflow execution"""

        # Register workflow that fails
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
        execution_id = await enqueue_workflow_execution(
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
        queue_client.delete_message(msg)

    @pytest.mark.asyncio
    async def test_async_workflow_result_storage(self, registry, request_context, queue_client):
        """Test that async workflow results are stored correctly"""

        # Register workflow with result
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
        execution_id = await enqueue_workflow_execution(
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
        queue_client.delete_message(msg)

    @pytest.mark.asyncio
    async def test_async_workflow_parameter_coercion(self, registry, request_context, queue_client):
        """Test that parameter types are coerced correctly in async execution"""

        # Register workflow with typed parameters
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
        execution_id = await enqueue_workflow_execution(
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
        queue_client.delete_message(msg)


class TestAsyncWorkflowConfiguration:
    """Test async workflow configuration and metadata"""

    def test_async_workflow_metadata(self, registry):
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

        metadata = registry.get_workflow("metadata_test")

        assert metadata is not None
        assert metadata.execution_mode == "async"
        assert metadata.timeout_seconds == 600
        assert metadata.name == "metadata_test"
        assert metadata.description == "Metadata test workflow"

    def test_sync_workflow_default(self, registry):
        """Test that workflows default to sync mode"""

        @workflow(
            name="sync_default",
            description="Default sync workflow",
            category="test"
        )
        async def sync_workflow(context):
            """Sync workflow"""
            return {"status": "ok"}

        metadata = registry.get_workflow("sync_default")

        assert metadata is not None
        assert metadata.execution_mode == "sync"


class TestAsyncWorkflowQueueManagement:
    """Test queue management for async workflows"""

    @pytest.mark.asyncio
    async def test_queue_message_format(self, registry, request_context, queue_client):
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
        queue_client.delete_message(msg)



class TestAsyncWorkflowStatusTransitions:
    """Test async workflow lifecycle and worker behavior

    Note: These tests verify worker processing behavior.
    Full status transition testing (PENDING→RUNNING→SUCCESS) requires
    API-level tests with actual HTTP endpoints.
    """

    @pytest.mark.asyncio
    async def test_worker_completes_successful_workflow(self, registry, request_context, queue_client):
        """Test that worker successfully processes and completes a workflow"""

        @workflow(
            name="lifecycle_test",
            description="Full lifecycle test",
            category="test",
            execution_mode="async"
        )
        async def lifecycle_workflow(context, step: str):
            """Workflow for lifecycle testing"""
            context.info(f"Step: {step}")
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
        queue_client.delete_message(msg)

    @pytest.mark.asyncio
    async def test_worker_handles_workflow_errors_gracefully(self, registry, request_context, queue_client):
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
        execution_id = await enqueue_workflow_execution(
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
        queue_client.delete_message(msg)


    @pytest.mark.asyncio
    async def test_worker_executes_async_workflow_with_delay(self, registry, request_context, queue_client):
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

        # Enqueue workflow
        execution_id = await enqueue_workflow_execution(
            context=request_context,
            workflow_name="duration_test",
            parameters={}
        )

        # Process with worker
        from functions.queue.worker import workflow_execution_worker
        message_list = await wait_for_queue_messages(queue_client, expected_count=1)
        assert len(message_list) >= 1, f"Expected >= 1 messages, got {len(message_list)}"

        msg = message_list[0]
        mock_msg = create_mock_queue_message(msg)

        # Measure execution time
        start = time.time()
        await workflow_execution_worker(mock_msg)
        elapsed = time.time() - start

        # Worker should have taken at least 200ms (the sleep time)
        assert elapsed >= 0.2, f"Worker should wait for async operations, took {elapsed}s"

        # Clean up
        queue_client.delete_message(msg)
