"""
Data Providers API
Returns metadata for all registered data providers
"""

import json
import logging

import azure.functions as func

from shared.decorators import with_request_context
from shared.discovery import scan_all_data_providers
from shared.handlers.discovery_handlers import convert_data_provider_metadata_to_model
from shared.models import DataProviderMetadata
from shared.openapi_decorators import openapi_endpoint

logger = logging.getLogger(__name__)

# Create blueprint for data provider endpoints
bp = func.Blueprint()


@bp.route(route="data-providers", methods=["GET"])
@bp.function_name("list_data_providers")
@openapi_endpoint(
    path="/data-providers",
    method="GET",
    summary="List all data providers",
    description="Returns metadata for all registered data providers in the system. Triggers workspace re-scan to pick up new providers.",
    tags=["Data Providers"],
    response_model=list[DataProviderMetadata]
)
@with_request_context
async def list_data_providers(req: func.HttpRequest) -> func.HttpResponse:
    """
    GET /api/data-providers
    Return metadata for all registered data providers

    Requires authentication (uses request context from SWA/EasyAuth)
    Triggers workspace re-scan to discover new providers before returning metadata.

    Returns:
        200: List of DataProviderMetadata
        500: Internal server error
    """
    try:
        # Dynamically scan all data providers (always fresh)
        providers = []

        for dp in scan_all_data_providers():
            try:
                provider_model = convert_data_provider_metadata_to_model(dp)
                providers.append(provider_model)
            except Exception as e:
                logger.error(
                    f"Failed to convert data provider '{dp.name}': {e}",
                    exc_info=True
                )

        logger.info(f"Returning {len(providers)} data providers")

        return func.HttpResponse(
            json.dumps([p.model_dump(mode="json", by_alias=True, exclude_none=True) for p in providers]),
            status_code=200,
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Error retrieving data providers: {str(e)}", exc_info=True)

        error_response = {
            "error": "InternalServerError",
            "message": "Failed to retrieve data providers"
        }

        return func.HttpResponse(
            json.dumps(error_response),
            status_code=500,
            mimetype="application/json"
        )
