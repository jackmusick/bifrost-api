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
from pydantic import ValidationError

from src.models.schemas import Form, FormAccessLevel, FormSchema, FormValidationIssue

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
        self._validation_errors: list[FormValidationIssue] = []  # Validation errors from loading
        self._workspace_path: Path | None = None  # For relative path calculation
        self._initialized = True
        logger.info("FormsRegistry initialized")

    def load_all_forms(self, workspace_paths: list[Path]) -> None:
        """
        Scan workspace directories for *.form.json files and load metadata.

        Also validates forms proactively and stores validation errors for later retrieval.

        Args:
            workspace_paths: List of workspace directories to scan
        """
        # Load all forms into a temporary dict first (outside lock for better performance)
        temp_forms = {}
        temp_errors: list[FormValidationIssue] = []
        forms_loaded = 0
        forms_scanned = 0

        # Use first workspace path for relative path calculation
        workspace_path_for_relative = workspace_paths[0] if workspace_paths else None
        self._workspace_path = workspace_path_for_relative

        for workspace_path in workspace_paths:
            if not workspace_path.exists():
                logger.warning(f"Workspace path does not exist: {workspace_path}")
                continue

            # Recursively find all *.form.json and form.json files
            form_files = list(workspace_path.rglob("*.form.json")) + list(workspace_path.rglob("form.json"))
            for form_file in form_files:
                forms_scanned += 1
                try:
                    # Load metadata (basic parsing)
                    metadata = self._load_form_metadata_sync(form_file)
                    temp_forms[metadata.id] = metadata

                    # Proactively validate the full form schema
                    validation_errors = self._validate_form_schema_sync(form_file, workspace_path)
                    if validation_errors:
                        temp_errors.extend(validation_errors)
                        logger.warning(
                            f"Form has validation errors: {metadata.name} ({len(validation_errors)} errors)")
                    else:
                        forms_loaded += 1
                        logger.debug(f"Loaded form metadata: {metadata.name} (id={metadata.id})")

                except Exception as e:
                    # Create validation issue for load errors
                    relative_path = self._get_relative_path(form_file, workspace_path)
                    form_name = self._extract_form_name_from_file(form_file)
                    temp_errors.append(FormValidationIssue(
                        file_path=relative_path,
                        file_name=form_file.name,
                        form_name=form_name,
                        error_message=str(e),
                        field_name=None,
                        field_index=None
                    ))
                    logger.error(f"Failed to load form from {form_file}: {e}", exc_info=True)

        # Atomically replace the entire registry with loaded forms and errors
        with self._lock:
            self._forms = temp_forms
            self._validation_errors = temp_errors

        logger.info(
            f"Loaded {forms_loaded} forms into registry "
            f"({forms_scanned} scanned, {len(temp_errors)} validation errors)")

    def _get_relative_path(self, file_path: Path, workspace_path: Path) -> str:
        """Get relative path from workspace for a file"""
        try:
            return str(file_path.relative_to(workspace_path))
        except ValueError:
            return str(file_path)

    def _extract_form_name_from_file(self, file_path: Path) -> str | None:
        """Try to extract form name from file without full validation"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('name')
        except Exception:
            return None

    def _validate_form_schema_sync(
        self, file_path: Path, workspace_path: Path
    ) -> list[FormValidationIssue]:
        """
        Validate form schema and return any validation errors.

        Args:
            file_path: Path to form file
            workspace_path: Root workspace path for relative paths

        Returns:
            List of FormValidationIssue (empty if valid)
        """
        issues: list[FormValidationIssue] = []
        relative_path = self._get_relative_path(file_path, workspace_path)

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            form_name = data.get('name')

            # Check for formSchema
            if 'formSchema' not in data:
                issues.append(FormValidationIssue(
                    file_path=relative_path,
                    file_name=file_path.name,
                    form_name=form_name,
                    error_message="Missing 'formSchema' field",
                    field_name=None,
                    field_index=None
                ))
                return issues

            # Validate FormSchema using Pydantic
            try:
                FormSchema(**data['formSchema'])
            except ValidationError as e:
                # Parse Pydantic validation errors
                for error in e.errors():
                    loc = error.get('loc', [])
                    msg = error.get('msg', str(error))

                    # Extract field info from location
                    field_name = None
                    field_index = None
                    for i, part in enumerate(loc):
                        if part == 'fields' and i + 1 < len(loc):
                            idx = loc[i + 1]
                            if isinstance(idx, int):
                                field_index = idx
                                # Try to get field name from data
                                fields = data['formSchema'].get('fields', [])
                                if field_index < len(fields):
                                    field_name = fields[field_index].get('name')

                    # Build human-readable error message
                    loc_str = '.'.join(str(x) for x in loc)
                    error_message = f"{loc_str}: {msg}" if loc_str else msg

                    issues.append(FormValidationIssue(
                        file_path=relative_path,
                        file_name=file_path.name,
                        form_name=form_name,
                        error_message=error_message,
                        field_name=field_name,
                        field_index=field_index
                    ))

        except json.JSONDecodeError as e:
            issues.append(FormValidationIssue(
                file_path=relative_path,
                file_name=file_path.name,
                form_name=None,
                error_message=f"Invalid JSON: {e}",
                field_name=None,
                field_index=None
            ))
        except Exception as e:
            issues.append(FormValidationIssue(
                file_path=relative_path,
                file_name=file_path.name,
                form_name=None,
                error_message=str(e),
                field_name=None,
                field_index=None
            ))

        return issues

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

        # Parse datetime fields (optional for workspace forms)
        now = datetime.utcnow()
        created_at = now
        updated_at = now
        if data.get('createdAt'):
            created_at = datetime.fromisoformat(data['createdAt'].replace('Z', '+00:00'))
        if data.get('updatedAt'):
            updated_at = datetime.fromisoformat(data['updatedAt'].replace('Z', '+00:00'))

        # Parse accessLevel enum
        access_level = None
        if data.get('accessLevel'):
            access_level = FormAccessLevel(data['accessLevel'])

        # Generate ID from file path if not provided (for workspace forms)
        form_id = data.get('id') or f"workspace-{file_path.stem}"

        # For workspace forms, orgId defaults to GLOBAL if isGlobal=true, else empty
        org_id = data.get('orgId', 'GLOBAL' if data.get('isGlobal', False) else '')

        return FormMetadata(
            id=form_id,
            name=data['name'],
            linkedWorkflow=data['linkedWorkflow'],
            orgId=org_id,
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

        # Parse datetime fields (optional for workspace forms)
        now = datetime.utcnow()
        created_at = now
        updated_at = now
        if data.get('createdAt'):
            created_at = datetime.fromisoformat(data['createdAt'].replace('Z', '+00:00'))
        if data.get('updatedAt'):
            updated_at = datetime.fromisoformat(data['updatedAt'].replace('Z', '+00:00'))

        # Parse accessLevel enum
        access_level = None
        if data.get('accessLevel'):
            access_level = FormAccessLevel(data['accessLevel'])

        # Generate ID from file path if not provided (for workspace forms)
        form_id = data.get('id') or f"workspace-{file_path.stem}"

        # For workspace forms, orgId defaults to GLOBAL if isGlobal=true, else empty
        org_id = data.get('orgId', 'GLOBAL' if data.get('isGlobal', False) else '')

        return FormMetadata(
            id=form_id,
            name=data['name'],
            linkedWorkflow=data['linkedWorkflow'],
            orgId=org_id,
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

            file_path = Path(metadata.filePath)

            # Parse FormSchema
            form_schema = FormSchema(**data['formSchema'])

            # Parse datetime fields (optional for workspace forms)
            now = datetime.utcnow()
            created_at = now
            updated_at = now
            if data.get('createdAt'):
                created_at = datetime.fromisoformat(data['createdAt'].replace('Z', '+00:00'))
            if data.get('updatedAt'):
                updated_at = datetime.fromisoformat(data['updatedAt'].replace('Z', '+00:00'))

            # Parse accessLevel enum
            access_level = None
            if data.get('accessLevel'):
                access_level = FormAccessLevel(data['accessLevel'])

            # Generate ID from file path if not provided (for workspace forms)
            actual_id = data.get('id') or f"workspace-{file_path.stem}"

            # For workspace forms, orgId defaults to GLOBAL if isGlobal=true, else empty
            org_id = data.get('orgId', 'GLOBAL' if data.get('isGlobal', False) else '')

            return Form(
                id=actual_id,
                orgId=org_id,
                name=data['name'],
                description=data.get('description'),
                linkedWorkflow=data['linkedWorkflow'],
                formSchema=form_schema,
                isActive=data.get('isActive', True),
                isGlobal=data.get('isGlobal', False),
                accessLevel=access_level,
                createdBy=data.get('createdBy', 'workspace'),
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
            self._validation_errors.clear()
            logger.info("Forms registry cleared")

    def get_form_count(self) -> int:
        """Get total number of registered forms"""
        return len(self._forms)

    def get_validation_errors(self) -> list[FormValidationIssue]:
        """
        Get all validation errors from the last form load.

        Returns:
            List of FormValidationIssue objects
        """
        return list(self._validation_errors)

    def get_valid_form_count(self) -> int:
        """Get number of forms that loaded without validation errors"""
        # Forms that have metadata but no validation errors
        error_paths = {e.file_path for e in self._validation_errors}
        return sum(
            1 for form in self._forms.values()
            if self._get_relative_path_from_metadata(form) not in error_paths
        )

    def _get_relative_path_from_metadata(self, metadata: FormMetadata) -> str:
        """Get relative path from metadata.filePath"""
        if self._workspace_path:
            try:
                return str(Path(metadata.filePath).relative_to(self._workspace_path))
            except ValueError:
                pass
        return metadata.filePath

    def get_scan_stats(self) -> dict:
        """
        Get statistics about form scanning.

        Returns:
            Dict with scanned_forms, valid_forms, error_count
        """
        error_count = len(self._validation_errors)
        total_forms = len(self._forms)
        # Valid forms = forms without errors
        valid_count = self.get_valid_form_count()

        return {
            "scanned_forms": total_forms,
            "valid_forms": valid_count,
            "error_count": error_count
        }


# Convenience function to get singleton instance
def get_forms_registry() -> FormsRegistry:
    """Get the singleton FormsRegistry instance"""
    return FormsRegistry()
