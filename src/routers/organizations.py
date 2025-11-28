"""
Organizations Router

CRUD operations for client organizations.
API-compatible with the existing Azure Functions implementation.
"""

import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

# Import existing Pydantic models for API compatibility
from shared.models import (
    CreateOrganizationRequest,
    ErrorResponse,
    Organization,
    UpdateOrganizationRequest,
)

from src.core.auth import CurrentSuperuser, UserPrincipal
from src.core.database import DbSession

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/organizations", tags=["Organizations"])


# =============================================================================
# Repository (PostgreSQL implementation)
# =============================================================================

from datetime import datetime
from sqlalchemy import select
from src.models.database import Organization as OrganizationModel


class OrganizationRepository:
    """PostgreSQL-based organization repository."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_organizations(self, active_only: bool = True) -> list[Organization]:
        """List all organizations."""
        query = select(OrganizationModel)
        if active_only:
            query = query.where(OrganizationModel.is_active == True)
        query = query.order_by(OrganizationModel.name)

        result = await self.db.execute(query)
        orgs = result.scalars().all()

        return [self._to_pydantic(org) for org in orgs]

    async def get_organization(self, org_id: UUID) -> Organization | None:
        """Get organization by ID."""
        result = await self.db.execute(
            select(OrganizationModel).where(OrganizationModel.id == org_id)
        )
        org = result.scalar_one_or_none()

        if org:
            return self._to_pydantic(org)
        return None

    async def get_organization_by_domain(self, domain: str) -> Organization | None:
        """Get organization by domain."""
        result = await self.db.execute(
            select(OrganizationModel)
            .where(OrganizationModel.domain == domain.lower())
            .where(OrganizationModel.is_active == True)
        )
        org = result.scalar_one_or_none()

        if org:
            return self._to_pydantic(org)
        return None

    async def create_organization(
        self,
        request: CreateOrganizationRequest,
        created_by: str,
    ) -> Organization:
        """Create a new organization."""
        now = datetime.utcnow()

        org = OrganizationModel(
            name=request.name,
            domain=request.domain.lower() if request.domain else None,
            is_active=True,
            created_by=created_by,
            created_at=now,
            updated_at=now,
        )

        self.db.add(org)
        await self.db.flush()
        await self.db.refresh(org)

        logger.info(f"Created organization {org.id}: {org.name}")
        return self._to_pydantic(org)

    async def update_organization(
        self,
        org_id: UUID,
        request: UpdateOrganizationRequest,
    ) -> Organization | None:
        """Update an organization."""
        result = await self.db.execute(
            select(OrganizationModel).where(OrganizationModel.id == org_id)
        )
        org = result.scalar_one_or_none()

        if not org:
            return None

        if request.name is not None:
            org.name = request.name
        if request.domain is not None:
            org.domain = request.domain.lower() if request.domain else None
        if request.isActive is not None:
            org.is_active = request.isActive

        org.updated_at = datetime.utcnow()

        await self.db.flush()
        await self.db.refresh(org)

        logger.info(f"Updated organization {org_id}")
        return self._to_pydantic(org)

    async def delete_organization(self, org_id: UUID) -> bool:
        """Soft delete an organization."""
        result = await self.db.execute(
            select(OrganizationModel).where(OrganizationModel.id == org_id)
        )
        org = result.scalar_one_or_none()

        if not org:
            return False

        org.is_active = False
        org.updated_at = datetime.utcnow()

        await self.db.flush()
        logger.info(f"Soft deleted organization {org_id}")
        return True

    def _to_pydantic(self, org: OrganizationModel) -> Organization:
        """Convert SQLAlchemy model to Pydantic model."""
        return Organization(
            id=str(org.id),
            name=org.name,
            domain=org.domain,
            isActive=org.is_active,
            createdAt=org.created_at,
            createdBy=org.created_by,
            updatedAt=org.updated_at,
        )


# =============================================================================
# HTTP Endpoints
# =============================================================================


@router.get(
    "",
    response_model=list[Organization],
    summary="List all organizations",
    description="Get all organizations (Platform admin only)",
)
async def list_organizations(
    user: CurrentSuperuser,
    db: DbSession,
) -> list[Organization]:
    """List all organizations."""
    repo = OrganizationRepository(db)
    return await repo.list_organizations(active_only=True)


@router.post(
    "",
    response_model=Organization,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new organization",
    description="Create a new client organization (Platform admin only)",
)
async def create_organization(
    request: CreateOrganizationRequest,
    user: CurrentSuperuser,
    db: DbSession,
) -> Organization:
    """Create a new client organization."""
    repo = OrganizationRepository(db)
    return await repo.create_organization(request, user.email)


@router.get(
    "/{org_id}",
    response_model=Organization,
    summary="Get organization by ID",
    description="Get a specific organization by ID (Platform admin only)",
)
async def get_organization(
    org_id: UUID,
    user: CurrentSuperuser,
    db: DbSession,
) -> Organization:
    """Get a specific organization by ID."""
    repo = OrganizationRepository(db)
    org = await repo.get_organization(org_id)

    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )

    return org


@router.patch(
    "/{org_id}",
    response_model=Organization,
    summary="Update an organization",
    description="Update an existing organization (Platform admin only)",
)
async def update_organization(
    org_id: UUID,
    request: UpdateOrganizationRequest,
    user: CurrentSuperuser,
    db: DbSession,
) -> Organization:
    """Update an organization."""
    repo = OrganizationRepository(db)
    org = await repo.update_organization(org_id, request)

    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )

    return org


@router.delete(
    "/{org_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an organization",
    description="Soft delete an organization (sets IsActive=False, Platform admin only)",
)
async def delete_organization(
    org_id: UUID,
    user: CurrentSuperuser,
    db: DbSession,
) -> None:
    """Soft delete an organization."""
    repo = OrganizationRepository(db)
    success = await repo.delete_organization(org_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )
