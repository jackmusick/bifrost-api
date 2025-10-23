"""
Data Providers Handlers
Business logic for data provider discovery and option retrieval
Extracted from functions/data_providers.py for unit testability
"""

import hashlib
import json
import logging
from datetime import datetime, timedelta
from typing import Any

from shared.models import ErrorResponse
from shared.registry import get_registry

# TYPE_CHECKING import for type hints
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from shared.request_context import RequestContext

logger = logging.getLogger(__name__)

# Simple in-memory cache for data provider results
# In production, this would use Redis or Azure Cache
_cache: dict[str, dict[str, Any]] = {}


def validate_data_provider_inputs(
    provider_metadata: "DataProviderMetadata",
    inputs: dict[str, Any] | None
) -> list[str]:
    """
    Validate input parameters against data provider parameter definitions (T025).

    Args:
        provider_metadata: Data provider metadata with parameter definitions
        inputs: Input values provided by caller

    Returns:
        List of validation error messages (empty if valid)

    Validation rules:
        1. All required parameters must be present in inputs
        2. Input values must match expected types (basic validation)
        3. Extra inputs (not defined in parameters) are allowed (forward compatibility)
    """
    errors = []
    inputs = inputs or {}

    # Check required parameters
    for param in provider_metadata.parameters:
        if param.required and param.name not in inputs:
            errors.append(
                f"Required parameter '{param.name}' is missing"
            )

    # Note: We allow extra inputs for forward compatibility
    # This allows forms to pass inputs that may be used by future provider versions

    return errors


def compute_cache_key(provider_name: str, inputs: dict[str, Any] | None = None, org_id: str | None = None) -> str:
    """
    Compute cache key for data provider with inputs (T012).

    Args:
        provider_name: Name of the data provider
        inputs: Input parameter values (optional)
        org_id: Organization ID (optional)

    Returns:
        Cache key string

    Format:
        - Without inputs: "{org_id}:{provider_name}"
        - With inputs: "{org_id}:{provider_name}:{input_hash}"
    """
    if not inputs:
        # Backward compatible format
        return f"{org_id}:{provider_name}" if org_id else provider_name

    # Sort keys for deterministic hash
    input_str = json.dumps(inputs, sort_keys=True)
    input_hash = hashlib.sha256(input_str.encode()).hexdigest()[:16]

    if org_id:
        return f"{org_id}:{provider_name}:{input_hash}"
    else:
        return f"{provider_name}:{input_hash}"


async def get_data_provider_options_handler(
    provider_name: str,
    context: "RequestContext",
    no_cache: bool = False,
    inputs: dict[str, Any] | None = None
) -> tuple[dict[str, Any], int]:
    """
    Call a data provider and return options.

    Args:
        provider_name: Name of the data provider
        context: RequestContext with organization context
        no_cache: If True, bypass cache
        inputs: Optional input parameter values for the data provider (T024)

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

    # Get provider from registry
    registry = get_registry()
    provider_metadata = registry.get_data_provider(provider_name)

    if not provider_metadata:
        logger.warning(f"Data provider not found: {provider_name}")
        error = ErrorResponse(
            error="NotFound",
            message=f"Data provider '{provider_name}' not found"
        )
        return error.model_dump(), 404

    # T025: Validate input parameters against provider parameter definitions
    validation_errors = validate_data_provider_inputs(provider_metadata, inputs)
    if validation_errors:
        error = ErrorResponse(
            error="BadRequest",
            message="Invalid or missing required parameters",
            details={"errors": validation_errors}
        )
        return error.model_dump(), 400

    # Get provider function
    provider_func = provider_metadata.function
    cache_ttl = provider_metadata.cache_ttl_seconds

    # T026: Compute cache key with inputs hash (if inputs provided)
    cache_key = compute_cache_key(
        provider_name=provider_name,
        inputs=inputs,
        org_id=context.org_id
    )
    cached_result = None
    cache_expires_at = None

    if not no_cache and cache_key in _cache:
        cached_entry = _cache[cache_key]
        expires_at = cached_entry['expires_at']

        # Check if cache is still valid
        if datetime.utcnow() < expires_at:
            cached_result = cached_entry['data']
            cache_expires_at = expires_at.isoformat() + "Z"
            logger.info(
                f"Cache hit for data provider: {provider_name}",
                extra={
                    "provider": provider_name,
                    "org_id": context.org_id,
                    "expires_at": cache_expires_at
                }
            )

    # Call provider if not cached
    if cached_result is None:
        try:
            logger.info(
                f"Calling data provider: {provider_name}",
                extra={
                    "provider": provider_name,
                    "org_id": context.org_id,
                    "inputs": inputs if inputs else {}
                }
            )

            # T027: Call provider function with validated inputs as kwargs
            if inputs and provider_metadata.parameters:
                # Provider has parameters - pass inputs as keyword arguments
                options = await provider_func(context, **inputs)
            else:
                # No parameters or no inputs - call with context only (backward compatible)
                options = await provider_func(context)

            # Validate options format (basic check)
            if not isinstance(options, list):
                raise ValueError(
                    f"Data provider must return a list, got {type(options).__name__}")

            # Cache the result
            expires_at = datetime.utcnow() + timedelta(seconds=cache_ttl)
            _cache[cache_key] = {
                'data': options,
                'expires_at': expires_at
            }
            cache_expires_at = expires_at.isoformat() + "Z"

            logger.info(
                f"Data provider executed successfully: {provider_name}",
                extra={
                    "provider": provider_name,
                    "options_count": len(options),
                    "cached_until": cache_expires_at
                }
            )

            # Build response
            response = {
                "provider": provider_name,
                "options": options,
                "cached": False,
                "cache_expires_at": cache_expires_at
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

    # Return cached result
    response = {
        "provider": provider_name,
        "options": cached_result,
        "cached": True,
        "cache_expires_at": cache_expires_at
    }

    return response, 200


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
    registry = get_registry()
    providers = registry.get_all_data_providers()

    # Convert to response format (T031 - include parameters for User Story 1)
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
