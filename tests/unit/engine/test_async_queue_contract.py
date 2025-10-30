"""
Unit tests for async workflow queue message contract

These tests verify that we create and process queue messages correctly
without depending on actual Azure Queue Storage infrastructure.
"""

import json
import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from shared.async_executor import enqueue_workflow_execution
from shared.context import ExecutionContext, Organization


class TestQueueMessageCreation:
    """Test that enqueue creates properly formatted queue messages"""

    @pytest.mark.asyncio
    @patch('shared.async_executor.get_queue_client')
    @patch('shared.async_executor.get_execution_logger')
    async def test_enqueue_sends_message_with_correct_structure(
        self, mock_get_logger, mock_get_queue_client
    ):
        """Test enqueue creates queue message with all required fields"""

        # Setup mocks
        mock_queue_client = MagicMock()
        mock_queue_client.send_message = AsyncMock()

        # Mock context manager protocol
        mock_context_manager = MagicMock()
        mock_context_manager.__aenter__ = AsyncMock(return_value=mock_queue_client)
        mock_context_manager.__aexit__ = AsyncMock(return_value=False)
        mock_get_queue_client.return_value = mock_context_manager

        mock_exec_logger = MagicMock()
        mock_exec_logger.create_execution = AsyncMock()
        mock_exec_logger.update_execution = AsyncMock()
        mock_get_logger.return_value = mock_exec_logger

        # Create execution context
        org = Organization(id="test-org", name="Test Org", is_active=True)
        context = ExecutionContext(
            user_id="test-user",
            email="test@example.com",
            name="Test User",
            scope="test-org",
            organization=org,
            is_platform_admin=False,
            is_function_key=False,
            execution_id="test-exec-queue"
        )

        # Execute
        execution_id = await enqueue_workflow_execution(
            context=context,
            workflow_name="test_workflow",
            parameters={"value": 42, "name": "test"}
        )

        # Verify execution ID returned
        assert execution_id is not None
        assert len(execution_id) > 0

        # Verify queue message was sent
        assert mock_queue_client.send_message.called

        # Extract and verify message structure
        call_args = mock_queue_client.send_message.call_args
        message_json = call_args[0][0]  # First positional argument
        message_data = json.loads(message_json)

        # Verify required fields
        assert message_data["execution_id"] == execution_id
        assert message_data["workflow_name"] == "test_workflow"
        assert message_data["org_id"] == "test-org"
        assert message_data["user_id"] == "test-user"
        assert message_data["user_email"] == "test@example.com"
        assert message_data["user_name"] == "Test User"
        assert message_data["parameters"]["value"] == 42
        assert message_data["parameters"]["name"] == "test"

    @pytest.mark.asyncio
    @patch('shared.async_executor.get_queue_client')
    @patch('shared.async_executor.get_execution_logger')
    async def test_enqueue_creates_execution_record(
        self, mock_get_logger, mock_get_queue_client
    ):
        """Test that enqueue creates execution record with PENDING status"""

        # Setup mocks
        mock_queue_client = MagicMock()
        mock_queue_client.send_message = AsyncMock()

        # Mock context manager protocol
        mock_context_manager = MagicMock()
        mock_context_manager.__aenter__ = AsyncMock(return_value=mock_queue_client)
        mock_context_manager.__aexit__ = AsyncMock(return_value=False)
        mock_get_queue_client.return_value = mock_context_manager

        mock_exec_logger = MagicMock()
        mock_exec_logger.create_execution = AsyncMock()
        mock_exec_logger.update_execution = AsyncMock()
        mock_get_logger.return_value = mock_exec_logger

        org = Organization(id="test-org", name="Test Org", is_active=True)
        context = ExecutionContext(
            user_id="test-user",
            email="test@example.com",
            name="Test User",
            scope="test-org",
            organization=org,
            is_platform_admin=False,
            is_function_key=False,
            execution_id="test-exec-create"
        )

        await enqueue_workflow_execution(
            context=context,
            workflow_name="test_workflow",
            parameters={"test": "data"},
            form_id="form-123"
        )

        # Verify create_execution was called
        assert mock_exec_logger.create_execution.called
        create_call = mock_exec_logger.create_execution.call_args
        assert create_call.kwargs["workflow_name"] == "test_workflow"
        assert create_call.kwargs["org_id"] == "test-org"
        assert create_call.kwargs["form_id"] == "form-123"

        # Verify update_execution was called with PENDING status
        assert mock_exec_logger.update_execution.called

    @pytest.mark.asyncio
    @patch('shared.async_executor.get_queue_client')
    @patch('shared.async_executor.get_execution_logger')
    async def test_enqueue_includes_form_id_when_provided(
        self, mock_get_logger, mock_get_queue_client
    ):
        """Test that form_id is included in queue message when provided"""

        # Setup mocks
        mock_queue_client = MagicMock()
        mock_queue_client.send_message = AsyncMock()

        # Mock context manager protocol
        mock_context_manager = MagicMock()
        mock_context_manager.__aenter__ = AsyncMock(return_value=mock_queue_client)
        mock_context_manager.__aexit__ = AsyncMock(return_value=False)
        mock_get_queue_client.return_value = mock_context_manager

        mock_exec_logger = MagicMock()
        mock_exec_logger.create_execution = AsyncMock()
        mock_exec_logger.update_execution = AsyncMock()
        mock_get_logger.return_value = mock_exec_logger

        org = Organization(id="test-org", name="Test Org", is_active=True)
        context = ExecutionContext(
            user_id="test-user",
            email="test@example.com",
            name="Test User",
            scope="test-org",
            organization=org,
            is_platform_admin=False,
            is_function_key=False,
            execution_id="test-exec-form"
        )

        # Execute with form_id
        await enqueue_workflow_execution(
            context=context,
            workflow_name="test_workflow",
            parameters={"data": "value"},
            form_id="form-456"
        )

        # Extract message and verify form_id
        call_args = mock_queue_client.send_message.call_args
        message_json = call_args[0][0]
        message_data = json.loads(message_json)

        assert message_data["form_id"] == "form-456"

    @pytest.mark.asyncio
    @patch('shared.async_executor.get_queue_client')
    @patch('shared.async_executor.get_execution_logger')
    async def test_enqueue_handles_empty_parameters(
        self, mock_get_logger, mock_get_queue_client
    ):
        """Test that enqueue handles empty parameters correctly"""

        # Setup mocks
        mock_queue_client = MagicMock()
        mock_queue_client.send_message = AsyncMock()

        # Mock context manager protocol
        mock_context_manager = MagicMock()
        mock_context_manager.__aenter__ = AsyncMock(return_value=mock_queue_client)
        mock_context_manager.__aexit__ = AsyncMock(return_value=False)
        mock_get_queue_client.return_value = mock_context_manager

        mock_exec_logger = MagicMock()
        mock_exec_logger.create_execution = AsyncMock()
        mock_exec_logger.update_execution = AsyncMock()
        mock_get_logger.return_value = mock_exec_logger

        org = Organization(id="test-org", name="Test Org", is_active=True)
        context = ExecutionContext(
            user_id="test-user",
            email="test@example.com",
            name="Test User",
            scope="test-org",
            organization=org,
            is_platform_admin=False,
            is_function_key=False,
            execution_id="test-exec-empty"
        )

        # Execute with empty parameters
        await enqueue_workflow_execution(
            context=context,
            workflow_name="test_workflow",
            parameters={}
        )

        # Extract message and verify parameters
        call_args = mock_queue_client.send_message.call_args
        message_json = call_args[0][0]
        message_data = json.loads(message_json)

        assert message_data["parameters"] == {}

    @pytest.mark.asyncio
    @patch('shared.async_executor.get_queue_client')
    @patch('shared.async_executor.get_execution_logger')
    async def test_multiple_enqueues_create_unique_execution_ids(
        self, mock_get_logger, mock_get_queue_client
    ):
        """Test that multiple enqueues get unique execution IDs"""

        # Setup mocks
        mock_queue_client = MagicMock()
        mock_queue_client.send_message = AsyncMock()

        # Mock context manager protocol
        mock_context_manager = MagicMock()
        mock_context_manager.__aenter__ = AsyncMock(return_value=mock_queue_client)
        mock_context_manager.__aexit__ = AsyncMock(return_value=False)
        mock_get_queue_client.return_value = mock_context_manager

        mock_exec_logger = MagicMock()
        mock_exec_logger.create_execution = AsyncMock()
        mock_exec_logger.update_execution = AsyncMock()
        mock_get_logger.return_value = mock_exec_logger

        org = Organization(id="test-org", name="Test Org", is_active=True)
        context = ExecutionContext(
            user_id="test-user",
            email="test@example.com",
            name="Test User",
            scope="test-org",
            organization=org,
            is_platform_admin=False,
            is_function_key=False,
            execution_id="test-exec-multi"
        )

        # Enqueue 3 executions
        returned_ids = []
        for i in range(3):
            exec_id = await enqueue_workflow_execution(
                context=context,
                workflow_name="test_workflow",
                parameters={"index": i}
            )
            returned_ids.append(exec_id)

        # Verify all IDs are unique
        assert len(set(returned_ids)) == 3

        # Verify 3 messages were sent
        assert mock_queue_client.send_message.call_count == 3

        # Verify each message has a unique execution ID
        sent_ids = set()
        for call_obj in mock_queue_client.send_message.call_args_list:
            message_json = call_obj[0][0]
            message_data = json.loads(message_json)
            sent_ids.add(message_data["execution_id"])

        assert len(sent_ids) == 3


class TestQueueMessageProcessing:
    """Test that worker can process queue messages correctly"""

    def test_worker_message_structure_roundtrip(self):
        """Test that queue message can be parsed from JSON"""
        # Create realistic queue message
        message_data = {
            "execution_id": "test-exec-123",
            "workflow_name": "test_workflow",
            "org_id": "test-org",
            "user_id": "test-user",
            "user_name": "Test User",
            "user_email": "test@example.com",
            "parameters": {"value": 42}
        }

        # Simulate what worker does: get_body() -> decode -> parse JSON
        message_json = json.dumps(message_data).encode('utf-8')
        message_body = message_json.decode('utf-8')
        parsed = json.loads(message_body)

        # Verify all expected fields are present
        assert parsed["execution_id"] == "test-exec-123"
        assert parsed["workflow_name"] == "test_workflow"
        assert parsed["org_id"] == "test-org"
        assert parsed["user_id"] == "test-user"
        assert parsed["user_name"] == "Test User"
        assert parsed["user_email"] == "test@example.com"
        assert parsed["parameters"]["value"] == 42

    def test_worker_message_missing_required_fields_detection(self):
        """Test that queue message with missing fields can be detected"""
        # Create message missing execution_id
        message_data = {
            "workflow_name": "test_workflow",
            "org_id": "test-org"
            # Missing execution_id
        }

        message_json = json.dumps(message_data).encode('utf-8')
        message_body = message_json.decode('utf-8')
        parsed = json.loads(message_body)

        # Verify we can detect the missing field
        with pytest.raises(KeyError):
            _ = parsed["execution_id"]

    def test_worker_message_malformed_json_detection(self):
        """Test that malformed JSON can be detected"""
        # Invalid JSON
        malformed_json = b"not valid json {"

        # Verify JSON parsing fails
        with pytest.raises(json.JSONDecodeError):
            json.loads(malformed_json.decode('utf-8'))

    def test_worker_message_with_all_optional_fields(self):
        """Test queue message with all optional fields"""
        # Create message with all fields including form_id
        message_data = {
            "execution_id": "test-exec-123",
            "workflow_name": "test_workflow",
            "org_id": "test-org",
            "user_id": "test-user",
            "user_name": "Test User",
            "user_email": "test@example.com",
            "parameters": {"value": 42},
            "form_id": "form-456"
        }

        message_json = json.dumps(message_data).encode('utf-8')
        message_body = message_json.decode('utf-8')
        parsed = json.loads(message_body)

        # Verify all fields including optional ones
        assert "form_id" in parsed
        assert parsed["form_id"] == "form-456"
        assert "parameters" in parsed

    def test_worker_extracts_execution_id_from_message(self):
        """Test extracting execution ID from message"""
        message_data = {
            "execution_id": "exec-uuid-12345",
            "workflow_name": "test_workflow",
            "org_id": "test-org",
            "user_id": "test-user",
            "user_name": "Test User",
            "user_email": "test@example.com",
            "parameters": {}
        }

        message_json = json.dumps(message_data).encode('utf-8')
        message_body = message_json.decode('utf-8')
        parsed = json.loads(message_body)

        # Simulate worker extraction
        execution_id = parsed["execution_id"]
        workflow_name = parsed["workflow_name"]
        org_id = parsed["org_id"]
        user_id = parsed["user_id"]

        assert execution_id == "exec-uuid-12345"
        assert workflow_name == "test_workflow"
        assert org_id == "test-org"
        assert user_id == "test-user"

    def test_worker_extracts_parameters_from_message(self):
        """Test extracting parameters from message"""
        message_data = {
            "execution_id": "exec-123",
            "workflow_name": "test_workflow",
            "org_id": "test-org",
            "user_id": "test-user",
            "user_name": "Test User",
            "user_email": "test@example.com",
            "parameters": {
                "email": "user@example.com",
                "age": 25,
                "tags": ["admin", "user"],
                "config": {"timeout": 300}
            }
        }

        message_json = json.dumps(message_data).encode('utf-8')
        message_body = message_json.decode('utf-8')
        parsed = json.loads(message_body)

        # Simulate parameter extraction
        parameters = parsed["parameters"]

        assert parameters["email"] == "user@example.com"
        assert parameters["age"] == 25
        assert parameters["tags"] == ["admin", "user"]
        assert parameters["config"]["timeout"] == 300


class TestQueueMessageFormat:
    """Test the format of queue messages"""

    def test_queue_message_json_serializable(self):
        """Test that queue messages can be serialized to JSON"""
        # Create a realistic message
        message = {
            "execution_id": "test-123",
            "workflow_name": "my_workflow",
            "org_id": "org-123",
            "user_id": "user-123",
            "user_name": "Test User",
            "user_email": "test@example.com",
            "parameters": {
                "string_param": "value",
                "int_param": 42,
                "bool_param": True,
                "list_param": [1, 2, 3],
                "dict_param": {"nested": "value"}
            },
            "form_id": "form-123"
        }

        # Should serialize without error
        json_str = json.dumps(message)
        assert json_str is not None

        # Should deserialize without error
        parsed = json.loads(json_str)
        assert parsed == message

    def test_queue_message_with_complex_parameters(self):
        """Test queue message with complex parameter structures"""
        message = {
            "execution_id": "test-123",
            "workflow_name": "complex_workflow",
            "org_id": "org-123",
            "user_id": "user-123",
            "user_name": "Test User",
            "user_email": "test@example.com",
            "parameters": {
                "items": [
                    {"id": 1, "name": "item1", "values": [10, 20, 30]},
                    {"id": 2, "name": "item2", "values": [40, 50, 60]}
                ],
                "config": {
                    "timeout": 300,
                    "retries": 3,
                    "tags": ["important", "automated"]
                }
            },
            "form_id": None
        }

        # Should serialize and deserialize correctly
        json_str = json.dumps(message)
        parsed = json.loads(json_str)

        assert len(parsed["parameters"]["items"]) == 2
        assert parsed["parameters"]["items"][0]["id"] == 1
        assert parsed["parameters"]["config"]["timeout"] == 300
        assert parsed["parameters"]["config"]["tags"] == ["important", "automated"]
