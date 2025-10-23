"""
OAuth API endpoints
Manage OAuth connections for workflows and integrations
"""

import azure.functions as func

from shared.models import (
    CreateOAuthConnectionRequest,
    UpdateOAuthConnectionRequest,
)
from shared.decorators import require_platform_admin, with_request_context
from shared.handlers.oauth_handlers import (
    create_oauth_connection_handler,
    list_oauth_connections_handler,
    get_oauth_connection_handler,
    update_oauth_connection_handler,
    delete_oauth_connection_handler,
    authorize_oauth_connection_handler,
    cancel_oauth_authorization_handler,
    refresh_oauth_token_handler,
    oauth_callback_handler,
    get_oauth_credentials_handler,
    get_oauth_refresh_job_status_handler,
    trigger_oauth_refresh_job_handler,
)
from shared.openapi_decorators import openapi_endpoint

# Create blueprint for OAuth endpoints
bp = func.Blueprint()


@bp.function_name("oauth_create_connection")
@bp.route(route="oauth/connections", methods=["POST"])
@openapi_endpoint(
    path="/oauth/connections",
    method="POST",
    summary="Create OAuth connection",
    description="Create a new OAuth connection for integrations (Platform admin only)",
    tags=["OAuth"],
    request_model=CreateOAuthConnectionRequest
)
@with_request_context
@require_platform_admin
async def create_oauth_connection(req: func.HttpRequest) -> func.HttpResponse:
    """POST /api/oauth/connections - Create a new OAuth connection"""
    return await create_oauth_connection_handler(req)


@bp.function_name("oauth_list_connections")
@bp.route(route="oauth/connections", methods=["GET"])
@openapi_endpoint(
    path="/oauth/connections",
    method="GET",
    summary="List OAuth connections",
    description="List all OAuth connections (Platform admin only)",
    tags=["OAuth"]
)
@with_request_context
@require_platform_admin
async def list_oauth_connections(req: func.HttpRequest) -> func.HttpResponse:
    """GET /api/oauth/connections - List all OAuth connections"""
    return await list_oauth_connections_handler(req)


@bp.function_name("oauth_get_connection")
@bp.route(route="oauth/connections/{name}", methods=["GET"])
@openapi_endpoint(
    path="/oauth/connections/{name}",
    method="GET",
    summary="Get OAuth connection",
    description="Get a specific OAuth connection (Platform admin only)",
    tags=["OAuth"]
)
@with_request_context
@require_platform_admin
async def get_oauth_connection(req: func.HttpRequest) -> func.HttpResponse:
    """GET /api/oauth/connections/{name} - Get specific OAuth connection"""
    return await get_oauth_connection_handler(req)


@bp.function_name("oauth_update_connection")
@bp.route(route="oauth/connections/{name}", methods=["PUT"])
@openapi_endpoint(
    path="/oauth/connections/{name}",
    method="PUT",
    summary="Update OAuth connection",
    description="Update an existing OAuth connection (Platform admin only)",
    tags=["OAuth"],
    request_model=UpdateOAuthConnectionRequest
)
@with_request_context
@require_platform_admin
async def update_oauth_connection(req: func.HttpRequest) -> func.HttpResponse:
    """PUT /api/oauth/connections/{name} - Update OAuth connection"""
    return await update_oauth_connection_handler(req)


@bp.function_name("oauth_delete_connection")
@bp.route(route="oauth/connections/{name}", methods=["DELETE"])
@openapi_endpoint(
    path="/oauth/connections/{name}",
    method="DELETE",
    summary="Delete OAuth connection",
    description="Delete an OAuth connection (Platform admin only)",
    tags=["OAuth"]
)
@with_request_context
@require_platform_admin
async def delete_oauth_connection(req: func.HttpRequest) -> func.HttpResponse:
    """DELETE /api/oauth/connections/{name} - Delete OAuth connection"""
    return await delete_oauth_connection_handler(req)


@bp.function_name("oauth_authorize_connection")
@bp.route(route="oauth/connections/{name}/authorize", methods=["POST"])
@openapi_endpoint(
    path="/oauth/connections/{name}/authorize",
    method="POST",
    summary="Authorize OAuth connection",
    description="Start OAuth authorization flow (Platform admin only)",
    tags=["OAuth"]
)
@with_request_context
@require_platform_admin
async def authorize_oauth_connection(req: func.HttpRequest) -> func.HttpResponse:
    """POST /api/oauth/connections/{name}/authorize - Start authorization"""
    return await authorize_oauth_connection_handler(req)


@bp.function_name("oauth_cancel_authorization")
@bp.route(route="oauth/connections/{name}/cancel", methods=["POST"])
@openapi_endpoint(
    path="/oauth/connections/{name}/cancel",
    method="POST",
    summary="Cancel OAuth authorization",
    description="Cancel OAuth authorization (Platform admin only)",
    tags=["OAuth"]
)
@with_request_context
@require_platform_admin
async def cancel_oauth_authorization(req: func.HttpRequest) -> func.HttpResponse:
    """POST /api/oauth/connections/{name}/cancel - Cancel authorization"""
    return await cancel_oauth_authorization_handler(req)


@bp.function_name("oauth_refresh_token")
@bp.route(route="oauth/connections/{name}/refresh", methods=["POST"])
@openapi_endpoint(
    path="/oauth/connections/{name}/refresh",
    method="POST",
    summary="Refresh OAuth token",
    description="Refresh OAuth token (Platform admin only)",
    tags=["OAuth"]
)
@with_request_context
@require_platform_admin
async def refresh_oauth_token(req: func.HttpRequest) -> func.HttpResponse:
    """POST /api/oauth/connections/{name}/refresh - Refresh token"""
    return await refresh_oauth_token_handler(req)


@bp.function_name("oauth_callback")
@bp.route(route="oauth/callback/{connection_name}", methods=["POST"])
@openapi_endpoint(
    path="/oauth/callback/{connection_name}",
    method="POST",
    summary="OAuth callback",
    description="Handle OAuth provider callback",
    tags=["OAuth"],
    path_params={
        "connection_name": {
            "description": "OAuth connection name",
            "schema": {"type": "string"},
            "required": True
        }
    }
)
async def oauth_callback(req: func.HttpRequest) -> func.HttpResponse:
    """POST /api/oauth/callback/{connection_name} - Handle OAuth callback"""
    return await oauth_callback_handler(req)


@bp.function_name("oauth_get_credentials")
@bp.route(route="oauth/connections/{name}/credentials", methods=["GET"])
@openapi_endpoint(
    path="/oauth/connections/{name}/credentials",
    method="GET",
    summary="Get OAuth credentials",
    description="Get OAuth credentials (Platform admin only)",
    tags=["OAuth"]
)
@with_request_context
@require_platform_admin
async def get_oauth_credentials(req: func.HttpRequest) -> func.HttpResponse:
    """GET /api/oauth/connections/{name}/credentials - Get credentials"""
    return await get_oauth_credentials_handler(req)


@bp.function_name("oauth_refresh_job_status")
@bp.route(route="oauth/refresh_job_status", methods=["GET"])
@openapi_endpoint(
    path="/oauth/refresh_job_status",
    method="GET",
    summary="Get refresh job status",
    description="Get status of OAuth token refresh jobs (Platform admin only)",
    tags=["OAuth"]
)
@with_request_context
@require_platform_admin
async def get_oauth_refresh_job_status(req: func.HttpRequest) -> func.HttpResponse:
    """GET /api/oauth/refresh_job_status - Get refresh job status"""
    return await get_oauth_refresh_job_status_handler(req)


@bp.function_name("oauth_trigger_refresh_job")
@bp.route(route="oauth/refresh_all", methods=["POST"])
@openapi_endpoint(
    path="/oauth/refresh_all",
    method="POST",
    summary="Trigger refresh job",
    description="Manually trigger OAuth token refresh job for all expiring tokens (Platform admin only)",
    tags=["OAuth"]
)
@with_request_context
@require_platform_admin
async def trigger_oauth_refresh_job(req: func.HttpRequest) -> func.HttpResponse:
    """POST /api/oauth/refresh_all - Manually trigger refresh job"""
    return await trigger_oauth_refresh_job_handler(req)
