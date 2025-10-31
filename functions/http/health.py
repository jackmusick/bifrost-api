"""
Health monitoring API endpoints.

Provides REST API for checking the health status of the API.
- /health: Basic liveness check (always returns 200 if API is running)
- /health/keyvault: Detailed KeyVault health check (requires platform admin)
"""

import json
import logging

import azure.functions as func

from shared.auth import is_platform_admin, require_auth
from shared.handlers.health_handlers import (
    perform_basic_health_check,
    perform_keyvault_health_check,
)
from shared.keyvault import KeyVaultClient
from shared.models import ErrorResponse
from shared.openapi_decorators import openapi_endpoint

logger = logging.getLogger(__name__)

# Create blueprint for health endpoints
bp = func.Blueprint()

# Initialize Key Vault manager lazily (only for /health/keyvault endpoint)
def get_kv_manager():
    """Get or create KeyVault manager on demand."""
    try:
        return KeyVaultClient()
    except Exception as e:
        logger.error(f"Failed to initialize Key Vault manager: {e}")
        return None


@bp.function_name("health_general")
@bp.route(route="health", methods=["GET"])
@openapi_endpoint(
    path="/health",
    method="GET",
    summary="Basic health check",
    description="Simple liveness check - returns 200 if API is running",
    tags=["Health"],
    response_model=None  # Will be inferred from handler
)
async def general_health(req: func.HttpRequest) -> func.HttpResponse:
    """
    GET /api/health

    Basic liveness check for the API.
    Returns 200 OK if the API is running and able to respond to requests.
    Does NOT check external dependencies (use /health/keyvault for detailed checks).

    Returns:
        200: BasicHealthResponse with status

    Example:
        GET /api/health
        Response: {
            "status": "healthy",
            "service": "Bifrost Integrations API",
            "timestamp": "2025-10-15T12:34:56.789Z"
        }
    """
    response = perform_basic_health_check()

    return func.HttpResponse(
        json.dumps(response.model_dump(mode="json")),
        status_code=200,
        mimetype="application/json"
    )


@bp.function_name("health_keyvault")
@bp.route(route="health/keyvault", methods=["GET"])
@openapi_endpoint(
    path="/health/keyvault",
    method="GET",
    summary="Check Key Vault health",
    description="Check the health status of Azure Key Vault integration (Platform admin only)",
    tags=["Health"],
    response_model=None  # Will be inferred from handler
)
@require_auth
async def keyvault_health(req: func.HttpRequest) -> func.HttpResponse:
    """
    GET /api/health/keyvault

    Check the health status of Azure Key Vault integration.

    Returns:
        200: KeyVaultHealthResponse with health status
        403: Permission denied (not platform admin)
        500: Unexpected error during health check

    Example:
        GET /api/health/keyvault
        Response: {
            "status": "healthy",
            "message": "Key Vault is accessible and all permissions are configured correctly",
            "vaultUrl": "https://my-vault.vault.azure.net/",
            "canConnect": true,
            "canListSecrets": true,
            "canGetSecrets": true,
            "secretCount": 15,
            "lastChecked": "2025-10-12T12:34:56.789Z"
        }
    """
    user = req.user  # type: ignore[attr-defined]
    logger.info(f"User {user.email} checking Key Vault health")

    try:
        # Check if user is platform admin
        if not is_platform_admin(user.user_id):
            logger.warning(f"User {user.email} is not a platform admin - denied health check access")
            error = ErrorResponse(
                error="Forbidden",
                message="Only platform administrators can check Key Vault health"
            )
            return func.HttpResponse(
                json.dumps(error.model_dump()),
                status_code=403,
                mimetype="application/json"
            )

        # Perform health check (get KV manager on demand)
        kv_manager = get_kv_manager()
        response = await perform_keyvault_health_check(kv_manager)

        return func.HttpResponse(
            json.dumps(response.model_dump(mode="json")),
            status_code=200,
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Error during health check: {e}", exc_info=True)
        error = ErrorResponse(
            error="InternalServerError",
            message=f"Failed to perform health check: {str(e)}"
        )
        return func.HttpResponse(
            json.dumps(error.model_dump()),
            status_code=500,
            mimetype="application/json"
        )
