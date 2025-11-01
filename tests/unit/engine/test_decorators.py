"""
Unit tests for workflow and data provider decorators
Tests decorator registration, metadata extraction, and parameter handling
"""

import pytest

from shared.decorators import VALID_PARAM_TYPES, data_provider, param, workflow


@pytest.fixture
def registry(isolated_registry):
    """Use isolated registry for each test to prevent state pollution"""
    return isolated_registry


class TestWorkflowDecorator:
    """Test @workflow decorator"""

    def test_workflow_decorator_basic(self, registry):
        """Test basic workflow decorator"""
        @workflow(
            name="test_workflow",
            description="Test workflow"
        )
        def test_func():
            return "test result"

        # Verify workflow is registered
        assert registry.has_workflow("test_workflow")

        # Verify function still works normally
        result = test_func()
        assert result == "test result"

        # Verify metadata
        workflow_meta = registry.get_workflow("test_workflow")
        assert workflow_meta.name == "test_workflow"
        assert workflow_meta.description == "Test workflow"
        assert workflow_meta.category == "General"
        assert workflow_meta.tags == []
        assert workflow_meta.execution_mode == "async"  # New default

    def test_workflow_decorator_full_options(self, registry):
        """Test workflow decorator with all options"""
        @workflow(
            name="user_onboarding",
            description="Onboard new M365 user",
            category="user_management",
            tags=["m365", "user"]
        )
        def onboard_user(context, first_name, last_name):
            return f"Onboarded {first_name} {last_name}"

        workflow_meta = registry.get_workflow("user_onboarding")
        assert workflow_meta.category == "user_management"
        assert workflow_meta.tags == ["m365", "user"]
        assert workflow_meta.execution_mode == "async"  # New default

        # Verify function still callable
        result = onboard_user(None, "John", "Doe")
        assert result == "Onboarded John Doe"

    def test_workflow_decorator_execution_mode_async(self, registry):
        """Test workflow with async execution mode"""
        @workflow(
            name="utility_workflow",
            description="Utility function",
            execution_mode="async"
        )
        def utility_func():
            return "utility"

        workflow_meta = registry.get_workflow("utility_workflow")
        assert workflow_meta.execution_mode == "async"

    def test_workflow_endpoint_defaults_to_sync(self, registry):
        """Test that workflows with endpoint_enabled default to sync"""
        @workflow(
            name="webhook_workflow",
            description="Webhook endpoint",
            endpoint_enabled=True
        )
        def webhook_func():
            return "webhook"

        workflow_meta = registry.get_workflow("webhook_workflow")
        assert workflow_meta.execution_mode == "sync"  # Auto-defaults to sync
        assert workflow_meta.endpoint_enabled is True

    def test_workflow_endpoint_explicit_async_override(self, registry):
        """Test that explicit async overrides endpoint default"""
        @workflow(
            name="async_webhook",
            description="Async webhook",
            endpoint_enabled=True,
            execution_mode="async"
        )
        def async_webhook_func():
            return "async webhook"

        workflow_meta = registry.get_workflow("async_webhook")
        assert workflow_meta.execution_mode == "async"  # Explicit wins
        assert workflow_meta.endpoint_enabled is True

    def test_workflow_function_metadata_preserved(self, registry):
        """Test that function metadata is preserved"""
        @workflow(
            name="test_workflow",
            description="Test"
        )
        def test_func():
            """Original docstring"""
            pass

        assert hasattr(test_func, '_workflow_metadata')
        assert test_func.__name__ == "test_func"
        assert test_func.__doc__ == "Original docstring"


class TestParamDecorator:
    """Test @param decorator"""

    def test_param_decorator_basic(self, registry):
        """Test basic param decorator"""
        @workflow(name="test_workflow", description="Test")
        @param("email", type="email", label="Email Address", required=True)
        def test_func(context, email):
            return email

        workflow_meta = registry.get_workflow("test_workflow")
        assert len(workflow_meta.parameters) == 1

        param_meta = workflow_meta.parameters[0]
        assert param_meta.name == "email"
        assert param_meta.type == "email"
        assert param_meta.label == "Email Address"
        assert param_meta.required is True

    def test_param_decorator_multiple_params(self, registry):
        """Test multiple @param decorators"""
        @workflow(name="user_onboarding", description="Onboard user")
        @param("first_name", type="string", label="First Name", required=True)
        @param("last_name", type="string", label="Last Name", required=True)
        @param("email", type="email", label="Email", required=True)
        @param("license", type="string", label="License Type", data_provider="get_licenses")
        def onboard_user(context, first_name, last_name, email, license):
            pass

        workflow_meta = registry.get_workflow("user_onboarding")
        assert len(workflow_meta.parameters) == 4

        # Parameters should be in order (decorators applied bottom-up, but we reverse)
        param_names = [p.name for p in workflow_meta.parameters]
        assert param_names == ["first_name", "last_name", "email", "license"]

    def test_param_decorator_with_validation(self, registry):
        """Test param with validation rules"""
        @workflow(name="test_workflow", description="Test")
        @param(
            "age",
            type="int",
            label="Age",
            required=True,
            validation={"min": 0, "max": 120}
        )
        def test_func(context, age):
            pass

        workflow_meta = registry.get_workflow("test_workflow")
        param_meta = workflow_meta.parameters[0]
        assert param_meta.validation == {"min": 0, "max": 120}

    def test_param_decorator_with_data_provider(self, registry):
        """Test param with data provider"""
        @workflow(name="test_workflow", description="Test")
        @param(
            "license",
            type="string",
            label="License Type",
            data_provider="get_available_licenses"
        )
        def test_func(context, license):
            pass

        workflow_meta = registry.get_workflow("test_workflow")
        param_meta = workflow_meta.parameters[0]
        assert param_meta.data_provider == "get_available_licenses"

    def test_param_decorator_with_default_value(self, registry):
        """Test param with default value"""
        @workflow(name="test_workflow", description="Test")
        @param(
            "location",
            type="string",
            label="Location",
            default_value="NYC",
            help_text="Office location"
        )
        def test_func(context, location="NYC"):
            pass

        workflow_meta = registry.get_workflow("test_workflow")
        param_meta = workflow_meta.parameters[0]
        assert param_meta.default_value == "NYC"
        assert param_meta.help_text == "Office location"

    def test_param_decorator_label_auto_generated(self, registry):
        """Test that label is auto-generated from parameter name"""
        @workflow(name="test_workflow", description="Test")
        @param("first_name", type="string", required=True)
        def test_func(context, first_name):
            pass

        workflow_meta = registry.get_workflow("test_workflow")
        param_meta = workflow_meta.parameters[0]
        assert param_meta.label == "First Name"  # Auto-generated from "first_name"

    def test_param_decorator_without_workflow_no_registration(self, registry):
        """Test that @param without @workflow doesn't register workflow"""
        @param("email", type="email")
        def test_func(context, email):
            return email

        # Function should still work
        result = test_func(None, "test@example.com")
        assert result == "test@example.com"

        # But no workflow should be registered
        assert registry.get_workflow_count() == 0

        # Pending parameters should be stored on function
        assert hasattr(test_func, '_pending_parameters')
        assert len(test_func._pending_parameters) == 1

    def test_param_decorator_invalid_type_raises_error(self):
        """Test that invalid parameter type raises error"""
        with pytest.raises(ValueError, match="Invalid parameter type"):
            @workflow(name="test_workflow", description="Test")
            @param("test", type="invalid_type")
            def test_func(context, test):
                pass

    def test_param_decorator_all_valid_types(self, registry):
        """Test all valid parameter types"""
        for param_type in VALID_PARAM_TYPES:
            registry.clear_all()

            @workflow(name=f"test_{param_type}", description="Test")
            @param("test_param", type=param_type)
            def test_func(context, test_param):
                pass

            workflow_meta = registry.get_workflow(f"test_{param_type}")
            assert workflow_meta.parameters[0].type == param_type


class TestDataProviderDecorator:
    """Test @data_provider decorator"""

    def test_data_provider_decorator_basic(self, registry):
        """Test basic data provider decorator"""
        @data_provider(
            name="get_licenses",
            description="Returns available licenses"
        )
        def get_licenses(context):
            return [{"label": "E5", "value": "SPE_E5"}]

        # Verify provider is registered
        assert registry.has_data_provider("get_licenses")

        # Verify function still works
        result = get_licenses(None)
        assert result == [{"label": "E5", "value": "SPE_E5"}]

        # Verify metadata
        provider_meta = registry.get_data_provider("get_licenses")
        assert provider_meta.name == "get_licenses"
        assert provider_meta.description == "Returns available licenses"
        assert provider_meta.category == "General"
        assert provider_meta.cache_ttl_seconds == 300

    def test_data_provider_decorator_full_options(self, registry):
        """Test data provider with all options"""
        @data_provider(
            name="get_available_licenses",
            description="Returns available M365 licenses",
            category="m365",
            cache_ttl_seconds=600
        )
        def get_available_licenses(context):
            return []

        provider_meta = registry.get_data_provider("get_available_licenses")
        assert provider_meta.category == "m365"
        assert provider_meta.cache_ttl_seconds == 600

    def test_data_provider_function_metadata_preserved(self, registry):
        """Test that function metadata is preserved"""
        @data_provider(
            name="test_provider",
            description="Test"
        )
        def test_func(context):
            """Original docstring"""
            return []

        assert hasattr(test_func, '_data_provider_metadata')
        assert test_func.__name__ == "test_func"
        assert test_func.__doc__ == "Original docstring"


class TestDecoratorIntegration:
    """Test decorators working together"""

    def test_workflow_with_params_and_data_provider(self, registry):
        """Test complete workflow with params using data provider"""
        # First register data provider
        @data_provider(
            name="get_available_licenses",
            description="Get licenses",
            category="m365"
        )
        def get_licenses(context):
            return [
                {"label": "E5", "value": "SPE_E5"},
                {"label": "E3", "value": "SPE_E3"}
            ]

        # Then register workflow that uses it
        @workflow(
            name="user_onboarding",
            description="Onboard user",
            category="user_management",
            tags=["m365"]
        )
        @param("first_name", type="string", label="First Name", required=True)
        @param("last_name", type="string", label="Last Name", required=True)
        @param("email", type="email", label="Email", required=True,
               validation={"pattern": r"^[a-zA-Z0-9._%+-]+@"})
        @param("license", type="string", label="License",
               data_provider="get_available_licenses")
        def onboard_user(context, first_name, last_name, email, license):
            return f"Created {email} with {license}"

        # Verify workflow registered
        workflow_meta = registry.get_workflow("user_onboarding")
        assert len(workflow_meta.parameters) == 4

        # Verify data provider registered
        provider_meta = registry.get_data_provider("get_available_licenses")
        assert provider_meta is not None

        # Verify parameter links to provider
        license_param = next(p for p in workflow_meta.parameters if p.name == "license")
        assert license_param.data_provider == "get_available_licenses"

        # Verify both functions still work
        licenses = get_licenses(None)
        assert len(licenses) == 2

        result = onboard_user(None, "John", "Doe", "john@example.com", "SPE_E5")
        assert "john@example.com" in result

    def test_multiple_workflows_in_registry(self, registry):
        """Test multiple workflows can coexist"""
        @workflow(name="workflow1", description="First")
        @param("param1", type="string")
        def func1(context, param1):
            pass

        @workflow(name="workflow2", description="Second")
        @param("param2", type="int")
        def func2(context, param2):
            pass

        assert registry.get_workflow_count() == 2
        assert registry.has_workflow("workflow1")
        assert registry.has_workflow("workflow2")

        # Verify each has correct params
        w1 = registry.get_workflow("workflow1")
        w2 = registry.get_workflow("workflow2")

        assert w1.parameters[0].name == "param1"
        assert w2.parameters[0].name == "param2"
