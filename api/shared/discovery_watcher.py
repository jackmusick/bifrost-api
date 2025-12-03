"""
Discovery Watcher Module

Watchdog-based file system watcher for real-time discovery of workflows,
data providers, and forms. Syncs discovered metadata to the database for
persistent storage and efficient querying.

Architecture:
    File System → Watcher Events → Database (add/update/deactivate)
                                 → In-Memory Index (optional, for fast lookups)

Usage:
    from shared.discovery_watcher import (
        start_watcher, stop_watcher, build_initial_index,
        get_workflow_path, get_provider_path, get_form_path,
        sync_to_database  # New: for startup DB sync
    )

    # On startup (scheduler container)
    workspace_paths = get_workspace_paths()
    build_initial_index(workspace_paths)
    await sync_to_database()  # Sync index to DB
    start_watcher(workspace_paths)

    # On shutdown
    stop_watcher()

    # During execution (worker container)
    # Query from database instead of in-memory index
"""

import json
import logging
import re
import threading
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

logger = logging.getLogger(__name__)


# =============================================================================
# Metadata Extraction (parsing workflow/provider decorators)
# =============================================================================


@dataclass
class WorkflowMetadata:
    """Extracted workflow metadata from file."""
    name: str
    file_path: str
    description: str | None = None
    category: str = "General"
    schedule: str | None = None
    parameters: list[dict] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    endpoint_enabled: bool = False
    allowed_methods: list[str] = field(default_factory=lambda: ["POST"])
    execution_mode: str = "sync"


@dataclass
class ProviderMetadata:
    """Extracted data provider metadata from file."""
    name: str
    file_path: str
    description: str | None = None


@dataclass
class FormMetadata:
    """Extracted form metadata from file."""
    form_id: str
    file_path: str
    name: str | None = None
    description: str | None = None
    linked_workflow: str | None = None

# =============================================================================
# Thread-safe indexes (kept for backward compatibility + fast lookups)
# =============================================================================

_lock = threading.Lock()
_workflow_index: dict[str, str] = {}  # name → file_path
_provider_index: dict[str, str] = {}  # name → file_path
_form_index: dict[str, str] = {}  # id → file_path

# Extended indexes with full metadata (for DB sync)
_workflow_metadata: dict[str, WorkflowMetadata] = {}  # name → metadata
_provider_metadata: dict[str, ProviderMetadata] = {}  # name → metadata
_form_metadata: dict[str, FormMetadata] = {}  # id → metadata

# Pending DB operations (batched for efficiency)
_pending_db_ops: list[tuple[str, str, Any]] = []  # (op_type, entity_type, data)
_db_sync_event = threading.Event()

# =============================================================================
# Regex patterns for extracting metadata without importing
# =============================================================================

# Basic name extraction patterns
WORKFLOW_PATTERN = re.compile(
    r'@workflow\s*\([^)]*name\s*=\s*["\']([^"\']+)["\']', re.MULTILINE
)
PROVIDER_PATTERN = re.compile(
    r'@data_provider\s*\([^)]*name\s*=\s*["\']([^"\']+)["\']', re.MULTILINE
)

# Extended patterns for additional metadata
WORKFLOW_DESCRIPTION_PATTERN = re.compile(
    r'@workflow\s*\([^)]*description\s*=\s*["\']([^"\']+)["\']', re.MULTILINE
)
WORKFLOW_CATEGORY_PATTERN = re.compile(
    r'@workflow\s*\([^)]*category\s*=\s*["\']([^"\']+)["\']', re.MULTILINE
)
WORKFLOW_SCHEDULE_PATTERN = re.compile(
    r'@workflow\s*\([^)]*schedule\s*=\s*["\']([^"\']+)["\']', re.MULTILINE
)
WORKFLOW_ENDPOINT_ENABLED_PATTERN = re.compile(
    r'@workflow\s*\([^)]*endpoint_enabled\s*=\s*(True|False)', re.MULTILINE
)
WORKFLOW_EXECUTION_MODE_PATTERN = re.compile(
    r'@workflow\s*\([^)]*execution_mode\s*=\s*["\']([^"\']+)["\']', re.MULTILINE
)
PROVIDER_DESCRIPTION_PATTERN = re.compile(
    r'@data_provider\s*\([^)]*description\s*=\s*["\']([^"\']+)["\']', re.MULTILINE
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
            # Remove any workflows/providers from this file and queue DB deactivation
            for name, path in list(_workflow_index.items()):
                if path == file_path:
                    del _workflow_index[name]
                    if name in _workflow_metadata:
                        del _workflow_metadata[name]
                    # Queue deactivation (not deletion) for DB
                    _pending_db_ops.append(("deactivate", "workflow", name))
                    logger.info(f"Removed workflow '{name}' from index (file deleted)")

            for name, path in list(_provider_index.items()):
                if path == file_path:
                    del _provider_index[name]
                    if name in _provider_metadata:
                        del _provider_metadata[name]
                    _pending_db_ops.append(("deactivate", "provider", name))
                    logger.info(f"Removed provider '{name}' from index (file deleted)")

            for form_id, path in list(_form_index.items()):
                if path == file_path:
                    del _form_index[form_id]
                    if form_id in _form_metadata:
                        del _form_metadata[form_id]
                    _pending_db_ops.append(("deactivate", "form", form_id))
                    logger.info(f"Removed form '{form_id}' from index (file deleted)")

        # Signal that there are pending DB operations
        _db_sync_event.set()

    def _index_python_file(self, path: Path, event_type: str) -> None:
        """Parse Python file and update workflow/provider indexes with full metadata."""
        try:
            content = path.read_text(encoding="utf-8")
            file_str = str(path)

            with _lock:
                # First remove old entries from this file
                for name, fpath in list(_workflow_index.items()):
                    if fpath == file_str:
                        del _workflow_index[name]
                        if name in _workflow_metadata:
                            del _workflow_metadata[name]
                for name, fpath in list(_provider_index.items()):
                    if fpath == file_str:
                        del _provider_index[name]
                        if name in _provider_metadata:
                            del _provider_metadata[name]

                # Extract workflows with full metadata
                for match in WORKFLOW_PATTERN.finditer(content):
                    name = match.group(1)
                    _workflow_index[name] = file_str

                    # Extract additional metadata
                    desc_match = WORKFLOW_DESCRIPTION_PATTERN.search(content)
                    cat_match = WORKFLOW_CATEGORY_PATTERN.search(content)
                    sched_match = WORKFLOW_SCHEDULE_PATTERN.search(content)
                    endpoint_match = WORKFLOW_ENDPOINT_ENABLED_PATTERN.search(content)
                    mode_match = WORKFLOW_EXECUTION_MODE_PATTERN.search(content)

                    metadata = WorkflowMetadata(
                        name=name,
                        file_path=file_str,
                        description=desc_match.group(1) if desc_match else None,
                        category=cat_match.group(1) if cat_match else "General",
                        schedule=sched_match.group(1) if sched_match else None,
                        endpoint_enabled=endpoint_match.group(1) == "True" if endpoint_match else False,
                        execution_mode=mode_match.group(1) if mode_match else "sync",
                    )
                    _workflow_metadata[name] = metadata

                    # Queue DB upsert
                    _pending_db_ops.append(("upsert", "workflow", metadata))
                    logger.debug(f"Indexed workflow '{name}' from {path.name} ({event_type})")

                # Extract providers with metadata
                for match in PROVIDER_PATTERN.finditer(content):
                    name = match.group(1)
                    _provider_index[name] = file_str

                    desc_match = PROVIDER_DESCRIPTION_PATTERN.search(content)
                    metadata = ProviderMetadata(
                        name=name,
                        file_path=file_str,
                        description=desc_match.group(1) if desc_match else None,
                    )
                    _provider_metadata[name] = metadata

                    _pending_db_ops.append(("upsert", "provider", metadata))
                    logger.debug(f"Indexed provider '{name}' from {path.name} ({event_type})")

            # Signal pending DB operations (outside lock)
            if _pending_db_ops:
                _db_sync_event.set()

        except Exception as e:
            logger.warning(f"Failed to index {path}: {e}")

    def _index_form_file(self, path: Path, event_type: str) -> None:
        """Parse form JSON and update form index with metadata."""
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
                        if fid in _form_metadata:
                            del _form_metadata[fid]

                _form_index[form_id] = file_str

                # Extract metadata from form JSON
                metadata = FormMetadata(
                    form_id=form_id,
                    file_path=file_str,
                    name=data.get("name"),
                    description=data.get("description"),
                    linked_workflow=data.get("linkedWorkflow") or data.get("linked_workflow"),
                )
                _form_metadata[form_id] = metadata

                _pending_db_ops.append(("upsert", "form", metadata))
                logger.debug(f"Indexed form '{form_id}' from {path.name} ({event_type})")

            # Signal pending DB operations
            if _pending_db_ops:
                _db_sync_event.set()

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
            "pending_db_ops": len(_pending_db_ops),
        }


# =============================================================================
# Database Sync Functions
# =============================================================================


async def sync_to_database() -> dict[str, int]:
    """
    Sync all in-memory index data to the database.

    This should be called:
    1. After build_initial_index() on startup
    2. Periodically by a background task to flush pending operations

    Returns:
        Dict with counts of workflows, providers, and forms synced
    """
    from src.core.database import get_db_context
    from src.models import Workflow, DataProvider, Form
    from sqlalchemy import select

    counts = {"workflows": 0, "providers": 0, "forms": 0}
    now = datetime.utcnow()

    async with get_db_context() as db:
        # Get all current metadata from indexes
        with _lock:
            workflow_data = dict(_workflow_metadata)
            provider_data = dict(_provider_metadata)
            form_data = dict(_form_metadata)
            workflow_names = set(_workflow_index.keys())
            provider_names = set(_provider_index.keys())

        # --- Sync Workflows ---
        # Get existing workflows from DB
        result = await db.execute(select(Workflow))
        existing_workflows = {w.name: w for w in result.scalars().all()}

        # Upsert workflows from index
        for name, meta in workflow_data.items():
            if name in existing_workflows:
                # Update existing
                wf = existing_workflows[name]
                wf.file_path = meta.file_path
                wf.description = meta.description
                wf.category = meta.category
                wf.schedule = meta.schedule
                wf.endpoint_enabled = meta.endpoint_enabled
                wf.execution_mode = meta.execution_mode
                wf.is_active = True
                wf.last_seen_at = now
            else:
                # Insert new
                wf = Workflow(
                    id=uuid4(),
                    name=name,
                    file_path=meta.file_path,
                    description=meta.description,
                    category=meta.category,
                    schedule=meta.schedule,
                    parameters_schema=meta.parameters,
                    tags=meta.tags,
                    endpoint_enabled=meta.endpoint_enabled,
                    allowed_methods=meta.allowed_methods,
                    execution_mode=meta.execution_mode,
                    is_active=True,
                    last_seen_at=now,
                )
                db.add(wf)
            counts["workflows"] += 1

        # Deactivate workflows no longer in filesystem
        for name, wf in existing_workflows.items():
            if name not in workflow_names and wf.is_active:
                wf.is_active = False
                logger.info(f"Deactivated workflow '{name}' (not found in filesystem)")

        # --- Sync Data Providers ---
        result = await db.execute(select(DataProvider))
        existing_providers = {p.name: p for p in result.scalars().all()}

        for name, meta in provider_data.items():
            if name in existing_providers:
                dp = existing_providers[name]
                dp.file_path = meta.file_path
                dp.description = meta.description
                dp.is_active = True
                dp.last_seen_at = now
            else:
                dp = DataProvider(
                    id=uuid4(),
                    name=name,
                    file_path=meta.file_path,
                    description=meta.description,
                    is_active=True,
                    last_seen_at=now,
                )
                db.add(dp)
            counts["providers"] += 1

        for name, dp in existing_providers.items():
            if name not in provider_names and dp.is_active:
                dp.is_active = False
                logger.info(f"Deactivated data provider '{name}' (not found in filesystem)")

        # --- Sync Forms (only file-based forms, not DB-created ones) ---
        # Only sync forms that have file_path (workspace forms)
        result = await db.execute(
            select(Form).where(Form.file_path.isnot(None))
        )
        existing_forms = {f.name: f for f in result.scalars().all()}

        for form_id, meta in form_data.items():
            form_name = meta.name or form_id
            if form_name in existing_forms:
                form = existing_forms[form_name]
                form.file_path = meta.file_path
                form.description = meta.description
                form.linked_workflow = meta.linked_workflow
                form.is_active = True
                form.last_seen_at = now
            else:
                # Note: Forms created from files need a created_by
                form = Form(
                    id=uuid4(),
                    name=form_name,
                    file_path=meta.file_path,
                    description=meta.description,
                    linked_workflow=meta.linked_workflow,
                    is_active=True,
                    last_seen_at=now,
                    created_by="system:discovery",
                )
                db.add(form)
            counts["forms"] += 1

        # Deactivate file-based forms no longer in filesystem
        form_names_from_files = {(m.name or fid) for fid, m in form_data.items()}
        for name, form in existing_forms.items():
            if name not in form_names_from_files and form.is_active:
                form.is_active = False
                logger.info(f"Deactivated form '{name}' (not found in filesystem)")

        await db.commit()

    # Clear pending operations
    with _lock:
        _pending_db_ops.clear()
        _db_sync_event.clear()

    logger.info(
        f"Database sync complete: {counts['workflows']} workflows, "
        f"{counts['providers']} providers, {counts['forms']} forms"
    )
    return counts


async def process_pending_db_ops() -> int:
    """
    Process pending database operations from file watcher events.

    This is called by a background task to batch DB updates.

    Returns:
        Number of operations processed
    """
    from src.core.database import get_db_context
    from src.models import Workflow, DataProvider, Form
    from sqlalchemy import select

    with _lock:
        ops = list(_pending_db_ops)
        _pending_db_ops.clear()
        _db_sync_event.clear()

    if not ops:
        return 0

    now = datetime.utcnow()
    processed = 0

    async with get_db_context() as db:
        for op_type, entity_type, data in ops:
            try:
                if entity_type == "workflow":
                    if op_type == "upsert":
                        meta: WorkflowMetadata = data
                        result = await db.execute(
                            select(Workflow).where(Workflow.name == meta.name)
                        )
                        wf = result.scalar_one_or_none()
                        if wf:
                            wf.file_path = meta.file_path
                            wf.description = meta.description
                            wf.category = meta.category
                            wf.schedule = meta.schedule
                            wf.endpoint_enabled = meta.endpoint_enabled
                            wf.execution_mode = meta.execution_mode
                            wf.is_active = True
                            wf.last_seen_at = now
                        else:
                            wf = Workflow(
                                id=uuid4(),
                                name=meta.name,
                                file_path=meta.file_path,
                                description=meta.description,
                                category=meta.category,
                                schedule=meta.schedule,
                                endpoint_enabled=meta.endpoint_enabled,
                                execution_mode=meta.execution_mode,
                                is_active=True,
                                last_seen_at=now,
                            )
                            db.add(wf)
                    elif op_type == "deactivate":
                        name: str = data
                        result = await db.execute(
                            select(Workflow).where(Workflow.name == name)
                        )
                        wf = result.scalar_one_or_none()
                        if wf:
                            wf.is_active = False

                elif entity_type == "provider":
                    if op_type == "upsert":
                        meta: ProviderMetadata = data
                        result = await db.execute(
                            select(DataProvider).where(DataProvider.name == meta.name)
                        )
                        dp = result.scalar_one_or_none()
                        if dp:
                            dp.file_path = meta.file_path
                            dp.description = meta.description
                            dp.is_active = True
                            dp.last_seen_at = now
                        else:
                            dp = DataProvider(
                                id=uuid4(),
                                name=meta.name,
                                file_path=meta.file_path,
                                description=meta.description,
                                is_active=True,
                                last_seen_at=now,
                            )
                            db.add(dp)
                    elif op_type == "deactivate":
                        name: str = data
                        result = await db.execute(
                            select(DataProvider).where(DataProvider.name == name)
                        )
                        dp = result.scalar_one_or_none()
                        if dp:
                            dp.is_active = False

                elif entity_type == "form":
                    if op_type == "upsert":
                        meta: FormMetadata = data
                        form_name = meta.name or meta.form_id
                        result = await db.execute(
                            select(Form).where(Form.name == form_name)
                        )
                        form = result.scalar_one_or_none()
                        if form:
                            form.file_path = meta.file_path
                            form.description = meta.description
                            form.linked_workflow = meta.linked_workflow
                            form.is_active = True
                            form.last_seen_at = now
                        else:
                            form = Form(
                                id=uuid4(),
                                name=form_name,
                                file_path=meta.file_path,
                                description=meta.description,
                                linked_workflow=meta.linked_workflow,
                                is_active=True,
                                last_seen_at=now,
                                created_by="system:discovery",
                            )
                            db.add(form)
                    elif op_type == "deactivate":
                        form_id: str = data
                        # Try to find by name first, then by file path pattern
                        result = await db.execute(
                            select(Form).where(Form.name == form_id)
                        )
                        form = result.scalar_one_or_none()
                        if form:
                            form.is_active = False

                processed += 1

            except Exception as e:
                logger.error(f"Error processing DB op ({op_type}, {entity_type}): {e}")

        await db.commit()

    logger.debug(f"Processed {processed} pending DB operations")
    return processed


def has_pending_db_ops() -> bool:
    """Check if there are pending database operations."""
    with _lock:
        return len(_pending_db_ops) > 0


def wait_for_db_ops(timeout: float = 5.0) -> bool:
    """
    Wait for pending database operations signal.

    Returns True if there are ops to process, False if timeout.
    """
    return _db_sync_event.wait(timeout=timeout)
