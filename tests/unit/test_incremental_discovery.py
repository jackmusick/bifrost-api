"""
Unit tests for incremental discovery feature
Tests the reload_file query parameter for GET /api/workflows
"""

import pytest
from pathlib import Path
from shared.registry import get_registry


class TestRegistryRemoveMethods:
    """Test registry removal methods"""

    def test_remove_workflow_by_name(self):
        """Test removing a workflow by name"""
        from shared.registry import WorkflowMetadata

        registry = get_registry()
        registry.clear_all()

        # Register a workflow
        metadata = WorkflowMetadata(
            name="test_workflow",
            description="Test workflow",
            source_file_path="/test/workflow.py"
        )
        registry.register_workflow(metadata)

        assert registry.has_workflow("test_workflow")

        # Remove it
        result = registry.remove_workflow("test_workflow")
        assert result is True
        assert not registry.has_workflow("test_workflow")

        # Try removing non-existent workflow
        result = registry.remove_workflow("nonexistent")
        assert result is False

    def test_remove_workflows_by_file_path(self):
        """Test removing workflows by file path"""
        from shared.registry import WorkflowMetadata

        registry = get_registry()
        registry.clear_all()

        # Register multiple workflows from same file
        metadata1 = WorkflowMetadata(
            name="workflow_1",
            description="First workflow",
            source_file_path="/test/multi_workflow.py"
        )
        metadata2 = WorkflowMetadata(
            name="workflow_2",
            description="Second workflow",
            source_file_path="/test/multi_workflow.py"
        )
        metadata3 = WorkflowMetadata(
            name="workflow_3",
            description="Third workflow",
            source_file_path="/test/other_workflow.py"
        )

        registry.register_workflow(metadata1)
        registry.register_workflow(metadata2)
        registry.register_workflow(metadata3)

        assert registry.get_workflow_count() == 3

        # Remove workflows from first file
        removed = registry.remove_workflows_by_file_path("/test/multi_workflow.py")
        assert len(removed) == 2
        assert "workflow_1" in removed
        assert "workflow_2" in removed
        assert registry.get_workflow_count() == 1
        assert registry.has_workflow("workflow_3")

        # Try removing non-existent file path
        removed = registry.remove_workflows_by_file_path("/test/nonexistent.py")
        assert len(removed) == 0


class TestValidationEndpointFix:
    """Test validation endpoint fix for source_file_path checking"""

    @pytest.mark.asyncio
    async def test_validation_detects_decorator_by_file_path(self):
        """Test that validation checks source_file_path instead of count"""
        import tempfile
        from shared.handlers.workflows_handlers import validate_workflow_file
        from shared.registry import get_registry

        registry = get_registry()
        registry.clear_all()

        # Create a valid workflow file
        workflow_code = '''
from shared.decorators import workflow

@workflow(
    name="test_validation_workflow",
    description="Test workflow for validation"
)
async def test_validation_workflow(context):
    return "success"
'''

        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(workflow_code)
            temp_path = f.name

        try:
            # First validation - workflow not in registry
            result1 = await validate_workflow_file(path=temp_path, content=workflow_code)
            assert result1.valid is True, f"First validation should pass, got issues: {result1.issues}"

            # Second validation - workflow now in registry (should still pass)
            result2 = await validate_workflow_file(path=temp_path, content=workflow_code)
            assert result2.valid is True, f"Second validation should pass (re-validation), got issues: {result2.issues}"

        finally:
            Path(temp_path).unlink(missing_ok=True)
            registry.clear_all()

    @pytest.mark.asyncio
    async def test_validation_detects_missing_decorator(self):
        """Test that validation correctly reports missing decorator"""
        import tempfile
        from shared.handlers.workflows_handlers import validate_workflow_file
        from shared.registry import get_registry

        registry = get_registry()
        registry.clear_all()

        # Create a file without @workflow decorator
        code_without_decorator = '''
async def my_function(context):
    return "no decorator"
'''

        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code_without_decorator)
            temp_path = f.name

        try:
            result = await validate_workflow_file(path=temp_path, content=code_without_decorator)
            assert result.valid is False
            assert any("No @workflow decorator found" in issue.message for issue in result.issues)

        finally:
            Path(temp_path).unlink(missing_ok=True)
            registry.clear_all()
