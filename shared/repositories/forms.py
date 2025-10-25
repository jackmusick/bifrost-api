"""
Form Repository
Manages forms with workflow index for efficient "forms by workflow" queries

Indexes maintained:
1. Primary: form:{uuid} (Entities table)
2. Workflow index: workflowform:{workflow_name}:{form_id} (Relationships table)
"""

import json
import logging
from datetime import datetime
from typing import TYPE_CHECKING, cast

from shared.models import CreateFormRequest, Form, FormSchema, UpdateFormRequest, generate_entity_id
from shared.storage import TableStorageService

from .scoped_repository import ScopedRepository

if TYPE_CHECKING:
    from shared.context import ExecutionContext

logger = logging.getLogger(__name__)


class FormRepository(ScopedRepository):
    """
    Repository for workflow forms

    Manages form records with workflow index for efficient queries like:
    - "What forms use the CreateUserWorkflow?"
    - "List all forms linked to this workflow"

    Supports org-scoped and global forms with automatic fallback.
    """

    def __init__(self, context: 'ExecutionContext'):
        super().__init__("Entities", context)
        self.relationships_service = TableStorageService("Relationships")

    def create_form(
        self,
        form_request: CreateFormRequest,
        created_by: str
    ) -> Form:
        """
        Create form with workflow index

        Writes to:
        1. Entities table (primary form record)
        2. Relationships table (workflow index for "forms by workflow" queries)

        Args:
            form_request: Form creation request
            created_by: User ID creating the form

        Returns:
            Created Form model

        Raises:
            Exception: If form or index creation fails
        """
        form_id = generate_entity_id()
        now = datetime.utcnow()

        # Determine partition key based on isGlobal flag
        partition_key = "GLOBAL" if form_request.isGlobal else self.scope

        # 1. Primary form record (Entities table)
        form_entity = {
            "PartitionKey": partition_key,
            "RowKey": f"form:{form_id}",
            "Name": form_request.name,
            "Description": form_request.description,
            "LinkedWorkflow": form_request.linkedWorkflow,
            "FormSchema": json.dumps(form_request.formSchema.model_dump()),
            "IsActive": True,
            "AccessLevel": form_request.accessLevel.value if form_request.accessLevel else "role_based",
            "CreatedBy": created_by,
            "CreatedAt": now.isoformat(),
            "UpdatedAt": now.isoformat(),
            # NEW MVP fields (T012)
            "LaunchWorkflowId": form_request.launchWorkflowId,
            "AllowedQueryParams": json.dumps(form_request.allowedQueryParams) if form_request.allowedQueryParams is not None else None,
            "DefaultLaunchParams": json.dumps(form_request.defaultLaunchParams) if form_request.defaultLaunchParams is not None else None,
        }

        # 2. Workflow index (for "what forms use this workflow?")
        workflow_index_entity = {
            "PartitionKey": "GLOBAL",
            "RowKey": f"workflowform:{form_request.linkedWorkflow}:{form_id}",
            "FormId": form_id,
            "FormName": form_request.name,  # Display field for list views
            "IsActive": True,  # Display field for filtering
            "AccessLevel": form_request.accessLevel.value if form_request.accessLevel else "role_based",  # Display field
            "PartitionKey_Original": partition_key,  # Track where form lives
            "CreatedAt": now.isoformat(),
        }

        try:
            # Write primary record
            self.insert(form_entity)

            # Write workflow index
            self.relationships_service.insert_entity(workflow_index_entity)

            logger.info(
                f"Created form {form_id} in partition {partition_key} "
                f"(workflow={form_request.linkedWorkflow}, isGlobal={form_request.isGlobal})"
            )

            return self._entity_to_model(form_entity, form_id)

        except Exception as e:
            logger.error(f"Failed to create form {form_id}: {e}", exc_info=True)
            # TODO: Add cleanup/rollback logic
            raise

    def get_form(self, form_id: str) -> Form | None:
        """
        Get form by ID with org → GLOBAL fallback

        Args:
            form_id: Form ID (UUID)

        Returns:
            Form model or None if not found
        """
        entity = self.get_with_fallback(f"form:{form_id}")

        if entity:
            return self._entity_to_model(entity, form_id)

        return None

    def list_forms(
        self,
        active_only: bool = True,
        include_global: bool = True
    ) -> list[Form]:
        """
        List forms visible to current user

        Args:
            active_only: Only return active forms
            include_global: Include global forms (default True)

        Returns:
            List of Form models
        """
        additional_filter = "IsActive eq true" if active_only else None

        if include_global:
            # Query both org and GLOBAL partitions
            entities = self.query_with_fallback("form:", additional_filter=additional_filter)
        else:
            # Query only org partition
            entities = self.query_org_only("form:", additional_filter=additional_filter)

        forms = []
        for entity in entities:
            form_id = entity["RowKey"].split(":", 1)[1]
            forms.append(self._entity_to_model(entity, form_id))

        logger.info(
            f"Found {len(forms)} forms "
            f"(active_only={active_only}, include_global={include_global})"
        )

        return forms

    def list_forms_by_workflow(
        self,
        workflow_name: str,
        active_only: bool = True
    ) -> list[Form]:
        """
        List forms that use a specific workflow (optimized with index)

        Uses workflow index for efficient query - NO full table scan!

        Args:
            workflow_name: Workflow name to filter by
            active_only: Only return active forms

        Returns:
            List of Form models
        """
        # Query workflow index
        filter_query = (
            f"PartitionKey eq 'GLOBAL' and "
            f"RowKey ge 'workflowform:{workflow_name}:' and "
            f"RowKey lt 'workflowform:{workflow_name}~'"
        )

        if active_only:
            filter_query += " and IsActive eq true"

        index_entities = list(self.relationships_service.query_entities(filter_query))

        # Fetch full form records
        forms = []
        for index_entity in index_entities:
            form_id = index_entity.get("FormId")
            if form_id:
                form = self.get_form(form_id)
                if form:
                    forms.append(form)

        logger.info(f"Found {len(forms)} forms using workflow {workflow_name}")
        return forms

    def update_form(
        self,
        form_id: str,
        updates: UpdateFormRequest
    ) -> Form:
        """
        Update form and RE-INDEX if workflow changed

        If LinkedWorkflow changes, we must:
        1. Delete old workflow index
        2. Create new workflow index

        Args:
            form_id: Form ID
            updates: Update request

        Returns:
            Updated Form model

        Raises:
            ValueError: If form not found
        """
        # Get existing form
        form_entity = self.get_with_fallback(f"form:{form_id}")

        if not form_entity:
            raise ValueError(f"Form {form_id} not found")

        old_workflow = form_entity.get("LinkedWorkflow")
        new_workflow = updates.linkedWorkflow
        now = datetime.utcnow()

        # Update form entity fields
        if updates.name is not None:
            form_entity["Name"] = updates.name

        if updates.description is not None:
            form_entity["Description"] = updates.description

        if updates.linkedWorkflow is not None:
            form_entity["LinkedWorkflow"] = updates.linkedWorkflow

        if updates.formSchema is not None:
            form_entity["FormSchema"] = json.dumps(updates.formSchema.model_dump())

        if updates.isActive is not None:
            form_entity["IsActive"] = updates.isActive

        # NEW MVP fields (T012)
        if updates.launchWorkflowId is not None:
            form_entity["LaunchWorkflowId"] = updates.launchWorkflowId

        if updates.allowedQueryParams is not None:
            form_entity["AllowedQueryParams"] = json.dumps(updates.allowedQueryParams)

        if updates.defaultLaunchParams is not None:
            form_entity["DefaultLaunchParams"] = json.dumps(updates.defaultLaunchParams)

        form_entity["UpdatedAt"] = now.isoformat()

        # Save primary record
        self.update(form_entity)

        # RE-INDEX if workflow changed
        if new_workflow and new_workflow != old_workflow:
            try:
                # Delete old workflow index
                if old_workflow:
                    self.relationships_service.delete_entity(
                        "GLOBAL",
                        f"workflowform:{old_workflow}:{form_id}"
                    )
                    logger.debug(f"Deleted old workflow index: {old_workflow}")

                # Create new workflow index
                workflow_index_entity = {
                    "PartitionKey": "GLOBAL",
                    "RowKey": f"workflowform:{new_workflow}:{form_id}",
                    "FormId": form_id,
                    "FormName": form_entity.get("Name"),
                    "IsActive": form_entity.get("IsActive", True),
                    "IsPublic": form_entity.get("IsPublic", False),
                    "PartitionKey_Original": form_entity["PartitionKey"],
                    "UpdatedAt": now.isoformat(),
                }
                self.relationships_service.insert_entity(workflow_index_entity)

                logger.info(f"Re-indexed form {form_id}: {old_workflow} → {new_workflow}")

            except Exception as e:
                logger.error(f"Failed to re-index form {form_id}: {e}", exc_info=True)
                # Continue - primary record was updated successfully

        # Also update workflow index display fields if form name or active status changed
        elif (updates.name is not None or updates.isActive is not None) and old_workflow:
            try:
                workflow_index = self.relationships_service.get_entity(
                    "GLOBAL",
                    f"workflowform:{old_workflow}:{form_id}"
                )
                if workflow_index:
                    if updates.name is not None:
                        workflow_index["FormName"] = updates.name
                    if updates.isActive is not None:
                        workflow_index["IsActive"] = updates.isActive
                    workflow_index["UpdatedAt"] = now.isoformat()
                    self.relationships_service.update_entity(workflow_index)
                    logger.debug(f"Updated workflow index display fields for form {form_id}")
            except Exception as e:
                logger.warning(f"Failed to update workflow index display fields: {e}")

        logger.info(f"Updated form {form_id}")
        return self._entity_to_model(form_entity, form_id)

    def soft_delete_form(self, form_id: str) -> bool:
        """
        Soft delete form (set IsActive=False)

        Also updates workflow index to mark form as inactive.

        Args:
            form_id: Form ID

        Returns:
            True if deleted, False if not found
        """
        # Get existing form
        form_entity = self.get_with_fallback(f"form:{form_id}")

        if not form_entity:
            return False

        workflow_name = form_entity.get("LinkedWorkflow")
        now = datetime.utcnow()

        # Soft delete primary record
        form_entity["IsActive"] = False
        form_entity["UpdatedAt"] = now.isoformat()
        self.update(form_entity)

        # Update workflow index to mark inactive
        if workflow_name:
            try:
                workflow_index = self.relationships_service.get_entity(
                    "GLOBAL",
                    f"workflowform:{workflow_name}:{form_id}"
                )
                if workflow_index:
                    workflow_index["IsActive"] = False
                    workflow_index["UpdatedAt"] = now.isoformat()
                    self.relationships_service.update_entity(workflow_index)
            except Exception as e:
                logger.warning(f"Failed to update workflow index on soft delete: {e}")

        logger.info(f"Soft deleted form {form_id}")
        return True

    def delete_form(self, form_id: str) -> bool:
        """
        Permanently delete form.

        WARNING: This is a hard delete. Use soft_delete_form for soft delete.

        Args:
            form_id: Form ID to permanently delete

        Returns:
            True if deleted, False if not found
        """
        # Find existing form
        form_entity = self.get_with_fallback(f"form:{form_id}")

        if not form_entity:
            logger.info(f"Cannot delete form {form_id}: Not found")
            return False

        workflow_name = form_entity.get("LinkedWorkflow")

        try:
            # Delete primary record
            partition_key = form_entity["PartitionKey"]
            self.delete(partition_key, f"form:{form_id}")

            # Delete workflow index if exists
            if workflow_name:
                self.relationships_service.delete_entity(
                    "GLOBAL",
                    f"workflowform:{workflow_name}:{form_id}"
                )

            logger.info(f"Permanently deleted form {form_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete form {form_id}: {e}", exc_info=True)
            return False

    def _entity_to_model(self, entity: dict, form_id: str) -> Form:
        """
        Convert entity dict to Form model

        Args:
            entity: Entity dictionary from table storage
            form_id: Form ID (extracted from RowKey)

        Returns:
            Form model
        """
        # Parse FormSchema from JSON string
        form_schema_raw = entity.get("FormSchema")
        form_schema = None
        if form_schema_raw:
            if isinstance(form_schema_raw, str):
                schema_dict = json.loads(form_schema_raw)
                form_schema = FormSchema(**schema_dict)
            elif isinstance(form_schema_raw, dict):
                form_schema = FormSchema(**form_schema_raw)

        # Parse datetime fields (cast because _parse_datetime with default always returns datetime)
        created_at = cast(datetime, self._parse_datetime(entity.get("CreatedAt"), datetime.utcnow()))
        updated_at = cast(datetime, self._parse_datetime(entity.get("UpdatedAt"), datetime.utcnow()))

        # Parse AllowedQueryParams from JSON string (NEW MVP field)
        allowed_query_params = None
        allowed_query_params_raw = entity.get("AllowedQueryParams")
        if allowed_query_params_raw:
            if isinstance(allowed_query_params_raw, str):
                allowed_query_params = json.loads(allowed_query_params_raw)
            elif isinstance(allowed_query_params_raw, list):
                allowed_query_params = allowed_query_params_raw

        # Parse DefaultLaunchParams from JSON string (NEW MVP field)
        default_launch_params = None
        default_launch_params_raw = entity.get("DefaultLaunchParams")
        if default_launch_params_raw:
            if isinstance(default_launch_params_raw, str):
                default_launch_params = json.loads(default_launch_params_raw)
            elif isinstance(default_launch_params_raw, dict):
                default_launch_params = default_launch_params_raw

        return Form(
            id=form_id,
            orgId=cast(str, entity.get("PartitionKey", "")),
            name=cast(str, entity.get("Name", "")),
            description=entity.get("Description"),
            linkedWorkflow=cast(str, entity.get("LinkedWorkflow", "")),
            formSchema=cast(FormSchema, form_schema) if form_schema else FormSchema(fields=[]),
            isActive=entity.get("IsActive", True),
            isGlobal=entity.get("PartitionKey") == "GLOBAL",
            accessLevel=entity.get("AccessLevel"),  # Will default to None if not set
            createdBy=cast(str, entity.get("CreatedBy", "")),
            createdAt=created_at,
            updatedAt=updated_at,
            # NEW MVP fields (T012)
            launchWorkflowId=entity.get("LaunchWorkflowId"),
            allowedQueryParams=allowed_query_params,
            defaultLaunchParams=default_launch_params,
        )
