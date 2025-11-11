"""
OAuth Connection Handlers
Business logic for OAuth connection management endpoints.
Extracted from functions/oauth_api.py to enable unit testing.
"""

import logging
import uuid
from urllib.parse import urlencode

import azure.functions as func
from pydantic import ValidationError

from shared.models import (
    CreateOAuthConnectionRequest,
    OAuthCredentialsResponse,
    UpdateOAuthConnectionRequest,
)
from shared.services.oauth_provider import OAuthProviderClient
from shared.services.oauth_test_service import OAuthTestService
from shared.repositories.oauth import OAuthRepository
from shared.keyvault import KeyVaultClient
from shared.async_storage import AsyncTableStorageService
from shared.custom_types import get_context, get_route_param
from shared.handlers.response_helpers import (
    success_response,
    not_found,
    conflict,
    validation_error,
    bad_request,
    internal_error,
)

logger = logging.getLogger(__name__)


async def create_oauth_connection_handler(req: func.HttpRequest) -> func.HttpResponse:
    """Create a new OAuth connection."""
    context = get_context(req)
    org_id = context.scope

    logger.info(f"User {context.email} creating OAuth connection for org {org_id}")

    try:
        request_body = req.get_json()
        create_request = CreateOAuthConnectionRequest(**request_body)

        oauth_repo = OAuthRepository()

        # Check if connection already exists
        existing = await oauth_repo.get_connection(create_request.connection_name, org_id)
        if existing:
            return conflict("OAuth connection", create_request.connection_name)

        # Create connection
        connection = await oauth_repo.create_connection(
            request=create_request,
            org_id=org_id,
            created_by=context.user_id
        )

        logger.info(f"Created OAuth connection: {create_request.connection_name}")

        # If client_credentials flow, immediately acquire token
        if create_request.oauth_flow_type == "client_credentials":
            logger.info(f"Client credentials flow detected, acquiring initial token for {create_request.connection_name}")

            try:
                # Get client secret from Key Vault
                client_secret = None
                if connection.client_secret_ref:
                    async with KeyVaultClient() as keyvault:
                        client_secret = await keyvault.get_secret(connection.client_secret_ref)

                if not client_secret:
                    raise ValueError("Client credentials flow requires client_secret")

                # Get initial token
                oauth_provider = OAuthProviderClient()
                success, result = await oauth_provider.get_client_credentials_token(
                    token_url=connection.token_url,
                    client_id=connection.client_id,
                    client_secret=client_secret,
                    scopes=connection.scopes
                )

                if not success:
                    error_msg = result.get("error_description", result.get("error", "Token acquisition failed"))
                    logger.error(f"Failed to acquire client credentials token: {error_msg}")
                    await oauth_repo.update_status(
                        connection_name=create_request.connection_name,
                        org_id=org_id,
                        status="failed",
                        status_message=f"Failed to acquire initial token: {error_msg}"
                    )
                else:
                    # Store tokens
                    await oauth_repo.store_tokens(
                        connection_name=connection.connection_name,
                        org_id=connection.org_id,
                        access_token=result["access_token"],
                        refresh_token=None,  # Client credentials doesn't use refresh tokens
                        expires_at=result["expires_at"],
                        token_type=result["token_type"],
                        updated_by="system"
                    )

                    # Update status to completed
                    await oauth_repo.update_status(
                        connection_name=create_request.connection_name,
                        org_id=org_id,
                        status="completed",
                        status_message="Client credentials token acquired successfully"
                    )

                    logger.info(f"Client credentials token acquired for {create_request.connection_name}")

                    # Re-fetch connection to get updated status
                    updated_connection = await oauth_repo.get_connection(create_request.connection_name, org_id)
                    if updated_connection:
                        connection = updated_connection

            except Exception as e:
                logger.error(f"Error acquiring client credentials token: {str(e)}", exc_info=True)
                await oauth_repo.update_status(
                    org_id=org_id,
                    connection_name=create_request.connection_name,
                    status="failed",
                    status_message=f"Failed to acquire initial token: {str(e)}"
                )
                # Re-fetch connection to get updated status
                updated_connection = await oauth_repo.get_connection(org_id, create_request.connection_name)
                if updated_connection:
                    connection = updated_connection

        detail = connection.to_detail() if connection else None
        if detail is None:
            return internal_error("Failed to retrieve created connection")
        return success_response(detail.model_dump(mode="json"), 201)

    except ValidationError as e:
        logger.warning(f"Validation error creating OAuth connection: {e}")
        return validation_error("Invalid request data", errors=e.errors())

    except ValueError as e:
        logger.error(f"Error parsing request: {str(e)}")
        return bad_request("Invalid JSON in request body")

    except Exception as e:
        logger.error(f"Error creating OAuth connection: {str(e)}", exc_info=True)
        return internal_error("Failed to create OAuth connection")


async def list_oauth_connections_handler(req: func.HttpRequest) -> func.HttpResponse:
    """List all OAuth connections for an organization."""
    context = get_context(req)
    org_id = context.scope
    is_global_scope = (org_id == "GLOBAL")

    logger.info(f"User {context.email} listing OAuth connections for org {org_id}")

    try:
        oauth_repo = OAuthRepository()
        # Only include GLOBAL connections when viewing GLOBAL scope
        # When viewing a specific org, only show that org's connections
        connections = await oauth_repo.list_connections(org_id, include_global=is_global_scope)

        details = [conn.to_detail() for conn in connections]
        return success_response([d.model_dump(mode="json") for d in details])

    except Exception as e:
        logger.error(f"Error listing OAuth connections: {str(e)}", exc_info=True)
        return internal_error("Failed to list OAuth connections")


async def get_oauth_connection_handler(req: func.HttpRequest) -> func.HttpResponse:
    """Get a specific OAuth connection by name."""
    context = get_context(req)
    org_id = context.scope
    name = get_route_param(req, "name")

    logger.info(f"User {context.email} getting OAuth connection: {name}")

    try:
        oauth_repo = OAuthRepository()
        connection = await oauth_repo.get_connection(name, org_id)

        if not connection:
            return not_found("OAuth connection", name)

        detail = connection.to_detail()
        return success_response(detail.model_dump(mode="json"))

    except Exception as e:
        logger.error(f"Error getting OAuth connection: {str(e)}", exc_info=True)
        return internal_error("Failed to get OAuth connection")


async def update_oauth_connection_handler(req: func.HttpRequest) -> func.HttpResponse:
    """Update an existing OAuth connection."""
    context = get_context(req)
    org_id = context.scope
    name = get_route_param(req, "name")

    logger.info(f"User {context.email} updating OAuth connection: {name}")

    try:
        request_body = req.get_json()
        update_request = UpdateOAuthConnectionRequest(**request_body)

        oauth_repo = OAuthRepository()
        connection = await oauth_repo.get_connection(name, org_id)

        if not connection:
            return not_found("OAuth connection", name)

        # Update connection
        updated = await oauth_repo.update_connection(
            connection_name=name,
            org_id=org_id,
            request=update_request,
            updated_by=context.user_id
        )

        logger.info(f"Updated OAuth connection: {name}")
        if updated is None:
            return internal_error("Failed to retrieve updated connection")
        detail = updated.to_detail()
        return success_response(detail.model_dump(mode="json"))

    except ValidationError as e:
        logger.warning(f"Validation error updating OAuth connection: {e}")
        return validation_error("Invalid request data", errors=e.errors())

    except ValueError as e:
        logger.error(f"Error parsing request: {str(e)}")
        return bad_request("Invalid JSON in request body")

    except Exception as e:
        logger.error(f"Error updating OAuth connection: {str(e)}", exc_info=True)
        return internal_error("Failed to update OAuth connection")


async def delete_oauth_connection_handler(req: func.HttpRequest) -> func.HttpResponse:
    """Delete an OAuth connection."""
    context = get_context(req)
    org_id = context.scope
    name = get_route_param(req, "name")

    logger.info(f"User {context.email} deleting OAuth connection: {name}")

    try:
        oauth_repo = OAuthRepository()
        connection = await oauth_repo.get_connection(name, org_id)

        if not connection:
            return not_found("OAuth connection", name)

        await oauth_repo.delete_connection(name, org_id)
        logger.info(f"Deleted OAuth connection: {name}")

        return func.HttpResponse(status_code=204)

    except Exception as e:
        logger.error(f"Error deleting OAuth connection: {str(e)}", exc_info=True)
        return internal_error("Failed to delete OAuth connection")


async def authorize_oauth_connection_handler(req: func.HttpRequest) -> func.HttpResponse:
    """Start OAuth authorization flow."""
    context = get_context(req)
    org_id = context.scope
    name = get_route_param(req, "name")

    logger.info(f"User {context.email} authorizing OAuth connection: {name}")

    try:
        oauth_repo = OAuthRepository()
        connection = await oauth_repo.get_connection(name, org_id)

        if not connection:
            return not_found("OAuth connection", name)

        # Check if client credentials flow (doesn't need authorization)
        if connection.oauth_flow_type == "client_credentials":
            return bad_request("Client credentials flow does not require authorization")

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
        await oauth_repo.update_status(
            connection_name=name,
            org_id=org_id,
            status="waiting_callback",
            status_message=f"Waiting for OAuth callback (state: {state})"
        )

        logger.info(f"Generated authorization URL for {name}")

        # Return authorization URL
        return success_response({
            "authorization_url": authorization_url,
            "state": state,
            "message": "Visit the authorization URL to complete OAuth flow"
        })

    except Exception as e:
        logger.error(f"Error authorizing OAuth connection: {str(e)}", exc_info=True)
        return internal_error("Failed to start authorization flow")


async def cancel_oauth_authorization_handler(req: func.HttpRequest) -> func.HttpResponse:
    """Cancel OAuth authorization."""
    context = get_context(req)
    org_id = context.scope
    name = get_route_param(req, "name")

    logger.info(f"User {context.email} canceling OAuth authorization: {name}")

    try:
        oauth_repo = OAuthRepository()
        connection = await oauth_repo.get_connection(name, org_id)

        if not connection:
            return not_found("OAuth connection", name)

        # Reset to not_connected status
        await oauth_repo.update_status(
            connection_name=name,
            org_id=org_id,
            status="not_connected",
            status_message="Authorization canceled by user"
        )

        logger.info(f"Canceled OAuth authorization: {name}")

        return success_response({"message": "Authorization canceled"})

    except Exception as e:
        logger.error(f"Error canceling OAuth authorization: {str(e)}", exc_info=True)
        return internal_error("Failed to cancel authorization")


async def refresh_oauth_token_handler(req: func.HttpRequest) -> func.HttpResponse:
    """Refresh OAuth token."""
    context = get_context(req)
    org_id = context.scope
    name = get_route_param(req, "name")

    logger.info(f"User {context.email} refreshing OAuth token: {name}")

    try:
        oauth_repo = OAuthRepository()
        connection = await oauth_repo.get_connection(name, org_id)

        if not connection:
            return not_found("OAuth connection", name)

        # Refresh token
        success = await oauth_repo.refresh_token(name, org_id)
        if not success:
            return bad_request("Failed to refresh token")

        logger.info(f"Refreshed OAuth token: {name}")
        return success_response({"message": "Token refreshed"})

    except Exception as e:
        logger.error(f"Error refreshing OAuth token: {str(e)}", exc_info=True)
        return internal_error("Failed to refresh token")


async def oauth_callback_handler(req: func.HttpRequest) -> func.HttpResponse:
    """
    Handle OAuth provider callback.

    This is called by the UI callback page, not directly by the OAuth provider.
    The UI receives the authorization code from the OAuth provider redirect,
    then sends it here for server-side token exchange.
    """
    connection_name = get_route_param(req, "connection_name")

    # Get code from POST body
    try:
        request_body = req.get_json()
        code = request_body.get("code")
    except ValueError:
        logger.error("Invalid JSON in callback request body")
        return bad_request("Request body must be valid JSON")

    logger.info(f"OAuth callback received for {connection_name}")

    try:
        # Create services
        oauth_repo = OAuthRepository()
        oauth_provider = OAuthProviderClient()
        oauth_test = OAuthTestService()

        # Try to find connection (check GLOBAL first for simplicity)
        connection = await oauth_repo.get_connection(connection_name, "GLOBAL")

        if not connection:
            # Try other orgs if needed (for now, just fail)
            logger.error(f"OAuth connection not found: {connection_name}")
            return not_found("OAuth connection", connection_name)

        # Validate authorization code
        if not code:
            logger.error("OAuth callback missing authorization code")
            return bad_request("Missing authorization code")

        # Exchange code for tokens
        logger.info(f"Exchanging authorization code for tokens: {connection_name}")

        await oauth_repo.update_status(
            connection_name=connection_name,
            org_id=connection.org_id,
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
                async with KeyVaultClient() as keyvault:
                    client_secret = await keyvault.get_secret(connection.client_secret_ref)
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

            await oauth_repo.update_status(
                org_id=connection.org_id,
                connection_name=connection_name,
                status="failed",
                status_message=f"Token exchange failed: {error_msg}"
            )

            # Return structured response with error_message field
            return success_response({
                "success": False,
                "message": "OAuth token exchange failed",
                "status": "failed",
                "connection_name": connection_name,
                "warning_message": None,
                "error_message": error_msg
            })

        # Test connection
        logger.info(f"Testing OAuth connection: {connection_name}")

        test_success, test_message = await oauth_test.test_connection(
            access_token=result["access_token"],
            authorization_url=connection.authorization_url or "",
            token_url=connection.token_url
        )

        # Store tokens
        await oauth_repo.store_tokens(
            connection_name=connection_name,
            org_id=connection.org_id,
            access_token=result["access_token"],
            refresh_token=result.get("refresh_token"),
            expires_at=result["expires_at"],
            token_type=result["token_type"],
            updated_by="system"
        )

        # Update final status
        final_status = "completed" if test_success else "failed"
        await oauth_repo.update_status(
            connection_name=connection_name,
            org_id=connection.org_id,
            status=final_status,
            status_message=test_message
        )

        logger.info(f"OAuth connection completed: {connection_name} (status={final_status})")

        # Check if refresh token was provided
        warning_message = None
        refresh_token = result.get("refresh_token")
        logger.info(f"Refresh token check for {connection_name}: refresh_token={refresh_token!r}, type={type(refresh_token)}")

        if not refresh_token:
            warning_message = (
                "The OAuth provider did not return a refresh token. "
                "This connection will not be able to automatically refresh when the access token expires. "
                "If this was unintentional, review your OAuth application settings with the provider."
            )
            logger.warning(f"No refresh token returned for {connection_name}")

        # Return JSON success response with structured fields
        return success_response({
            "success": True,
            "message": "OAuth connection completed successfully",
            "status": final_status,
            "connection_name": connection_name,
            "warning_message": warning_message,
            "error_message": None
        })

    except ValidationError as e:
        logger.warning(f"Validation error in OAuth callback: {e}")
        return validation_error("Invalid callback data", errors=e.errors())

    except ValueError as e:
        logger.error(f"Error in OAuth callback: {str(e)}")
        return bad_request(f"Invalid callback request: {str(e)}")

    except Exception as e:
        logger.error(f"Error handling OAuth callback: {str(e)}", exc_info=True)
        return internal_error("Failed to handle OAuth callback")


async def get_oauth_credentials_handler(req: func.HttpRequest) -> func.HttpResponse:
    """Get OAuth credentials for a connection."""
    context = get_context(req)
    org_id = context.scope
    name = get_route_param(req, "name")

    logger.info(f"User {context.email} getting OAuth credentials: {name}")

    try:
        oauth_repo = OAuthRepository()
        connection = await oauth_repo.get_connection(name, org_id)

        if not connection:
            return not_found("OAuth connection", name)

        # Build credentials response from connection
        # Note: actual access_token and refresh_token are stored in Config/KeyVault by reference
        # We only return the metadata (type and expiration)
        credentials = None

        response = OAuthCredentialsResponse(
            connection_name=name,
            credentials=credentials,
            status=connection.status,
            expires_at=connection.expires_at.isoformat() if connection.expires_at else None
        )
        return success_response(response.model_dump(mode="json"))

    except Exception as e:
        logger.error(f"Error getting OAuth credentials: {str(e)}", exc_info=True)
        return internal_error("Failed to get OAuth credentials")


async def get_oauth_refresh_job_status_handler(req: func.HttpRequest) -> func.HttpResponse:
    """Get status of OAuth token refresh jobs (returns last run info)."""
    context = get_context(req)

    logger.info(f"User {context.email} checking OAuth refresh job status")

    try:
        # Get job status from Config table
        config_service = AsyncTableStorageService("Config")

        try:
            job_status = await config_service.get_entity("SYSTEM", "jobstatus:TokenRefreshJob")

            if job_status:
                # Convert to dict and remove Azure Table metadata
                status_dict = {
                    k: v for k, v in job_status.items()
                    if not k.startswith("_") and k not in ["PartitionKey", "RowKey", "Timestamp", "etag"]
                }
                return success_response(status_dict)
            else:
                # No job has run yet
                return success_response({"message": "No refresh jobs have run yet"})
        except Exception:
            # No job has run yet
            return success_response({"message": "No refresh jobs have run yet"})

    except Exception as e:
        logger.error(f"Error getting refresh job status: {str(e)}", exc_info=True)
        return internal_error("Failed to get refresh job status")


async def trigger_oauth_refresh_job_handler(req: func.HttpRequest) -> func.HttpResponse:
    """Manually trigger the OAuth token refresh job."""
    context = get_context(req)

    logger.info(f"User {context.email} manually triggering OAuth refresh job")

    try:
        # Initialize service and run refresh job
        oauth_repo = OAuthRepository()
        results = await oauth_repo.run_refresh_job(
            trigger_type="manual",
            trigger_user=context.email
        )

        # Return results
        return success_response({
            "message": "Refresh job completed",
            **results
        })

    except Exception as e:
        logger.error(f"Manual OAuth refresh job failed: {str(e)}", exc_info=True)
        return internal_error(f"Failed to trigger refresh job: {str(e)}")
