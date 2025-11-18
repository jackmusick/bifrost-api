"""
Forms Registry
Singleton registry for storing form metadata with lazy-loading support
"""

import json
import logging
import threading
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

import aiofiles

from shared.models import Form, FormAccessLevel, FormSchema

logger = logging.getLogger(__name__)


@dataclass
class FormMetadata:
    """Lightweight form metadata for caching"""
    id: str
    name: str
    linkedWorkflow: str
    orgId: str
    isActive: bool
    isGlobal: bool
    accessLevel: FormAccessLevel | None
    filePath: str
    createdAt: datetime
    updatedAt: datetime
    launchWorkflowId: str | None = None


class FormsRegistry:
    """
    Singleton registry for forms with lazy-loading
    Thread-safe storage of form metadata with on-demand full form loading
    """

    _instance: Optional['FormsRegistry'] = None
    _lock = threading.Lock()

    def __new__(cls):
        """Singleton pattern - only one instance exists"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Initialize registry storage (only runs once)"""
        if self._initialized:
            return

        self._forms: dict[str, FormMetadata] = {}  # Keyed by form ID
        self._initialized = True
        logger.info("FormsRegistry initialized")

    def load_all_forms(self, workspace_paths: list[Path]) -> None:
        """
        Scan workspace directories for *.form.json files and load metadata

        Args:
            workspace_paths: List of workspace directories to scan
        """
        # Load all forms into a temporary dict first (outside lock for better performance)
        temp_forms = {}
        forms_loaded = 0

        for workspace_path in workspace_paths:
            if not workspace_path.exists():
                logger.warning(f"Workspace path does not exist: {workspace_path}")
                continue

            # Recursively find all *.form.json files
            for form_file in workspace_path.rglob("*.form.json"):
                try:
                    metadata = self._load_form_metadata_sync(form_file)
                    temp_forms[metadata.id] = metadata
                    forms_loaded += 1
                    logger.debug(f"Loaded form metadata: {metadata.name} (id={metadata.id})")
                except Exception as e:
                    logger.error(f"Failed to load form from {form_file}: {e}", exc_info=True)

        # Atomically replace the entire registry with loaded forms
        with self._lock:
            self._forms = temp_forms

        logger.info(f"Loaded {forms_loaded} forms into registry")

    def _load_form_metadata_sync(self, file_path: Path) -> FormMetadata:
        """
        Load lightweight metadata from form JSON file (synchronous)

        Args:
            file_path: Path to *.form.json file

        Returns:
            FormMetadata object

        Raises:
            Exception: If file cannot be read or parsed
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Parse datetime fields
        created_at = datetime.fromisoformat(data['createdAt'].replace('Z', '+00:00'))
        updated_at = datetime.fromisoformat(data['updatedAt'].replace('Z', '+00:00'))

        # Parse accessLevel enum
        access_level = None
        if data.get('accessLevel'):
            access_level = FormAccessLevel(data['accessLevel'])

        return FormMetadata(
            id=data['id'],
            name=data['name'],
            linkedWorkflow=data['linkedWorkflow'],
            orgId=data['orgId'],
            isActive=data.get('isActive', True),
            isGlobal=data.get('isGlobal', False),
            accessLevel=access_level,
            filePath=str(file_path),
            createdAt=created_at,
            updatedAt=updated_at,
            launchWorkflowId=data.get('launchWorkflowId')
        )

    async def _load_form_metadata(self, file_path: Path) -> FormMetadata:
        """
        Load lightweight metadata from form JSON file

        Args:
            file_path: Path to *.form.json file

        Returns:
            FormMetadata object

        Raises:
            Exception: If file cannot be read or parsed
        """
        async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
            content = await f.read()
            data = json.loads(content)

        # Parse datetime fields
        created_at = datetime.fromisoformat(data['createdAt'].replace('Z', '+00:00'))
        updated_at = datetime.fromisoformat(data['updatedAt'].replace('Z', '+00:00'))

        # Parse accessLevel enum
        access_level = None
        if data.get('accessLevel'):
            access_level = FormAccessLevel(data['accessLevel'])

        return FormMetadata(
            id=data['id'],
            name=data['name'],
            linkedWorkflow=data['linkedWorkflow'],
            orgId=data['orgId'],
            isActive=data.get('isActive', True),
            isGlobal=data.get('isGlobal', False),
            accessLevel=access_level,
            filePath=str(file_path),
            createdAt=created_at,
            updatedAt=updated_at,
            launchWorkflowId=data.get('launchWorkflowId')
        )

    async def get_form_metadata(self, form_id: str) -> FormMetadata | None:
        """
        Get cached form metadata (fast, no file I/O)

        Args:
            form_id: Form ID

        Returns:
            FormMetadata or None if not found
        """
        return self._forms.get(form_id)

    async def get_form_full(self, form_id: str) -> Form | None:
        """
        Load full form from file (lazy-loading)

        Args:
            form_id: Form ID

        Returns:
            Full Form model or None if not found
        """
        metadata = self._forms.get(form_id)
        if not metadata:
            return None

        try:
            async with aiofiles.open(metadata.filePath, 'r', encoding='utf-8') as f:
                content = await f.read()
                data = json.loads(content)

            # Parse FormSchema
            form_schema = FormSchema(**data['formSchema'])

            # Parse datetime fields
            created_at = datetime.fromisoformat(data['createdAt'].replace('Z', '+00:00'))
            updated_at = datetime.fromisoformat(data['updatedAt'].replace('Z', '+00:00'))

            # Parse accessLevel enum
            access_level = None
            if data.get('accessLevel'):
                access_level = FormAccessLevel(data['accessLevel'])

            return Form(
                id=data['id'],
                orgId=data['orgId'],
                name=data['name'],
                description=data.get('description'),
                linkedWorkflow=data['linkedWorkflow'],
                formSchema=form_schema,
                isActive=data.get('isActive', True),
                isGlobal=data.get('isGlobal', False),
                accessLevel=access_level,
                createdBy=data['createdBy'],
                createdAt=created_at,
                updatedAt=updated_at,
                launchWorkflowId=data.get('launchWorkflowId'),
                allowedQueryParams=data.get('allowedQueryParams'),
                defaultLaunchParams=data.get('defaultLaunchParams')
            )

        except Exception as e:
            logger.error(f"Failed to load full form {form_id}: {e}", exc_info=True)
            return None

    def get_all_metadata(self) -> list[FormMetadata]:
        """
        Get all cached form metadata (fast, no file I/O)

        Returns:
            List of FormMetadata objects
        """
        return list(self._forms.values())

    async def reload_form(self, file_path: Path) -> None:
        """
        Reload form metadata when file changes (for hot-reload)

        Args:
            file_path: Path to *.form.json file that changed
        """
        try:
            metadata = await self._load_form_metadata(file_path)
            with self._lock:
                self._forms[metadata.id] = metadata
            logger.info(f"Reloaded form: {metadata.name} (id={metadata.id})")
        except Exception as e:
            logger.error(f"Failed to reload form from {file_path}: {e}", exc_info=True)

    async def add_form(self, metadata: FormMetadata) -> None:
        """
        Add new form to registry cache

        Args:
            metadata: FormMetadata to add
        """
        with self._lock:
            self._forms[metadata.id] = metadata
        logger.info(f"Added form to registry: {metadata.name} (id={metadata.id})")

    def remove_form(self, form_id: str) -> None:
        """
        Remove form from registry cache

        Args:
            form_id: Form ID to remove
        """
        with self._lock:
            if form_id in self._forms:
                form_name = self._forms[form_id].name
                del self._forms[form_id]
                logger.info(f"Removed form from registry: {form_name} (id={form_id})")

    def get_forms_by_workflow(self, workflow_name: str) -> list[FormMetadata]:
        """
        Get all forms that link to a specific workflow (filter in-memory)

        Args:
            workflow_name: Workflow name to filter by

        Returns:
            List of FormMetadata objects
        """
        return [
            form for form in self._forms.values()
            if form.linkedWorkflow == workflow_name
        ]

    def clear_all(self) -> None:
        """Clear all registered forms (for testing)"""
        with self._lock:
            self._forms.clear()
            logger.info("Forms registry cleared")

    def get_form_count(self) -> int:
        """Get total number of registered forms"""
        return len(self._forms)


# Convenience function to get singleton instance
def get_forms_registry() -> FormsRegistry:
    """Get the singleton FormsRegistry instance"""
    return FormsRegistry()
