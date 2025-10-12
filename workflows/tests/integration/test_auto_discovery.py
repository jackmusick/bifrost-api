"""
Integration tests for workflow auto-discovery
Tests that workflows are automatically discovered and registered
"""

import pytest
from shared.registry import get_registry


# Import workflows to trigger auto-discovery
import workflows  # noqa: F401


class TestAutoDiscovery:
    """Test workflow auto-discovery system"""

    def test_user_onboarding_workflow_discovered(self):
        """Test that user_onboarding workflow is auto-discovered"""
        registry = get_registry()

        # Workflow should be registered
        assert registry.has_workflow("user_onboarding")

        # Get workflow metadata
        workflow = registry.get_workflow("user_onboarding")
        assert workflow is not None
        assert workflow.name == "user_onboarding"
        assert workflow.description == "Onboard new Microsoft 365 user with license assignment"
        assert workflow.category == "user_management"
        assert "m365" in workflow.tags
        assert "user" in workflow.tags

    def test_user_onboarding_parameters(self):
        """Test that user_onboarding has correct parameters"""
        registry = get_registry()
        workflow = registry.get_workflow("user_onboarding")

        assert len(workflow.parameters) == 5

        # Check parameter names in order
        param_names = [p.name for p in workflow.parameters]
        assert param_names == ["first_name", "last_name", "email", "license", "department"]

        # Check first_name parameter
        first_name = workflow.parameters[0]
        assert first_name.name == "first_name"
        assert first_name.type == "string"
        assert first_name.label == "First Name"
        assert first_name.required is True

        # Check email parameter with validation
        email = workflow.parameters[2]
        assert email.name == "email"
        assert email.type == "email"
        assert email.required is True
        assert email.validation is not None
        assert "pattern" in email.validation

        # Check license parameter with data provider
        license_param = workflow.parameters[3]
        assert license_param.name == "license"
        assert license_param.data_provider == "get_available_licenses"
        assert license_param.required is True

        # Check department parameter with default
        department = workflow.parameters[4]
        assert department.name == "department"
        assert department.required is False
        assert department.default_value == ""

    def test_workflow_function_callable(self):
        """Test that discovered workflow function is callable"""
        registry = get_registry()
        workflow = registry.get_workflow("user_onboarding")

        # Function should be stored
        assert workflow.function is not None
        assert callable(workflow.function)

    def test_registry_summary(self):
        """Test registry summary includes discovered workflows"""
        registry = get_registry()
        summary = registry.get_summary()

        assert summary["workflows_count"] >= 1
        assert "user_onboarding" in summary["workflows"]
