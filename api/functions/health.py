"""
Health monitoring API endpoints.

Provides REST API for checking the health status of Azure Key Vault
integration and other system dependencies.
"""

import logging
import json
from datetime import datetime
import azure.functions as func
from shared.models import (
    HealthCheck,
    GeneralHealthResponse,
    KeyVaultHealthResponse,
    ErrorResponse
)
from shared.openapi_decorators import openapi_endpoint
from shared.keyvault import KeyVaultClient
from shared.auth import require_auth, is_platform_admin

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
    response_model=GeneralHealthResponse
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
    logger.info("General health check requested")

    checks = []
    overall_status = "healthy"

    # Check 1: API health (always healthy if we got here)
    checks.append(HealthCheck(
        service="API",
        healthy=True,
        message="API is running",
        metadata={}
    ))

    # Check 2: Key Vault health
    if kv_manager:
        try:
            health_result = kv_manager.health_check()
            kv_status = health_result.get("status", "unhealthy")
            kv_healthy = kv_status == "healthy"

            # Downgrade overall status if Key Vault is degraded/unhealthy
            if kv_status == "degraded" and overall_status == "healthy":
                overall_status = "degraded"
            elif kv_status == "unhealthy":
                overall_status = "degraded"  # Not fully unhealthy since API still works

            checks.append(HealthCheck(
                service="Key Vault",
                healthy=kv_healthy,
                message="Key Vault accessible" if kv_healthy else health_result.get("error", "Key Vault not accessible"),
                metadata={
                    "vaultUrl": kv_manager.vault_url if hasattr(kv_manager, 'vault_url') else None,
                    "canConnect": health_result.get("can_connect", False),
                    "canListSecrets": health_result.get("can_list_secrets", False),
                    "canGetSecrets": health_result.get("can_get_secrets", False),
                    "secretCount": health_result.get("secret_count")
                }
            ))
        except Exception as e:
            logger.error(f"Key Vault health check failed: {e}", exc_info=True)
            overall_status = "degraded"
            checks.append(HealthCheck(
                service="Key Vault",
                healthy=False,
                message=f"Health check failed: {str(e)}",
                metadata={}
            ))
    else:
        overall_status = "degraded"
        checks.append(HealthCheck(
            service="Key Vault",
            healthy=False,
            message="Key Vault manager not initialized",
            metadata={}
        ))

    response = GeneralHealthResponse(
        status=overall_status,
        service="Bifrost Integrations API",
        timestamp=datetime.utcnow(),
        checks=checks
    )

    logger.info(
        f"General health check completed: {overall_status}",
        extra={
            "overall_status": overall_status,
            "checks_count": len(checks)
        }
    )

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
    response_model=KeyVaultHealthResponse
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
    user = req.user
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

        # Check if Key Vault manager is available
        if not kv_manager:
            logger.error("Key Vault manager not initialized")
            response = KeyVaultHealthResponse(
                status="unhealthy",
                message="Key Vault manager is not initialized. Check AZURE_KEY_VAULT_URL configuration.",
                vaultUrl=None,
                canConnect=False,
                canListSecrets=False,
                canGetSecrets=False,
                secretCount=None,
                lastChecked=datetime.utcnow()
            )
            return func.HttpResponse(
                json.dumps(response.model_dump(mode="json")),
                status_code=200,
                mimetype="application/json"
            )

        # Perform health check using KeyVaultClient
        health_result = kv_manager.health_check()

        # Determine overall status based on health check results
        status = health_result.get("status", "unhealthy")
        can_connect = health_result.get("can_connect", False)
        can_list = health_result.get("can_list_secrets", False)
        can_get = health_result.get("can_get_secrets", False)
        secret_count = health_result.get("secret_count")

        # Build status message
        if status == "healthy":
            message = "Key Vault is accessible and all permissions are configured correctly"
        elif status == "degraded":
            message = "Key Vault is accessible but some permissions may be limited"
        else:
            message = health_result.get("error", "Key Vault is not accessible")

        # Build response
        response = KeyVaultHealthResponse(
            status=status,
            message=message,
            vaultUrl=kv_manager.vault_url if hasattr(kv_manager, 'vault_url') else None,
            canConnect=can_connect,
            canListSecrets=can_list,
            canGetSecrets=can_get,
            secretCount=secret_count,
            lastChecked=datetime.utcnow()
        )

        logger.info(
            f"Key Vault health check completed: {status}",
            extra={
                "status": status,
                "can_connect": can_connect,
                "can_list": can_list,
                "can_get": can_get,
                "checked_by": user.email
            }
        )

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
