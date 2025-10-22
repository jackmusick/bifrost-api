"""
Discovery API
Returns metadata for all registered workflows and data providers
"""

import json
import logging

import azure.functions as func

from shared.decorators import with_request_context
from shared.handlers.discovery_handlers import get_discovery_metadata
from shared.models import MetadataResponse
from shared.openapi_decorators import openapi_endpoint

logger = logging.getLogger(__name__)

# Create blueprint for discovery endpoints
bp = func.Blueprint()


@bp.route(route="discovery", methods=["GET"])
@openapi_endpoint(
    path="/discovery",
    method="GET",
    summary="Discover available workflows and data providers",
    description="Returns metadata for all registered workflows and data providers.",
    tags=["Discovery"],
    response_model=MetadataResponse
)
@with_request_context
async def get_discovery_metadata_handler(req: func.HttpRequest) -> func.HttpResponse:
    """
    GET /api/discovery
    Return metadata for all registered workflows and data providers

    Requires authentication (uses request context from SWA/EasyAuth)

    Returns:
        200: MetadataResponse with workflows and dataProviders arrays
        500: Internal server error
    """
    logger.info(f"Metadata endpoint called - headers: {list(req.headers.keys())}")
    logger.info(f"x-functions-key header present: {'x-functions-key' in req.headers}")

    try:
        # Call business logic handler
        metadata = get_discovery_metadata()

        logger.info(
            f"Returning metadata: {len(metadata.workflows)} workflows, "
            f"{len(metadata.dataProviders)} data providers"
        )

        return func.HttpResponse(
            json.dumps(metadata.model_dump(by_alias=True, exclude_none=True)),
            status_code=200,
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Error retrieving metadata: {str(e)}", exc_info=True)

        error_response = {
            "error": "InternalServerError",
            "message": "Failed to retrieve metadata"
        }

        return func.HttpResponse(
            json.dumps(error_response),
            status_code=500,
            mimetype="application/json"
        )
