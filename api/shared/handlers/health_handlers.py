"""
Health Check Handlers
Business logic for system health monitoring
Extracted from functions/health.py for unit testability
"""

import logging
from datetime import datetime
from typing import Literal, Optional

from shared.keyvault import KeyVaultClient
from shared.models import BasicHealthResponse, GeneralHealthResponse, HealthCheck, KeyVaultHealthResponse

logger = logging.getLogger(__name__)

# Type alias for health status
HealthStatus = Literal["healthy", "degraded", "unhealthy"]


def perform_basic_health_check() -> BasicHealthResponse:
    """
    Perform a basic health check (liveness check).
    This simply confirms the API is running and able to respond.
    Does NOT check external dependencies.

    Returns:
        BasicHealthResponse: Basic health status
    """
    return BasicHealthResponse(
        status="healthy",
        service="Bifrost Integrations API",
        timestamp=datetime.utcnow().isoformat() + "Z"
    )


def check_api_health() -> HealthCheck:
    """
    Check API health (always healthy if this code runs).

    Returns:
        HealthCheck: API health status with metadata
    """
    return HealthCheck(
        service="API",
        healthy=True,
        message="API is running",
        metadata={}
    )


async def check_keyvault_health(kv_manager: Optional[KeyVaultClient]) -> tuple[HealthCheck, HealthStatus]:
    """
    Check Key Vault health and return health check result with status update.

    Args:
        kv_manager: KeyVaultClient instance or None if not initialized

    Returns:
        tuple: (HealthCheck, overall_status_update)
            - HealthCheck: Key Vault health status with metadata
            - overall_status_update: "healthy", "degraded", or "unhealthy"

    Raises:
        Exception: If health check fails (logged and handled internally)
    """
    overall_status = "healthy"

    if kv_manager is None:
        logger.warning("Key Vault manager not initialized")
        return HealthCheck(
            service="Key Vault",
            healthy=False,
            message="Key Vault manager not initialized",
            metadata={}
        ), "degraded"

    try:
        health_result = await kv_manager.health_check()
        kv_status = health_result.get("status", "unhealthy")
        kv_healthy = kv_status == "healthy"

        # Determine overall status impact
        if kv_status == "degraded":
            overall_status = "degraded"
        elif kv_status == "unhealthy":
            overall_status = "degraded"  # Not fully unhealthy since API still works

        check = HealthCheck(
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
        )
        return check, overall_status

    except Exception as e:
        logger.error(f"Key Vault health check failed: {e}", exc_info=True)
        return HealthCheck(
            service="Key Vault",
            healthy=False,
            message=f"Health check failed: {str(e)}",
            metadata={}
        ), "degraded"


async def perform_general_health_check(kv_manager: Optional[KeyVaultClient]) -> GeneralHealthResponse:
    """
    Perform a comprehensive general health check.

    Args:
        kv_manager: KeyVaultClient instance or None

    Returns:
        GeneralHealthResponse: Overall health status with all service checks
    """
    logger.info("Performing general health check")

    checks = []
    overall_status: HealthStatus = "healthy"

    # Check 1: API health
    checks.append(check_api_health())

    # Check 2: Key Vault health
    kv_check, kv_status = await check_keyvault_health(kv_manager)
    checks.append(kv_check)

    # Update overall status if Key Vault has issues
    if kv_status != "healthy":
        overall_status = kv_status

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

    return response


async def perform_keyvault_health_check(kv_manager: Optional[KeyVaultClient]) -> KeyVaultHealthResponse:
    """
    Perform a detailed Key Vault health check.

    Args:
        kv_manager: KeyVaultClient instance or None

    Returns:
        KeyVaultHealthResponse: Detailed Key Vault health status

    Raises:
        Exception: If health check fails (logged and handled internally)
    """
    logger.info("Performing Key Vault health check")

    # Check if Key Vault manager is available
    if not kv_manager:
        logger.error("Key Vault manager not initialized")
        return KeyVaultHealthResponse(
            status="unhealthy",
            message="Key Vault manager is not initialized. Check AZURE_KEY_VAULT_URL configuration.",
            vaultUrl=None,
            canConnect=False,
            canListSecrets=False,
            canGetSecrets=False,
            secretCount=None,
            lastChecked=datetime.utcnow()
        )

    try:
        # Perform health check
        health_result = await kv_manager.health_check()

        # Extract results
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
                "can_get": can_get
            }
        )

        return response

    except Exception as e:
        logger.error(f"Error during Key Vault health check: {e}", exc_info=True)
        return KeyVaultHealthResponse(
            status="unhealthy",
            message=f"Failed to perform health check: {str(e)}",
            vaultUrl=kv_manager.vault_url if hasattr(kv_manager, 'vault_url') else None,
            canConnect=False,
            canListSecrets=False,
            canGetSecrets=False,
            secretCount=None,
            lastChecked=datetime.utcnow()
        )
