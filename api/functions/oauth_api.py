"""
OAuth API endpoints
Manage OAuth connections for workflows and integrations
"""

import json
import logging
import uuid
from datetime import datetime
from urllib.parse import urlencode

import azure.functions as func
from pydantic import ValidationError

from models.oauth_connection import (
    CreateOAuthConnectionRequest,
    OAuthConnectionDetail,
    OAuthCredentials,
    OAuthCredentialsResponse,
    UpdateOAuthConnectionRequest,
)
from services.oauth_provider import OAuthProviderClient
from services.oauth_storage_service import OAuthStorageService
from services.oauth_test_service import OAuthTestService
from shared.custom_types import get_context, get_route_param
from shared.decorators import require_platform_admin, with_request_context
from shared.keyvault import KeyVaultClient
from shared.models import ErrorResponse, OAuthCallbackRequest, OAuthCallbackResponse
from shared.openapi_decorators import openapi_endpoint
from shared.storage import TableStorageService

logger = logging.getLogger(__name__)

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
    """
    POST /api/oauth/connections
    Create a new OAuth connection

    Request body: CreateOAuthConnectionRequest

    Requires: User must be authenticated (platform admin or have canManageConfig)
    """
    context = get_context(req)
    org_id = context.scope

    logger.info(f"User {context.email} creating OAuth connection for org {org_id}")

    try:
        # Parse and validate request body
        request_body = req.get_json()
        create_request = CreateOAuthConnectionRequest(**request_body)

        # Create OAuth storage service
        oauth_service = OAuthStorageService()

        # Check if connection already exists
        existing = await oauth_service.get_connection(org_id, create_request.connection_name)
        if existing:
            error = ErrorResponse(
                error="Conflict",
                message=f"OAuth connection '{create_request.connection_name}' already exists"
            )
            return func.HttpResponse(
                json.dumps(error.model_dump()),
                status_code=409,
                mimetype="application/json"
            )

        # Create connection
        connection = await oauth_service.create_connection(
            org_id=org_id,
            request=create_request,
            created_by=context.user_id
        )

        logger.info(f"Created OAuth connection: {create_request.connection_name}")

        # Return detail response
        detail = connection.to_detail()
        return func.HttpResponse(
            json.dumps(detail.model_dump(mode="json")),
            status_code=201,
            mimetype="application/json"
        )

    except ValidationError as e:
        logger.warning(f"Validation error creating OAuth connection: {e}")
        error = ErrorResponse(
            error="ValidationError",
            message="Invalid request data",
            details={"errors": e.errors()}
        )
        return func.HttpResponse(
            json.dumps(error.model_dump()),
            status_code=400,
            mimetype="application/json"
        )

    except ValueError as e:
        logger.error(f"Error parsing request: {str(e)}")
        error = ErrorResponse(
            error="BadRequest",
            message="Invalid JSON in request body"
        )
        return func.HttpResponse(
            json.dumps(error.model_dump()),
            status_code=400,
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Error creating OAuth connection: {str(e)}", exc_info=True)
        error = ErrorResponse(
            error="InternalServerError",
            message="Failed to create OAuth connection"
        )
        return func.HttpResponse(
            json.dumps(error.model_dump()),
            status_code=500,
            mimetype="application/json"
        )


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
    """
    GET /api/oauth/connections
    List OAuth connections for an organization

    Returns org-specific connections + GLOBAL connections (with org-specific taking precedence)

    Platform admin only endpoint
    """
    context = get_context(req)
    org_id = context.scope

    logger.info(f"User {context.email} listing OAuth connections for org {org_id}")

    try:
        # Create OAuth storage service
        oauth_service = OAuthStorageService()

        # List connections - always include GLOBAL fallback
        connections = await oauth_service.list_connections(org_id, include_global=True)

        # Convert to summary responses
        summaries = [conn.to_summary() for conn in connections]

        logger.info(f"Returning {len(summaries)} OAuth connections")

        return func.HttpResponse(
            json.dumps([s.model_dump(mode="json") for s in summaries]),
            status_code=200,
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Error listing OAuth connections: {str(e)}", exc_info=True)
        error = ErrorResponse(
            error="InternalServerError",
            message="Failed to list OAuth connections"
        )
        return func.HttpResponse(
            json.dumps(error.model_dump()),
            status_code=500,
            mimetype="application/json"
        )


@bp.function_name("oauth_get_connection")
@bp.route(route="oauth/connections/{connection_name}", methods=["GET"])
@openapi_endpoint(
    path="/oauth/connections/{connection_name}",
    method="GET",
    summary="Get OAuth connection",
    description="Get OAuth connection details (Platform admin only)",
    tags=["OAuth"],
    response_model=OAuthConnectionDetail,
    path_params={
        "connection_name": {
            "description": "Connection name",
            "schema": {"type": "string"},
            "required": True
        }
    }
)
@with_request_context
@require_platform_admin
async def get_oauth_connection(req: func.HttpRequest) -> func.HttpResponse:
    """
    GET /api/oauth/connections/{connection_name}
    Get OAuth connection details

    Route params: connection_name

    Platform admin only endpoint
    """
    context = get_context(req)
    connection_name = get_route_param(req, "connection_name")
    org_id = context.scope

    logger.info(f"User {context.email} retrieving OAuth connection {connection_name} for org {org_id}")

    try:
        # Create OAuth storage service
        oauth_service = OAuthStorageService()

        # Get connection with org→GLOBAL fallback
        connection = await oauth_service.get_connection(org_id, connection_name)

        if not connection:
            error = ErrorResponse(
                error="NotFound",
                message=f"OAuth connection '{connection_name}' not found"
            )
            return func.HttpResponse(
                json.dumps(error.model_dump()),
                status_code=404,
                mimetype="application/json"
            )

        # Return detail response (masks sensitive fields)
        detail = connection.to_detail()
        return func.HttpResponse(
            json.dumps(detail.model_dump(mode="json")),
            status_code=200,
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Error retrieving OAuth connection: {str(e)}", exc_info=True)
        error = ErrorResponse(
            error="InternalServerError",
            message="Failed to retrieve OAuth connection"
        )
        return func.HttpResponse(
            json.dumps(error.model_dump()),
            status_code=500,
            mimetype="application/json"
        )


@bp.function_name("oauth_update_connection")
@bp.route(route="oauth/connections/{connection_name}", methods=["PUT"])
@openapi_endpoint(
    path="/oauth/connections/{connection_name}",
    method="PUT",
    summary="Update OAuth connection",
    description="Update an OAuth connection (Platform admin only)",
    tags=["OAuth"],
    path_params={
        "connection_name": {
            "description": "Connection name",
            "schema": {"type": "string"},
            "required": True
        }
    },
    request_model=UpdateOAuthConnectionRequest
)
@with_request_context
@require_platform_admin
async def update_oauth_connection(req: func.HttpRequest) -> func.HttpResponse:
    """
    PUT /api/oauth/connections/{connection_name}
    Update an OAuth connection

    Route params: connection_name
    Request body: UpdateOAuthConnectionRequest

    Requires: User must be authenticated (platform admin or have canManageConfig)
    """
    context = get_context(req)
    connection_name = get_route_param(req, "connection_name")
    org_id = context.scope

    logger.info(f"User {context.email} updating OAuth connection {connection_name} for org {org_id}")

    try:
        # Parse and validate request body
        request_body = req.get_json()
        update_request = UpdateOAuthConnectionRequest(**request_body)

        # Create OAuth storage service
        oauth_service = OAuthStorageService()

        # Update connection
        connection = await oauth_service.update_connection(
            org_id=org_id,
            connection_name=connection_name,
            request=update_request,
            updated_by=context.user_id
        )

        if not connection:
            error = ErrorResponse(
                error="NotFound",
                message=f"OAuth connection '{connection_name}' not found"
            )
            return func.HttpResponse(
                json.dumps(error.model_dump()),
                status_code=404,
                mimetype="application/json"
            )

        logger.info(f"Updated OAuth connection: {connection_name}")

        # Return detail response
        detail = connection.to_detail()
        return func.HttpResponse(
            json.dumps(detail.model_dump(mode="json")),
            status_code=200,
            mimetype="application/json"
        )

    except ValidationError as e:
        logger.warning(f"Validation error updating OAuth connection: {e}")
        error = ErrorResponse(
            error="ValidationError",
            message="Invalid request data",
            details={"errors": e.errors()}
        )
        return func.HttpResponse(
            json.dumps(error.model_dump()),
            status_code=400,
            mimetype="application/json"
        )

    except ValueError as e:
        logger.error(f"Error parsing request: {str(e)}")
        error = ErrorResponse(
            error="BadRequest",
            message="Invalid JSON in request body"
        )
        return func.HttpResponse(
            json.dumps(error.model_dump()),
            status_code=400,
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Error updating OAuth connection: {str(e)}", exc_info=True)
        error = ErrorResponse(
            error="InternalServerError",
            message="Failed to update OAuth connection"
        )
        return func.HttpResponse(
            json.dumps(error.model_dump()),
            status_code=500,
            mimetype="application/json"
        )


@bp.function_name("oauth_delete_connection")
@bp.route(route="oauth/connections/{connection_name}", methods=["DELETE"])
@openapi_endpoint(
    path="/oauth/connections/{connection_name}",
    method="DELETE",
    summary="Delete OAuth connection",
    description="Delete an OAuth connection (Platform admin only)",
    tags=["OAuth"],
    path_params={
        "connection_name": {
            "description": "Connection name",
            "schema": {"type": "string"},
            "required": True
        }
    }
)
@with_request_context
@require_platform_admin
async def delete_oauth_connection(req: func.HttpRequest) -> func.HttpResponse:
    """
    DELETE /api/oauth/connections/{connection_name}
    Delete an OAuth connection

    Route params: connection_name

    Requires: User must be authenticated (platform admin or have canManageConfig)

    Note: This will be enhanced in User Story 5 to check for dependent workflows
    """
    context = get_context(req)
    connection_name = get_route_param(req, "connection_name")
    org_id = context.scope

    logger.info(f"User {context.email} deleting OAuth connection {connection_name} for org {org_id}")

    try:
        # Create OAuth storage service
        oauth_service = OAuthStorageService()

        # Delete connection (idempotent)
        deleted = await oauth_service.delete_connection(org_id, connection_name)

        if deleted:
            logger.info(f"Deleted OAuth connection: {connection_name}")
        else:
            logger.debug(f"OAuth connection not found (already deleted): {connection_name}")

        # Return 204 No Content (idempotent delete)
        return func.HttpResponse(
            status_code=204
        )

    except Exception as e:
        logger.error(f"Error deleting OAuth connection: {str(e)}", exc_info=True)
        error = ErrorResponse(
            error="InternalServerError",
            message="Failed to delete OAuth connection"
        )
        return func.HttpResponse(
            json.dumps(error.model_dump()),
            status_code=500,
            mimetype="application/json"
        )


# ==================== AUTHORIZATION FLOW ENDPOINTS ====================

@bp.function_name("oauth_authorize")
@bp.route(route="oauth/connections/{connection_name}/authorize", methods=["POST"])
@openapi_endpoint(
    path="/oauth/connections/{connection_name}/authorize",
    method="POST",
    summary="Authorize OAuth connection",
    description="Initiate OAuth authorization flow (Platform admin only)",
    tags=["OAuth"],
    path_params={
        "connection_name": {
            "description": "Connection name",
            "schema": {"type": "string"},
            "required": True
        }
    }
)
@with_request_context
@require_platform_admin
async def authorize_oauth_connection(req: func.HttpRequest) -> func.HttpResponse:
    """
    POST /api/oauth/connections/{connection_name}/authorize
    Initiate OAuth authorization flow

    Returns authorization URL for user to visit

    Route params: connection_name

    Platform admin only endpoint
    """
    context = get_context(req)
    connection_name = get_route_param(req, "connection_name")
    org_id = context.scope

    logger.info(f"User {context.email} initiating OAuth authorization for {connection_name}")

    try:
        # Get OAuth storage service
        oauth_service = OAuthStorageService()

        # Get connection
        connection = await oauth_service.get_connection(org_id, connection_name)

        if not connection:
            error = ErrorResponse(
                error="NotFound",
                message=f"OAuth connection '{connection_name}' not found"
            )
            return func.HttpResponse(
                json.dumps(error.model_dump()),
                status_code=404,
                mimetype="application/json"
            )

        # Check if client credentials flow (doesn't need authorization)
        if connection.oauth_flow_type == "client_credentials":
            error = ErrorResponse(
                error="BadRequest",
                message="Client credentials flow does not require authorization"
            )
            return func.HttpResponse(
                json.dumps(error.model_dump()),
                status_code=400,
                mimetype="application/json"
            )

        # Generate state parameter for CSRF protection
        state = str(uuid.uuid4())

        # Build full redirect URI (UI callback page)
        # req.url is like: https://domain.com/api/oauth/connections/name/authorize
        # We need: https://domain.com/oauth/callback/connection_name (no /api/)
        base_url = req.url.split('/api')[0] if '/api' in req.url else req.url.rsplit('/', 4)[0]
        # Ensure redirect_uri doesn't have /api/ prefix
        redirect_path = connection.redirect_uri
        if redirect_path.startswith('/api/'):
            redirect_path = redirect_path[4:]  # Remove /api prefix
        full_redirect_uri = f"{base_url}{redirect_path}"

        logger.info(f"Using redirect_uri for authorization: {full_redirect_uri}")

        # Build authorization URL
        auth_params = {
            "client_id": connection.client_id,
            "redirect_uri": full_redirect_uri,
            "response_type": "code",
            "scope": connection.scopes.replace(",", " "),  # OAuth spec uses space-separated
            "state": state
        }

        authorization_url = f"{connection.authorization_url}?{urlencode(auth_params)}"

        # Update connection status to waiting_callback
        await oauth_service.update_connection_status(
            org_id=org_id,
            connection_name=connection_name,
            status="waiting_callback",
            status_message=f"Waiting for OAuth callback (state: {state})"
        )

        logger.info(f"Generated authorization URL for {connection_name}")

        # Return authorization URL
        return func.HttpResponse(
            json.dumps({
                "authorization_url": authorization_url,
                "state": state,
                "message": "Visit the authorization URL to complete OAuth flow"
            }),
            status_code=200,
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Error initiating OAuth authorization: {str(e)}", exc_info=True)
        error = ErrorResponse(
            error="InternalServerError",
            message="Failed to initiate OAuth authorization"
        )
        return func.HttpResponse(
            json.dumps(error.model_dump()),
            status_code=500,
            mimetype="application/json"
        )


@bp.function_name("oauth_cancel_authorization")
@bp.route(route="oauth/connections/{connection_name}/cancel", methods=["POST"])
@openapi_endpoint(
    path="/oauth/connections/{connection_name}/cancel",
    method="POST",
    summary="Cancel OAuth authorization",
    description="Cancel OAuth authorization (Platform admin only)",
    tags=["OAuth"],
    path_params={
        "connection_name": {
            "description": "Connection name",
            "schema": {"type": "string"},
            "required": True
        }
    }
)
@with_request_context
@require_platform_admin
async def cancel_oauth_authorization(req: func.HttpRequest) -> func.HttpResponse:
    """
    POST /api/oauth/connections/{connection_name}/cancel
    Cancel OAuth authorization (reset to not_connected status)

    Useful when authorization is stuck in waiting_callback state

    Route params: connection_name

    Platform admin only endpoint
    """
    context = get_context(req)
    connection_name = get_route_param(req, "connection_name")
    org_id = context.scope

    logger.info(f"User {context.email} canceling OAuth authorization for {connection_name}")

    try:
        # Get OAuth storage service
        oauth_service = OAuthStorageService()

        # Get connection
        connection = await oauth_service.get_connection(org_id, connection_name)

        if not connection:
            error = ErrorResponse(
                error="NotFound",
                message=f"OAuth connection '{connection_name}' not found"
            )
            return func.HttpResponse(
                json.dumps(error.model_dump()),
                status_code=404,
                mimetype="application/json"
            )

        # Reset to not_connected status
        await oauth_service.update_connection_status(
            org_id=org_id,
            connection_name=connection_name,
            status="not_connected",
            status_message="Authorization canceled by user"
        )

        logger.info(f"Canceled OAuth authorization for {connection_name}")

        # Return 204 No Content
        return func.HttpResponse(
            status_code=204
        )

    except Exception as e:
        logger.error(f"Error canceling OAuth authorization: {str(e)}", exc_info=True)
        error = ErrorResponse(
            error="InternalServerError",
            message="Failed to cancel OAuth authorization"
        )
        return func.HttpResponse(
            json.dumps(error.model_dump()),
            status_code=500,
            mimetype="application/json"
        )


@bp.function_name("oauth_refresh_token")
@bp.route(route="oauth/connections/{connection_name}/refresh", methods=["POST"])
@openapi_endpoint(
    path="/oauth/connections/{connection_name}/refresh",
    method="POST",
    summary="Refresh OAuth token",
    description="Manually refresh OAuth access token using refresh token (Platform admin only)",
    tags=["OAuth"],
    path_params={
        "connection_name": {
            "description": "Connection name",
            "schema": {"type": "string"},
            "required": True
        }
    }
)
@with_request_context
@require_platform_admin
async def refresh_oauth_token(req: func.HttpRequest) -> func.HttpResponse:
    """
    POST /api/oauth/connections/{connection_name}/refresh
    Manually refresh OAuth access token using refresh token

    Route params: connection_name

    Platform admin only endpoint
    """
    context = get_context(req)
    connection_name = get_route_param(req, "connection_name")
    org_id = context.scope

    logger.info(f"User {context.email} refreshing OAuth token for {connection_name}")

    try:
        # Create services
        oauth_service = OAuthStorageService()
        oauth_provider = OAuthProviderClient()
        config_service = TableStorageService("Config")

        try:
            keyvault = KeyVaultClient()
        except ValueError as e:
            logger.error(f"KeyVault not available: {e}")
            error = ErrorResponse(
                error="ServiceUnavailable",
                message="OAuth token refresh requires KeyVault configuration"
            )
            return func.HttpResponse(
                json.dumps(error.model_dump()),
                status_code=503,
                mimetype="application/json"
            )

        # Get connection
        connection = await oauth_service.get_connection(org_id, connection_name)

        if not connection:
            error = ErrorResponse(
                error="NotFound",
                message=f"OAuth connection '{connection_name}' not found"
            )
            return func.HttpResponse(
                json.dumps(error.model_dump()),
                status_code=404,
                mimetype="application/json"
            )

        # Check if connection has active tokens
        if connection.status != "completed":
            error = ErrorResponse(
                error="BadRequest",
                message=f"Cannot refresh token - connection status is {connection.status}"
            )
            return func.HttpResponse(
                json.dumps(error.model_dump()),
                status_code=400,
                mimetype="application/json"
            )

        # Check if connection has refresh token
        if not connection.oauth_response_ref:
            error = ErrorResponse(
                error="BadRequest",
                message="Connection has no stored tokens to refresh"
            )
            return func.HttpResponse(
                json.dumps(error.model_dump()),
                status_code=400,
                mimetype="application/json"
            )

        # Get OAuth response config entry to retrieve refresh token
        oauth_response_key = f"config:{connection.oauth_response_ref}"
        oauth_response_config = config_service.get_entity(
            connection.org_id,
            oauth_response_key
        )

        if not oauth_response_config:
            logger.error(f"OAuth response config not found: {oauth_response_key}")
            error = ErrorResponse(
                error="InternalServerError",
                message="OAuth credentials not properly configured"
            )
            return func.HttpResponse(
                json.dumps(error.model_dump()),
                status_code=500,
                mimetype="application/json"
            )

        # Get Key Vault secret name
        keyvault_secret_name = oauth_response_config.get("Value")

        if not keyvault_secret_name:
            logger.error("OAuth response config missing Key Vault secret name")
            error = ErrorResponse(
                error="InternalServerError",
                message="OAuth credentials not properly configured"
            )
            return func.HttpResponse(
                json.dumps(error.model_dump()),
                status_code=500,
                mimetype="application/json"
            )

        # Retrieve OAuth tokens from Key Vault
        # Note: keyvault_secret_name is already the full secret name (e.g., "GLOBAL--oauth-response-HaloPSA")
        # so we use the _client directly instead of get_secret() which expects org_id and secret_key
        try:
            secret = keyvault._client.get_secret(keyvault_secret_name)
            oauth_response_json = secret.value
            oauth_response = json.loads(oauth_response_json)
        except Exception as e:
            logger.error(
                f"Failed to retrieve OAuth tokens from Key Vault: {e}",
                extra={"secret_name": keyvault_secret_name}
            )
            error = ErrorResponse(
                error="InternalServerError",
                message="Failed to retrieve OAuth credentials"
            )
            return func.HttpResponse(
                json.dumps(error.model_dump()),
                status_code=500,
                mimetype="application/json"
            )

        # Get refresh token
        refresh_token = oauth_response.get("refresh_token")
        logger.info(f"Retrieved refresh_token from Key Vault: is_none={refresh_token is None}")

        if not refresh_token:
            error = ErrorResponse(
                error="BadRequest",
                message="No refresh token available - please reconnect the OAuth connection to obtain new credentials"
            )
            return func.HttpResponse(
                json.dumps(error.model_dump()),
                status_code=400,
                mimetype="application/json"
            )

        # Get client secret from Key Vault (or leave None for PKCE)
        client_secret = None
        if connection.client_secret_ref:
            try:
                # Get client secret config entry to retrieve Key Vault secret name
                client_secret_key = f"config:{connection.client_secret_ref}"
                client_secret_config = config_service.get_entity(
                    connection.org_id,
                    client_secret_key
                )

                if client_secret_config:
                    keyvault_secret_name = client_secret_config.get("Value")
                    if keyvault_secret_name:
                        secret = keyvault._client.get_secret(keyvault_secret_name)
                        client_secret = secret.value
                        logger.info(f"Retrieved client_secret from Key Vault for {connection_name}")
            except Exception as e:
                logger.warning(f"Failed to retrieve client_secret from Key Vault: {e}")

        # Refresh the access token
        logger.info(f"Refreshing access token for {connection_name}")

        success, result = await oauth_provider.refresh_access_token(
            token_url=connection.token_url,
            refresh_token=refresh_token,
            client_id=connection.client_id,
            client_secret=client_secret
        )

        if not success:
            error_msg = result.get("error_description", result.get("error", "Token refresh failed"))
            logger.error(f"Token refresh failed: {error_msg}")

            await oauth_service.update_connection_status(
                org_id=connection.org_id,
                connection_name=connection_name,
                status="failed",
                status_message=f"Token refresh failed: {error_msg}"
            )

            error = ErrorResponse(
                error="TokenRefreshFailed",
                message=error_msg
            )
            return func.HttpResponse(
                json.dumps(error.model_dump()),
                status_code=400,
                mimetype="application/json"
            )

        # Store refreshed tokens
        # Use new refresh_token if provided and not None, otherwise keep the old one
        new_refresh_token = result.get("refresh_token") or refresh_token
        logger.info(f"Storing tokens: new_refresh_token_from_response={result.get('refresh_token') is not None}, using_fallback={'yes' if result.get('refresh_token') is None else 'no'}, final_refresh_token_is_none={new_refresh_token is None}")

        await oauth_service.store_tokens(
            org_id=connection.org_id,
            connection_name=connection_name,
            access_token=result["access_token"],
            refresh_token=new_refresh_token,  # Use new refresh token if provided, else keep old one
            expires_at=result["expires_at"],
            token_type=result["token_type"],
            updated_by=context.user_id
        )

        # Update connection status with last_refresh_at timestamp
        await oauth_service.update_connection_status(
            org_id=connection.org_id,
            connection_name=connection_name,
            status="completed",
            status_message="Token refreshed successfully",
            expires_at=result["expires_at"],
            last_refresh_at=datetime.utcnow()
        )

        logger.info(f"Successfully refreshed OAuth token for {connection_name}")

        # Return success response
        return func.HttpResponse(
            json.dumps({
                "success": True,
                "message": "OAuth token refreshed successfully",
                "expires_at": result["expires_at"].isoformat() if isinstance(result["expires_at"], datetime) else result["expires_at"]
            }),
            status_code=200,
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Error refreshing OAuth token: {str(e)}", exc_info=True)
        error = ErrorResponse(
            error="InternalServerError",
            message="Failed to refresh OAuth token"
        )
        return func.HttpResponse(
            json.dumps(error.model_dump()),
            status_code=500,
            mimetype="application/json"
        )


@bp.function_name("oauth_callback")
@bp.route(route="oauth/callback/{connection_name}", methods=["POST"])
@openapi_endpoint(
    path="/oauth/callback/{connection_name}",
    method="POST",
    summary="OAuth callback",
    description="OAuth callback endpoint - exchanges authorization code for tokens",
    tags=["OAuth"],
    path_params={
        "connection_name": {
            "description": "Connection name",
            "schema": {"type": "string"},
            "required": True
        }
    },
    request_model=OAuthCallbackRequest,
    response_model=OAuthCallbackResponse
)
async def oauth_callback(req: func.HttpRequest) -> func.HttpResponse:
    """
    POST /api/oauth/callback/{connection_name}
    OAuth callback endpoint - exchanges authorization code for tokens

    This is called by the UI callback page, not directly by the OAuth provider.
    The UI receives the authorization code from the OAuth provider redirect,
    then sends it here for server-side token exchange.

    Route params: connection_name
    Request body: { code, state }

    Note: This endpoint is public (no auth required) - called from UI callback page
    """
    connection_name = get_route_param(req, "connection_name")

    # Get code and state from POST body instead of query params
    try:
        request_body = req.get_json()
        code = request_body.get("code")
    except ValueError:
        logger.error("Invalid JSON in callback request body")
        return func.HttpResponse(
            json.dumps({"error": "Invalid request", "message": "Request body must be valid JSON"}),
            status_code=400,
            mimetype="application/json"
        )

    logger.info(f"OAuth callback received for {connection_name}")

    try:
        # Create services
        oauth_service = OAuthStorageService()
        oauth_provider = OAuthProviderClient()
        oauth_test = OAuthTestService()

        # Try to find connection (check GLOBAL first for simplicity)
        connection = await oauth_service.get_connection("GLOBAL", connection_name)

        if not connection:
            # Try other orgs if needed (for now, just fail)
            logger.error(f"OAuth connection not found: {connection_name}")
            error = ErrorResponse(
                error="NotFound",
                message=f"OAuth connection '{connection_name}' not found"
            )
            return func.HttpResponse(
                json.dumps(error.model_dump()),
                status_code=404,
                mimetype="application/json"
            )

        # Validate authorization code
        if not code:
            logger.error("OAuth callback missing authorization code")
            error = ErrorResponse(
                error="BadRequest",
                message="Missing authorization code"
            )
            return func.HttpResponse(
                json.dumps(error.model_dump()),
                status_code=400,
                mimetype="application/json"
            )

        # Exchange code for tokens
        logger.info(f"Exchanging authorization code for tokens: {connection_name}")

        await oauth_service.update_connection_status(
            org_id=connection.org_id,
            connection_name=connection_name,
            status="testing",
            status_message="Exchanging authorization code for access token"
        )

        # Build full redirect URI (UI callback page URL) - must match authorize endpoint
        # req.url is like: https://domain.com/api/oauth/callback/connection_name
        # We need: https://domain.com/oauth/callback/connection_name (no /api/)
        base_url = req.url.split('/api')[0] if '/api' in req.url else req.url.rsplit('/', 3)[0]
        # Ensure redirect_uri doesn't have /api/ prefix (same logic as authorize endpoint)
        redirect_path = connection.redirect_uri
        if redirect_path.startswith('/api/'):
            redirect_path = redirect_path[4:]  # Remove /api prefix
        full_redirect_uri = f"{base_url}{redirect_path}"

        logger.info(f"Using redirect_uri for token exchange: {full_redirect_uri}")

        # Get client secret from Key Vault (or leave None for PKCE)
        client_secret = None
        if connection.client_secret_ref:
            try:
                # Get client secret config entry to retrieve Key Vault secret name
                config_service = TableStorageService("Config")
                client_secret_key = f"config:{connection.client_secret_ref}"
                client_secret_config = config_service.get_entity(
                    connection.org_id,
                    client_secret_key
                )

                if client_secret_config:
                    keyvault_secret_name = client_secret_config.get("Value")
                    if keyvault_secret_name:
                        try:
                            keyvault = KeyVaultClient()
                            secret = keyvault._client.get_secret(keyvault_secret_name)
                            client_secret = secret.value
                            logger.info(f"Retrieved client_secret from Key Vault for {connection_name}")
                        except ValueError as e:
                            logger.warning(f"KeyVault not available for client_secret retrieval: {e}")
            except Exception as e:
                logger.warning(f"Failed to retrieve client_secret from Key Vault: {e}")

        success, result = await oauth_provider.exchange_code_for_token(
            token_url=connection.token_url,
            code=code,
            client_id=connection.client_id,
            client_secret=client_secret,
            redirect_uri=full_redirect_uri
        )

        if not success:
            error_msg = result.get("error_description", result.get("error", "Token exchange failed"))
            logger.error(f"Token exchange failed: {error_msg}")

            await oauth_service.update_connection_status(
                org_id=connection.org_id,
                connection_name=connection_name,
                status="failed",
                status_message=f"Token exchange failed: {error_msg}"
            )

            # Return structured response instead of generic error
            return func.HttpResponse(
                json.dumps({
                    "success": False,
                    "message": "OAuth token exchange failed",
                    "status": "failed",
                    "connection_name": connection_name,
                    "warning_message": None,
                    "error_message": error_msg
                }),
                status_code=200,
                mimetype="application/json"
            )

        # Test connection
        logger.info(f"Testing OAuth connection: {connection_name}")

        test_success, test_message = await oauth_test.test_connection(
            access_token=result["access_token"],
            authorization_url=connection.authorization_url,
            token_url=connection.token_url
        )

        # Store tokens
        await oauth_service.store_tokens(
            org_id=connection.org_id,
            connection_name=connection_name,
            access_token=result["access_token"],
            refresh_token=result.get("refresh_token"),
            expires_at=result["expires_at"],
            token_type=result["token_type"],
            updated_by="system"
        )

        # Update final status
        final_status = "completed" if test_success else "failed"
        await oauth_service.update_connection_status(
            org_id=connection.org_id,
            connection_name=connection_name,
            status=final_status,
            status_message=test_message
        )

        logger.info(f"OAuth connection completed: {connection_name} (status={final_status})")

        # Check if refresh token was provided
        warning_message = None
        if not result.get("refresh_token"):
            warning_message = (
                "The OAuth provider did not return a refresh token. "
                "This connection will not be able to automatically refresh when the access token expires. "
                "If this was unintentional, review your OAuth application settings with the provider."
            )
            logger.warning(f"No refresh token returned for {connection_name}")

        # Return JSON success response
        return func.HttpResponse(
            json.dumps({
                "success": True,
                "message": "OAuth connection completed successfully",
                "status": final_status,
                "connection_name": connection_name,
                "warning_message": warning_message,
                "error_message": None
            }),
            status_code=200,
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Error processing OAuth callback: {str(e)}", exc_info=True)

        # Try to update connection status
        try:
            await oauth_service.update_connection_status(
                org_id="GLOBAL",  # Fallback
                connection_name=connection_name,
                status="failed",
                status_message=f"Callback processing error: {str(e)}"
            )
        except Exception:
            pass

        error = ErrorResponse(
            error="InternalServerError",
            message=f"Failed to process OAuth callback: {str(e)}"
        )
        return func.HttpResponse(
            json.dumps(error.model_dump()),
            status_code=500,
            mimetype="application/json"
        )


# ==================== CREDENTIALS ACCESS ENDPOINT (USER STORY 3) ====================

@bp.function_name("oauth_get_credentials")
@bp.route(route="oauth/credentials/{connection_name}", methods=["GET"])
@openapi_endpoint(
    path="/oauth/credentials/{connection_name}",
    method="GET",
    summary="Get OAuth credentials",
    description="Get OAuth credentials for workflow consumption",
    tags=["OAuth"],
    path_params={
        "connection_name": {
            "description": "Connection name",
            "schema": {"type": "string"},
            "required": True
        }
    },
    response_model=OAuthCredentialsResponse
)
@with_request_context
async def get_oauth_credentials(req: func.HttpRequest) -> func.HttpResponse:
    """
    GET /api/oauth/credentials/{connection_name}
    Get OAuth credentials for workflow consumption

    Returns actual access_token and refresh_token for use in API calls.
    This endpoint is intended for workflow consumption only.

    Route params: connection_name

    Requires: User must be authenticated

    Security: This endpoint returns sensitive credentials. It should only be
    called from authenticated contexts (workflows, functions).
    """
    context = get_context(req)
    connection_name = get_route_param(req, "connection_name")
    org_id = context.scope

    logger.info(
        f"User {context.email} retrieving OAuth credentials for {connection_name}",
        extra={"org_id": org_id, "user_id": context.user_id}
    )

    try:
        # Create services
        oauth_service = OAuthStorageService()
        config_service = TableStorageService("Config")

        try:
            keyvault = KeyVaultClient()
        except ValueError as e:
            logger.error(f"KeyVault not available: {e}")
            error = ErrorResponse(
                error="ServiceUnavailable",
                message="OAuth credentials retrieval requires KeyVault configuration"
            )
            return func.HttpResponse(
                json.dumps(error.model_dump()),
                status_code=503,
                mimetype="application/json"
            )

        # Get connection with org→GLOBAL fallback
        connection = await oauth_service.get_connection(org_id, connection_name)

        if not connection:
            error = ErrorResponse(
                error="NotFound",
                message=f"OAuth connection '{connection_name}' not found"
            )
            return func.HttpResponse(
                json.dumps(error.model_dump()),
                status_code=404,
                mimetype="application/json"
            )

        # Check connection status
        if connection.status != "completed":
            # Return response with no credentials
            response = OAuthCredentialsResponse(
                connection_name=connection_name,
                credentials=None,
                status=connection.status,
                expires_at=None
            )
            return func.HttpResponse(
                json.dumps(response.model_dump(mode="json")),
                status_code=200,
                mimetype="application/json"
            )

        # Get OAuth response config entry
        oauth_response_key = f"config:{connection.oauth_response_ref}"
        oauth_response_config = config_service.get_entity(
            connection.org_id,
            oauth_response_key
        )

        if not oauth_response_config:
            logger.error(f"OAuth response config not found: {oauth_response_key}")
            error = ErrorResponse(
                error="InternalServerError",
                message="OAuth credentials not properly configured"
            )
            return func.HttpResponse(
                json.dumps(error.model_dump()),
                status_code=500,
                mimetype="application/json"
            )

        # Get Key Vault secret name
        keyvault_secret_name = oauth_response_config.get("Value")

        if not keyvault_secret_name:
            logger.error("OAuth response config missing Key Vault secret name")
            error = ErrorResponse(
                error="InternalServerError",
                message="OAuth credentials not properly configured"
            )
            return func.HttpResponse(
                json.dumps(error.model_dump()),
                status_code=500,
                mimetype="application/json"
            )

        # Retrieve actual OAuth tokens from Key Vault
        # Note: keyvault_secret_name is already the full secret name (e.g., "GLOBAL--oauth-response-HaloPSA")
        # so we use the _client directly instead of get_secret() which expects org_id and secret_key
        try:
            secret = keyvault._client.get_secret(keyvault_secret_name)
            oauth_response_json = secret.value
            oauth_response = json.loads(oauth_response_json)
        except Exception as e:
            logger.error(
                f"Failed to retrieve OAuth tokens from Key Vault: {e}",
                extra={"secret_name": keyvault_secret_name}
            )
            error = ErrorResponse(
                error="InternalServerError",
                message="Failed to retrieve OAuth credentials"
            )
            return func.HttpResponse(
                json.dumps(error.model_dump()),
                status_code=500,
                mimetype="application/json"
            )

        # Parse OAuth response
        access_token = oauth_response.get("access_token")
        refresh_token = oauth_response.get("refresh_token")
        token_type = oauth_response.get("token_type", "Bearer")
        expires_at_str = oauth_response.get("expires_at")

        if not access_token:
            logger.error("OAuth response missing access_token")
            error = ErrorResponse(
                error="InternalServerError",
                message="OAuth credentials incomplete"
            )
            return func.HttpResponse(
                json.dumps(error.model_dump()),
                status_code=500,
                mimetype="application/json"
            )

        # Build credentials response
        credentials = OAuthCredentials(
            connection_name=connection_name,
            access_token=access_token,
            token_type=token_type,
            expires_at=expires_at_str,
            refresh_token=refresh_token,
            scopes=connection.scopes
        )

        response = OAuthCredentialsResponse(
            connection_name=connection_name,
            credentials=credentials,
            status=connection.status,
            expires_at=expires_at_str
        )

        logger.info(
            f"Retrieved OAuth credentials for {connection_name}",
            extra={"org_id": org_id, "user_id": context.user_id}
        )

        return func.HttpResponse(
            json.dumps(response.model_dump(mode="json")),
            status_code=200,
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Error retrieving OAuth credentials: {str(e)}", exc_info=True)
        error = ErrorResponse(
            error="InternalServerError",
            message="Failed to retrieve OAuth credentials"
        )
        return func.HttpResponse(
            json.dumps(error.model_dump()),
            status_code=500,
            mimetype="application/json"
        )


# ==================== REFRESH JOB STATUS ENDPOINT (USER STORY 4) ====================

@bp.function_name("oauth_refresh_job_status")
@bp.route(route="oauth/refresh_job_status", methods=["GET"])
@openapi_endpoint(
    path="/oauth/refresh_job_status",
    method="GET",
    summary="Get OAuth refresh job status",
    description="Get status of the last OAuth token refresh job (Platform admin only)",
    tags=["OAuth"]
)
@with_request_context
@require_platform_admin
async def get_oauth_refresh_job_status(req: func.HttpRequest) -> func.HttpResponse:
    """
    GET /api/oauth/refresh_job_status
    Get status of the last OAuth token refresh job

    Returns metrics and logs from the automatic token refresh scheduler

    Platform admin only endpoint
    """
    context = get_context(req)
    logger.info(f"User {context.email} retrieving OAuth refresh job status")

    try:
        # Get job status from SystemConfig table
        system_config_table = TableStorageService("SystemConfig")

        try:
            # Single point query - very efficient!
            job_status = system_config_table.get_entity("OAuthJobStatus", "TokenRefreshJob")
        except Exception as e:
            # Table doesn't exist yet or no job has run
            if "TableNotFound" in str(e) or "ResourceNotFound" in str(e):
                job_status = None
            else:
                raise

        if not job_status:
            # No job has run yet
            return func.HttpResponse(
                json.dumps({
                    "message": "No refresh job runs yet",
                    "last_run": None
                }),
                status_code=200,
                mimetype="application/json"
            )

        # Parse errors if present
        errors = []
        if job_status.get("Errors"):
            try:
                errors = json.loads(job_status.get("Errors"))
            except Exception:
                errors = []

        response = {
            "last_run": {
                "start_time": job_status.get("StartTime"),
                "end_time": job_status.get("EndTime"),
                "duration_seconds": job_status.get("DurationSeconds", 0),
                "status": job_status.get("Status"),
                "total_connections": job_status.get("TotalConnections", 0),
                "needs_refresh": job_status.get("NeedsRefresh", 0),
                "refreshed_successfully": job_status.get("RefreshedSuccessfully", 0),
                "refresh_failed": job_status.get("RefreshFailed", 0),
                "errors": errors,
                "error": job_status.get("ErrorMessage")  # Present if job itself failed
            }
        }

        return func.HttpResponse(
            json.dumps(response),
            status_code=200,
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Error retrieving OAuth refresh job status: {str(e)}", exc_info=True)
        error = ErrorResponse(
            error="InternalServerError",
            message="Failed to retrieve refresh job status"
        )
        return func.HttpResponse(
            json.dumps(error.model_dump()),
            status_code=500,
            mimetype="application/json"
        )
