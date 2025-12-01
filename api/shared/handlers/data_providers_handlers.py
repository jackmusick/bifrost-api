"""
Data Providers Handlers
Business logic for data provider discovery and option retrieval
Routes execution through the unified engine for SDK access
"""

import logging
import uuid
from typing import Any, TYPE_CHECKING

from shared.context import Caller
from shared.discovery import load_data_provider, scan_all_data_providers
from shared.engine import ExecutionRequest, execute
from shared.models import ErrorResponse, ExecutionStatus

if TYPE_CHECKING:
    from shared.context import ExecutionContext

logger = logging.getLogger(__name__)


def validate_data_provider_inputs(
    provider_metadata,
    inputs: dict[str, Any] | None
) -> list[str]:
    """
    Validate input parameters against data provider parameter definitions.

    Args:
        provider_metadata: Data provider metadata with parameter definitions
        inputs: Input values provided by caller

    Returns:
        List of validation error messages (empty if valid)

    Validation rules:
        1. All required parameters must be present in inputs
        2. Extra inputs (not defined in parameters) are allowed (forward compatibility)
    """
    errors = []
    inputs = inputs or {}

    # Check required parameters
    for param in provider_metadata.parameters:
        if param.required and param.name not in inputs:
            errors.append(
                f"Required parameter '{param.name}' is missing"
            )

    return errors


async def get_data_provider_options_handler(
    provider_name: str,
    context: "ExecutionContext",
    no_cache: bool = False,
    inputs: dict[str, Any] | None = None
) -> tuple[dict[str, Any], int]:
    """
    Call a data provider and return options.

    Routes execution through the unified engine to provide full SDK access
    (config, secrets, oauth, etc.) while maintaining lightweight execution
    (no DB tracking via transient=True).

    Args:
        provider_name: Name of the data provider
        context: ExecutionContext with organization context
        no_cache: If True, bypass cache
        inputs: Optional input parameter values for the data provider

    Returns:
        Tuple of (response_dict, status_code)

    Response structure:
        {
            "provider": "get_available_licenses",
            "options": [
                {
                    "label": "Microsoft 365 E3",
                    "value": "SPE_E3",
                    "metadata": { ... }
                }
            ],
            "cached": False,
            "cache_expires_at": "2025-10-10T12:05:00Z"
        }

    Status codes:
        200: Success
        400: Missing or invalid provider name, or invalid/missing required parameters
        404: Provider not found
        500: Provider execution error
    """
    if not provider_name:
        error = ErrorResponse(
            error="BadRequest",
            message="providerName is required"
        )
        return error.model_dump(), 400

    # Dynamically load data provider (always fresh import)
    try:
        result = load_data_provider(provider_name)
        if not result:
            logger.warning(f"Data provider not found: {provider_name}")
            error = ErrorResponse(
                error="NotFound",
                message=f"Data provider '{provider_name}' not found"
            )
            return error.model_dump(), 404

        provider_func, provider_metadata = result
        logger.debug(f"Loaded data provider fresh: {provider_name}")
    except Exception as e:
        # Load failed (likely syntax error)
        logger.error(f"Failed to load data provider {provider_name}: {e}", exc_info=True)
        error = ErrorResponse(
            error="DataProviderLoadError",
            message=f"Failed to load data provider '{provider_name}': {str(e)}"
        )
        return error.model_dump(), 500

    # Validate input parameters against provider parameter definitions
    validation_errors = validate_data_provider_inputs(provider_metadata, inputs)
    if validation_errors:
        error = ErrorResponse(
            error="BadRequest",
            message="Invalid or missing required parameters",
            details={"errors": validation_errors}
        )
        return error.model_dump(), 400

    # Execute through unified engine (provides SDK context, caching, etc.)
    try:
        logger.info(
            f"Executing data provider via engine: {provider_name}",
            extra={
                "provider": provider_name,
                "org_id": context.org_id,
                "inputs": inputs if inputs else {}
            }
        )

        request = ExecutionRequest(
            execution_id=str(uuid.uuid4()),
            caller=Caller(
                user_id=context.user_id,
                email=context.email,
                name=context.name
            ),
            organization=context.organization,
            config=context._config,
            func=provider_func,
            name=provider_name,
            tags=["data_provider"],
            cache_ttl_seconds=provider_metadata.cache_ttl_seconds,
            parameters=inputs or {},
            transient=True,  # No execution tracking for data providers
            no_cache=no_cache,
            is_platform_admin=context.is_platform_admin
        )

        result = await execute(request)

        # Handle execution result
        if result.status != ExecutionStatus.SUCCESS:
            logger.error(
                f"Data provider execution failed: {provider_name}",
                extra={
                    "provider": provider_name,
                    "error": result.error_message,
                    "error_type": result.error_type
                }
            )
            # Build error details - include logs for platform admins
            details: dict[str, Any] = {"provider": provider_name}
            if context.is_platform_admin and result.logs:
                # Extract log messages for admin visibility
                details["logs"] = [
                    log.get("message", str(log)) if isinstance(log, dict) else str(log)
                    for log in result.logs
                ]
            error = ErrorResponse(
                error="InternalError",
                message=f"Failed to execute data provider: {result.error_message}",
                details=details
            )
            return error.model_dump(), 500

        options = result.result

        # Validate options format (basic check)
        if not isinstance(options, list):
            error = ErrorResponse(
                error="InternalError",
                message=f"Data provider must return a list, got {type(options).__name__}",
                details={"provider": provider_name}
            )
            return error.model_dump(), 500

        logger.info(
            f"Data provider executed successfully: {provider_name}",
            extra={
                "provider": provider_name,
                "options_count": len(options),
                "cached": result.cached
            }
        )

        # Build response
        response = {
            "provider": provider_name,
            "options": options,
            "cached": result.cached,
            "cache_expires_at": result.cache_expires_at
        }

        return response, 200

    except Exception as e:
        logger.error(
            f"Error executing data provider: {provider_name}",
            extra={
                "provider": provider_name,
                "error": str(e)
            },
            exc_info=True
        )

        error = ErrorResponse(
            error="InternalError",
            message=f"Failed to execute data provider: {str(e)}",
            details={"provider": provider_name}
        )

        return error.model_dump(), 500


async def list_data_providers_handler() -> tuple[dict[str, Any], int]:
    """
    List all available data providers.

    Returns:
        Tuple of (response_dict, status_code)

    Response structure:
        {
            "providers": [
                {
                    "name": "get_available_licenses",
                    "description": "Returns available M365 licenses",
                    "category": "m365",
                    "cache_ttl_seconds": 300
                }
            ]
        }

    Status codes:
        200: Success
    """
    # Dynamically scan all data providers (always fresh)
    providers = scan_all_data_providers()

    # Convert to response format (include parameters)
    provider_list = [
        {
            "name": p.name,
            "description": p.description,
            "category": p.category,
            "cache_ttl_seconds": p.cache_ttl_seconds,
            "parameters": [
                {
                    "name": param.name,
                    "type": param.type,
                    "required": param.required,
                    "label": param.label,
                    "defaultValue": param.default_value,
                    "helpText": param.help_text,
                }
                for param in (p.parameters or [])
            ]
        }
        for p in providers
    ]

    response = {
        "providers": provider_list
    }

    return response, 200
