"""
Unit tests for discovery handlers
Tests discovery logic with mocked discovery module dependencies
"""

from unittest.mock import patch


from shared.handlers.discovery_handlers import (
    convert_workflow_metadata_to_model,
    convert_data_provider_metadata_to_model,
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


class TestConvertWorkflowMetadataToModel:
    """Tests for convert_workflow_metadata_to_model"""

    def test_basic_workflow_conversion(self):
        """Test converting basic workflow metadata"""
        from shared.discovery import WorkflowMetadata as DiscoveryWorkflowMetadata

        discovery_workflow = DiscoveryWorkflowMetadata(
            name="test_workflow",
            description="Test description",
            category="Test",
            tags=["test"],
            parameters=[],
            execution_mode="sync",
            timeout_seconds=60,
            retry_policy=None,
            schedule=None,
            endpoint_enabled=False,
            allowed_methods=["POST"],
            disable_global_key=False,
            public_endpoint=False,
            source="workspace",
            source_file_path="/mounts/workspace/test_workflow.py"
        )

        result = convert_workflow_metadata_to_model(discovery_workflow)

        assert isinstance(result, WorkflowMetadata)
        assert result.name == "test_workflow"
        assert result.description == "Test description"
        assert result.category == "Test"
        assert result.tags == ["test"]
        assert result.sourceFilePath == "/mounts/workspace/test_workflow.py"
        assert result.relativeFilePath == "test_workflow.py"


class TestConvertDataProviderMetadataToModel:
    """Tests for convert_data_provider_metadata_to_model"""

    def test_basic_provider_conversion(self):
        """Test converting basic provider metadata"""
        from shared.discovery import DataProviderMetadata as DiscoveryDataProviderMetadata

        discovery_provider = DiscoveryDataProviderMetadata(
            name="test_provider",
            description="Test provider",
            category="General",
            cache_ttl_seconds=300,
            parameters=[],
            source_file_path="/mounts/workspace/test_provider.py"
        )

        result = convert_data_provider_metadata_to_model(discovery_provider)

        assert isinstance(result, DataProviderMetadata)
        assert result.name == "test_provider"
        assert result.description == "Test provider"
        assert result.category == "General"
        assert result.cache_ttl_seconds == 300
        assert result.sourceFilePath == "/mounts/workspace/test_provider.py"
        assert result.relativeFilePath == "test_provider.py"


class TestGetDiscoveryMetadata:
    """Tests for get_discovery_metadata"""

    @patch("shared.handlers.discovery_handlers.scan_all_forms")
    @patch("shared.handlers.discovery_handlers.scan_all_data_providers")
    @patch("shared.handlers.discovery_handlers.scan_all_workflows")
    async def test_empty_discovery(
        self,
        mock_scan_workflows,
        mock_scan_providers,
        mock_scan_forms
    ):
        """Test discovery with empty results"""
        mock_scan_workflows.return_value = []
        mock_scan_providers.return_value = []
        mock_scan_forms.return_value = []

        result = await get_discovery_metadata()

        assert isinstance(result, MetadataResponse)
        assert len(result.workflows) == 0
        assert len(result.dataProviders) == 0

    @patch("shared.handlers.discovery_handlers.scan_all_forms")
    @patch("shared.handlers.discovery_handlers.scan_all_data_providers")
    @patch("shared.handlers.discovery_handlers.scan_all_workflows")
    async def test_single_workflow_and_provider(
        self,
        mock_scan_workflows,
        mock_scan_providers,
        mock_scan_forms
    ):
        """Test discovery with single workflow and provider"""
        from shared.discovery import (
            WorkflowMetadata as DiscoveryWorkflowMetadata,
            DataProviderMetadata as DiscoveryDataProviderMetadata
        )

        mock_workflow = DiscoveryWorkflowMetadata(
            name="test_workflow",
            description="Test description",
            category="Test",
            tags=["test"],
            parameters=[],
            execution_mode="sync",
            timeout_seconds=60,
            source="workspace",
            source_file_path="/mounts/workspace/test_workflow.py"
        )

        mock_provider = DiscoveryDataProviderMetadata(
            name="test_provider",
            description="Provider description",
            category="General",
            cache_ttl_seconds=300,
            parameters=[],
            source_file_path="/mounts/workspace/test_provider.py"
        )

        mock_scan_workflows.return_value = [mock_workflow]
        mock_scan_providers.return_value = [mock_provider]
        mock_scan_forms.return_value = []

        result = await get_discovery_metadata()

        assert isinstance(result, MetadataResponse)
        assert len(result.workflows) == 1
        assert len(result.dataProviders) == 1
        assert isinstance(result.workflows[0], WorkflowMetadata)
        assert isinstance(result.dataProviders[0], DataProviderMetadata)

    @patch("shared.handlers.discovery_handlers.scan_all_forms")
    @patch("shared.handlers.discovery_handlers.scan_all_data_providers")
    @patch("shared.handlers.discovery_handlers.scan_all_workflows")
    async def test_multiple_workflows_and_providers(
        self,
        mock_scan_workflows,
        mock_scan_providers,
        mock_scan_forms
    ):
        """Test discovery with multiple workflows and providers"""
        from shared.discovery import (
            WorkflowMetadata as DiscoveryWorkflowMetadata,
            DataProviderMetadata as DiscoveryDataProviderMetadata
        )

        # Create multiple workflow mocks
        workflows = []
        for i in range(3):
            mock_workflow = DiscoveryWorkflowMetadata(
                name=f"workflow_{i}",
                description=f"Workflow {i} description",
                category="Test",
                tags=["test"],
                parameters=[],
                execution_mode="sync",
                timeout_seconds=60,
                source="workspace",
                source_file_path=f"/mounts/workspace/workflow_{i}.py"
            )
            workflows.append(mock_workflow)

        # Create multiple provider mocks
        providers = []
        for i in range(2):
            mock_provider = DiscoveryDataProviderMetadata(
                name=f"provider_{i}",
                description=f"Provider {i} description",
                category="General",
                cache_ttl_seconds=300,
                parameters=[],
                source_file_path=f"/mounts/workspace/provider_{i}.py"
            )
            providers.append(mock_provider)

        mock_scan_workflows.return_value = workflows
        mock_scan_providers.return_value = providers
        mock_scan_forms.return_value = []

        result = await get_discovery_metadata()

        assert isinstance(result, MetadataResponse)
        assert len(result.workflows) == 3
        assert len(result.dataProviders) == 2
