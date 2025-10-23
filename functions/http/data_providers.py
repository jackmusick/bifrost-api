"""
Data Provider API Endpoint
HTTP handlers for calling data providers and returning options for forms
Business logic delegated to shared/handlers/data_providers_handlers.py
"""

import json
import logging

import azure.functions as func
from pydantic import BaseModel

from shared.custom_types import get_org_context
from shared.handlers.data_providers_handlers import (
    get_data_provider_options_handler,
    list_data_providers_handler
)
from shared.middleware import with_org_context
from shared.models import DataProviderMetadata, DataProviderRequest, DataProviderResponse
from shared.openapi_decorators import openapi_endpoint

logger = logging.getLogger(__name__)

# Create blueprint for data provider endpoints
bp = func.Blueprint()


@bp.function_name("data_providers_get_options")
@bp.route(route="data-providers/{providerName}", methods=["GET"])
@openapi_endpoint(
    path="/data-providers/{providerName}",
    method="GET",
    summary="Get data provider options",
    description="Call a data provider and return options",
    tags=["Data Providers"],
    response_model=DataProviderResponse,
    path_params={
        "providerName": {
            "description": "Name of the data provider",
            "schema": {"type": "string"},
            "required": True
        }
    },
    query_params={
        "no_cache": {
            "description": "Set to 'true' to bypass cache",
            "schema": {"type": "string"},
            "required": False
        }
    }
)
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
    context = get_org_context(req)

    provider_name = req.route_params.get('providerName') or ""
    no_cache = req.params.get('no_cache', '').lower() == 'true'

    # Delegate to handler (business logic layer)
    response_dict, status_code = await get_data_provider_options_handler(
        provider_name=provider_name,
        context=context,
        no_cache=no_cache
    )

    return func.HttpResponse(
        json.dumps(response_dict, default=str),
        status_code=status_code,
        mimetype="application/json"
    )


@bp.function_name("data_providers_get_options_with_inputs")
@bp.route(route="data-providers/{providerName}", methods=["POST"])
@openapi_endpoint(
    path="/data-providers/{providerName}",
    method="POST",
    summary="Get data provider options with inputs",
    description="Call a data provider with input parameters and return options (T032)",
    tags=["Data Providers"],
    request_model=DataProviderRequest,
    response_model=DataProviderResponse,
    path_params={
        "providerName": {
            "description": "Name of the data provider",
            "schema": {"type": "string"},
            "required": True
        }
    }
)
@with_org_context
async def get_data_provider_options_with_inputs(req: func.HttpRequest) -> func.HttpResponse:
    """
    Call a data provider with input parameters and return options (T032).

    Headers:
        X-Organization-Id: Organization ID (required)

    Path Parameters:
        providerName: Name of the data provider

    Request Body:
        {
            "inputs": {
                "param1": "value1",
                "param2": "value2"
            }
        }

    Response:
        200: {
            "provider": "get_github_repos",
            "options": [
                {
                    "label": "my-repo",
                    "value": "owner/my-repo"
                }
            ],
            "cached": false,
            "cache_expires_at": "2025-10-10T12:05:00Z"
        }
        400: Invalid or missing required parameters
        404: Provider not found
        500: Provider execution error
    """
    # Get context from request (injected by @with_org_context decorator)
    context = get_org_context(req)

    provider_name = req.route_params.get('providerName') or ""

    # Parse request body
    try:
        body = req.get_json() if req.get_body() else {}
        inputs = body.get('inputs')
    except Exception as e:
        logger.error(f"Error parsing request body: {e}")
        return func.HttpResponse(
            json.dumps({
                "error": "BadRequest",
                "message": "Invalid JSON in request body"
            }),
            status_code=400,
            mimetype="application/json"
        )

    # Delegate to handler (business logic layer)
    response_dict, status_code = await get_data_provider_options_handler(
        provider_name=provider_name,
        context=context,
        no_cache=False,
        inputs=inputs
    )

    return func.HttpResponse(
        json.dumps(response_dict, default=str),
        status_code=status_code,
        mimetype="application/json"
    )


class DataProviderListResponse(BaseModel):
    """Response model for listing data providers"""
    providers: list[DataProviderMetadata]


@bp.function_name("data_providers_list")
@bp.route(route="data-providers", methods=["GET"])
@openapi_endpoint(
    path="/data-providers",
    method="GET",
    summary="List data providers",
    description="List all available data providers",
    tags=["Data Providers"],
    response_model=DataProviderListResponse
)
async def list_data_providers(req: func.HttpRequest) -> func.HttpResponse:
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
    # Delegate to handler (business logic layer)
    response_dict, status_code = await list_data_providers_handler()

    return func.HttpResponse(
        json.dumps(response_dict),
        status_code=status_code,
        mimetype="application/json"
    )
