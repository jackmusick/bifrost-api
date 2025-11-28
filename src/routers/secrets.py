"""
Secrets Router

Secret management API endpoints.
Provides REST API for listing, creating, updating, and deleting secrets.
API-compatible with the existing Azure Functions implementation.

Note: In the Docker-based deployment, secrets are stored in PostgreSQL
instead of Azure Key Vault.
"""

import logging
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# Import existing Pydantic models for API compatibility
from shared.models import (
    SecretCreateRequest,
    SecretListResponse,
    SecretResponse,
    SecretUpdateRequest,
)

from src.core.auth import Context, CurrentSuperuser
from src.core.database import DbSession
from src.core.security import encrypt_secret, decrypt_secret
from src.models.database import Secret as SecretModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/secrets", tags=["Secrets"])


# =============================================================================
# Repository
# =============================================================================


class SecretRepository:
    """PostgreSQL-based secret repository (replaces Azure Key Vault)."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_secrets(self, org_id: str | None = None) -> SecretListResponse:
        """List secrets, optionally filtered by organization."""
        query = select(SecretModel)

        if org_id:
            # Return org-specific and global secrets
            query = query.where(
                (SecretModel.organization_id == UUID(org_id)) |
                (SecretModel.organization_id == None)
            )

        result = await self.db.execute(query.order_by(SecretModel.name))
        secrets = result.scalars().all()

        secret_names = [s.name for s in secrets]
        return SecretListResponse(
            secrets=secret_names,
            orgId=org_id,
            count=len(secret_names),
        )

    async def create_secret(
        self,
        request: SecretCreateRequest,
        created_by: str,
    ) -> SecretResponse:
        """Create a new secret."""
        now = datetime.utcnow()

        # Check if secret already exists
        existing = await self.db.execute(
            select(SecretModel).where(
                SecretModel.name == request.secretKey,
                SecretModel.organization_id == (UUID(request.orgId) if request.orgId else None),
            )
        )
        if existing.scalar_one_or_none():
            raise ValueError(f"Secret {request.secretKey} already exists")

        # Encrypt the value
        encrypted_value = encrypt_secret(request.value)

        secret = SecretModel(
            name=request.secretKey,
            encrypted_value=encrypted_value,
            organization_id=UUID(request.orgId) if request.orgId else None,
            created_at=now,
            updated_at=now,
        )

        self.db.add(secret)
        await self.db.flush()
        await self.db.refresh(secret)

        logger.info(f"Created secret {request.secretKey}")
        return SecretResponse(
            name=secret.name,
            orgId=request.orgId,
            secretKey=request.secretKey,
            value=request.value,  # Return value only on creation
            message="Secret created successfully",
        )

    async def update_secret(
        self,
        secret_key: str,
        request: SecretUpdateRequest,
        org_id: str | None = None,
    ) -> SecretResponse:
        """Update an existing secret."""
        result = await self.db.execute(
            select(SecretModel).where(
                SecretModel.name == secret_key,
                SecretModel.organization_id == (UUID(org_id) if org_id else None),
            )
        )
        secret = result.scalar_one_or_none()

        if not secret:
            raise ValueError(f"Secret {secret_key} not found")

        # Encrypt the new value
        secret.encrypted_value = encrypt_secret(request.value)
        secret.updated_at = datetime.utcnow()

        await self.db.flush()
        await self.db.refresh(secret)

        logger.info(f"Updated secret {secret_key}")
        return SecretResponse(
            name=secret.name,
            orgId=org_id,
            secretKey=secret_key,
            message="Secret updated successfully",
        )

    async def delete_secret(
        self,
        secret_key: str,
        org_id: str | None = None,
    ) -> bool:
        """Delete a secret."""
        result = await self.db.execute(
            select(SecretModel).where(
                SecretModel.name == secret_key,
                SecretModel.organization_id == (UUID(org_id) if org_id else None),
            )
        )
        secret = result.scalar_one_or_none()

        if not secret:
            return False

        await self.db.delete(secret)
        await self.db.flush()

        logger.info(f"Deleted secret {secret_key}")
        return True


# =============================================================================
# HTTP Endpoints
# =============================================================================


@router.get(
    "",
    response_model=SecretListResponse,
    summary="List secrets",
    description="List available secrets, optionally filtered by organization",
)
async def list_secrets(
    ctx: Context,
    user: CurrentSuperuser,
    org_id: str | None = Query(None, description="Filter by organization ID"),
) -> SecretListResponse:
    """List available secrets."""
    repo = SecretRepository(ctx.db)
    return await repo.list_secrets(org_id)


@router.post(
    "",
    response_model=SecretResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create secret",
    description="Create a new secret",
)
async def create_secret(
    request: SecretCreateRequest,
    ctx: Context,
    user: CurrentSuperuser,
) -> SecretResponse:
    """Create a new secret."""
    repo = SecretRepository(ctx.db)

    try:
        return await repo.create_secret(request, user.email)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error creating secret: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create secret",
        )


@router.put(
    "/{secret_key}",
    response_model=SecretResponse,
    summary="Update secret",
    description="Update an existing secret",
)
async def update_secret(
    secret_key: str,
    request: SecretUpdateRequest,
    ctx: Context,
    user: CurrentSuperuser,
) -> SecretResponse:
    """Update an existing secret."""
    repo = SecretRepository(ctx.db)

    try:
        return await repo.update_secret(
            secret_key,
            request,
            str(ctx.org_id) if ctx.org_id else None,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error updating secret: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update secret",
        )


@router.delete(
    "/{secret_key}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete secret",
    description="Delete a secret",
)
async def delete_secret(
    secret_key: str,
    ctx: Context,
    user: CurrentSuperuser,
) -> None:
    """Delete a secret."""
    repo = SecretRepository(ctx.db)

    success = await repo.delete_secret(
        secret_key,
        str(ctx.org_id) if ctx.org_id else None,
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Secret not found",
        )
