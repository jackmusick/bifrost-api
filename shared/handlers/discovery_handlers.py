"""
Discovery Handlers
Business logic for workflow and data provider metadata discovery.
Extracted from functions/discovery.py for unit testability.
"""

import logging
from typing import Any

from pydantic import ValidationError
from shared.models import DataProviderMetadata, MetadataResponse, WorkflowMetadata
from shared.registry import get_registry

logger = logging.getLogger(__name__)


def extract_relative_path(source_file_path: str | None) -> str | None:
    """
    Extract workspace-relative file path from absolute path.

    Args:
        source_file_path: Absolute file path (e.g., /path/to/workspace/repo/workflows/my_workflow.py)

    Returns:
        Relative path after /home/, /platform/, or /workspace/ (e.g., workflows/my_workflow.py)
        Returns None if source_file_path is None or no marker found
    """
    if not source_file_path:
        return None

    # Extract everything after /home/, /platform/, or /workspace/
    for marker in ['/home/', '/platform/', '/workspace/']:
        if marker in source_file_path:
            return source_file_path.split(marker, 1)[1]

    return None


def convert_registry_workflow_to_model(
    registry_workflow: Any,
) -> WorkflowMetadata:
    """
    Convert a registry WorkflowMetadata dataclass to a Pydantic model.

    Args:
        registry_workflow: Workflow metadata from registry (dataclass)

    Returns:
        WorkflowMetadata Pydantic model for API response
    """
    # Convert parameters from registry dataclass to dict with proper field mapping
    parameters = []
    if registry_workflow.parameters:
        for p in registry_workflow.parameters:
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

    return WorkflowMetadata(
        name=registry_workflow.name,
        description=registry_workflow.description,
        category=registry_workflow.category,
        tags=registry_workflow.tags,
        parameters=parameters,
        executionMode=registry_workflow.execution_mode,
        timeoutSeconds=registry_workflow.timeout_seconds,
        retryPolicy=registry_workflow.retry_policy,
        schedule=registry_workflow.schedule,
        endpointEnabled=registry_workflow.endpoint_enabled,
        allowedMethods=registry_workflow.allowed_methods,
        disableGlobalKey=registry_workflow.disable_global_key,
        publicEndpoint=registry_workflow.public_endpoint,
        source=registry_workflow.source,
        sourceFilePath=registry_workflow.source_file_path,
        relativeFilePath=extract_relative_path(registry_workflow.source_file_path),
    )


def convert_registry_provider_to_model(
    registry_provider: Any,
) -> DataProviderMetadata:
    """
    Convert a registry DataProviderMetadata dataclass to a Pydantic model.

    Args:
        registry_provider: Provider metadata from registry (dataclass)

    Returns:
        DataProviderMetadata Pydantic model for API response
    """
    # Convert parameters from registry dataclass to dict with proper field mapping (T024)
    parameters = []
    if registry_provider.parameters:
        for p in registry_provider.parameters:
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

    source_file_path = getattr(registry_provider, 'source_file_path', None)
    return DataProviderMetadata(
        name=registry_provider.name,
        description=registry_provider.description,
        category=registry_provider.category,
        cache_ttl_seconds=registry_provider.cache_ttl_seconds,
        parameters=parameters,
        sourceFilePath=source_file_path,
        relativeFilePath=extract_relative_path(source_file_path),
    )


def get_discovery_metadata() -> MetadataResponse:
    """
    Retrieve discovery metadata for all registered workflows and data providers.

    This is the core business logic for the discovery endpoint. It:
    1. Gets the registry singleton
    2. Converts all registered workflows to Pydantic models
    3. Converts all registered data providers to Pydantic models
    4. Returns a MetadataResponse object

    Validation errors are caught and logged to system_logger, with offending
    items skipped from the response.

    Returns:
        MetadataResponse with workflows and dataProviders lists

    Raises:
        Exception: If registry access fails (logged and propagated)
    """
    logger.info("Retrieving discovery metadata")

    # Get registry singleton
    registry = get_registry()

    # Get all workflows from registry and convert to models
    # Skip workflows that fail validation and log to system logger
    workflows = []
    for w in registry.get_all_workflows():
        try:
            workflow_model = convert_registry_workflow_to_model(w)
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

    # Get all data providers from registry and convert to models
    # Skip data providers that fail validation and log to system logger
    data_providers = []
    for dp in registry.get_all_data_providers():
        try:
            provider_model = convert_registry_provider_to_model(dp)
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

    logger.info(
        f"Retrieved metadata: {len(workflows)} workflows, "
        f"{len(data_providers)} data providers"
    )

    # Build and return response
    response = MetadataResponse(
        workflows=workflows,
        dataProviders=data_providers,
    )

    return response
