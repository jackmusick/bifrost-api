"""
Users Router

List and manage users, view user roles and forms.
API-compatible with the existing Azure Functions implementation.
"""

import logging
from datetime import datetime
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import ValidationError
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

# Import existing Pydantic models for API compatibility
from shared.models import (
    CreateUserRequest,
    ErrorResponse,
    UpdateUserRequest,
    User,
    UserFormsResponse,
    UserRolesResponse,
    UserType,
)

from src.core.auth import CurrentSuperuser, UserPrincipal
from src.core.database import DbSession
from src.models.database import User as UserModel, UserRole as UserRoleModel, FormRole as FormRoleModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/users", tags=["Users"])


# =============================================================================
# Repository
# =============================================================================


class UserManagementRepository:
    """PostgreSQL-based user management repository."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_users(
        self,
        user_type: str | None = None,
        org_id: UUID | None = None,
    ) -> list[User]:
        """List users with optional filtering."""
        query = select(UserModel).where(UserModel.is_active == True)

        if user_type:
            if user_type.lower() == "platform":
                query = query.where(UserModel.is_superuser == True)
            elif user_type.lower() == "org":
                query = query.where(UserModel.is_superuser == False)

        if org_id:
            query = query.where(UserModel.organization_id == org_id)

        query = query.order_by(UserModel.email)

        result = await self.db.execute(query)
        users = result.scalars().all()

        return [self._to_pydantic(u) for u in users]

    async def get_user(self, user_id: str) -> User | None:
        """Get user by ID (string, can be UUID or email)."""
        # Try UUID first
        try:
            uuid_id = UUID(user_id)
            result = await self.db.execute(
                select(UserModel).where(UserModel.id == uuid_id)
            )
        except ValueError:
            # Fall back to email lookup
            result = await self.db.execute(
                select(UserModel).where(UserModel.email == user_id)
            )

        user = result.scalar_one_or_none()
        if user:
            return self._to_pydantic(user)
        return None

    async def get_user_roles(self, user_id: str) -> list[str]:
        """Get role IDs assigned to a user."""
        # Get user
        try:
            uuid_id = UUID(user_id)
            query = select(UserRoleModel.role_id).where(UserRoleModel.user_id == uuid_id)
        except ValueError:
            # Lookup by email
            user_result = await self.db.execute(
                select(UserModel.id).where(UserModel.email == user_id)
            )
            user_uuid = user_result.scalar_one_or_none()
            if not user_uuid:
                return []
            query = select(UserRoleModel.role_id).where(UserRoleModel.user_id == user_uuid)

        result = await self.db.execute(query)
        return [str(row) for row in result.scalars().all()]

    async def get_user_forms(self, user_id: str) -> tuple[UserType, bool, list[str]]:
        """
        Get forms accessible to a user.

        Returns:
            Tuple of (user_type, has_access_to_all, form_ids)
        """
        user = await self.get_user(user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")

        user_type = user.userType

        # Platform admins have access to all forms
        if user.isPlatformAdmin:
            return user_type, True, []

        # Get user's roles
        role_ids = await self.get_user_roles(user_id)
        if not role_ids:
            return user_type, False, []

        # Get forms for those roles
        role_uuids = [UUID(r) for r in role_ids]
        result = await self.db.execute(
            select(FormRoleModel.form_id).where(FormRoleModel.role_id.in_(role_uuids))
        )
        form_ids = list(set(str(fid) for fid in result.scalars().all()))

        return user_type, False, form_ids

    async def create_user(
        self,
        request: CreateUserRequest,
        created_by: str,
    ) -> User:
        """Create a new user."""
        now = datetime.utcnow()

        # Determine user type based on isPlatformAdmin
        is_superuser = request.isPlatformAdmin
        org_id = UUID(request.orgId) if request.orgId else None

        user = UserModel(
            email=request.email,
            name=request.displayName,
            hashed_password="",  # No password for externally authenticated users
            is_active=True,
            is_superuser=is_superuser,
            is_verified=True,  # Trusted since created by admin
            organization_id=org_id,
            created_at=now,
            updated_at=now,
        )

        self.db.add(user)
        await self.db.flush()
        await self.db.refresh(user)

        logger.info(f"Created user {user.email} (id: {user.id})")
        return self._to_pydantic(user)

    async def update_user(
        self,
        user_id: str,
        request: UpdateUserRequest,
    ) -> User | None:
        """Update a user."""
        # Get user
        try:
            uuid_id = UUID(user_id)
            result = await self.db.execute(
                select(UserModel).where(UserModel.id == uuid_id)
            )
        except ValueError:
            result = await self.db.execute(
                select(UserModel).where(UserModel.email == user_id)
            )

        user = result.scalar_one_or_none()
        if not user:
            return None

        if request.displayName is not None:
            user.name = request.displayName

        if request.isActive is not None:
            user.is_active = request.isActive

        if request.isPlatformAdmin is not None:
            user.is_superuser = request.isPlatformAdmin
            if request.isPlatformAdmin:
                # Promoting to platform admin - remove org
                user.organization_id = None
            elif request.orgId:
                user.organization_id = UUID(request.orgId)

        if request.orgId is not None and not request.isPlatformAdmin:
            user.organization_id = UUID(request.orgId) if request.orgId else None

        user.updated_at = datetime.utcnow()

        await self.db.flush()
        await self.db.refresh(user)

        logger.info(f"Updated user {user_id}")
        return self._to_pydantic(user)

    async def delete_user(self, user_id: str) -> bool:
        """Delete a user (soft delete via is_active)."""
        try:
            uuid_id = UUID(user_id)
            result = await self.db.execute(
                select(UserModel).where(UserModel.id == uuid_id)
            )
        except ValueError:
            result = await self.db.execute(
                select(UserModel).where(UserModel.email == user_id)
            )

        user = result.scalar_one_or_none()
        if not user:
            return False

        user.is_active = False
        user.updated_at = datetime.utcnow()

        await self.db.flush()
        logger.info(f"Deleted user {user_id}")
        return True

    def _to_pydantic(self, user: UserModel) -> User:
        """Convert SQLAlchemy model to Pydantic model."""
        return User(
            id=str(user.id),
            email=user.email,
            displayName=user.name or user.email.split("@")[0],
            userType=UserType.PLATFORM if user.is_superuser else UserType.ORG,
            isPlatformAdmin=user.is_superuser,
            isActive=user.is_active,
            lastLogin=user.updated_at,  # Use updated_at as proxy
            createdAt=user.created_at,
            entraUserId=None,
            lastEntraIdSync=None,
        )


# =============================================================================
# HTTP Endpoints
# =============================================================================


@router.get(
    "",
    response_model=list[User],
    summary="List users",
    description="List all users with optional filtering by type and organization",
)
async def list_users(
    user: CurrentSuperuser,
    db: DbSession,
    type: str | None = Query(None, description="Filter by user type: 'platform' or 'org'"),
    orgId: UUID | None = Query(None, description="Filter org users by organization ID"),
) -> list[User]:
    """List users with optional filtering."""
    repo = UserManagementRepository(db)
    return await repo.list_users(user_type=type, org_id=orgId)


@router.post(
    "",
    response_model=User,
    status_code=status.HTTP_201_CREATED,
    summary="Create user",
    description="Create a new user proactively (Platform admin only)",
)
async def create_user(
    request: CreateUserRequest,
    user: CurrentSuperuser,
    db: DbSession,
) -> User:
    """Create a new user."""
    repo = UserManagementRepository(db)
    return await repo.create_user(request, user.email)


@router.get(
    "/{user_id}",
    response_model=User,
    summary="Get user details",
    description="Get a specific user's details (Platform admin only)",
)
async def get_user(
    user_id: str,
    user: CurrentSuperuser,
    db: DbSession,
) -> User:
    """Get a specific user's details."""
    repo = UserManagementRepository(db)
    result = await repo.get_user(user_id)

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return result


@router.patch(
    "/{user_id}",
    response_model=User,
    summary="Update user",
    description="Update user properties including role transitions",
)
async def update_user(
    user_id: str,
    request: UpdateUserRequest,
    user: CurrentSuperuser,
    db: DbSession,
) -> User:
    """Update a user."""
    repo = UserManagementRepository(db)
    result = await repo.update_user(user_id, request)

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return result


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete user",
    description="Delete a user from the system",
)
async def delete_user(
    user_id: str,
    user: CurrentSuperuser,
    db: DbSession,
) -> None:
    """Delete a user."""
    # Users cannot delete themselves
    if user_id == str(user.user_id) or user_id == user.email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete yourself",
        )

    repo = UserManagementRepository(db)
    success = await repo.delete_user(user_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )


@router.get(
    "/{user_id}/roles",
    response_model=UserRolesResponse,
    summary="Get user roles",
    description="Get all roles assigned to a user",
)
async def get_user_roles(
    user_id: str,
    user: CurrentSuperuser,
    db: DbSession,
) -> UserRolesResponse:
    """Get all roles assigned to a user."""
    repo = UserManagementRepository(db)
    role_ids = await repo.get_user_roles(user_id)
    return UserRolesResponse(roleIds=role_ids)


@router.get(
    "/{user_id}/forms",
    response_model=UserFormsResponse,
    summary="Get user forms",
    description="Get all forms a user can access based on their roles",
)
async def get_user_forms(
    user_id: str,
    user: CurrentSuperuser,
    db: DbSession,
) -> UserFormsResponse:
    """Get all forms a user can access."""
    repo = UserManagementRepository(db)

    try:
        user_type, has_all, form_ids = await repo.get_user_forms(user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return UserFormsResponse(
        userType=user_type,
        hasAccessToAllForms=has_all,
        formIds=form_ids,
    )
