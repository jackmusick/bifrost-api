"""
Data Provider API Endpoint
Handles calling data providers and returning options for forms
"""

import azure.functions as func
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List

from engine.shared.middleware import with_org_context
from engine.shared.registry import get_registry
from engine.shared.models import ErrorResponse

logger = logging.getLogger(__name__)

# Create blueprint for data provider endpoints
bp = func.Blueprint()

# Simple in-memory cache for data provider results
# In production, this would use Redis or Azure Cache
_cache: Dict[str, Dict[str, Any]] = {}


@bp.route(route="data-providers/{providerName}", methods=["GET"], auth_level=func.AuthLevel.ADMIN)
@with_org_context
async def get_data_provider_options(req: func.HttpRequest) -> func.HttpResponse:
    """
    Call a data provider and return options.

    Headers:
        X-Organization-Id: Organization ID (required)

    Path Parameters:
        providerName: Name of the data provider

    Query Parameters:
        no_cache: Set to "true" to bypass cache

    Response:
        200: {
            "provider": "get_available_licenses",
            "options": [
                {
                    "label": "Microsoft 365 E3",
                    "value": "SPE_E3",
                    "metadata": { ... }
                }
            ],
            "cached": false,
            "cache_expires_at": "2025-10-10T12:05:00Z"
        }
        404: Provider not found
        500: Provider execution error
    """
    # Get context from request (injected by @with_org_context decorator)
    context = req.context

    provider_name = req.route_params.get('providerName')
    no_cache = req.params.get('no_cache', '').lower() == 'true'

    # Get provider from registry
    registry = get_registry()
    provider_metadata = registry.get_data_provider(provider_name)

    if not provider_metadata:
        logger.warning(f"Data provider not found: {provider_name}")
        error = ErrorResponse(
            error="NotFound",
            message=f"Data provider '{provider_name}' not found"
        )
        return func.HttpResponse(
            json.dumps(error.model_dump()),
            status_code=404,
            mimetype="application/json"
        )

    # Get provider function
    provider_func = provider_metadata.function
    cache_ttl = provider_metadata.cache_ttl_seconds

    # Check cache (keyed by org_id + provider_name)
    cache_key = f"{context.org_id}:{provider_name}"
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
                    "org_id": context.org_id
                }
            )

            # Call provider function
            options = await provider_func(context)

            # Validate options format (basic check)
            if not isinstance(options, list):
                raise ValueError(f"Data provider must return a list, got {type(options).__name__}")

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

            return func.HttpResponse(
                json.dumps(response, default=str),
                status_code=200,
                mimetype="application/json"
            )

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

            return func.HttpResponse(
                json.dumps(error.model_dump()),
                status_code=500,
                mimetype="application/json"
            )

    # Return cached result
    response = {
        "provider": provider_name,
        "options": cached_result,
        "cached": True,
        "cache_expires_at": cache_expires_at
    }

    return func.HttpResponse(
        json.dumps(response, default=str),
        status_code=200,
        mimetype="application/json"
    )


@bp.route(route="data-providers", methods=["GET"])
def list_data_providers(req: func.HttpRequest) -> func.HttpResponse:
    """
    List all available data providers.

    Response:
        200: {
            "providers": [
                {
                    "name": "get_available_licenses",
                    "description": "Returns available M365 licenses",
                    "category": "m365",
                    "cache_ttl_seconds": 300
                }
            ]
        }
    """
    registry = get_registry()
    providers = registry.get_all_data_providers()

    # Convert to response format
    provider_list = [
        {
            "name": p.name,
            "description": p.description,
            "category": p.category,
            "cache_ttl_seconds": p.cache_ttl_seconds
        }
        for p in providers
    ]

    response = {
        "providers": provider_list
    }

    return func.HttpResponse(
        json.dumps(response),
        status_code=200,
        mimetype="application/json"
    )
