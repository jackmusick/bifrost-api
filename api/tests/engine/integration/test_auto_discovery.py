"""
Integration tests for workflow auto-discovery
Tests that workflows are automatically discovered and registered
"""

import pytest
from shared.registry import get_registry


# Import workspace modules to trigger auto-discovery
import sys
import importlib.util
from pathlib import Path

# Manually trigger workspace discovery for tests
workspace_path = Path(__file__).parent.parent.parent.parent / "workspace"
if workspace_path.exists():
    for py_file in workspace_path.rglob("*.py"):
        if py_file.name.startswith("_"):
            continue

        relative_path = py_file.relative_to(workspace_path)
        module_parts = list(relative_path.parts[:-1]) + [py_file.stem]
        module_name = f"workspace.{'.'.join(module_parts)}"

        try:
            spec = importlib.util.spec_from_file_location(module_name, py_file)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                sys.modules[module_name] = module
                spec.loader.exec_module(module)
                print(f"Successfully imported {module_name}")
        except Exception as e:
            print(f"Failed to import {module_name}: {e}")
            pass


class TestAutoDiscovery:
    """Test workflow auto-discovery system"""

    def test_test_workflow_discovered(self):
        """Test that test_workflow is auto-discovered"""
        registry = get_registry()

        # Workflow should be registered
        assert registry.has_workflow("test_workflow")

        # Get workflow metadata
        workflow = registry.get_workflow("test_workflow")
        assert workflow is not None
        assert workflow.name == "test_workflow"
        assert workflow.description == "Simple test workflow for validation"
        assert workflow.category == "testing"
        assert "test" in workflow.tags
        assert "example" in workflow.tags

    def test_test_workflow_parameters(self):
        """Test that test_workflow has correct parameters"""
        registry = get_registry()
        workflow = registry.get_workflow("test_workflow")

        assert len(workflow.parameters) == 2

        # Check parameter names in order
        param_names = [p.name for p in workflow.parameters]
        assert param_names == ["name", "count"]

        # Check name parameter
        name_param = workflow.parameters[0]
        assert name_param.name == "name"
        assert name_param.type == "string"
        assert name_param.label == "Name"
        assert name_param.required is True
        assert name_param.help_text == "Name to greet"

        # Check count parameter with default
        count_param = workflow.parameters[1]
        assert count_param.name == "count"
        assert count_param.type == "int"
        assert count_param.label == "Count"
        assert count_param.required is False
        assert count_param.default_value == 1
        assert count_param.help_text == "Number of times to greet"

    def test_workflow_function_callable(self):
        """Test that discovered workflow function is callable"""
        registry = get_registry()
        workflow = registry.get_workflow("test_workflow")

        # Function should be stored
        assert workflow is not None
        assert workflow.function is not None
        assert callable(workflow.function)

    def test_registry_summary(self):
        """Test registry summary includes discovered workflows"""
        registry = get_registry()
        summary = registry.get_summary()

        assert summary["workflows_count"] >= 1
        assert "test_workflow" in summary["workflows"]
