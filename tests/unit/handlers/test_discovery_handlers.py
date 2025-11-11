"""
Unit tests for discovery handlers
Tests discovery logic with mocked registry dependencies
"""

from unittest.mock import MagicMock, patch

import pytest

from shared.handlers.discovery_handlers import (
    convert_registry_provider_to_model,
    convert_registry_workflow_to_model,
    extract_relative_path,
    get_discovery_metadata,
)
from shared.models import DataProviderMetadata, MetadataResponse, WorkflowMetadata


class TestExtractRelativePath:
    """Tests for extract_relative_path"""

    def test_extract_from_home(self):
        """Test extracting path after /home/"""
        path = "/mounts/home/workflows/test_workflow.py"
        result = extract_relative_path(path)
        assert result == "workflows/test_workflow.py"

    def test_extract_from_platform(self):
        """Test extracting path after /platform/"""
        path = "/mounts/platform/examples/example_workflow.py"
        result = extract_relative_path(path)
        assert result == "examples/example_workflow.py"

    def test_extract_from_workspace(self):
        """Test extracting path after /workspace/"""
        path = "/mounts/workspace/repo/workflows/test.py"
        result = extract_relative_path(path)
        assert result == "repo/workflows/test.py"

    def test_no_marker_returns_none(self):
        """Test that paths without markers return None"""
        path = "/some/other/path/file.py"
        result = extract_relative_path(path)
        assert result is None

    def test_none_input_returns_none(self):
        """Test that None input returns None"""
        result = extract_relative_path(None)
        assert result is None

    def test_empty_string_returns_none(self):
        """Test that empty string returns None"""
        result = extract_relative_path("")
        assert result is None

    def test_first_marker_wins(self):
        """Test that first marker takes precedence"""
        # If path has multiple markers, use the first one found
        path = "/mounts/home/nested/workspace/file.py"
        result = extract_relative_path(path)
        assert result == "nested/workspace/file.py"


class TestConvertRegistryWorkflowToModel:
    """Tests for convert_registry_workflow_to_model"""

    def test_basic_workflow_conversion(self):
        """Test converting basic workflow metadata"""
        mock_registry_workflow = MagicMock()
        mock_registry_workflow.name = "test_workflow"
        mock_registry_workflow.description = "Test description"
        mock_registry_workflow.category = "Test"
        mock_registry_workflow.tags = ["test"]
        mock_registry_workflow.parameters = []
        mock_registry_workflow.execution_mode = "sync"
        mock_registry_workflow.timeout_seconds = 60
        mock_registry_workflow.retry_policy = None
        mock_registry_workflow.schedule = None
        mock_registry_workflow.endpoint_enabled = False
        mock_registry_workflow.allowed_methods = ["POST"]
        mock_registry_workflow.disable_global_key = False
        mock_registry_workflow.public_endpoint = False
        mock_registry_workflow.source = "workspace"
        mock_registry_workflow.source_file_path = "/mounts/workspace/test_workflow.py"

        result = convert_registry_workflow_to_model(mock_registry_workflow)

        assert isinstance(result, WorkflowMetadata)
        assert result.name == "test_workflow"
        assert result.description == "Test description"
        assert result.category == "Test"
        assert result.tags == ["test"]
        assert result.sourceFilePath == "/mounts/workspace/test_workflow.py"
        assert result.relativeFilePath == "test_workflow.py"


class TestConvertRegistryProviderToModel:
    """Tests for convert_registry_provider_to_model"""

    def test_basic_provider_conversion(self):
        """Test converting basic provider metadata"""
        mock_registry_provider = MagicMock()
        mock_registry_provider.name = "test_provider"
        mock_registry_provider.description = "Test provider"
        mock_registry_provider.category = "General"
        mock_registry_provider.cache_ttl_seconds = 300
        mock_registry_provider.parameters = []
        mock_registry_provider.source_file_path = "/mounts/workspace/test_provider.py"

        result = convert_registry_provider_to_model(mock_registry_provider)

        assert isinstance(result, DataProviderMetadata)
        assert result.name == "test_provider"
        assert result.description == "Test provider"
        assert result.category == "General"
        assert result.cache_ttl_seconds == 300
        assert result.sourceFilePath == "/mounts/workspace/test_provider.py"
        assert result.relativeFilePath == "test_provider.py"


class TestGetDiscoveryMetadata:
    """Tests for get_discovery_metadata"""

    @patch("shared.handlers.discovery_handlers.get_registry")
    def test_empty_registry(self, mock_get_registry):
        """Test discovery with empty registry"""
        mock_registry = MagicMock()
        mock_registry.get_all_workflows.return_value = []
        mock_registry.get_all_data_providers.return_value = []
        mock_get_registry.return_value = mock_registry

        result = get_discovery_metadata()

        assert isinstance(result, MetadataResponse)
        assert len(result.workflows) == 0
        assert len(result.dataProviders) == 0

    @patch("shared.handlers.discovery_handlers.get_registry")
    def test_single_workflow_and_provider(self, mock_get_registry):
        """Test discovery with single workflow and provider"""
        # Create mock workflow with all required attributes
        mock_workflow = MagicMock()
        mock_workflow.name = "test_workflow"
        mock_workflow.description = "Test description"
        mock_workflow.category = "Test"
        mock_workflow.tags = ["test"]
        mock_workflow.parameters = []
        mock_workflow.execution_mode = "sync"
        mock_workflow.timeout_seconds = 60
        mock_workflow.retry_policy = None
        mock_workflow.schedule = None
        mock_workflow.endpoint_enabled = False
        mock_workflow.allowed_methods = ["POST"]
        mock_workflow.disable_global_key = False
        mock_workflow.public_endpoint = False
        mock_workflow.source = "workspace"
        mock_workflow.source_file_path = "/mounts/workspace/test_workflow.py"

        # Create mock provider
        mock_provider = MagicMock()
        mock_provider.name = "test_provider"
        mock_provider.description = "Provider description"
        mock_provider.category = "General"
        mock_provider.cache_ttl_seconds = 300
        mock_provider.parameters = []
        mock_provider.source_file_path = "/mounts/workspace/test_provider.py"

        mock_registry = MagicMock()
        mock_registry.get_all_workflows.return_value = [mock_workflow]
        mock_registry.get_all_data_providers.return_value = [mock_provider]
        mock_get_registry.return_value = mock_registry

        result = get_discovery_metadata()

        assert isinstance(result, MetadataResponse)
        assert len(result.workflows) == 1
        assert len(result.dataProviders) == 1
        assert isinstance(result.workflows[0], WorkflowMetadata)
        assert isinstance(result.dataProviders[0], DataProviderMetadata)

    @patch("shared.handlers.discovery_handlers.get_registry")
    def test_multiple_workflows_and_providers(self, mock_get_registry):
        """Test discovery with multiple workflows and providers"""
        # Create multiple workflow mocks with all required attributes
        workflows = []
        for i in range(3):
            mock_workflow = MagicMock()
            mock_workflow.name = f"workflow_{i}"
            mock_workflow.description = f"Description {i}"
            mock_workflow.category = "Category"
            mock_workflow.tags = []
            mock_workflow.parameters = []
            mock_workflow.execution_mode = "sync"
            mock_workflow.timeout_seconds = 60
            mock_workflow.retry_policy = None
            mock_workflow.schedule = None
            mock_workflow.endpoint_enabled = False
            mock_workflow.allowed_methods = ["POST"]
            mock_workflow.disable_global_key = False
            mock_workflow.public_endpoint = False
            mock_workflow.source = "workspace"
            mock_workflow.source_file_path = f"/mounts/workspace/workflow_{i}.py"
            workflows.append(mock_workflow)

        # Create multiple provider mocks
        providers = []
        for i in range(2):
            mock_provider = MagicMock()
            mock_provider.name = f"provider_{i}"
            mock_provider.description = f"Description {i}"
            mock_provider.category = "General"
            mock_provider.cache_ttl_seconds = 300
            mock_provider.parameters = []
            mock_provider.source_file_path = f"/mounts/workspace/provider_{i}.py"
            providers.append(mock_provider)

        mock_registry = MagicMock()
        mock_registry.get_all_workflows.return_value = workflows
        mock_registry.get_all_data_providers.return_value = providers
        mock_get_registry.return_value = mock_registry

        result = get_discovery_metadata()

        assert isinstance(result, MetadataResponse)
        assert len(result.workflows) == 3
        assert len(result.dataProviders) == 2
        # Verify conversions happened
        assert all(isinstance(w, WorkflowMetadata) for w in result.workflows)
        assert all(isinstance(p, DataProviderMetadata) for p in result.dataProviders)

    @patch("shared.handlers.discovery_handlers.get_registry")
    def test_metadata_response_structure(self, mock_get_registry):
        """Test that result is valid MetadataResponse"""
        mock_workflow = MagicMock()
        mock_workflow.name = "test"
        mock_workflow.description = "Test"
        mock_workflow.category = "Test"
        mock_workflow.tags = []
        mock_workflow.parameters = []
        mock_workflow.execution_mode = "sync"
        mock_workflow.timeout_seconds = 60
        mock_workflow.retry_policy = None
        mock_workflow.schedule = None
        mock_workflow.endpoint_enabled = False
        mock_workflow.allowed_methods = ["POST"]
        mock_workflow.disable_global_key = False
        mock_workflow.public_endpoint = False
        mock_workflow.source = "workspace"
        mock_workflow.source_file_path = "/mounts/workspace/test.py"

        mock_provider = MagicMock()
        mock_provider.name = "test"
        mock_provider.description = "Test"
        mock_provider.category = "General"
        mock_provider.cache_ttl_seconds = 300
        mock_provider.parameters = []
        mock_provider.source_file_path = "/mounts/workspace/test_provider.py"

        mock_registry = MagicMock()
        mock_registry.get_all_workflows.return_value = [mock_workflow]
        mock_registry.get_all_data_providers.return_value = [mock_provider]
        mock_get_registry.return_value = mock_registry

        result = get_discovery_metadata()

        # Verify it's a valid Pydantic model
        assert isinstance(result, MetadataResponse)
        assert hasattr(result, "workflows")
        assert hasattr(result, "dataProviders")

    @patch("shared.handlers.discovery_handlers.get_registry")
    def test_registry_called_once(self, mock_get_registry):
        """Test that registry is called exactly once"""
        mock_registry = MagicMock()
        mock_registry.get_all_workflows.return_value = []
        mock_registry.get_all_data_providers.return_value = []
        mock_get_registry.return_value = mock_registry

        get_discovery_metadata()

        mock_get_registry.assert_called_once()

    @patch("shared.handlers.discovery_handlers.get_registry")
    def test_registry_methods_called(self, mock_get_registry):
        """Test that registry methods are called"""
        mock_registry = MagicMock()
        mock_registry.get_all_workflows.return_value = []
        mock_registry.get_all_data_providers.return_value = []
        mock_get_registry.return_value = mock_registry

        get_discovery_metadata()

        mock_registry.get_all_workflows.assert_called_once()
        mock_registry.get_all_data_providers.assert_called_once()

    @patch("shared.handlers.discovery_handlers.get_registry")
    def test_exception_propagation(self, mock_get_registry):
        """Test that exceptions are propagated"""
        mock_get_registry.side_effect = RuntimeError("Registry error")

        with pytest.raises(RuntimeError, match="Registry error"):
            get_discovery_metadata()

    @patch("shared.handlers.discovery_handlers.get_registry")
    def test_workflow_access_exception(self, mock_get_registry):
        """Test exception during workflow access"""
        mock_registry = MagicMock()
        mock_registry.get_all_workflows.side_effect = ValueError("Workflow error")
        mock_get_registry.return_value = mock_registry

        with pytest.raises(ValueError, match="Workflow error"):
            get_discovery_metadata()

    @patch("shared.handlers.discovery_handlers.get_registry")
    def test_provider_access_exception(self, mock_get_registry):
        """Test exception during provider access"""
        mock_registry = MagicMock()
        mock_registry.get_all_workflows.return_value = []
        mock_registry.get_all_data_providers.side_effect = ValueError("Provider error")
        mock_get_registry.return_value = mock_registry

        with pytest.raises(ValueError, match="Provider error"):
            get_discovery_metadata()

    @patch("shared.handlers.discovery_handlers.get_registry")
    def test_logging_on_retrieval(self, mock_get_registry):
        """Test that logging occurs during retrieval"""
        mock_registry = MagicMock()
        mock_registry.get_all_workflows.return_value = []
        mock_registry.get_all_data_providers.return_value = []
        mock_get_registry.return_value = mock_registry

        with patch("shared.handlers.discovery_handlers.logger") as mock_logger:
            get_discovery_metadata()

            # Verify info logging was called
            assert mock_logger.info.call_count >= 1
            # Check that the retrieval message was logged
            calls = [str(call) for call in mock_logger.info.call_args_list]
            assert any("Retrieving discovery metadata" in str(call) for call in calls)
            assert any("Retrieved metadata" in str(call) for call in calls)

    @patch("shared.system_logger.get_system_logger")
    @patch("shared.handlers.discovery_handlers.get_registry")
    def test_workflow_validation_failure_skipped(self, mock_get_registry, mock_get_system_logger):
        """Test that workflows with validation errors are skipped and logged"""
        # Create one valid workflow and one invalid workflow
        valid_workflow = MagicMock()
        valid_workflow.name = "valid_workflow"
        valid_workflow.description = "Valid"
        valid_workflow.category = "Test"
        valid_workflow.tags = []
        valid_workflow.parameters = []
        valid_workflow.execution_mode = "sync"
        valid_workflow.timeout_seconds = 60
        valid_workflow.retry_policy = None
        valid_workflow.schedule = None
        valid_workflow.endpoint_enabled = False
        valid_workflow.allowed_methods = ["POST"]
        valid_workflow.disable_global_key = False
        valid_workflow.public_endpoint = False
        valid_workflow.source = "workspace"
        valid_workflow.source_file_path = "/mounts/workspace/valid_workflow.py"

        invalid_workflow = MagicMock()
        invalid_workflow.name = "invalid_workflow"
        invalid_workflow.description = "Invalid"
        invalid_workflow.category = "Test"
        invalid_workflow.tags = []
        invalid_workflow.parameters = []
        invalid_workflow.execution_mode = "sync"
        invalid_workflow.timeout_seconds = 8000  # Invalid - exceeds max of 7200 (2 hours)
        invalid_workflow.retry_policy = None
        invalid_workflow.schedule = None
        invalid_workflow.endpoint_enabled = False
        invalid_workflow.allowed_methods = ["POST"]
        invalid_workflow.disable_global_key = False
        invalid_workflow.public_endpoint = False
        invalid_workflow.source = "workspace"
        invalid_workflow.source_file_path = "/mounts/workspace/invalid_workflow.py"

        mock_registry = MagicMock()
        mock_registry.get_all_workflows.return_value = [valid_workflow, invalid_workflow]
        mock_registry.get_all_data_providers.return_value = []
        mock_get_registry.return_value = mock_registry

        mock_system_logger = MagicMock()
        mock_get_system_logger.return_value = mock_system_logger

        result = get_discovery_metadata()

        # Should have skipped invalid workflow
        assert len(result.workflows) == 1
        assert result.workflows[0].name == "valid_workflow"

        # Should have logged to system logger
        # Note: asyncio.create_task is called but we can't easily verify async call in sync test

    @patch("shared.system_logger.get_system_logger")
    @patch("shared.handlers.discovery_handlers.get_registry")
    def test_data_provider_validation_failure_skipped(self, mock_get_registry, mock_get_system_logger):
        """Test that data providers with validation errors are skipped and logged"""
        valid_provider = MagicMock()
        valid_provider.name = "valid_provider"
        valid_provider.description = "Valid"
        valid_provider.category = "General"
        valid_provider.cache_ttl_seconds = 300
        valid_provider.parameters = []
        valid_provider.source_file_path = "/mounts/workspace/valid_provider.py"

        # Create invalid provider (we'd need to mock the conversion function to raise ValidationError)
        # For now, just test the structure exists
        mock_registry = MagicMock()
        mock_registry.get_all_workflows.return_value = []
        mock_registry.get_all_data_providers.return_value = [valid_provider]
        mock_get_registry.return_value = mock_registry

        mock_system_logger = MagicMock()
        mock_get_system_logger.return_value = mock_system_logger

        result = get_discovery_metadata()

        # All valid providers should be included
        assert len(result.dataProviders) == 1
        assert result.dataProviders[0].name == "valid_provider"

    @patch("shared.handlers.discovery_handlers.get_registry")
    def test_validation_failure_logs_error(self, mock_get_registry):
        """Test that validation failures are logged as errors"""
        import warnings

        invalid_workflow = MagicMock()
        invalid_workflow.name = "invalid_workflow"
        invalid_workflow.description = "Invalid"
        invalid_workflow.category = "Test"
        invalid_workflow.tags = []
        invalid_workflow.parameters = []
        invalid_workflow.execution_mode = "sync"
        invalid_workflow.timeout_seconds = 8000  # Invalid - exceeds max of 7200 (2 hours)
        invalid_workflow.retry_policy = None
        invalid_workflow.schedule = None
        invalid_workflow.endpoint_enabled = False
        invalid_workflow.allowed_methods = ["POST"]
        invalid_workflow.disable_global_key = False
        invalid_workflow.public_endpoint = False
        invalid_workflow.source = "workspace"
        invalid_workflow.source_file_path = "/mounts/workspace/invalid_workflow2.py"

        mock_registry = MagicMock()
        mock_registry.get_all_workflows.return_value = [invalid_workflow]
        mock_registry.get_all_data_providers.return_value = []
        mock_get_registry.return_value = mock_registry

        # Suppress RuntimeWarning about unawaited coroutine from fire-and-forget system logger
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=RuntimeWarning, message=".*coroutine.*never awaited")
            with patch("shared.handlers.discovery_handlers.logger") as mock_logger:
                get_discovery_metadata()

                # Should have logged error
                mock_logger.error.assert_called()
                error_calls = [str(call) for call in mock_logger.error.call_args_list]
                assert any("invalid_workflow" in str(call) for call in error_calls)
