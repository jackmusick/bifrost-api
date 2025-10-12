"""
Admin Metadata Endpoint
Returns metadata for all registered workflows and data providers
"""

import logging
import json
import azure.functions as func

from engine.shared.registry import get_registry

logger = logging.getLogger(__name__)

# Create blueprint for admin endpoints
bp = func.Blueprint()


@bp.route(route="registry/metadata", methods=["GET"], auth_level=func.AuthLevel.ADMIN)
def get_metadata(req: func.HttpRequest) -> func.HttpResponse:
    """
    GET /registry/metadata
    Return metadata for all registered workflows and data providers

    Requires function key (Management API can call this)

    Returns:
        200: MetadataResponse with workflows and dataProviders arrays
        500: Internal server error
    """
    logger.info(f"Metadata endpoint called - headers: {list(req.headers.keys())}")
    logger.info(f"x-functions-key header present: {'x-functions-key' in req.headers}")

    try:
        # Get registry singleton
        registry = get_registry()

        # Get all workflows
        workflows = []
        for workflow_meta in registry.get_all_workflows():
            # Convert parameters to dict format
            parameters = []
            for param in workflow_meta.parameters:
                param_dict = {
                    "name": param.name,
                    "type": param.type,
                    "label": param.label,
                    "required": param.required
                }

                # Add optional fields if present
                if param.validation:
                    param_dict["validation"] = param.validation
                if param.data_provider:
                    param_dict["dataProvider"] = param.data_provider
                if param.default_value is not None:
                    param_dict["defaultValue"] = param.default_value
                if param.help_text:
                    param_dict["helpText"] = param.help_text

                parameters.append(param_dict)

            # Build workflow metadata dict
            workflow_dict = {
                "name": workflow_meta.name,
                "description": workflow_meta.description,
                "category": workflow_meta.category,
                "tags": workflow_meta.tags,
                "requiresOrg": workflow_meta.requires_org,
                "parameters": parameters,
                # Execution mode
                "executionMode": workflow_meta.execution_mode,
                # Forms
                "exposeInForms": workflow_meta.expose_in_forms
            }

            workflows.append(workflow_dict)

        # Get all data providers
        data_providers = []
        for provider_meta in registry.get_all_data_providers():
            provider_dict = {
                "name": provider_meta.name,
                "description": provider_meta.description,
                "category": provider_meta.category,
                "cacheTtlSeconds": provider_meta.cache_ttl_seconds
            }

            data_providers.append(provider_dict)

        # Build response
        response_data = {
            "workflows": workflows,
            "dataProviders": data_providers
        }

        logger.info(
            f"Returning metadata: {len(workflows)} workflows, "
            f"{len(data_providers)} data providers"
        )

        return func.HttpResponse(
            json.dumps(response_data),
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
