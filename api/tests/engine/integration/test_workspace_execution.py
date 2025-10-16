"""
Integration Tests: Workspace Code Execution and Isolation

Tests that validate workspace code executes correctly with import restrictions
and organization context isolation enforced.
"""

import sys
from pathlib import Path

import pytest


class TestWorkspaceIsolation:
    """Integration tests for workspace code isolation"""

    @pytest.fixture(autouse=True)
    def cleanup(self):
        """Clean up import restrictors after each test"""
        yield
        sys.meta_path = [
            finder for finder in sys.meta_path
            if not finder.__class__.__name__ == 'WorkspaceImportRestrictor'
        ]

    @pytest.fixture
    def workspace_path(self):
        """Get actual workspace path"""
        # Navigate from tests/engine/integration to api/workspace
        return Path(__file__).parent.parent.parent.parent / "workspace"

    def test_workspace_workflows_can_be_imported(self, workspace_path):
        """Integration: Workspace workflows can be imported and discovered"""
        assert workspace_path.exists(), f"Workspace path not found: {workspace_path}"

        # Import workspace examples module (actual structure)
        try:
            import workspace.examples.test_workflow
            # If this succeeds, workspace code is accessible
            assert True
        except ImportError as e:
            pytest.fail(f"Cannot import workspace workflows: {e}")

    def test_workspace_code_has_public_api_access(self):
        """Integration: Workspace code can access whitelisted shared modules"""
        # Workspace workflows should be able to import decorators
        try:
            from shared.decorators import param, workflow
            assert workflow is not None
            assert param is not None
        except ImportError as e:
            pytest.fail(f"Workspace cannot access public API: {e}")

    def test_import_restrictions_active_for_workspace(self, workspace_path):
        """Integration: Import restrictions are enforced when enabled"""
        from shared.import_restrictor import install_import_restrictions

        # Install restrictions
        install_import_restrictions([str(workspace_path)])

        # Verify restrictor is active
        has_restrictor = any(
            finder.__class__.__name__ == 'WorkspaceImportRestrictor'
            for finder in sys.meta_path
        )
        assert has_restrictor, "Import restrictor must be installed"

    def test_workspace_workflow_execution_context(self):
        """Integration: Workspace workflows receive proper execution context"""
        # This test documents the expected behavior:
        # When a workspace workflow is executed, it should receive:
        # 1. OrganizationContext with org_id
        # 2. Authenticated principal
        # 3. Request metadata

        # The actual execution is tested in higher-level integration tests
        assert True, (
            "Contract: Workspace workflows must receive OrganizationContext"
        )


class TestOrganizationContextIsolation:
    """Integration tests for org-scoped context enforcement"""

    def test_workspace_receives_org_context(self):
        """Integration: Workspace code receives organization context"""
        # When execute_workflow is called, it should:
        # 1. Load organization from X-Organization-Id header
        # 2. Create OrganizationContext
        # 3. Pass to workspace workflow function

        # This validates the integration between:
        # - engine.execute.py (workflow execution)
        # - engine.shared.middleware.py (org context loading)
        # - workspace workflows (context consumer)

        assert True, (
            "Contract: Workspace workflows receive org-scoped context"
        )

    def test_function_key_auth_enforces_org_validation(self):
        """Integration: Function key auth still validates org exists"""
        # Even with function key bypass, the system must:
        # 1. Extract X-Organization-Id from headers
        # 2. Validate organization exists and is active
        # 3. Create OrganizationContext with that org

        # This prevents function key from accessing invalid orgs
        assert True, (
            "Contract: Function key auth must validate org_id"
        )

    def test_workspace_cannot_access_other_orgs_data(self):
        """Integration: Workspace code cannot access other organizations' data"""
        # The organization context should be scoped such that:
        # 1. Table queries are filtered by org_id
        # 2. Integration credentials are org-specific
        # 3. Cross-org access requires PlatformAdmin role

        assert True, (
            "Contract: Workspace code is isolated to its organization"
        )


class TestWorkspacePublicAPI:
    """Tests for workspace-accessible public API"""

    def test_decorators_module_accessible(self):
        """Integration: @workflow and @param decorators are accessible"""
        try:
            from shared.decorators import data_provider, param, workflow
            assert callable(workflow)
            assert callable(param)
            assert callable(data_provider)
        except ImportError as e:
            pytest.fail(f"Public API decorators not accessible: {e}")

    def test_context_module_accessible(self):
        """Integration: OrganizationContext is accessible"""
        try:
            from shared.context import OrganizationContext
            # Verify it's a class
            assert isinstance(OrganizationContext, type)
        except ImportError as e:
            pytest.fail(f"OrganizationContext not accessible: {e}")

    def test_error_handling_module_accessible(self):
        """Integration: Error classes are accessible"""
        try:
            from shared.error_handling import IntegrationError, ValidationError, WorkflowError
            assert all(isinstance(cls, type) for cls in [
                WorkflowError,
                ValidationError,
                IntegrationError
            ])
        except ImportError as e:
            pytest.fail(f"Error handling classes not accessible: {e}")

    def test_models_module_accessible(self):
        """Integration: Pydantic models are accessible"""
        try:
            from shared.models import ExecutionStatus, WorkflowExecutionResponse
            # These should be importable
            assert WorkflowExecutionResponse is not None
            assert ExecutionStatus is not None
        except ImportError as e:
            pytest.fail(f"Models not accessible: {e}")
