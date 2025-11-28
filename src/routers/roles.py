"""
Roles Router

Manage roles for organization users.
- Assign users to roles (UserRoles)
- Assign forms to roles (FormRoles)

API-compatible with the existing Azure Functions implementation.
"""

import logging
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

# Import existing Pydantic models for API compatibility
from shared.models import (
    AssignFormsToRoleRequest,
    AssignUsersToRoleRequest,
    CreateRoleRequest,
    Role,
    RoleFormsResponse,
    RoleUsersResponse,
    UpdateRoleRequest,
)

from src.core.auth import CurrentSuperuser
from src.core.database import DbSession
from src.models.database import (
    Role as RoleModel,
    UserRole as UserRoleModel,
    FormRole as FormRoleModel,
    User as UserModel,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/roles", tags=["Roles"])


# =============================================================================
# Repository
# =============================================================================


class RoleRepository:
    """PostgreSQL-based role repository."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_roles(self, active_only: bool = True) -> list[Role]:
        """List all roles."""
        query = select(RoleModel)
        if active_only:
            query = query.where(RoleModel.is_active == True)
        query = query.order_by(RoleModel.name)

        result = await self.db.execute(query)
        roles = result.scalars().all()

        return [self._to_pydantic(r) for r in roles]

    async def get_role(self, role_id: UUID) -> Role | None:
        """Get role by ID."""
        result = await self.db.execute(
            select(RoleModel).where(RoleModel.id == role_id)
        )
        role = result.scalar_one_or_none()

        if role:
            return self._to_pydantic(role)
        return None

    async def create_role(
        self,
        request: CreateRoleRequest,
        created_by: str,
    ) -> Role:
        """Create a new role."""
        now = datetime.utcnow()

        role = RoleModel(
            name=request.name,
            description=request.description,
            is_active=True,
            created_by=created_by,
            created_at=now,
            updated_at=now,
        )

        self.db.add(role)
        await self.db.flush()
        await self.db.refresh(role)

        logger.info(f"Created role {role.id}: {role.name}")
        return self._to_pydantic(role)

    async def update_role(
        self,
        role_id: UUID,
        request: UpdateRoleRequest,
    ) -> Role | None:
        """Update a role."""
        result = await self.db.execute(
            select(RoleModel).where(RoleModel.id == role_id)
        )
        role = result.scalar_one_or_none()

        if not role:
            return None

        if request.name is not None:
            role.name = request.name
        if request.description is not None:
            role.description = request.description

        role.updated_at = datetime.utcnow()

        await self.db.flush()
        await self.db.refresh(role)

        logger.info(f"Updated role {role_id}")
        return self._to_pydantic(role)

    async def delete_role(self, role_id: UUID) -> bool:
        """Soft delete a role."""
        result = await self.db.execute(
            select(RoleModel).where(RoleModel.id == role_id)
        )
        role = result.scalar_one_or_none()

        if not role:
            return False

        role.is_active = False
        role.updated_at = datetime.utcnow()

        await self.db.flush()
        logger.info(f"Soft deleted role {role_id}")
        return True

    async def get_role_users(self, role_id: UUID) -> list[str]:
        """Get user IDs assigned to a role."""
        result = await self.db.execute(
            select(UserRoleModel.user_id).where(UserRoleModel.role_id == role_id)
        )
        return [str(uid) for uid in result.scalars().all()]

    async def assign_users_to_role(
        self,
        role_id: UUID,
        user_ids: list[str],
        assigned_by: str,
    ) -> None:
        """Assign users to a role."""
        now = datetime.utcnow()

        for user_id in user_ids:
            # Try to parse as UUID, otherwise lookup by email
            try:
                user_uuid = UUID(user_id)
            except ValueError:
                result = await self.db.execute(
                    select(UserModel.id).where(UserModel.email == user_id)
                )
                user_uuid = result.scalar_one_or_none()
                if not user_uuid:
                    logger.warning(f"User {user_id} not found, skipping")
                    continue

            # Check if already assigned
            existing = await self.db.execute(
                select(UserRoleModel).where(
                    UserRoleModel.user_id == user_uuid,
                    UserRoleModel.role_id == role_id,
                )
            )
            if existing.scalar_one_or_none():
                continue

            user_role = UserRoleModel(
                user_id=user_uuid,
                role_id=role_id,
                assigned_by=assigned_by,
                assigned_at=now,
            )
            self.db.add(user_role)

        await self.db.flush()
        logger.info(f"Assigned {len(user_ids)} users to role {role_id}")

    async def remove_user_from_role(self, role_id: UUID, user_id: str) -> bool:
        """Remove a user from a role."""
        try:
            user_uuid = UUID(user_id)
        except ValueError:
            result = await self.db.execute(
                select(UserModel.id).where(UserModel.email == user_id)
            )
            user_uuid = result.scalar_one_or_none()
            if not user_uuid:
                return False

        result = await self.db.execute(
            delete(UserRoleModel).where(
                UserRoleModel.user_id == user_uuid,
                UserRoleModel.role_id == role_id,
            )
        )

        if result.rowcount > 0:
            logger.info(f"Removed user {user_id} from role {role_id}")
            return True
        return False

    async def get_role_forms(self, role_id: UUID) -> list[str]:
        """Get form IDs assigned to a role."""
        result = await self.db.execute(
            select(FormRoleModel.form_id).where(FormRoleModel.role_id == role_id)
        )
        return [str(fid) for fid in result.scalars().all()]

    async def assign_forms_to_role(
        self,
        role_id: UUID,
        form_ids: list[str],
        assigned_by: str,
    ) -> None:
        """Assign forms to a role."""
        now = datetime.utcnow()

        for form_id in form_ids:
            form_uuid = UUID(form_id)

            # Check if already assigned
            existing = await self.db.execute(
                select(FormRoleModel).where(
                    FormRoleModel.form_id == form_uuid,
                    FormRoleModel.role_id == role_id,
                )
            )
            if existing.scalar_one_or_none():
                continue

            form_role = FormRoleModel(
                form_id=form_uuid,
                role_id=role_id,
                assigned_by=assigned_by,
                assigned_at=now,
            )
            self.db.add(form_role)

        await self.db.flush()
        logger.info(f"Assigned {len(form_ids)} forms to role {role_id}")

    async def remove_form_from_role(self, role_id: UUID, form_id: UUID) -> bool:
        """Remove a form from a role."""
        result = await self.db.execute(
            delete(FormRoleModel).where(
                FormRoleModel.form_id == form_id,
                FormRoleModel.role_id == role_id,
            )
        )

        if result.rowcount > 0:
            logger.info(f"Removed form {form_id} from role {role_id}")
            return True
        return False

    def _to_pydantic(self, role: RoleModel) -> Role:
        """Convert SQLAlchemy model to Pydantic model."""
        return Role(
            id=str(role.id),
            name=role.name,
            description=role.description,
            isActive=role.is_active,
            createdBy=role.created_by,
            createdAt=role.created_at,
            updatedAt=role.updated_at,
        )


# =============================================================================
# HTTP Endpoints
# =============================================================================


@router.get(
    "",
    response_model=list[Role],
    summary="List all roles",
    description="Get all roles (Platform admin only)",
)
async def list_roles(
    user: CurrentSuperuser,
    db: DbSession,
) -> list[Role]:
    """List all roles."""
    repo = RoleRepository(db)
    return await repo.list_roles()


@router.post(
    "",
    response_model=Role,
    status_code=status.HTTP_201_CREATED,
    summary="Create a role",
    description="Create a new role (Platform admin only)",
)
async def create_role(
    request: CreateRoleRequest,
    user: CurrentSuperuser,
    db: DbSession,
) -> Role:
    """Create a new role."""
    repo = RoleRepository(db)
    return await repo.create_role(request, user.email)


@router.put(
    "/{role_id}",
    response_model=Role,
    summary="Update a role",
    description="Update a role (Platform admin only)",
)
async def update_role(
    role_id: UUID,
    request: UpdateRoleRequest,
    user: CurrentSuperuser,
    db: DbSession,
) -> Role:
    """Update a role."""
    repo = RoleRepository(db)
    result = await repo.update_role(role_id, request)

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found",
        )

    return result


@router.delete(
    "/{role_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a role",
    description="Soft delete a role (Platform admin only)",
)
async def delete_role(
    role_id: UUID,
    user: CurrentSuperuser,
    db: DbSession,
) -> None:
    """Soft delete a role."""
    repo = RoleRepository(db)
    success = await repo.delete_role(role_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found",
        )


@router.get(
    "/{role_id}/users",
    response_model=RoleUsersResponse,
    summary="Get role users",
    description="Get all users assigned to a role",
)
async def get_role_users(
    role_id: UUID,
    user: CurrentSuperuser,
    db: DbSession,
) -> RoleUsersResponse:
    """Get all users assigned to a role."""
    repo = RoleRepository(db)
    user_ids = await repo.get_role_users(role_id)
    return RoleUsersResponse(userIds=user_ids)


@router.post(
    "/{role_id}/users",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Assign users to role",
    description="Assign users to a role (batch operation)",
)
async def assign_users_to_role(
    role_id: UUID,
    request: AssignUsersToRoleRequest,
    user: CurrentSuperuser,
    db: DbSession,
) -> None:
    """Assign users to a role."""
    repo = RoleRepository(db)
    await repo.assign_users_to_role(role_id, request.userIds, user.email)


@router.delete(
    "/{role_id}/users/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove user from role",
    description="Remove a user from a role",
)
async def remove_user_from_role(
    role_id: UUID,
    user_id: str,
    user: CurrentSuperuser,
    db: DbSession,
) -> None:
    """Remove a user from a role."""
    repo = RoleRepository(db)
    success = await repo.remove_user_from_role(role_id, user_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User-role assignment not found",
        )


@router.get(
    "/{role_id}/forms",
    response_model=RoleFormsResponse,
    summary="Get role forms",
    description="Get all forms assigned to a role",
)
async def get_role_forms(
    role_id: UUID,
    user: CurrentSuperuser,
    db: DbSession,
) -> RoleFormsResponse:
    """Get all forms assigned to a role."""
    repo = RoleRepository(db)
    form_ids = await repo.get_role_forms(role_id)
    return RoleFormsResponse(formIds=form_ids)


@router.post(
    "/{role_id}/forms",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Assign forms to role",
    description="Assign forms to a role (batch operation)",
)
async def assign_forms_to_role(
    role_id: UUID,
    request: AssignFormsToRoleRequest,
    user: CurrentSuperuser,
    db: DbSession,
) -> None:
    """Assign forms to a role."""
    repo = RoleRepository(db)
    await repo.assign_forms_to_role(role_id, request.formIds, user.email)


@router.delete(
    "/{role_id}/forms/{form_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove form from role",
    description="Remove a form from a role",
)
async def remove_form_from_role(
    role_id: UUID,
    form_id: UUID,
    user: CurrentSuperuser,
    db: DbSession,
) -> None:
    """Remove a form from a role."""
    repo = RoleRepository(db)
    success = await repo.remove_form_from_role(role_id, form_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Form-role assignment not found",
        )
