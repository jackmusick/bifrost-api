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
import os
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


def _get_workspace_relative_path(absolute_path: str) -> str:
    """
    Convert an absolute file path to a workspace-relative path.

    Args:
        absolute_path: Full path like '/workspace/forms/foo.form.json'

    Returns:
        Workspace-relative path like 'forms/foo.form.json'
    """
    workspace_loc = os.getenv("BIFROST_WORKSPACE_LOCATION", "/workspace")
    # Ensure workspace_loc doesn't have trailing slash
    workspace_loc = workspace_loc.rstrip("/")

    if absolute_path.startswith(workspace_loc):
        # Remove workspace prefix and leading slash
        relative = absolute_path[len(workspace_loc):]
        if relative.startswith("/"):
            relative = relative[1:]
        return relative

    # If not under workspace, return just the filename part under forms/
    path = Path(absolute_path)
    if path.suffix == ".json" and "form" in path.name.lower():
        return f"forms/{path.name}"

    return absolute_path  # Fallback to original


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
    is_platform: bool = False  # True if from platform/ directory


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
    form_schema: dict | None = None  # Full form_schema for field extraction
    is_active: bool = True
    organization_id: str | None = None
    access_level: str | None = None
    created_by: str = "system:discovery"
    launch_workflow_id: str | None = None
    allowed_query_params: list[str] | None = None
    default_launch_params: dict | None = None

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

# Track whether Python files changed (requires full import scan)
_python_files_changed = threading.Event()

# Track files being written to prevent re-triggering on our own writes
_files_being_written: set[str] = set()
_write_lock = threading.Lock()

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
_observer: Observer | None = None  # type: ignore[type-arg]


class WorkspaceEventHandler(FileSystemEventHandler):
    """Handle file system events for workspace directories."""

    def on_created(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        self._handle_file_change(str(event.src_path), "created")

    def on_modified(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        self._handle_file_change(str(event.src_path), "modified")

    def on_deleted(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        self._handle_file_delete(str(event.src_path))

    def on_moved(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        self._handle_file_delete(str(event.src_path))
        if hasattr(event, "dest_path"):
            self._handle_file_change(str(event.dest_path), "moved")

    def _handle_file_change(self, file_path: str, event_type: str) -> None:
        """Update index when a file is created/modified."""
        path = Path(file_path)

        # Skip __pycache__ and hidden files
        if "__pycache__" in file_path or path.name.startswith("."):
            return

        # Skip .tmp files (used for atomic writes)
        if path.suffix == ".tmp":
            return

        # Skip files we're currently writing to prevent infinite loops
        with _write_lock:
            if file_path in _files_being_written:
                logger.debug(f"Skipping self-triggered event for {path.name}")
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
        """Parse Python file and update workflow/provider indexes with full metadata.

        Note: We use regex for quick indexing but rely on periodic full sync for parameters.
        When a file changes, we just mark that a sync is needed.
        """
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

                # Extract workflows with basic regex (name only for quick indexing)
                for match in WORKFLOW_PATTERN.finditer(content):
                    name = match.group(1)
                    _workflow_index[name] = file_str
                    logger.debug(f"Detected workflow '{name}' from {path.name} ({event_type})")

                # Extract providers with basic regex
                for match in PROVIDER_PATTERN.finditer(content):
                    name = match.group(1)
                    _provider_index[name] = file_str
                    logger.debug(f"Detected provider '{name}' from {path.name} ({event_type})")

            # Trigger a full DB sync to get complete metadata with parameters
            # The sync_to_database() function will do a full import-based scan
            _python_files_changed.set()
            _db_sync_event.set()

        except Exception as e:
            logger.warning(f"Failed to index {path}: {e}")

    def _index_form_file(self, path: Path, event_type: str) -> None:
        """Parse form JSON and update form index with metadata."""
        try:
            content = path.read_text(encoding="utf-8")
            data = json.loads(content)

            # Get or generate form ID
            form_id = data.get("id")
            id_was_generated = False
            if not form_id:
                form_id = str(uuid4())
                id_was_generated = True

            file_str = str(path)
            # Store workspace-relative path in database
            relative_path = _get_workspace_relative_path(file_str)

            with _lock:
                # Remove old entry if this file had a different form_id before
                for fid, fpath in list(_form_index.items()):
                    if fpath == file_str or fpath == relative_path:
                        del _form_index[fid]
                        if fid in _form_metadata:
                            del _form_metadata[fid]

                _form_index[form_id] = file_str  # Keep absolute for lookups

                # Extract comprehensive metadata from form JSON
                org_id = data.get("org_id") or data.get("organization_id")
                if org_id == "GLOBAL":
                    org_id = None

                metadata = FormMetadata(
                    form_id=form_id,
                    file_path=relative_path,  # Store workspace-relative path
                    name=data.get("name"),
                    description=data.get("description"),
                    linked_workflow=data.get("linkedWorkflow") or data.get("linked_workflow"),
                    form_schema=data.get("form_schema"),
                    is_active=data.get("is_active", True),
                    organization_id=org_id,
                    access_level=data.get("access_level"),
                    created_by=data.get("created_by", "system:discovery"),
                    launch_workflow_id=data.get("launch_workflow_id"),
                    allowed_query_params=data.get("allowed_query_params"),
                    default_launch_params=data.get("default_launch_params"),
                )
                _form_metadata[form_id] = metadata

                _pending_db_ops.append(("upsert", "form", metadata))
                logger.debug(f"Indexed form '{form_id}' from {path.name} ({event_type})")

            # If we generated an ID, write it back to the file
            if id_was_generated:
                data["id"] = form_id
                # Mark file as being written to prevent re-triggering
                with _write_lock:
                    _files_being_written.add(file_str)
                try:
                    # Write atomically
                    temp_file = path.with_suffix('.tmp')
                    temp_file.write_text(json.dumps(data, indent=2), encoding='utf-8')
                    temp_file.replace(path)
                    logger.info(f"Generated ID {form_id} for form file: {path.name}")
                except Exception as e:
                    logger.warning(f"Failed to write generated ID to {path}: {e}")
                    if temp_file.exists():
                        temp_file.unlink()
                finally:
                    # Allow a small delay before removing from write set
                    # to let the filesystem settle
                    import time
                    time.sleep(0.1)
                    with _write_lock:
                        _files_being_written.discard(file_str)

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

    observer = Observer()
    handler = WorkspaceEventHandler()

    for path in workspace_paths:
        if path.exists():
            observer.schedule(handler, str(path), recursive=True)
            logger.info(f"Watching directory: {path}")
        else:
            logger.warning(f"Cannot watch non-existent path: {path}")

    observer.start()
    _observer = observer
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
    from shared.discovery import scan_all_workflows, scan_all_data_providers

    counts = {"workflows": 0, "providers": 0, "forms": 0}
    now = datetime.utcnow()

    async with get_db_context() as db:
        # Do full import-based scan to get complete metadata with parameters
        # This imports modules and executes decorators to get full metadata
        workflows_list = scan_all_workflows()
        providers_list = scan_all_data_providers()

        # Convert list to dict by name
        workflow_data = {w.name: w for w in workflows_list}
        provider_data = {p.name: p for p in providers_list}

        # Get forms from in-memory index (forms are JSON, no import needed)
        with _lock:
            form_data = dict(_form_metadata)
            workflow_names = set(workflow_data.keys())
            provider_names = set(provider_data.keys())

        # --- Sync Workflows ---
        # Get existing workflows from DB
        result = await db.execute(select(Workflow))
        existing_workflows = {w.name: w for w in result.scalars().all()}

        # Upsert workflows from index
        for name, meta in workflow_data.items():
            # Serialize parameters to dicts for JSONB storage
            from dataclasses import asdict
            parameters_json = [asdict(p) for p in meta.parameters] if meta.parameters else []

            if name in existing_workflows:
                # Update existing
                wf = existing_workflows[name]
                wf.file_path = meta.source_file_path or ""
                wf.description = meta.description
                wf.category = meta.category
                wf.schedule = meta.schedule
                wf.parameters_schema = parameters_json
                wf.tags = meta.tags
                wf.endpoint_enabled = meta.endpoint_enabled
                wf.allowed_methods = meta.allowed_methods
                wf.execution_mode = meta.execution_mode
                wf.is_platform = meta.is_platform
                wf.is_active = True
                wf.last_seen_at = now
            else:
                # Insert new
                wf = Workflow(
                    id=uuid4(),
                    name=name,
                    file_path=meta.source_file_path or "",
                    description=meta.description,
                    category=meta.category,
                    schedule=meta.schedule,
                    parameters_schema=parameters_json,
                    tags=meta.tags,
                    endpoint_enabled=meta.endpoint_enabled,
                    allowed_methods=meta.allowed_methods,
                    execution_mode=meta.execution_mode,
                    is_platform=meta.is_platform,
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
                dp.file_path = meta.source_file_path or ""
                dp.description = meta.description
                dp.is_active = True
                dp.last_seen_at = now
            else:
                dp = DataProvider(
                    id=uuid4(),
                    name=name,
                    file_path=meta.source_file_path or "",
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
    For forms, this creates/updates FormField records from form_schema.

    Returns:
        Number of operations processed
    """
    from src.core.database import get_db_context
    from src.models import Workflow, DataProvider, Form, FormField
    from src.models.enums import FormAccessLevel
    from sqlalchemy import select, delete
    from uuid import UUID as UUIDType

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
                        wf_meta = WorkflowMetadata(**data.__dict__) if hasattr(data, '__dict__') else data
                        result = await db.execute(
                            select(Workflow).where(Workflow.name == wf_meta.name)
                        )
                        wf = result.scalar_one_or_none()
                        if wf:
                            wf.file_path = wf_meta.file_path
                            wf.description = wf_meta.description
                            wf.category = wf_meta.category
                            wf.schedule = wf_meta.schedule
                            wf.endpoint_enabled = wf_meta.endpoint_enabled
                            wf.execution_mode = wf_meta.execution_mode
                            wf.is_active = True
                            wf.last_seen_at = now
                        else:
                            wf = Workflow(
                                id=uuid4(),
                                name=wf_meta.name,
                                file_path=wf_meta.file_path,
                                description=wf_meta.description,
                                category=wf_meta.category,
                                schedule=wf_meta.schedule,
                                endpoint_enabled=wf_meta.endpoint_enabled,
                                execution_mode=wf_meta.execution_mode,
                                is_active=True,
                                last_seen_at=now,
                            )
                            db.add(wf)
                    elif op_type == "deactivate":
                        wf_name: str = data
                        result = await db.execute(
                            select(Workflow).where(Workflow.name == wf_name)
                        )
                        wf = result.scalar_one_or_none()
                        if wf:
                            wf.is_active = False

                elif entity_type == "provider":
                    if op_type == "upsert":
                        prov_meta: ProviderMetadata = data
                        result = await db.execute(
                            select(DataProvider).where(DataProvider.name == prov_meta.name)
                        )
                        dp = result.scalar_one_or_none()
                        if dp:
                            dp.file_path = prov_meta.file_path
                            dp.description = prov_meta.description
                            dp.is_active = True
                            dp.last_seen_at = now
                        else:
                            dp = DataProvider(
                                id=uuid4(),
                                name=prov_meta.name,
                                file_path=prov_meta.file_path,
                                description=prov_meta.description,
                                is_active=True,
                                last_seen_at=now,
                            )
                            db.add(dp)
                    elif op_type == "deactivate":
                        prov_name: str = data
                        result = await db.execute(
                            select(DataProvider).where(DataProvider.name == prov_name)
                        )
                        dp = result.scalar_one_or_none()
                        if dp:
                            dp.is_active = False

                elif entity_type == "form":
                    if op_type == "upsert":
                        form_meta: FormMetadata = data
                        form_name = form_meta.name or form_meta.form_id

                        # Use the form_id from file if it looks like a UUID
                        try:
                            form_uuid = UUIDType(form_meta.form_id)
                        except (ValueError, TypeError):
                            form_uuid = uuid4()

                        # Try to find by ID first (for updates), then by name
                        result = await db.execute(
                            select(Form).where(Form.id == form_uuid)
                        )
                        form = result.scalar_one_or_none()

                        if not form:
                            # Check by name if not found by ID
                            result = await db.execute(
                                select(Form).where(Form.name == form_name)
                            )
                            form = result.scalar_one_or_none()

                        # Parse organization_id
                        org_uuid = None
                        if form_meta.organization_id:
                            try:
                                org_uuid = UUIDType(form_meta.organization_id)
                            except (ValueError, TypeError):
                                pass

                        # Parse access_level string to enum (default to ROLE_BASED)
                        access_level_enum = FormAccessLevel.ROLE_BASED
                        if form_meta.access_level:
                            try:
                                access_level_enum = FormAccessLevel(form_meta.access_level)
                            except ValueError:
                                pass

                        if form:
                            # Update existing form
                            form.name = form_name
                            form.file_path = form_meta.file_path
                            form.description = form_meta.description
                            form.linked_workflow = form_meta.linked_workflow
                            form.is_active = form_meta.is_active
                            form.organization_id = org_uuid
                            form.access_level = access_level_enum
                            form.launch_workflow_id = form_meta.launch_workflow_id
                            form.allowed_query_params = form_meta.allowed_query_params
                            form.default_launch_params = form_meta.default_launch_params
                            form.last_seen_at = now
                            form.updated_at = now
                        else:
                            # Create new form
                            form = Form(
                                id=form_uuid,
                                name=form_name,
                                file_path=form_meta.file_path,
                                description=form_meta.description,
                                linked_workflow=form_meta.linked_workflow,
                                is_active=form_meta.is_active,
                                organization_id=org_uuid,
                                access_level=access_level_enum,
                                created_by=form_meta.created_by,
                                launch_workflow_id=form_meta.launch_workflow_id,
                                allowed_query_params=form_meta.allowed_query_params,
                                default_launch_params=form_meta.default_launch_params,
                                last_seen_at=now,
                                created_at=now,
                                updated_at=now,
                            )
                            db.add(form)
                            await db.flush()  # Get the ID

                        # Sync form_fields from form_schema
                        if form_meta.form_schema and "fields" in form_meta.form_schema:
                            # Delete existing fields
                            await db.execute(
                                delete(FormField).where(FormField.form_id == form.id)
                            )
                            await db.flush()

                            # Create new fields from schema
                            for position, field_data in enumerate(form_meta.form_schema["fields"]):
                                field = FormField(
                                    form_id=form.id,
                                    name=field_data.get("name", f"field_{position}"),
                                    label=field_data.get("label"),
                                    type=field_data.get("type", "text"),
                                    required=field_data.get("required", False),
                                    position=position,
                                    placeholder=field_data.get("placeholder"),
                                    help_text=field_data.get("help_text"),
                                    default_value=field_data.get("default_value"),
                                    options=field_data.get("options"),
                                    data_provider=field_data.get("data_provider"),
                                    data_provider_inputs=field_data.get("data_provider_inputs"),
                                    visibility_expression=field_data.get("visibility_expression"),
                                    validation=field_data.get("validation"),
                                    allowed_types=field_data.get("allowed_types"),
                                    multiple=field_data.get("multiple"),
                                    max_size_mb=field_data.get("max_size_mb"),
                                    content=field_data.get("content"),
                                )
                                db.add(field)

                        logger.debug(f"Synced form '{form_name}' from file")

                    elif op_type == "deactivate":
                        form_id_str: str = data
                        # Try to find by ID first
                        try:
                            form_uuid = UUIDType(form_id_str)
                            result = await db.execute(
                                select(Form).where(Form.id == form_uuid)
                            )
                            form = result.scalar_one_or_none()
                        except (ValueError, TypeError):
                            form = None

                        # Try by name if not found
                        if not form:
                            result = await db.execute(
                                select(Form).where(Form.name == form_id_str)
                            )
                            form = result.scalar_one_or_none()

                        if form:
                            form.is_active = False

                processed += 1

            except Exception as e:
                logger.error(f"Error processing DB op ({op_type}, {entity_type}): {e}", exc_info=True)

        await db.commit()

    if processed > 0:
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


def python_files_need_sync() -> bool:
    """
    Check if Python files changed and need a full import-based sync.

    Returns True if Python files changed since last check, and clears the flag.
    """
    if _python_files_changed.is_set():
        _python_files_changed.clear()
        return True
    return False
