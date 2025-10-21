"""
Unit tests for Azure Storage Queue initialization

Tests the queue initialization module that ensures queues exist
before Azure Functions tries to bind to them.
"""

import pytest
from unittest.mock import MagicMock, patch

from shared.queue_init import init_queues, _mask_connection_string


class TestQueueInitialization:
    """Test queue initialization functionality"""

    @patch('shared.queue_init.QueueServiceClient')
    def test_init_queues_creates_new_queue(
            self, mock_service_client_class):
        """Test successful creation of a new queue"""
        # Setup mocks
        mock_service_client = MagicMock()
        mock_queue_client = MagicMock()
        (mock_service_client_class.from_connection_string.
         return_value) = mock_service_client
        mock_service_client.get_queue_client.return_value = (
            mock_queue_client)
        mock_queue_client.create_queue.return_value = None

        # Execute
        results = init_queues("UseDevelopmentStorage=true")

        # Verify
        assert len(results["created"]) == 2
        assert "workflow-executions" in results["created"]
        assert "workflow-executions-poison" in results["created"]
        assert len(results["already_exists"]) == 0
        assert len(results["failed"]) == 0

        (mock_service_client_class.from_connection_string.
         assert_called_once_with("UseDevelopmentStorage=true"))
        # Should be called twice, once for each queue
        assert mock_service_client.get_queue_client.call_count == 2
        mock_queue_client.create_queue.assert_called()

    @patch('shared.queue_init.QueueServiceClient')
    def test_init_queues_handles_already_existing_queue(
            self, mock_service_client_class):
        """Test handling of queue that already exists"""
        # Setup mocks
        mock_service_client = MagicMock()
        mock_queue_client = MagicMock()
        (mock_service_client_class.from_connection_string.
         return_value) = mock_service_client
        mock_service_client.get_queue_client.return_value = (
            mock_queue_client)

        # Simulate "queue already exists" error
        mock_queue_client.create_queue.side_effect = Exception(
            "QueueAlreadyExists"
        )

        # Execute
        results = init_queues("UseDevelopmentStorage=true")

        # Verify
        assert len(results["created"]) == 0
        assert len(results["already_exists"]) == 2
        assert "workflow-executions" in results["already_exists"]
        assert "workflow-executions-poison" in results["already_exists"]
        assert len(results["failed"]) == 0

    @patch('shared.queue_init.QueueServiceClient')
    def test_init_queues_handles_case_insensitive_already_exists(
            self, mock_service_client_class):
        """Test handling of 'already exists' error with different case"""
        # Setup mocks
        mock_service_client = MagicMock()
        mock_queue_client = MagicMock()
        (mock_service_client_class.from_connection_string.
         return_value) = mock_service_client
        mock_service_client.get_queue_client.return_value = (
            mock_queue_client)

        # Simulate "already exists" error with different message
        mock_queue_client.create_queue.side_effect = Exception(
            "The specified queue already exists."
        )

        # Execute
        results = init_queues("UseDevelopmentStorage=true")

        # Verify
        assert len(results["already_exists"]) == 2
        assert len(results["failed"]) == 0

    @patch('shared.queue_init.QueueServiceClient')
    def test_init_queues_handles_creation_failure(
            self, mock_service_client_class):
        """Test handling of queue creation failure"""
        # Setup mocks
        mock_service_client = MagicMock()
        mock_queue_client = MagicMock()
        (mock_service_client_class.from_connection_string.
         return_value) = mock_service_client
        mock_service_client.get_queue_client.return_value = (
            mock_queue_client)

        # Simulate unexpected error
        mock_queue_client.create_queue.side_effect = Exception(
            "Connection refused"
        )

        # Execute
        results = init_queues("UseDevelopmentStorage=true")

        # Verify
        assert len(results["failed"]) == 2
        assert results["failed"][0]["queue"] == "workflow-executions"
        assert results["failed"][1]["queue"] == "workflow-executions-poison"
        assert "Connection refused" in results["failed"][0]["error"]
        assert "Connection refused" in results["failed"][1]["error"]
        assert len(results["created"]) == 0
        assert len(results["already_exists"]) == 0

    @patch('shared.queue_init.os.environ.get')
    @patch('shared.queue_init.QueueServiceClient')
    def test_init_queues_uses_env_var_connection_string(
            self, mock_service_client_class, mock_env_get):
        """Test that init_queues uses AzureWebJobsStorage env var"""
        # Setup mocks
        mock_env_get.return_value = "DefaultEndpointsProtocol=https;..."
        mock_service_client = MagicMock()
        mock_queue_client = MagicMock()
        (mock_service_client_class.from_connection_string.
         return_value) = mock_service_client
        mock_service_client.get_queue_client.return_value = (
            mock_queue_client)
        mock_queue_client.create_queue.return_value = None

        # Execute without providing connection string
        init_queues()

        # Verify
        mock_env_get.assert_called_with(
            "AzureWebJobsStorage", "UseDevelopmentStorage=true")
        (mock_service_client_class.from_connection_string.
         assert_called_once_with("DefaultEndpointsProtocol=https;..."))

    def test_mask_connection_string_azurite(self):
        """Test connection string masking for Azurite"""
        result = _mask_connection_string("UseDevelopmentStorage=true")
        assert result == "UseDevelopmentStorage=true (Azurite)"
        assert "UseDevelopmentStorage" in result

    def test_mask_connection_string_production(self):
        """Test connection string masking for production Azure Storage"""
        conn_str = (
            "DefaultEndpointsProtocol=https;AccountName=myaccount;"
            "AccountKey=abc123def456ghi789jkl012mno345pqr567stu890;"
            "EndpointSuffix=core.windows.net"
        )
        result = _mask_connection_string(conn_str)

        # Should contain masked key
        is_masked = ("abc123" not in result or
                     result.count("abc123") == 1)
        assert is_masked
        assert "..." in result
        assert "DefaultEndpointsProtocol=https" in result

    def test_mask_connection_string_partial_account_key(self):
        """Test connection string masking with partial account key"""
        conn_str = (
            "DefaultEndpointsProtocol=https;AccountName=myaccount;"
            "AccountKey=short;EndpointSuffix=core.windows.net"
        )
        result = _mask_connection_string(conn_str)

        # Short keys should be fully masked
        assert "***" in result

    def test_mask_connection_string_no_account_key(self):
        """Test connection string masking for non-Azure connection strings"""
        conn_str = "some.other.connection.string"
        result = _mask_connection_string(conn_str)

        # Should return original if no masking needed
        assert result == "some.other.connection.string"


class TestQueueInitializationIntegration:
    """Integration tests for queue initialization (requires Azurite)"""

    @pytest.mark.skip(reason="Requires Azurite/Azure Storage running")
    def test_init_queues_creates_queue_in_azurite(self):
        """Test queue creation against actual Azurite instance"""
        # This test requires docker-compose.testing.yml to be running
        results = init_queues("UseDevelopmentStorage=true")

        assert len(results["created"]) >= 0  # May already exist
        assert len(results["failed"]) == 0
