"""
Config and IntegrationConfig API endpoints
- Manage global and organization-specific configuration key-value pairs
- Manage integration configurations (Microsoft Graph, HaloPSA)

Business logic extracted to shared/handlers/org_config_handlers.py
"""

import azure.functions as func

from shared.decorators import require_platform_admin, with_request_context
from shared.handlers.org_config_handlers import (
    delete_config_handler,
    delete_integration_handler,
    get_config_handler,
    get_integrations_handler,
    set_config_handler,
    set_integration_handler,
)
from shared.openapi_decorators import openapi_endpoint
from shared.models import Config, IntegrationConfig, SetConfigRequest, SetIntegrationConfigRequest

# Create blueprint for config endpoints
bp = func.Blueprint()


@bp.function_name("config_get_config")
@bp.route(route="config", methods=["GET"])
@openapi_endpoint(
    path="/config",
    method="GET",
    summary="Get configuration values",
    description="Get configuration values for current scope. Platform admins see all configs in their scope (set via X-Organization-Id header). Regular users see configs for their org.",
    tags=["Configuration"],
    response_model=list[Config]
)
@with_request_context
@require_platform_admin
async def get_config(req: func.HttpRequest) -> func.HttpResponse:
    """GET /api/config - Get configuration for current scope"""
    return await get_config_handler(req)


@bp.function_name("config_set_config")
@bp.route(route="config", methods=["POST"])
@openapi_endpoint(
    path="/config",
    method="POST",
    summary="Set configuration value",
    description="Set a configuration value in the current scope (Platform admin only)",
    tags=["Configuration"],
    request_model=SetConfigRequest,
    response_model=Config
)
@with_request_context
@require_platform_admin
async def set_config(req: func.HttpRequest) -> func.HttpResponse:
    """POST /api/config - Set a configuration key-value pair"""
    return await set_config_handler(req)


@bp.function_name("config_delete_config")
@bp.route(route="config/{key}", methods=["DELETE"])
@openapi_endpoint(
    path="/config/{key}",
    method="DELETE",
    summary="Delete configuration value",
    description="Delete a configuration value by key from current scope (Platform admin only)",
    tags=["Configuration"],
    path_params={
        "key": {
            "description": "Configuration key to delete",
            "schema": {"type": "string"}
        }
    }
)
@with_request_context
@require_platform_admin
async def delete_config(req: func.HttpRequest) -> func.HttpResponse:
    """DELETE /api/config/{key} - Delete a configuration key"""
    return await delete_config_handler(req)


# ==================== INTEGRATION CONFIG ENDPOINTS ====================


@bp.function_name("config_get_integrations")
@bp.route(route="organizations/{orgId}/integrations", methods=["GET"])
@openapi_endpoint(
    path="/organizations/{orgId}/integrations",
    method="GET",
    summary="Get organization integrations",
    description="Get all integration configurations for an organization (Platform admin only)",
    tags=["Integrations"],
    response_model=IntegrationConfig,
    path_params={
        "orgId": {
            "description": "Organization ID (UUID)",
            "schema": {"type": "string", "format": "uuid"}
        }
    }
)
@with_request_context
@require_platform_admin
async def get_integrations(req: func.HttpRequest) -> func.HttpResponse:
    """GET /api/organizations/{orgId}/integrations - Get all integration configurations"""
    return await get_integrations_handler(req)


@bp.function_name("config_set_integration")
@bp.route(route="organizations/{orgId}/integrations", methods=["POST"])
@openapi_endpoint(
    path="/organizations/{orgId}/integrations",
    method="POST",
    summary="Set organization integration",
    description="Set or update an integration configuration for an organization (Platform admin only)",
    tags=["Integrations"],
    request_model=SetIntegrationConfigRequest,
    response_model=IntegrationConfig,
    path_params={
        "orgId": {
            "description": "Organization ID (UUID)",
            "schema": {"type": "string", "format": "uuid"}
        }
    }
)
@with_request_context
@require_platform_admin
async def set_integration(req: func.HttpRequest) -> func.HttpResponse:
    """POST /api/organizations/{orgId}/integrations - Create or update integration configuration"""
    return await set_integration_handler(req)


@bp.function_name("config_delete_integration")
@bp.route(route="organizations/{orgId}/integrations/{type}", methods=["DELETE"])
@openapi_endpoint(
    path="/organizations/{orgId}/integrations/{type}",
    method="DELETE",
    summary="Delete organization integration",
    description="Delete an integration configuration for an organization (Platform admin only)",
    tags=["Integrations"],
    path_params={
        "orgId": {
            "description": "Organization ID (UUID)",
            "schema": {"type": "string", "format": "uuid"}
        },
        "type": {
            "description": "Integration type",
            "schema": {"type": "string", "enum": ["msgraph", "halopsa"]}
        }
    }
)
@with_request_context
@require_platform_admin
async def delete_integration(req: func.HttpRequest) -> func.HttpResponse:
    """DELETE /api/organizations/{orgId}/integrations/{type} - Delete integration configuration"""
    return await delete_integration_handler(req)
