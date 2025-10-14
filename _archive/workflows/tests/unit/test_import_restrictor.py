"""
Unit Tests: Import Restrictor (T060)

Tests the WorkspaceImportRestrictor class in isolation:
- Blocked prefix detection
- Whitelist handling
- Workspace path detection
- Stack inspection logic
- Error message generation
"""

import pytest
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from importlib.machinery import ModuleSpec


class TestWorkspaceImportRestrictor:
    """Unit tests for WorkspaceImportRestrictor"""

    @pytest.fixture
    def temp_workspace(self):
        """Create temporary workspace directory"""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace_path = os.path.join(tmpdir, "workspace")
            os.makedirs(workspace_path)
            yield workspace_path

    @pytest.fixture
    def restrictor(self, temp_workspace):
        """Create restrictor instance with temp workspace"""
        from engine.shared.import_restrictor import WorkspaceImportRestrictor
        return WorkspaceImportRestrictor([temp_workspace])

    def test_blocked_prefix_engine(self, restrictor):
        """Test that 'engine.' prefix is blocked"""
        assert restrictor._is_blocked_import('engine.shared.storage')
        assert restrictor._is_blocked_import('engine.execute')
        assert restrictor._is_blocked_import('engine.functions.api')

    def test_blocked_prefix_shared(self, restrictor):
        """Test that 'shared.' prefix is blocked"""
        assert restrictor._is_blocked_import('shared.storage')
        assert restrictor._is_blocked_import('shared.middleware')

    def test_not_blocked_other_modules(self, restrictor):
        """Test that other modules are not blocked"""
        assert not restrictor._is_blocked_import('azure.functions')
        assert not restrictor._is_blocked_import('pydantic')
        assert not restrictor._is_blocked_import('json')
        assert not restrictor._is_blocked_import('os')

    def test_allowed_exports_decorators(self, restrictor):
        """Test that engine.shared.decorators is whitelisted"""
        assert 'engine.shared.decorators' in restrictor.ALLOWED_SHARED_EXPORTS

    def test_allowed_exports_context(self, restrictor):
        """Test that engine.shared.context is whitelisted"""
        assert 'engine.shared.context' in restrictor.ALLOWED_SHARED_EXPORTS

    def test_allowed_exports_error_handling(self, restrictor):
        """Test that engine.shared.error_handling is whitelisted"""
        assert 'engine.shared.error_handling' in restrictor.ALLOWED_SHARED_EXPORTS

    def test_allowed_exports_models(self, restrictor):
        """Test that engine.shared.models is whitelisted"""
        assert 'engine.shared.models' in restrictor.ALLOWED_SHARED_EXPORTS

    def test_allowed_exports_registry(self, restrictor):
        """Test that engine.shared.registry is whitelisted (internal dependency)"""
        assert 'engine.shared.registry' in restrictor.ALLOWED_SHARED_EXPORTS

    def test_workspace_path_validation_absolute(self, temp_workspace):
        """Test that workspace paths must be absolute"""
        from engine.shared.import_restrictor import WorkspaceImportRestrictor

        # Absolute path should work
        restrictor = WorkspaceImportRestrictor([temp_workspace])
        assert len(restrictor.workspace_paths) == 1

        # Relative path should raise ValueError
        with pytest.raises(ValueError, match="must be absolute"):
            WorkspaceImportRestrictor(['relative/path'])

    def test_workspace_path_normalization(self, temp_workspace):
        """Test that workspace paths are normalized"""
        from engine.shared.import_restrictor import WorkspaceImportRestrictor

        # Path with trailing slash
        path_with_slash = temp_workspace + "/"
        restrictor = WorkspaceImportRestrictor([path_with_slash])

        # Should be normalized (no trailing slash)
        assert restrictor.workspace_paths[0] == os.path.normpath(temp_workspace)

    def test_is_workspace_code_inside_workspace(self, restrictor, temp_workspace):
        """Test detection of files inside workspace"""
        test_file = os.path.join(temp_workspace, "test_workflow.py")

        assert restrictor._is_workspace_code(test_file)

    def test_is_workspace_code_outside_workspace(self, restrictor, temp_workspace):
        """Test detection of files outside workspace"""
        # File outside workspace
        outside_file = "/tmp/other_file.py"

        assert not restrictor._is_workspace_code(outside_file)

    def test_is_workspace_code_nested_directory(self, restrictor, temp_workspace):
        """Test detection in nested workspace directory"""
        nested_file = os.path.join(temp_workspace, "subdir", "nested_workflow.py")

        assert restrictor._is_workspace_code(nested_file)

    def test_find_spec_allowed_module(self, restrictor):
        """Test that non-blocked modules return None (allow import)"""
        result = restrictor.find_spec('json')
        assert result is None  # None means allow import

    def test_find_spec_whitelisted_module(self, restrictor):
        """Test that whitelisted modules return None (allow import)"""
        result = restrictor.find_spec('engine.shared.decorators')
        assert result is None  # Whitelisted, allow

    @patch('engine.shared.import_restrictor.inspect.stack')
    def test_find_spec_blocked_from_non_workspace(self, mock_stack, restrictor):
        """Test that blocked imports from non-workspace code are allowed"""
        # Mock stack to show caller from engine (not workspace)
        mock_frame = Mock()
        mock_frame.filename = "/path/to/engine/execute.py"
        mock_stack.return_value = [mock_frame]

        result = restrictor.find_spec('engine.shared.storage')
        assert result is None  # Allow because not from workspace

    @patch('engine.shared.import_restrictor.inspect.stack')
    def test_find_spec_blocked_from_workspace(self, mock_stack, restrictor, temp_workspace):
        """Test that blocked imports from workspace code raise ImportError"""
        # Mock stack to show caller from workspace
        mock_frame = Mock()
        mock_frame.filename = os.path.join(temp_workspace, "my_workflow.py")
        mock_frame.lineno = 10
        mock_stack.return_value = [mock_frame]

        with pytest.raises(ImportError, match="Workspace code cannot import"):
            restrictor.find_spec('engine.shared.storage')

    @patch('engine.shared.import_restrictor.inspect.stack')
    def test_error_message_contains_blocked_module(self, mock_stack, restrictor, temp_workspace):
        """Test that error message includes blocked module name"""
        mock_frame = Mock()
        mock_frame.filename = os.path.join(temp_workspace, "workflow.py")
        mock_stack.return_value = [mock_frame]

        with pytest.raises(ImportError, match="engine.shared.storage"):
            restrictor.find_spec('engine.shared.storage')

    @patch('engine.shared.import_restrictor.inspect.stack')
    def test_error_message_contains_public_api_guidance(self, mock_stack, restrictor, temp_workspace):
        """Test that error message directs to public API"""
        mock_frame = Mock()
        mock_frame.filename = os.path.join(temp_workspace, "workflow.py")
        mock_stack.return_value = [mock_frame]

        with pytest.raises(ImportError, match="public API"):
            restrictor.find_spec('engine.shared.storage')

    @patch('engine.shared.import_restrictor.inspect.stack')
    def test_error_message_lists_allowed_imports(self, mock_stack, restrictor, temp_workspace):
        """Test that error message lists allowed imports"""
        mock_frame = Mock()
        mock_frame.filename = os.path.join(temp_workspace, "workflow.py")
        mock_stack.return_value = [mock_frame]

        with pytest.raises(ImportError, match="engine.shared.decorators"):
            restrictor.find_spec('engine.shared.storage')

    @patch('engine.shared.import_restrictor.inspect.stack')
    def test_error_message_includes_source_file(self, mock_stack, restrictor, temp_workspace):
        """Test that error message includes workspace file that attempted import"""
        workspace_file = os.path.join(temp_workspace, "my_workflow.py")
        mock_frame = Mock()
        mock_frame.filename = workspace_file
        mock_stack.return_value = [mock_frame]

        with pytest.raises(ImportError, match=workspace_file):
            restrictor.find_spec('engine.shared.storage')

    def test_install_import_restrictions(self, temp_workspace):
        """Test install_import_restrictions() adds to sys.meta_path"""
        from engine.shared.import_restrictor import (
            install_import_restrictions,
            remove_import_restrictions,
            get_active_restrictors
        )

        # Clean slate
        remove_import_restrictions()
        assert len(get_active_restrictors()) == 0

        # Install
        install_import_restrictions([temp_workspace])

        # Verify installed
        restrictors = get_active_restrictors()
        assert len(restrictors) == 1
        assert restrictors[0].workspace_paths == [os.path.normpath(temp_workspace)]

        # Cleanup
        remove_import_restrictions()

    def test_remove_import_restrictions(self, temp_workspace):
        """Test remove_import_restrictions() clears sys.meta_path"""
        from engine.shared.import_restrictor import (
            install_import_restrictions,
            remove_import_restrictions,
            get_active_restrictors
        )

        # Install
        install_import_restrictions([temp_workspace])
        assert len(get_active_restrictors()) > 0

        # Remove
        remove_import_restrictions()
        assert len(get_active_restrictors()) == 0

    def test_multiple_workspace_paths(self):
        """Test restrictor with multiple workspace paths"""
        from engine.shared.import_restrictor import WorkspaceImportRestrictor

        with tempfile.TemporaryDirectory() as tmpdir:
            workspace1 = os.path.join(tmpdir, "workspace1")
            workspace2 = os.path.join(tmpdir, "workspace2")
            os.makedirs(workspace1)
            os.makedirs(workspace2)

            restrictor = WorkspaceImportRestrictor([workspace1, workspace2])

            # Files in both workspaces should be detected
            assert restrictor._is_workspace_code(os.path.join(workspace1, "file.py"))
            assert restrictor._is_workspace_code(os.path.join(workspace2, "file.py"))

    def test_empty_workspace_paths_raises_error(self):
        """Test that empty workspace paths list raises ValueError"""
        from engine.shared.import_restrictor import install_import_restrictions

        with pytest.raises(ValueError, match="At least one workspace path"):
            install_import_restrictions([])

    @patch('engine.shared.import_restrictor.inspect.stack')
    def test_stack_inspection_finds_workspace_in_nested_calls(self, mock_stack, restrictor, temp_workspace):
        """Test that stack inspection finds workspace code in nested call stack"""
        # Mock stack with multiple frames, workspace code deeper in stack
        mock_frame1 = Mock()
        mock_frame1.filename = "/usr/lib/python3.11/importlib.py"  # System code

        mock_frame2 = Mock()
        mock_frame2.filename = os.path.join(temp_workspace, "my_workflow.py")  # Workspace!

        mock_frame3 = Mock()
        mock_frame3.filename = "/path/to/engine/execute.py"  # Engine code

        mock_stack.return_value = [mock_frame1, mock_frame2, mock_frame3]

        # Should detect workspace code in frame 2
        assert restrictor._is_caller_workspace_code()

    @patch('engine.shared.import_restrictor.inspect.stack')
    def test_stack_inspection_no_workspace_in_stack(self, mock_stack, restrictor):
        """Test that stack inspection returns False when no workspace code"""
        # Mock stack with only non-workspace frames
        mock_frame1 = Mock()
        mock_frame1.filename = "/usr/lib/python3.11/importlib.py"

        mock_frame2 = Mock()
        mock_frame2.filename = "/path/to/engine/execute.py"

        mock_stack.return_value = [mock_frame1, mock_frame2]

        # Should not detect workspace code
        assert not restrictor._is_caller_workspace_code()

    def test_audit_logging_on_violation(self, restrictor, temp_workspace):
        """Test that import violations are logged to audit system"""
        from unittest.mock import AsyncMock

        with patch('engine.shared.import_restrictor.inspect.stack') as mock_stack:
            # Mock workspace caller
            mock_frame = Mock()
            mock_frame.filename = os.path.join(temp_workspace, "workflow.py")
            mock_frame.lineno = 15
            mock_stack.return_value = [mock_frame]

            # Mock audit logger
            with patch('engine.shared.import_restrictor.logger') as mock_logger:
                with pytest.raises(ImportError):
                    restrictor.find_spec('engine.shared.storage')

                # Verify logging occurred
                mock_logger.warning.assert_called()
                call_args = mock_logger.warning.call_args
                assert 'Import restriction violated' in call_args[0][0]
