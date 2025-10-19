"""
Health monitoring API endpoints.

Provides REST API for checking the health status of Azure Key Vault
integration and other system dependencies.
"""

import json
import logging

import azure.functions as func

from shared.auth import is_platform_admin, require_auth
from shared.handlers.health_handlers import (
    perform_general_health_check,
    perform_keyvault_health_check,
)
from shared.keyvault import KeyVaultClient
from shared.models import ErrorResponse
from shared.openapi_decorators import openapi_endpoint

logger = logging.getLogger(__name__)

# Create blueprint for health endpoints
bp = func.Blueprint()

# Initialize Key Vault manager
try:
    kv_manager = KeyVaultClient()
except Exception as e:
    logger.error(f"Failed to initialize Key Vault manager: {e}")
    kv_manager = None


@bp.function_name("health_general")
@bp.route(route="health", methods=["GET"])
@openapi_endpoint(
    path="/health",
    method="GET",
    summary="General health check",
    description="Check the overall health status of the API and its dependencies",
    tags=["Health"],
    response_model=None  # Will be inferred from handler
)
async def general_health(req: func.HttpRequest) -> func.HttpResponse:
    """
    GET /api/health

    Check the overall health status of the API and its dependencies.

    Returns:
        200: GeneralHealthResponse with overall status and individual service checks

    Example:
        GET /api/health
        Response: {
            "status": "healthy",
            "service": "Bifrost Integrations API",
            "timestamp": "2025-10-15T12:34:56.789Z",
            "checks": [
                {
                    "service": "API",
                    "healthy": true,
                    "message": "API is running",
                    "metadata": {}
                },
                {
                    "service": "Key Vault",
                    "healthy": true,
                    "message": "Key Vault accessible",
                    "metadata": {
                        "vaultUrl": "https://...",
                        "canConnect": true,
                        "canListSecrets": true,
                        "canGetSecrets": true,
                        "secretCount": 15
                    }
                }
            ]
        }
    """
    response = perform_general_health_check(kv_manager)

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
def keyvault_health(req: func.HttpRequest) -> func.HttpResponse:
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

        # Perform health check
        response = perform_keyvault_health_check(kv_manager)

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
