"""
Forms File Repository
Manages forms stored as *.forms.json files in workspace with dynamic discovery
"""

import json
import logging
import os
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

import aiofiles

from shared.discovery import (
    scan_all_forms,
    load_form,
    get_form_metadata,
    get_forms_by_workflow,
    FormMetadata,
)
from shared.models import CreateFormRequest, Form, UpdateFormRequest, generate_entity_id

if TYPE_CHECKING:
    from shared.context import ExecutionContext

logger = logging.getLogger(__name__)


def generate_form_filename(form_name: str) -> str:
    """
    Generate filesystem-safe filename from form name

    Args:
        form_name: Human-readable form name

    Returns:
        Slugified filename (e.g., "simple-greeting.form.json")
    """
    # Convert to lowercase and replace non-alphanumeric chars with hyphens
    slug = re.sub(r'[^a-z0-9]+', '-', form_name.lower()).strip('-')
    # Limit length and ensure uniqueness via timestamp microseconds
    timestamp_suffix = datetime.utcnow().strftime("%f")[:6]  # 6-digit microsecond
    return f"{slug[:50]}-{timestamp_suffix}.form.json"


class FormsFileRepository:
    """
    Repository for forms stored as files

    Uses dynamic discovery for form lookups. Forms are always read fresh from disk.
    Role assignments still stored in Table Storage (Relationships table).
    """

    def __init__(self, context: 'ExecutionContext'):
        self.context = context
        self.workspace_location = Path(os.environ["BIFROST_WORKSPACE_LOCATION"])

    async def create_form(
        self,
        form_request: CreateFormRequest,
        created_by: str
    ) -> Form:
        """
        Create form by writing JSON file

        Args:
            form_request: Form creation request
            created_by: User ID creating the form

        Returns:
            Created Form model

        Raises:
            Exception: If file write fails
        """
        form_id = generate_entity_id()
        now = datetime.utcnow()

        # Determine orgId based on isGlobal flag
        org_id: str = "GLOBAL" if form_request.isGlobal else (self.context.org_id or "GLOBAL")

        # Generate unique filename
        filename = generate_form_filename(form_request.name)
        file_path = self.workspace_location / filename

        # Ensure file doesn't already exist (extremely unlikely with timestamp)
        if file_path.exists():
            raise ValueError(f"Form file already exists: {filename}")

        # Build form data
        form_data = {
            "id": form_id,
            "orgId": org_id,
            "name": form_request.name,
            "description": form_request.description,
            "linkedWorkflow": form_request.linkedWorkflow,
            "formSchema": form_request.formSchema.model_dump(),
            "isActive": True,
            "isGlobal": form_request.isGlobal,
            "accessLevel": form_request.accessLevel.value if form_request.accessLevel else "role_based",
            "createdBy": created_by,
            "createdAt": now.isoformat() + "Z",
            "updatedAt": now.isoformat() + "Z",
            "launchWorkflowId": form_request.launchWorkflowId,
            "allowedQueryParams": form_request.allowedQueryParams,
            "defaultLaunchParams": form_request.defaultLaunchParams,
        }

        # Write JSON file
        async with aiofiles.open(file_path, 'w', encoding='utf-8') as f:
            await f.write(json.dumps(form_data, indent=2))

        logger.info(
            f"Created form {form_id} in {filename} "
            f"(workflow={form_request.linkedWorkflow}, isGlobal={form_request.isGlobal})"
        )

        # Read back the form as a Form model (dynamic discovery will find it next scan)
        form = self._dict_to_form(form_data)
        return form

    def _dict_to_form(self, data: dict) -> Form:
        """Convert a form dict to a Form model."""
        from shared.models import FormSchema, FormAccessLevel

        # Parse dates - provide defaults for file-based forms
        now = datetime.utcnow()
        created_at = data.get('createdAt')
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
        elif created_at is None:
            created_at = now

        updated_at = data.get('updatedAt')
        if isinstance(updated_at, str):
            updated_at = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
        elif updated_at is None:
            updated_at = now

        # Parse form schema
        form_schema_data = data.get('formSchema', {})
        form_schema = FormSchema(**form_schema_data) if form_schema_data else None

        # Parse access level
        access_level = data.get('accessLevel')
        if access_level and isinstance(access_level, str):
            access_level = FormAccessLevel(access_level)

        return Form(
            id=data['id'],
            orgId=data.get('orgId', 'GLOBAL'),
            name=data['name'],
            description=data.get('description'),
            linkedWorkflow=data['linkedWorkflow'],
            formSchema=form_schema,  # type: ignore[arg-type]
            isActive=data.get('isActive', True),
            isGlobal=data.get('isGlobal', False),
            accessLevel=access_level,
            createdBy=data.get('createdBy', 'system'),
            createdAt=created_at,
            updatedAt=updated_at,
            launchWorkflowId=data.get('launchWorkflowId'),
            allowedQueryParams=data.get('allowedQueryParams'),
            defaultLaunchParams=data.get('defaultLaunchParams'),
        )

    async def get_form(self, form_id: str) -> Form | None:
        """
        Get form by ID with org scope filtering

        Args:
            form_id: Form ID (UUID)

        Returns:
            Form model or None if not found or not accessible
        """
        # Get metadata using dynamic discovery
        metadata = get_form_metadata(form_id)

        if not metadata:
            logger.debug(f"Form {form_id} not found")
            return None

        # Apply org scope filtering (skip for platform admins)
        if not self.context.is_platform_admin:
            if metadata.orgId != "GLOBAL" and metadata.orgId != self.context.org_id:
                logger.debug(f"Form {form_id} not accessible (org mismatch)")
                return None

        # Load full form data from file
        form_data = load_form(form_id)
        if not form_data:
            logger.warning(f"Form {form_id} metadata found but data missing")
            return None

        return self._dict_to_form(form_data)

    async def list_forms(
        self,
        active_only: bool = True,
        include_global: bool = True
    ) -> list[Form]:
        """
        List forms visible to current user

        Uses dynamic discovery for filtering, then loads full forms.

        Args:
            active_only: Only return active forms
            include_global: Include global forms (default True)

        Returns:
            List of Form models
        """
        all_metadata = scan_all_forms()

        # Filter by org scope
        if include_global:
            filtered = [
                m for m in all_metadata
                if m.orgId == self.context.org_id or m.orgId == "GLOBAL"
            ]
        else:
            filtered = [m for m in all_metadata if m.orgId == self.context.org_id]

        # Filter by active status
        if active_only:
            filtered = [m for m in filtered if m.isActive]

        # Load full forms
        forms = []
        for metadata in filtered:
            form_data = load_form(metadata.id)
            if form_data:
                forms.append(self._dict_to_form(form_data))

        logger.info(
            f"Found {len(forms)} forms "
            f"(active_only={active_only}, include_global={include_global})"
        )

        return forms

    async def list_forms_by_workflow(
        self,
        workflow_name: str,
        active_only: bool = True
    ) -> list[Form]:
        """
        List forms that use a specific workflow (filter in-memory)

        Args:
            workflow_name: Workflow name to filter by
            active_only: Only return active forms

        Returns:
            List of Form models
        """
        # Get forms by workflow using dynamic discovery
        metadata_list = get_forms_by_workflow(workflow_name)

        # Apply active filter
        if active_only:
            metadata_list = [m for m in metadata_list if m.isActive]

        # Apply org scope filter
        metadata_list = [
            m for m in metadata_list
            if m.orgId == self.context.org_id or m.orgId == "GLOBAL"
        ]

        # Load full forms
        forms = []
        for metadata in metadata_list:
            form_data = load_form(metadata.id)
            if form_data:
                forms.append(self._dict_to_form(form_data))

        logger.info(f"Found {len(forms)} forms using workflow {workflow_name}")
        return forms

    async def update_form(
        self,
        form_id: str,
        updates: UpdateFormRequest
    ) -> Form:
        """
        Update form by overwriting JSON file

        Args:
            form_id: Form ID
            updates: Update request

        Returns:
            Updated Form model

        Raises:
            ValueError: If form not found or not accessible
        """
        # Get existing form
        form = await self.get_form(form_id)
        if not form:
            raise ValueError(f"Form {form_id} not found or not accessible")

        metadata = get_form_metadata(form_id)
        if not metadata:
            raise ValueError(f"Form {form_id} metadata not found")

        file_path = Path(metadata.filePath)
        if not file_path.exists():
            raise ValueError(f"Form file not found: {metadata.filePath}")

        now = datetime.utcnow()

        # Load current form data
        async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
            form_data = json.loads(await f.read())

        # Apply updates
        if updates.name is not None:
            form_data["name"] = updates.name

        if updates.description is not None:
            form_data["description"] = updates.description

        if updates.linkedWorkflow is not None:
            form_data["linkedWorkflow"] = updates.linkedWorkflow

        if updates.formSchema is not None:
            form_data["formSchema"] = updates.formSchema.model_dump()

        if updates.isActive is not None:
            form_data["isActive"] = updates.isActive

        if updates.launchWorkflowId is not None:
            form_data["launchWorkflowId"] = updates.launchWorkflowId

        if updates.allowedQueryParams is not None:
            form_data["allowedQueryParams"] = updates.allowedQueryParams

        if updates.defaultLaunchParams is not None:
            form_data["defaultLaunchParams"] = updates.defaultLaunchParams

        form_data["updatedAt"] = now.isoformat() + "Z"

        # Write updated JSON file (atomic write via temp file)
        temp_file = file_path.with_suffix('.tmp')
        try:
            async with aiofiles.open(temp_file, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(form_data, indent=2))

            # Atomic replace
            temp_file.replace(file_path)

            logger.info(f"Updated form {form_id}")

            # Return updated form (dynamic discovery will find it fresh)
            return self._dict_to_form(form_data)

        except Exception as e:
            # Clean up temp file if it exists
            if temp_file.exists():
                temp_file.unlink()
            raise e

    async def soft_delete_form(self, form_id: str) -> bool:
        """
        Soft delete form (set IsActive=False)

        Args:
            form_id: Form ID

        Returns:
            True if deleted, False if not found
        """
        try:
            await self.update_form(form_id, UpdateFormRequest(isActive=False))  # type: ignore[call-arg]
            logger.info(f"Soft deleted form {form_id}")
            return True
        except ValueError:
            return False

    async def delete_form(self, form_id: str) -> bool:
        """
        Permanently delete form by moving to .archived/ directory

        Args:
            form_id: Form ID to permanently delete

        Returns:
            True if deleted, False if not found
        """
        # Get metadata using dynamic discovery
        metadata = get_form_metadata(form_id)
        if not metadata:
            logger.info(f"Cannot delete form {form_id}: Not found")
            return False

        # Check org scope
        if metadata.orgId != "GLOBAL" and metadata.orgId != self.context.org_id:
            logger.info(f"Cannot delete form {form_id}: Not accessible (org mismatch)")
            return False

        file_path = Path(metadata.filePath)
        if not file_path.exists():
            logger.warning(f"Form file not found: {metadata.filePath}")
            return False

        # Create .archived directory if it doesn't exist
        archived_dir = self.workspace_location / ".archived"
        archived_dir.mkdir(exist_ok=True)

        # Move file to .archived directory
        archived_path = archived_dir / file_path.name
        try:
            shutil.move(str(file_path), str(archived_path))
            logger.info(f"Moved form {form_id} to .archived/{file_path.name}")

            return True

        except Exception as e:
            logger.error(f"Failed to archive form {form_id}: {e}", exc_info=True)
            return False
