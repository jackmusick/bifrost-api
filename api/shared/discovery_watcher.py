"""
Discovery Watcher Module

Watchdog-based file system watcher for real-time discovery of workflows,
data providers, and forms. Maintains in-memory indexes for O(1) lookups.

Usage:
    from shared.discovery_watcher import (
        start_watcher, stop_watcher, build_initial_index,
        get_workflow_path, get_provider_path, get_form_path
    )

    # On startup
    workspace_paths = get_workspace_paths()
    build_initial_index(workspace_paths)
    start_watcher(workspace_paths)

    # On shutdown
    stop_watcher()

    # During execution
    file_path = get_workflow_path("my_workflow")  # O(1) lookup
"""

import json
import logging
import re
import threading
from pathlib import Path

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

logger = logging.getLogger(__name__)

# Thread-safe indexes
_lock = threading.Lock()
_workflow_index: dict[str, str] = {}  # name → file_path
_provider_index: dict[str, str] = {}  # name → file_path
_form_index: dict[str, str] = {}  # id → file_path

# Regex patterns for extracting names without importing
# These match @workflow(name="...") or @workflow(name='...') with any spacing
WORKFLOW_PATTERN = re.compile(
    r'@workflow\s*\([^)]*name\s*=\s*["\']([^"\']+)["\']', re.MULTILINE
)
PROVIDER_PATTERN = re.compile(
    r'@data_provider\s*\([^)]*name\s*=\s*["\']([^"\']+)["\']', re.MULTILINE
)

# Global observer instance
_observer: Observer | None = None


class WorkspaceEventHandler(FileSystemEventHandler):
    """Handle file system events for workspace directories."""

    def on_created(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        self._handle_file_change(event.src_path, "created")

    def on_modified(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        self._handle_file_change(event.src_path, "modified")

    def on_deleted(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        self._handle_file_delete(event.src_path)

    def on_moved(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        self._handle_file_delete(event.src_path)
        if hasattr(event, "dest_path"):
            self._handle_file_change(event.dest_path, "moved")

    def _handle_file_change(self, file_path: str, event_type: str) -> None:
        """Update index when a file is created/modified."""
        path = Path(file_path)

        # Skip __pycache__ and hidden files
        if "__pycache__" in file_path or path.name.startswith("."):
            return

        if path.suffix == ".py" and not path.name.startswith("_"):
            self._index_python_file(path, event_type)
        elif path.name.endswith(".form.json") or path.name == "form.json":
            self._index_form_file(path, event_type)

    def _handle_file_delete(self, file_path: str) -> None:
        """Remove entries from index when file is deleted."""
        with _lock:
            # Remove any workflows/providers from this file
            for name, path in list(_workflow_index.items()):
                if path == file_path:
                    del _workflow_index[name]
                    logger.info(f"Removed workflow '{name}' from index (file deleted)")

            for name, path in list(_provider_index.items()):
                if path == file_path:
                    del _provider_index[name]
                    logger.info(f"Removed provider '{name}' from index (file deleted)")

            for form_id, path in list(_form_index.items()):
                if path == file_path:
                    del _form_index[form_id]
                    logger.info(f"Removed form '{form_id}' from index (file deleted)")

    def _index_python_file(self, path: Path, event_type: str) -> None:
        """Parse Python file and update workflow/provider indexes."""
        try:
            content = path.read_text(encoding="utf-8")
            file_str = str(path)

            with _lock:
                # First remove old entries from this file
                for name, fpath in list(_workflow_index.items()):
                    if fpath == file_str:
                        del _workflow_index[name]
                for name, fpath in list(_provider_index.items()):
                    if fpath == file_str:
                        del _provider_index[name]

                # Add new entries
                for match in WORKFLOW_PATTERN.finditer(content):
                    name = match.group(1)
                    _workflow_index[name] = file_str
                    logger.debug(f"Indexed workflow '{name}' from {path.name} ({event_type})")

                for match in PROVIDER_PATTERN.finditer(content):
                    name = match.group(1)
                    _provider_index[name] = file_str
                    logger.debug(
                        f"Indexed provider '{name}' from {path.name} ({event_type})"
                    )

        except Exception as e:
            logger.warning(f"Failed to index {path}: {e}")

    def _index_form_file(self, path: Path, event_type: str) -> None:
        """Parse form JSON and update form index."""
        try:
            content = path.read_text(encoding="utf-8")
            data = json.loads(content)
            form_id = data.get("id") or f"workspace-{path.stem}"
            file_str = str(path)

            with _lock:
                # Remove old entry if this file had a different form_id before
                for fid, fpath in list(_form_index.items()):
                    if fpath == file_str:
                        del _form_index[fid]

                _form_index[form_id] = file_str
                logger.debug(f"Indexed form '{form_id}' from {path.name} ({event_type})")

        except Exception as e:
            logger.warning(f"Failed to index form {path}: {e}")


def build_initial_index(workspace_paths: list[Path]) -> None:
    """
    Build the initial index by scanning all workspace directories.

    This does a one-time scan of all files to populate the indexes.
    After this, the watchdog keeps the indexes updated.

    Args:
        workspace_paths: List of workspace directories to scan
    """
    handler = WorkspaceEventHandler()

    for workspace_path in workspace_paths:
        if not workspace_path.exists():
            logger.warning(f"Workspace path does not exist: {workspace_path}")
            continue

        # Scan all Python files
        for py_file in workspace_path.rglob("*.py"):
            if py_file.name.startswith("_"):
                continue
            if ".packages" in str(py_file) or "__pycache__" in str(py_file):
                continue
            handler._index_python_file(py_file, "initial")

        # Scan all form files
        for form_file in workspace_path.rglob("*.form.json"):
            handler._index_form_file(form_file, "initial")
        for form_file in workspace_path.rglob("form.json"):
            handler._index_form_file(form_file, "initial")

    with _lock:
        logger.info(
            f"Initial index built: {len(_workflow_index)} workflows, "
            f"{len(_provider_index)} providers, {len(_form_index)} forms"
        )


def start_watcher(workspace_paths: list[Path]) -> None:
    """
    Start the file system watcher for given paths.

    Args:
        workspace_paths: List of directories to watch
    """
    global _observer

    if _observer is not None:
        logger.warning("Watcher already running")
        return

    _observer = Observer()
    handler = WorkspaceEventHandler()

    for path in workspace_paths:
        if path.exists():
            _observer.schedule(handler, str(path), recursive=True)
            logger.info(f"Watching directory: {path}")
        else:
            logger.warning(f"Cannot watch non-existent path: {path}")

    _observer.start()
    logger.info("Workspace file watcher started")


def stop_watcher() -> None:
    """Stop the file system watcher."""
    global _observer
    if _observer:
        _observer.stop()
        _observer.join(timeout=5)
        _observer = None
        logger.info("Workspace file watcher stopped")


def get_workflow_path(name: str) -> str | None:
    """
    Get file path for a workflow by name.

    Args:
        name: Workflow name

    Returns:
        File path string or None if not found
    """
    with _lock:
        return _workflow_index.get(name)


def get_provider_path(name: str) -> str | None:
    """
    Get file path for a data provider by name.

    Args:
        name: Data provider name

    Returns:
        File path string or None if not found
    """
    with _lock:
        return _provider_index.get(name)


def get_form_path(form_id: str) -> str | None:
    """
    Get file path for a form by ID.

    Args:
        form_id: Form ID

    Returns:
        File path string or None if not found
    """
    with _lock:
        return _form_index.get(form_id)


def get_all_workflow_names() -> list[str]:
    """Get all indexed workflow names."""
    with _lock:
        return list(_workflow_index.keys())


def get_all_provider_names() -> list[str]:
    """Get all indexed data provider names."""
    with _lock:
        return list(_provider_index.keys())


def get_all_form_ids() -> list[str]:
    """Get all indexed form IDs."""
    with _lock:
        return list(_form_index.keys())


def get_index_stats() -> dict:
    """Get statistics about the current index state."""
    with _lock:
        return {
            "workflows": len(_workflow_index),
            "providers": len(_provider_index),
            "forms": len(_form_index),
            "watcher_running": _observer is not None and _observer.is_alive(),
        }
