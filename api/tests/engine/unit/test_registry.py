"""
Unit tests for WorkflowRegistry
Tests singleton pattern, registration, and retrieval
"""

import pytest
from shared.registry import (
    WorkflowRegistry,
    WorkflowMetadata,
    WorkflowParameter,
    DataProviderMetadata,
    get_registry
)


@pytest.fixture
def registry():
    """Get registry instance and clear it before each test"""
    reg = get_registry()
    reg.clear_all()
    return reg


class TestWorkflowRegistry:
    """Test WorkflowRegistry singleton and basic operations"""

    def test_singleton_pattern(self):
        """Test that registry follows singleton pattern"""
        registry1 = WorkflowRegistry()
        registry2 = WorkflowRegistry()
        registry3 = get_registry()

        assert registry1 is registry2
        assert registry2 is registry3

    def test_register_workflow(self, registry):
        """Test registering a workflow"""
        metadata = WorkflowMetadata(
            name="test_workflow",
            description="Test workflow",
            category="Testing",
            tags=["test"],
            requires_org=True,
            parameters=[],
            function=lambda: None
        )

        registry.register_workflow(metadata)

        assert registry.has_workflow("test_workflow")
        assert registry.get_workflow_count() == 1

    def test_register_workflow_with_parameters(self, registry):
        """Test registering workflow with parameters"""
        param1 = WorkflowParameter(
            name="email",
            type="email",
            label="Email Address",
            required=True
        )
        param2 = WorkflowParameter(
            name="license",
            type="string",
            label="License Type",
            data_provider="get_available_licenses"
        )

        metadata = WorkflowMetadata(
            name="user_onboarding",
            description="Onboard user",
            parameters=[param1, param2],
            function=lambda: None
        )

        registry.register_workflow(metadata)

        workflow = registry.get_workflow("user_onboarding")
        assert workflow is not None
        assert len(workflow.parameters) == 2
        assert workflow.parameters[0].name == "email"
        assert workflow.parameters[1].data_provider == "get_available_licenses"

    def test_get_workflow_not_found(self, registry):
        """Test getting non-existent workflow returns None"""
        result = registry.get_workflow("nonexistent")
        assert result is None

    def test_get_all_workflows(self, registry):
        """Test getting all workflows"""
        metadata1 = WorkflowMetadata(
            name="workflow1",
            description="First workflow",
            function=lambda: None
        )
        metadata2 = WorkflowMetadata(
            name="workflow2",
            description="Second workflow",
            function=lambda: None
        )

        registry.register_workflow(metadata1)
        registry.register_workflow(metadata2)

        workflows = registry.get_all_workflows()
        assert len(workflows) == 2
        workflow_names = {w.name for w in workflows}
        assert workflow_names == {"workflow1", "workflow2"}

    def test_overwrite_existing_workflow(self, registry):
        """Test that registering same workflow name overwrites"""
        metadata1 = WorkflowMetadata(
            name="test_workflow",
            description="First version",
            function=lambda: None
        )
        metadata2 = WorkflowMetadata(
            name="test_workflow",
            description="Second version",
            function=lambda: None
        )

        registry.register_workflow(metadata1)
        registry.register_workflow(metadata2)

        workflow = registry.get_workflow("test_workflow")
        assert workflow.description == "Second version"
        assert registry.get_workflow_count() == 1

    def test_register_data_provider(self, registry):
        """Test registering a data provider"""
        metadata = DataProviderMetadata(
            name="get_available_licenses",
            description="Returns available licenses",
            category="m365",
            cache_ttl_seconds=300,
            function=lambda: None
        )

        registry.register_data_provider(metadata)

        assert registry.has_data_provider("get_available_licenses")
        assert registry.get_data_provider_count() == 1

    def test_get_data_provider(self, registry):
        """Test retrieving data provider"""
        metadata = DataProviderMetadata(
            name="test_provider",
            description="Test provider",
            function=lambda: None
        )

        registry.register_data_provider(metadata)

        provider = registry.get_data_provider("test_provider")
        assert provider is not None
        assert provider.name == "test_provider"
        assert provider.cache_ttl_seconds == 300  # Default

    def test_get_all_data_providers(self, registry):
        """Test getting all data providers"""
        metadata1 = DataProviderMetadata(
            name="provider1",
            description="First provider",
            function=lambda: None
        )
        metadata2 = DataProviderMetadata(
            name="provider2",
            description="Second provider",
            cache_ttl_seconds=600,
            function=lambda: None
        )

        registry.register_data_provider(metadata1)
        registry.register_data_provider(metadata2)

        providers = registry.get_all_data_providers()
        assert len(providers) == 2
        provider_names = {p.name for p in providers}
        assert provider_names == {"provider1", "provider2"}

    def test_clear_all(self, registry):
        """Test clearing all registrations"""
        workflow_meta = WorkflowMetadata(
            name="test_workflow",
            description="Test",
            function=lambda: None
        )
        provider_meta = DataProviderMetadata(
            name="test_provider",
            description="Test",
            function=lambda: None
        )

        registry.register_workflow(workflow_meta)
        registry.register_data_provider(provider_meta)

        assert registry.get_workflow_count() == 1
        assert registry.get_data_provider_count() == 1

        registry.clear_all()

        assert registry.get_workflow_count() == 0
        assert registry.get_data_provider_count() == 0

    def test_get_summary(self, registry):
        """Test getting registry summary"""
        workflow_meta = WorkflowMetadata(
            name="test_workflow",
            description="Test",
            function=lambda: None
        )
        provider_meta = DataProviderMetadata(
            name="test_provider",
            description="Test",
            function=lambda: None
        )

        registry.register_workflow(workflow_meta)
        registry.register_data_provider(provider_meta)

        summary = registry.get_summary()
        assert summary["workflows_count"] == 1
        assert summary["data_providers_count"] == 1
        assert "test_workflow" in summary["workflows"]
        assert "test_provider" in summary["data_providers"]


class TestWorkflowParameter:
    """Test WorkflowParameter dataclass"""

    def test_create_parameter_minimal(self):
        """Test creating parameter with minimal fields"""
        param = WorkflowParameter(
            name="test_param",
            type="string"
        )

        assert param.name == "test_param"
        assert param.type == "string"
        assert param.label is None
        assert param.required is False
        assert param.validation is None
        assert param.data_provider is None
        assert param.default_value is None
        assert param.help_text is None

    def test_create_parameter_full(self):
        """Test creating parameter with all fields"""
        param = WorkflowParameter(
            name="email",
            type="email",
            label="Email Address",
            required=True,
            validation={"pattern": r"^[a-zA-Z0-9._%+-]+@"},
            data_provider=None,
            default_value="test@example.com",
            help_text="Enter your email address"
        )

        assert param.name == "email"
        assert param.type == "email"
        assert param.label == "Email Address"
        assert param.required is True
        assert "pattern" in param.validation
        assert param.default_value == "test@example.com"
        assert param.help_text == "Enter your email address"


class TestWorkflowMetadata:
    """Test WorkflowMetadata dataclass"""

    def test_create_metadata_minimal(self):
        """Test creating metadata with minimal fields"""
        metadata = WorkflowMetadata(
            name="test_workflow",
            description="Test workflow"
        )

        assert metadata.name == "test_workflow"
        assert metadata.description == "Test workflow"
        assert metadata.category == "General"
        assert metadata.tags == []
        assert metadata.requires_org is True
        assert metadata.parameters == []
        assert metadata.function is None

    def test_create_metadata_full(self):
        """Test creating metadata with all fields"""
        def test_func():
            pass

        param = WorkflowParameter(name="test", type="string")

        metadata = WorkflowMetadata(
            name="user_onboarding",
            description="Onboard users",
            category="user_management",
            tags=["m365", "user"],
            requires_org=True,
            parameters=[param],
            function=test_func
        )

        assert metadata.name == "user_onboarding"
        assert metadata.category == "user_management"
        assert metadata.tags == ["m365", "user"]
        assert len(metadata.parameters) == 1
        assert metadata.function is test_func


class TestDataProviderMetadata:
    """Test DataProviderMetadata dataclass"""

    def test_create_provider_metadata_minimal(self):
        """Test creating provider metadata with minimal fields"""
        metadata = DataProviderMetadata(
            name="test_provider",
            description="Test provider"
        )

        assert metadata.name == "test_provider"
        assert metadata.description == "Test provider"
        assert metadata.category == "General"
        assert metadata.cache_ttl_seconds == 300
        assert metadata.function is None

    def test_create_provider_metadata_full(self):
        """Test creating provider metadata with all fields"""
        def test_func():
            pass

        metadata = DataProviderMetadata(
            name="get_available_licenses",
            description="Returns available licenses",
            category="m365",
            cache_ttl_seconds=600,
            function=test_func
        )

        assert metadata.name == "get_available_licenses"
        assert metadata.category == "m365"
        assert metadata.cache_ttl_seconds == 600
        assert metadata.function is test_func
