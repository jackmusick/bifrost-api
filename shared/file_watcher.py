"""
File watcher for workspace modules.

Monitors the workspace directory for Python file changes and automatically
reloads modules when files are modified, added, or deleted. This enables
hot-reload in production while preserving debugger breakpoints.
"""

import sys
import threading
from pathlib import Path
from typing import Any

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer as WatchdogObserver


class WorkspaceFileHandler(FileSystemEventHandler):
    """Handles file system events for workspace Python files."""

    def __init__(self, workspace_paths: list[Path]):
        self.workspace_paths = workspace_paths
        self._processing_lock = threading.Lock()
        self._reload_func = None

    def set_reload_function(self, reload_func):
        """Set the function to call when a module needs reloading."""
        self._reload_func = reload_func

    def on_modified(self, event: FileSystemEvent):
        """Called when a file is modified."""
        if event.is_directory:
            return

        file_path = Path(str(event.src_path))
        if file_path.suffix == '.py' and not file_path.name.startswith('_'):
            print(f"📝 Workspace file modified: {file_path.name}")
            self._reload_module(file_path)

    def on_created(self, event: FileSystemEvent):
        """Called when a file is created."""
        if event.is_directory:
            return

        file_path = Path(str(event.src_path))
        if file_path.suffix == '.py' and not file_path.name.startswith('_'):
            print(f"✨ New workspace file detected: {file_path.name}")
            self._reload_module(file_path)

    def on_deleted(self, event: FileSystemEvent):
        """Called when a file is deleted."""
        if event.is_directory:
            return

        file_path = Path(str(event.src_path))
        if file_path.suffix == '.py':
            print(f"🗑️  Workspace file deleted: {file_path.name}")
            self._unregister_module(file_path)

    def _reload_module(self, file_path: Path):
        """Reload a single module."""
        with self._processing_lock:
            if self._reload_func:
                try:
                    self._reload_func(file_path)
                except Exception as e:
                    print(f"Failed to reload {file_path.name}: {e}")

    def _unregister_module(self, file_path: Path):
        """Unregister a deleted module."""
        with self._processing_lock:
            module_name = file_path.stem

            # Remove from sys.modules
            if module_name in sys.modules:
                del sys.modules[module_name]
                print(f"Removed {module_name} from sys.modules")

            # Remove from registry (if it was registered)
            from shared.registry import get_registry
            registry = get_registry()

            # Check if it was a workflow
            workflow = registry.get_workflow(module_name)
            if workflow:
                # Note: We'd need to add an unregister method to the registry
                print(
                    f"Module {module_name} was registered as workflow, needs cleanup")


class WorkspaceWatcher:
    """Watches workspace directories for file changes."""

    def __init__(self, workspace_paths: list[Path]):
        self.workspace_paths = workspace_paths
        self.observer: Any = None
        self.handler = WorkspaceFileHandler(workspace_paths)

    def set_reload_function(self, reload_func):
        """Set the function to call when a module needs reloading."""
        self.handler.set_reload_function(reload_func)

    def start(self):
        """Start watching workspace directories."""
        if not self.workspace_paths:
            print("⚠️  No workspace paths to watch")
            return

        self.observer = WatchdogObserver()

        for workspace_path in self.workspace_paths:
            if workspace_path.exists():
                self.observer.schedule(self.handler, str(workspace_path), recursive=True)
                print(f"👀 Watching workspace directory: {workspace_path}")
            else:
                print(f"⚠️  Workspace path does not exist: {workspace_path}")

        self.observer.start()
        print("✅ Workspace file watcher started")

    def stop(self):
        """Stop watching workspace directories."""
        if self.observer:
            self.observer.stop()
            self.observer.join()
            print("🛑 Workspace file watcher stopped")


# Global watcher instance
_watcher: WorkspaceWatcher | None = None


def start_workspace_watcher(workspace_paths: list[Path], reload_func):
    """Start the workspace file watcher."""
    global _watcher

    if _watcher:
        print("Workspace watcher already running")
        return

    _watcher = WorkspaceWatcher(workspace_paths)
    _watcher.set_reload_function(reload_func)
    _watcher.start()


def stop_workspace_watcher():
    """Stop the workspace file watcher."""
    global _watcher

    if _watcher:
        _watcher.stop()
        _watcher = None
