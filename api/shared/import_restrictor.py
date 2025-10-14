"""
Import Restriction System for Workspace Code Isolation

Prevents workspace code from importing engine internals while allowing
access to whitelisted public API modules.

This module implements a MetaPathFinder that intercepts import statements
and blocks workspace code from importing engine modules, except for explicitly
whitelisted shared exports.

Usage:
    from shared.import_restrictor import install_import_restrictions
    import os

    WORKSPACE_PATH = os.path.join(os.path.dirname(__file__), '..', 'workspace')
    install_import_restrictions([WORKSPACE_PATH])

    # Now workspace code imports are restricted
"""

import sys
import os
import inspect
import logging
from importlib.abc import MetaPathFinder
from importlib.machinery import ModuleSpec
from typing import List, Set, Optional, Any

logger = logging.getLogger(__name__)


class WorkspaceImportRestrictor(MetaPathFinder):
    """
    Meta path finder that blocks workspace code from importing engine modules.

    Blocked prefixes: engine.*, shared.* (except whitelisted exports)
    Allowed exports: engine.shared.decorators, engine.shared.context,
                     engine.shared.error_handling, engine.shared.models
    """

    # T028: Define blocked import prefixes
    BLOCKED_PREFIXES: tuple[str, ...] = ('engine.', 'shared.')

    # T029: Define whitelisted shared exports (public API)
    ALLOWED_SHARED_EXPORTS: Set[str] = {
        'engine.shared.decorators',
        'engine.shared.context',
        'engine.shared.error_handling',
        'engine.shared.models',
        'engine.shared.registry',  # Required by decorators (internal dependency)
        'engine.shared.config_resolver',  # Required by context (internal dependency)
        'engine.shared.keyvault'  # Required by config_resolver (internal dependency)
    }

    def __init__(self, workspace_paths: List[str]) -> None:
        """
        Initialize restrictor with workspace paths.

        Args:
            workspace_paths: List of absolute directory paths considered "workspace code"

        Raises:
            ValueError: If any workspace path is not absolute
        """
        # Validate all paths are absolute
        for path in workspace_paths:
            if not os.path.isabs(path):
                raise ValueError(
                    f"Workspace path must be absolute: {path}. "
                    f"Use os.path.abspath() or Path.resolve()"
                )

        self.workspace_paths = [os.path.normpath(p) for p in workspace_paths]
        logger.info(
            f"Import restrictor initialized with workspace paths: {self.workspace_paths}"
        )

    # T030: Implement find_spec() with stack inspection
    def find_spec(
        self,
        fullname: str,
        path: Optional[Any] = None,
        target: Optional[Any] = None
    ) -> Optional[ModuleSpec]:
        """
        Check if import should be blocked.

        Called automatically by Python's import system.

        Args:
            fullname: Fully qualified module name (e.g., "engine.shared.storage")
            path: Module search path
            target: Target module (optional)

        Returns:
            None: Allow import to proceed (return None, don't block)

        Raises:
            ImportError: If workspace code attempts to import blocked module
        """
        # Check if this is a blocked import
        if not self._is_blocked_import(fullname):
            return None  # Not blocked, allow import

        # Check if this is an allowed whitelisted export
        if fullname in self.ALLOWED_SHARED_EXPORTS:
            return None  # Whitelisted, allow import

        # Inspect call stack to determine if caller is workspace code
        if not self._is_caller_workspace_code():
            return None  # Not from workspace, allow import

        # T031: Blocked import from workspace - raise with clear error message
        self._raise_import_error(fullname)

    def _is_blocked_import(self, module_name: str) -> bool:
        """Check if module name matches blocked prefixes"""
        return any(module_name.startswith(prefix) for prefix in self.BLOCKED_PREFIXES)

    def _is_caller_workspace_code(self) -> bool:
        """
        Inspect call stack to determine if import originated from workspace code.

        Returns:
            True if any frame in the call stack is from workspace directory
        """
        # Get current call stack
        try:
            stack = inspect.stack()
        except KeyError:
            # During Azure Functions initialization, sys.modules['__main__'] may not exist
            # In this case, we're definitely not in workspace code (we're in startup)
            return False

        # Check each frame to see if it's from workspace
        for frame_info in stack:
            filename = frame_info.filename

            # Normalize path for comparison
            normalized_path = os.path.normpath(os.path.abspath(filename))

            # Check if this file is in any workspace path
            if self._is_workspace_code(normalized_path):
                return True

        return False

    def _is_workspace_code(self, filepath: str) -> bool:
        """
        Check if a file path is within workspace directories.

        Args:
            filepath: Absolute file path to check

        Returns:
            True if filepath is under any workspace path
        """
        normalized = os.path.normpath(os.path.abspath(filepath))

        for workspace_path in self.workspace_paths:
            # Check if file is under this workspace path
            try:
                rel_path = os.path.relpath(normalized, workspace_path)
                # If relative path doesn't start with '..', it's inside workspace
                if not rel_path.startswith('..'):
                    return True
            except ValueError:
                # Different drives on Windows - not in workspace
                continue

        return False

    def _raise_import_error(self, module_name: str) -> None:
        """
        Raise ImportError with helpful guidance for developers.

        Args:
            module_name: The blocked module that was attempted

        Raises:
            ImportError: Always raises with clear guidance
        """
        # Get caller information for better error message
        try:
            stack = inspect.stack()
        except KeyError:
            # During initialization, stack inspection may fail
            stack = []

        workspace_file = None

        for frame_info in stack:
            if self._is_workspace_code(frame_info.filename):
                workspace_file = frame_info.filename
                break

        # T031: Clear error message with guidance
        error_msg = (
            f"Workspace code cannot import engine module '{module_name}'. "
            f"\n\nWorkspace code can only import from the public API:\n"
            f"  - engine.shared.decorators (for @workflow, @param, @data_provider)\n"
            f"  - engine.shared.context (for OrganizationContext)\n"
            f"  - engine.shared.error_handling (for WorkflowException, etc.)\n"
            f"  - engine.shared.models (for Pydantic models)\n"
            f"\n"
            f"The requested module '{module_name}' is part of the internal engine "
            f"implementation and should not be accessed directly.\n"
            f"\n"
            f"See documentation at /docs/workspace-api.md for the complete public API."
        )

        if workspace_file:
            error_msg = f"{error_msg}\n\nImport attempted from: {workspace_file}"

        # T036: Log the violation attempt to audit log for security monitoring
        # NOTE: We only log to standard logger, not audit table, to avoid circular
        # import issues during startup when the audit system itself imports engine modules
        logger.warning(
            f"Import restriction violated: {module_name} from {workspace_file or 'unknown'}",
            extra={
                'blocked_module': module_name,
                'workspace_file': workspace_file,
                'event_type': 'import_violation_attempt'
            }
        )

        raise ImportError(error_msg)


# T032: Install function for convenience
def install_import_restrictions(workspace_paths: List[str]) -> None:
    """
    Install import restrictions before workspace code discovery.

    Must be called in function_app.py before importing any workspace modules.

    Args:
        workspace_paths: List of absolute paths to workspace directories

    Raises:
        ValueError: If workspace_paths contains relative paths

    Example:
        import os
        from shared.import_restrictor import install_import_restrictions

        WORKSPACE_PATH = os.path.join(os.path.dirname(__file__), 'workspace')
        install_import_restrictions([os.path.abspath(WORKSPACE_PATH)])
    """
    if not workspace_paths:
        raise ValueError("At least one workspace path must be provided")

    # Create and install restrictor
    restrictor = WorkspaceImportRestrictor(workspace_paths)

    # Add to sys.meta_path (import hook system)
    sys.meta_path.insert(0, restrictor)

    logger.info(
        f"Import restrictions installed for {len(workspace_paths)} workspace path(s)"
    )


def remove_import_restrictions() -> None:
    """
    Remove import restrictions (useful for testing).

    Removes all WorkspaceImportRestrictor instances from sys.meta_path.
    """
    sys.meta_path = [
        finder for finder in sys.meta_path
        if not isinstance(finder, WorkspaceImportRestrictor)
    ]
    logger.info("Import restrictions removed")


def get_active_restrictors() -> List[WorkspaceImportRestrictor]:
    """
    Get list of active import restrictors.

    Returns:
        List of WorkspaceImportRestrictor instances on sys.meta_path
    """
    return [
        finder for finder in sys.meta_path
        if isinstance(finder, WorkspaceImportRestrictor)
    ]
