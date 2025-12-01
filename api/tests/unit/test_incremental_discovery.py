"""
Unit tests for dynamic discovery feature.
Tests the dynamic discovery system for workflows.
"""

import pytest


class TestValidationWithDynamicDiscovery:
    """Test validation endpoint with dynamic discovery"""

    @pytest.mark.asyncio
    async def test_validation_detects_decorator_by_file_path(self, tmp_path, monkeypatch):
        """Test that validation checks source_file_path for decorator"""
        from shared.handlers.workflows_handlers import validate_workflow_file

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

        temp_path = tmp_path / "test_workflow.py"
        temp_path.write_text(workflow_code)
        monkeypatch.setenv("BIFROST_WORKSPACE_LOCATION", str(tmp_path))

        try:
            # First validation - workflow discovered dynamically
            result1 = await validate_workflow_file(path=str(temp_path), content=workflow_code)
            assert result1.valid is True, f"First validation should pass, got issues: {result1.issues}"

            # Second validation - should still pass (dynamic discovery)
            result2 = await validate_workflow_file(path=str(temp_path), content=workflow_code)
            assert result2.valid is True, f"Second validation should pass, got issues: {result2.issues}"

        finally:
            pass  # tmp_path cleanup is automatic

    @pytest.mark.asyncio
    async def test_validation_detects_missing_decorator(self, tmp_path, monkeypatch):
        """Test that validation correctly reports missing decorator"""
        from shared.handlers.workflows_handlers import validate_workflow_file

        # Create a file without @workflow decorator
        code_without_decorator = '''
async def my_function(context):
    return "no decorator"
'''

        temp_path = tmp_path / "no_decorator.py"
        temp_path.write_text(code_without_decorator)
        monkeypatch.setenv("BIFROST_WORKSPACE_LOCATION", str(tmp_path))

        try:
            result = await validate_workflow_file(path=str(temp_path), content=code_without_decorator)
            assert result.valid is False
            assert any("No @workflow decorator found" in issue.message for issue in result.issues)

        finally:
            pass  # tmp_path cleanup is automatic


class TestDynamicDiscoveryBehavior:
    """Test dynamic discovery behavior"""

    def test_workflow_discovered_after_creation(self, tmp_path, monkeypatch):
        """Test that workflows are discovered after file creation"""
        from shared.discovery import scan_all_workflows

        monkeypatch.setenv("BIFROST_WORKSPACE_LOCATION", str(tmp_path))

        # Initially empty
        workflows_before = scan_all_workflows()
        workspace_workflows = [w for w in workflows_before if str(tmp_path) in (w.source_file_path or "")]
        assert len(workspace_workflows) == 0

        # Create a workflow file
        workflow_code = '''
from shared.decorators import workflow

@workflow(
    name="dynamic_workflow",
    description="Dynamically discovered workflow"
)
async def dynamic_workflow(context):
    return "discovered"
'''
        workflow_path = tmp_path / "dynamic_workflow.py"
        workflow_path.write_text(workflow_code)

        # Should be discovered in next scan
        workflows_after = scan_all_workflows()
        workspace_workflows = [w for w in workflows_after if str(tmp_path) in (w.source_file_path or "")]
        assert len(workspace_workflows) == 1
        assert workspace_workflows[0].name == "dynamic_workflow"

    def test_workflow_changes_detected(self, tmp_path, monkeypatch):
        """Test that workflow changes are detected on rescan"""
        from shared.discovery import scan_all_workflows

        monkeypatch.setenv("BIFROST_WORKSPACE_LOCATION", str(tmp_path))

        # Create initial workflow
        workflow_code_v1 = '''
from shared.decorators import workflow

@workflow(
    name="changing_workflow",
    description="Version 1"
)
async def changing_workflow(context):
    return "v1"
'''
        workflow_path = tmp_path / "changing_workflow.py"
        workflow_path.write_text(workflow_code_v1)

        workflows = scan_all_workflows()
        workflow = next((w for w in workflows if w.name == "changing_workflow"), None)
        assert workflow is not None
        assert workflow.description == "Version 1"

        # Update workflow
        workflow_code_v2 = '''
from shared.decorators import workflow

@workflow(
    name="changing_workflow",
    description="Version 2 with changes"
)
async def changing_workflow(context):
    return "v2"
'''
        workflow_path.write_text(workflow_code_v2)

        # Rescan should detect change
        workflows = scan_all_workflows()
        workflow = next((w for w in workflows if w.name == "changing_workflow"), None)
        assert workflow is not None
        assert workflow.description == "Version 2 with changes"
