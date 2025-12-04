"""
Discovery Handlers
Business logic for workflow and data provider metadata discovery.
Uses dynamic discovery for always-fresh metadata.
"""

import logging
from typing import Any, TYPE_CHECKING

from pydantic import ValidationError
from shared.models import DataProviderMetadata as DataProviderMetadataModel, FormDiscoveryMetadata, MetadataResponse, WorkflowMetadata as WorkflowMetadataModel
from shared.discovery import scan_all_workflows, scan_all_data_providers, scan_all_forms

if TYPE_CHECKING:
    from shared.context import ExecutionContext

logger = logging.getLogger(__name__)


def extract_relative_path(source_file_path: str | None) -> str | None:
    """
    Extract workspace-relative file path from absolute path.

    Args:
        source_file_path: Absolute file path (e.g., /path/to/workspace/repo/workflows/my_workflow.py)

    Returns:
        Relative path after workspace root (e.g., workflows/my_workflow.py)
        Returns None if source_file_path is None or no marker found
    """
    if not source_file_path:
        return None

    import os
    from pathlib import Path

    # Get workspace location from environment
    workspace_location = os.getenv("BIFROST_WORKSPACE_LOCATION")
    if workspace_location:
        workspace_path = Path(workspace_location)
        source_path = Path(source_file_path)

        # Check if source_path is relative to workspace
        try:
            relative = source_path.relative_to(workspace_path)
            return str(relative)
        except ValueError:
            # Not relative to workspace, fall through to marker check
            pass

    # Fallback: Extract everything after /home/, /platform/, or /workspace/ markers
    for marker in ['/home/', '/platform/', '/workspace/']:
        if marker in source_file_path:
            return source_file_path.split(marker, 1)[1]

    return None


def convert_workflow_metadata_to_model(
    workflow_metadata: Any,
) -> WorkflowMetadataModel:
    """
    Convert a discovery WorkflowMetadata dataclass to a Pydantic model.

    Args:
        workflow_metadata: Workflow metadata from discovery (dataclass)

    Returns:
        WorkflowMetadata Pydantic model for API response
    """
    # Convert parameters from dataclass to dict with proper field mapping
    parameters = []
    if workflow_metadata.parameters:
        for p in workflow_metadata.parameters:
            param_dict = {
                "name": p.name,
                "type": p.type,
                "required": p.required,
            }
            # Add optional fields only if they're not None
            if p.label is not None:
                param_dict["label"] = p.label
            if p.data_provider is not None:
                param_dict["dataProvider"] = p.data_provider
            if p.default_value is not None:
                param_dict["defaultValue"] = p.default_value
            if p.help_text is not None:
                param_dict["helpText"] = p.help_text
            if p.validation is not None:
                param_dict["validation"] = p.validation
            if hasattr(p, 'description') and p.description is not None:
                param_dict["description"] = p.description
            parameters.append(param_dict)

    return WorkflowMetadataModel(
        name=workflow_metadata.name,
        description=workflow_metadata.description,
        category=workflow_metadata.category,
        tags=workflow_metadata.tags,
        parameters=parameters,
        executionMode=workflow_metadata.execution_mode,
        timeoutSeconds=workflow_metadata.timeout_seconds,
        retryPolicy=workflow_metadata.retry_policy,
        schedule=workflow_metadata.schedule,
        endpointEnabled=workflow_metadata.endpoint_enabled,
        allowedMethods=workflow_metadata.allowed_methods,
        disableGlobalKey=workflow_metadata.disable_global_key,
        publicEndpoint=workflow_metadata.public_endpoint,
        source=workflow_metadata.source,
        sourceFilePath=workflow_metadata.source_file_path,
        relativeFilePath=extract_relative_path(workflow_metadata.source_file_path),
    )


def convert_data_provider_metadata_to_model(
    provider_metadata: Any,
) -> DataProviderMetadataModel:
    """
    Convert a discovery DataProviderMetadata dataclass to a Pydantic model.

    Args:
        provider_metadata: Provider metadata from discovery (dataclass)

    Returns:
        DataProviderMetadata Pydantic model for API response
    """
    # Convert parameters from dataclass to dict with proper field mapping (T024)
    parameters = []
    if provider_metadata.parameters:
        for p in provider_metadata.parameters:
            param_dict = {
                "name": p.name,
                "type": p.type,
                "required": p.required,
            }
            # Add optional fields only if they're not None
            if p.label is not None:
                param_dict["label"] = p.label
            if p.default_value is not None:
                param_dict["defaultValue"] = p.default_value
            if p.help_text is not None:
                param_dict["helpText"] = p.help_text
            if hasattr(p, 'description') and p.description is not None:
                param_dict["description"] = p.description
            parameters.append(param_dict)

    source_file_path = getattr(provider_metadata, 'source_file_path', None)
    return DataProviderMetadataModel(
        name=provider_metadata.name,
        description=provider_metadata.description,
        category=provider_metadata.category,
        cache_ttl_seconds=provider_metadata.cache_ttl_seconds,
        parameters=parameters,
        sourceFilePath=source_file_path,
        relativeFilePath=extract_relative_path(source_file_path),
    )


async def get_discovery_metadata(context: 'ExecutionContext | None' = None) -> MetadataResponse:
    """
    Retrieve discovery metadata for all workflows, data providers, and forms.

    This is the core business logic for the discovery endpoint. It:
    1. Dynamically scans all workflows fresh from workspace directories
    2. Dynamically scans all data providers fresh from workspace directories
    3. Dynamically scans all forms fresh from workspace directories
    4. Filters forms based on user permissions (if context provided)
    5. Returns a MetadataResponse object

    Validation errors are caught and logged to system_logger, with offending
    items skipped from the response.

    Args:
        context: Optional ExecutionContext for permission filtering

    Returns:
        MetadataResponse with workflows, dataProviders, and forms lists
    """
    logger.info("Retrieving discovery metadata (dynamic scan)")

    # Dynamically scan all workflows and convert to models
    # Skip workflows that fail validation and log to system logger
    workflows = []
    for w in scan_all_workflows():
        try:
            workflow_model = convert_workflow_metadata_to_model(w)
            workflows.append(workflow_model)
        except ValidationError as e:
            logger.error(
                f"Validation failed for workflow '{w.name}': {e}",
                exc_info=True
            )
            # Log to system logger for visibility
            try:
                from shared.system_logger import get_system_logger
                import asyncio
                system_logger = get_system_logger()
                # Create task and keep reference to avoid "coroutine never awaited" warning
                task = asyncio.create_task(system_logger.log_validation_failure(
                    item_type="workflow",
                    item_name=w.name,
                    error=str(e),
                    source=w.source
                ))
                # Suppress exceptions in fire-and-forget task
                task.add_done_callback(lambda t: t.exception() if not t.cancelled() else None)
            except Exception as log_error:
                logger.warning(f"Failed to log validation failure: {log_error}")

    # Dynamically scan all data providers and convert to models
    # Skip data providers that fail validation and log to system logger
    data_providers = []
    for dp in scan_all_data_providers():
        try:
            provider_model = convert_data_provider_metadata_to_model(dp)
            data_providers.append(provider_model)
        except ValidationError as e:
            logger.error(
                f"Validation failed for data provider '{dp.name}': {e}",
                exc_info=True
            )
            # Log to system logger for visibility
            try:
                from shared.system_logger import get_system_logger
                import asyncio
                system_logger = get_system_logger()
                # Create task and keep reference to avoid "coroutine never awaited" warning
                task = asyncio.create_task(system_logger.log_validation_failure(
                    item_type="data_provider",
                    item_name=dp.name,
                    error=str(e),
                    source=getattr(dp, 'source', None)
                ))
                # Suppress exceptions in fire-and-forget task
                task.add_done_callback(lambda t: t.exception() if not t.cancelled() else None)
            except Exception as log_error:
                logger.warning(f"Failed to log validation failure: {log_error}")

    # Get forms - either filtered by permissions or all (for backward compatibility)
    forms = []
    if context:
        # Use authorization logic to get filtered forms
        from shared.handlers.forms_handlers import get_user_visible_forms
        user_forms_dicts = await get_user_visible_forms(context)

        # Convert dicts to FormDiscoveryMetadata models
        for form_dict in user_forms_dicts:
            try:
                form_model = FormDiscoveryMetadata(
                    id=form_dict['id'],
                    name=form_dict['name'],
                    linkedWorkflow=form_dict['linkedWorkflow'],
                    orgId=form_dict['orgId'],
                    isActive=form_dict['isActive'],
                    isGlobal=form_dict.get('isGlobal', False),
                    accessLevel=form_dict.get('accessLevel'),
                    createdAt=form_dict['createdAt'],
                    updatedAt=form_dict['updatedAt'],
                    launchWorkflowId=form_dict.get('launchWorkflowId')
                )
                forms.append(form_model)
            except (ValidationError, KeyError) as e:
                logger.error(
                    f"Validation failed for form '{form_dict.get('name', 'unknown')}': {e}",
                    exc_info=True
                )
    else:
        # No context provided - scan all forms dynamically
        for form_metadata in scan_all_forms():
            try:
                form_model = FormDiscoveryMetadata(
                    id=form_metadata.id,
                    name=form_metadata.name,
                    linkedWorkflow=form_metadata.linkedWorkflow,
                    orgId=form_metadata.orgId,
                    isActive=form_metadata.isActive,
                    isGlobal=form_metadata.isGlobal,
                    accessLevel=form_metadata.accessLevel,
                    createdAt=form_metadata.createdAt,
                    updatedAt=form_metadata.updatedAt,
                    launchWorkflowId=form_metadata.launchWorkflowId
                )
                forms.append(form_model)
            except ValidationError as e:
                logger.error(
                    f"Validation failed for form '{form_metadata.name}': {e}",
                    exc_info=True
                )

    logger.info(
        f"Retrieved metadata: {len(workflows)} workflows, "
        f"{len(data_providers)} data providers, "
        f"{len(forms)} forms"
    )

    # Build and return response
    response = MetadataResponse(
        workflows=workflows,
        dataProviders=data_providers,
        forms=forms,
    )

    return response
