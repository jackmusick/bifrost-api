"""
Config Router

Manage global and organization-specific configuration key-value pairs.
Manage integration configurations (Microsoft Graph, HaloPSA).
API-compatible with the existing Azure Functions implementation.
"""

import logging
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

# Import existing Pydantic models for API compatibility
from shared.models import (
    Config,
    IntegrationConfig,
    SetConfigRequest,
    SetIntegrationConfigRequest,
)

from src.core.auth import Context, CurrentSuperuser

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Configuration"])


# =============================================================================
# Config Endpoints
# =============================================================================


@router.get(
    "/api/config",
    response_model=list[Config],
    summary="Get configuration values",
    description="Get configuration values for current scope",
)
async def get_config(
    ctx: Context,
    user: CurrentSuperuser,
) -> list[Config]:
    """Get configuration for current scope."""
    from shared.handlers.org_config_handlers import get_config_logic
    from shared.context import ExecutionContext as SharedContext

    try:
        shared_ctx = SharedContext(
            user_id=str(ctx.user.user_id),
            name=ctx.user.name,
            email=ctx.user.email,
            is_platform_admin=ctx.user.is_superuser,
            org_id=str(ctx.org_id) if ctx.org_id else None,
        )

        configs = await get_config_logic(shared_ctx)
        return configs

    except Exception as e:
        logger.error(f"Error getting config: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get configuration",
        )


@router.post(
    "/api/config",
    response_model=Config,
    status_code=status.HTTP_201_CREATED,
    summary="Set configuration value",
    description="Set a configuration value in the current scope",
)
async def set_config(
    request: SetConfigRequest,
    ctx: Context,
    user: CurrentSuperuser,
) -> Config:
    """Set a configuration key-value pair."""
    from shared.handlers.org_config_handlers import set_config_logic
    from shared.context import ExecutionContext as SharedContext

    try:
        shared_ctx = SharedContext(
            user_id=str(ctx.user.user_id),
            name=ctx.user.name,
            email=ctx.user.email,
            is_platform_admin=ctx.user.is_superuser,
            org_id=str(ctx.org_id) if ctx.org_id else None,
        )

        config = await set_config_logic(shared_ctx, request)
        return config

    except Exception as e:
        logger.error(f"Error setting config: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to set configuration",
        )


@router.delete(
    "/api/config/{key}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete configuration value",
    description="Delete a configuration value by key",
)
async def delete_config(
    key: str,
    ctx: Context,
    user: CurrentSuperuser,
) -> None:
    """Delete a configuration key."""
    from shared.handlers.org_config_handlers import delete_config_logic
    from shared.context import ExecutionContext as SharedContext

    try:
        shared_ctx = SharedContext(
            user_id=str(ctx.user.user_id),
            name=ctx.user.name,
            email=ctx.user.email,
            is_platform_admin=ctx.user.is_superuser,
            org_id=str(ctx.org_id) if ctx.org_id else None,
        )

        success = await delete_config_logic(shared_ctx, key)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Configuration not found",
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting config: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete configuration",
        )


# =============================================================================
# Integration Config Endpoints
# =============================================================================


@router.get(
    "/api/organizations/{org_id}/integrations",
    response_model=list[IntegrationConfig],
    summary="Get organization integrations",
    description="Get all integration configurations for an organization",
)
async def get_integrations(
    org_id: UUID,
    ctx: Context,
    user: CurrentSuperuser,
) -> list[IntegrationConfig]:
    """Get integration configurations for an organization."""
    from shared.handlers.org_config_handlers import get_integrations_logic
    from shared.context import ExecutionContext as SharedContext

    try:
        shared_ctx = SharedContext(
            user_id=str(ctx.user.user_id),
            name=ctx.user.name,
            email=ctx.user.email,
            is_platform_admin=ctx.user.is_superuser,
            org_id=str(org_id),
        )

        integrations = await get_integrations_logic(shared_ctx, str(org_id))
        return integrations

    except Exception as e:
        logger.error(f"Error getting integrations: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get integrations",
        )


@router.post(
    "/api/organizations/{org_id}/integrations",
    response_model=IntegrationConfig,
    summary="Set organization integration",
    description="Set integration configuration for an organization",
)
async def set_integration(
    org_id: UUID,
    request: SetIntegrationConfigRequest,
    ctx: Context,
    user: CurrentSuperuser,
) -> IntegrationConfig:
    """Set integration configuration."""
    from shared.handlers.org_config_handlers import set_integration_logic
    from shared.context import ExecutionContext as SharedContext

    try:
        shared_ctx = SharedContext(
            user_id=str(ctx.user.user_id),
            name=ctx.user.name,
            email=ctx.user.email,
            is_platform_admin=ctx.user.is_superuser,
            org_id=str(org_id),
        )

        integration = await set_integration_logic(shared_ctx, str(org_id), request)
        return integration

    except Exception as e:
        logger.error(f"Error setting integration: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to set integration",
        )


@router.delete(
    "/api/organizations/{org_id}/integrations/{integration_type}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete organization integration",
    description="Delete integration configuration for an organization",
)
async def delete_integration(
    org_id: UUID,
    integration_type: str,
    ctx: Context,
    user: CurrentSuperuser,
) -> None:
    """Delete integration configuration."""
    from shared.handlers.org_config_handlers import delete_integration_logic
    from shared.context import ExecutionContext as SharedContext

    try:
        shared_ctx = SharedContext(
            user_id=str(ctx.user.user_id),
            name=ctx.user.name,
            email=ctx.user.email,
            is_platform_admin=ctx.user.is_superuser,
            org_id=str(org_id),
        )

        success = await delete_integration_logic(shared_ctx, str(org_id), integration_type)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Integration not found",
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting integration: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete integration",
        )
