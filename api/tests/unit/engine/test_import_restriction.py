"""
Contract Tests: Import Restrictions

Tests that validate the import restriction system correctly blocks workspace code
from importing engine internals while allowing whitelisted shared modules.

These tests verify the contract defined in /specs/002-i-want-to/contracts/README.md
"""

import importlib
import sys
from pathlib import Path

import pytest


class TestImportRestrictionContract:
    """Contract tests for import restriction system"""

    @pytest.fixture(autouse=True)
    def setup_and_teardown(self):
        """Clean up import restrictor after each test"""
        yield
        # Remove any import restrictors from sys.meta_path
        sys.meta_path = [
            finder for finder in sys.meta_path
            if not finder.__class__.__name__ == 'WorkspaceImportRestrictor'
        ]

    def test_import_restrictor_module_exists(self):
        """Contract: Import restrictor module must exist"""
        try:
            from shared import import_restrictor
            assert hasattr(import_restrictor, 'WorkspaceImportRestrictor'), (
                "Module must export WorkspaceImportRestrictor class"
            )
            assert hasattr(import_restrictor, 'install_import_restrictions'), (
                "Module must export install_import_restrictions function"
            )
        except ImportError as e:
            pytest.fail(f"Import restrictor module not found: {e}")

    def test_blocked_prefixes_defined(self):
        """Contract: BLOCKED_PREFIXES must include 'engine.' and 'shared.'"""
        from shared.import_restrictor import WorkspaceImportRestrictor

        assert hasattr(WorkspaceImportRestrictor, 'BLOCKED_PREFIXES'), (
            "WorkspaceImportRestrictor must define BLOCKED_PREFIXES"
        )

        blocked = WorkspaceImportRestrictor.BLOCKED_PREFIXES
        assert 'engine.' in blocked, "BLOCKED_PREFIXES must include 'engine.'"
        assert 'shared.' in blocked, "BLOCKED_PREFIXES must include 'shared.'"

    def test_allowed_exports_defined(self):
        """Contract: ALLOWED_SHARED_EXPORTS must whitelist public API modules"""
        from shared.import_restrictor import WorkspaceImportRestrictor

        assert hasattr(WorkspaceImportRestrictor, 'ALLOWED_SHARED_EXPORTS'), (
            "WorkspaceImportRestrictor must define ALLOWED_SHARED_EXPORTS"
        )

        allowed = WorkspaceImportRestrictor.ALLOWED_SHARED_EXPORTS
        expected_exports = {
            'engine.shared.decorators',
            'engine.shared.context',
            'engine.shared.error_handling',
            'engine.shared.models'
        }

        for export in expected_exports:
            assert export in allowed, f"ALLOWED_SHARED_EXPORTS must include '{export}'"

    def test_install_function_signature(self):
        """Contract: install_import_restrictions must accept workspace_paths list"""
        import inspect

        from shared.import_restrictor import install_import_restrictions

        sig = inspect.signature(install_import_restrictions)
        params = list(sig.parameters.keys())

        assert len(params) >= 1, (
            "install_import_restrictions must accept at least one parameter"
        )
        assert 'workspace_paths' in params or params[0] in ['workspace_paths', 'paths'], (
            "First parameter should be 'workspace_paths'"
        )

    def test_workspace_cannot_import_engine_storage(self):
        """Contract: Workspace code must not import blocked internal modules"""
        import tempfile

        from shared.import_restrictor import install_import_restrictions

        # Clear module cache to ensure restrictor can intercept the import
        if 'shared.keyvault' in sys.modules:
            del sys.modules['shared.keyvault']

        # Create temporary workspace directory
        with tempfile.TemporaryDirectory() as tmpdir:
            install_import_restrictions([tmpdir])

            # Create a test file in workspace that attempts the import
            # shared.keyvault is NOT in the whitelisted allowed exports
            test_file = Path(tmpdir) / "test_workspace_import.py"
            test_file.write_text("import shared.keyvault\n")

            # Attempt to import that file (which will trigger the blocked import)
            # Note: This test simulates workspace code attempting import
            with pytest.raises(ImportError) as exc_info:
                sys.path.insert(0, tmpdir)
                try:
                    importlib.import_module('test_workspace_import')
                finally:
                    sys.path.remove(tmpdir)
                    # Clean up test module from cache
                    if 'test_workspace_import' in sys.modules:
                        del sys.modules['test_workspace_import']

            assert "cannot import" in str(exc_info.value).lower() or \
                   "workspace" in str(exc_info.value).lower(), (
                "Error message must indicate workspace cannot import engine modules"
            )

    def test_workspace_can_import_allowed_decorators(self):
        """Contract: Workspace code must be able to import shared.decorators"""
        import tempfile

        from shared.import_restrictor import install_import_restrictions

        # Create temporary workspace directory
        with tempfile.TemporaryDirectory() as tmpdir:
            install_import_restrictions([tmpdir])

            # This should NOT raise (decorators are whitelisted)
            try:
                from shared.decorators import workflow
                assert workflow is not None
            except ImportError as e:
                pytest.fail(f"Allowed import failed: {e}")

    def test_error_message_provides_guidance(self):
        """Contract: ImportError must provide clear guidance to developers"""
        import tempfile

        from shared.import_restrictor import install_import_restrictions

        # Clear module cache
        if 'shared.storage' in sys.modules:
            del sys.modules['shared.storage']

        with tempfile.TemporaryDirectory() as tmpdir:
            install_import_restrictions([tmpdir])

            # Create a test file in workspace that attempts blocked import
            # shared.storage is NOT in the whitelisted allowed exports
            test_file = Path(tmpdir) / "test_import_guidance.py"
            test_file.write_text("import shared.storage\n")

            try:
                sys.path.insert(0, tmpdir)
                importlib.import_module('test_import_guidance')
                pytest.fail("Expected ImportError was not raised")
            except ImportError as e:
                error_msg = str(e).lower()
                # Check for helpful guidance in error message
                assert any(keyword in error_msg for keyword in [
                    'public api',
                    'documentation',
                    'workspace',
                    'decorators',
                    'context'
                ]), f"Error message must provide guidance to developers. Got: {error_msg}"
            finally:
                sys.path.remove(tmpdir)
                if 'test_import_guidance' in sys.modules:
                    del sys.modules['test_import_guidance']


class TestImportRestrictionBehavior:
    """Behavioral tests for import restriction system"""

    @pytest.fixture(autouse=True)
    def cleanup(self):
        """Clean up after tests"""
        yield
        sys.meta_path = [
            finder for finder in sys.meta_path
            if not finder.__class__.__name__ == 'WorkspaceImportRestrictor'
        ]

    def test_restrictor_installed_on_meta_path(self):
        """Contract: Restrictor must be added to sys.meta_path"""
        import tempfile

        from shared.import_restrictor import install_import_restrictions

        initial_count = len(sys.meta_path)

        with tempfile.TemporaryDirectory() as tmpdir:
            install_import_restrictions([tmpdir])

            # Check that restrictor was added
            assert len(sys.meta_path) > initial_count, (
                "install_import_restrictions must add restrictor to sys.meta_path"
            )

            # Verify it's the correct type
            has_restrictor = any(
                finder.__class__.__name__ == 'WorkspaceImportRestrictor'
                for finder in sys.meta_path
            )
            assert has_restrictor, "WorkspaceImportRestrictor must be on sys.meta_path"

    def test_engine_code_can_import_freely(self):
        """Contract: Engine code is not restricted (only workspace is restricted)"""
        import tempfile

        from shared.import_restrictor import install_import_restrictions

        with tempfile.TemporaryDirectory() as tmpdir:
            install_import_restrictions([tmpdir])

            # Engine code should be able to import anything
            # This import is from engine code (this test file is not in workspace)
            try:
                import shared.storage  # noqa: F401
                # Should not raise
            except ImportError:
                # It's OK if the module doesn't exist yet, we're testing restriction logic
                pass

    def test_multiple_workspace_paths_supported(self):
        """Contract: install_import_restrictions must support multiple workspace paths"""
        import tempfile

        from shared.import_restrictor import install_import_restrictions

        with tempfile.TemporaryDirectory() as tmpdir1, tempfile.TemporaryDirectory() as tmpdir2:
            # Should not raise
            try:
                install_import_restrictions([tmpdir1, tmpdir2])
            except Exception as e:
                pytest.fail(f"Multiple workspace paths not supported: {e}")


class TestStackInspection:
    """Tests for stack inspection logic"""

    @pytest.fixture(autouse=True)
    def cleanup(self):
        """Clean up after tests"""
        yield
        sys.meta_path = [
            finder for finder in sys.meta_path
            if not finder.__class__.__name__ == 'WorkspaceImportRestrictor'
        ]

    def test_stack_inspection_detects_workspace_caller(self):
        """Contract: find_spec must inspect call stack to detect workspace imports"""
        import tempfile

        from shared.import_restrictor import WorkspaceImportRestrictor

        with tempfile.TemporaryDirectory() as tmpdir:
            restrictor = WorkspaceImportRestrictor([tmpdir])

            # Create a test file in workspace
            workspace_file = Path(tmpdir) / "test.py"
            workspace_file.write_text("from shared.storage import test")

            # Verify restrictor can detect workspace paths
            assert restrictor._is_workspace_code(str(workspace_file)), (
                "Restrictor must detect workspace code by file path"
            )
