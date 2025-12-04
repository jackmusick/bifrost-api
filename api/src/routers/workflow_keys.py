"""
Workflow Keys Router

API key management for workflow execution.
Allows platform admins to create and revoke API keys for workflow authentication.

Keys can be:
- Global (workflow_name=NULL): Works for all workflows
- Workflow-specific: Only works for a specific workflow
"""

import hashlib
import logging
import secrets
from datetime import datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select, or_

from src.core.auth import Context, CurrentSuperuser
from src.core.database import DbSession
from src.models import WorkflowKey
from shared.models import WorkflowKeyCreateRequest, WorkflowKeyResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/workflow-keys", tags=["Workflow Keys"])


# =============================================================================
# Request/Response Models
# =============================================================================

# WorkflowKeyResponse with raw_key for creation
class WorkflowKeyCreatedResponse(WorkflowKeyResponse):
    """Response when creating a key - includes the raw key (shown only once)."""
    raw_key: str


# =============================================================================
# Helper Functions
# =============================================================================


def generate_api_key() -> tuple[str, str]:
    """
    Generate a secure API key.

    Returns:
        Tuple of (raw_key, hashed_key)
    """
    raw_key = secrets.token_urlsafe(32)
    hashed_key = hashlib.sha256(raw_key.encode()).hexdigest()
    return raw_key, hashed_key


def mask_key(hashed_key: str) -> str:
    """Create a masked display version of the key hash."""
    return f"{hashed_key[:4]}...{hashed_key[-4:]}"


# =============================================================================
# HTTP Endpoints
# =============================================================================


@router.get(
    "",
    response_model=list[WorkflowKeyResponse],
    summary="List workflow API keys",
    description="List all API keys (Platform admin only)",
)
async def list_keys(
    ctx: Context,
    user: CurrentSuperuser,
    db: DbSession,
) -> list[WorkflowKeyResponse]:
    """List all workflow API keys."""
    query = select(WorkflowKey).where(
        WorkflowKey.revoked == False  # noqa: E712
    ).order_by(WorkflowKey.created_at.desc())

    result = await db.execute(query)
    keys = result.scalars().all()

    return [
        WorkflowKeyResponse(
            id=str(key.id),
            workflow_name=key.workflow_name,
            masked_key=mask_key(key.hashed_key),
            description=key.description,
            created_by=key.created_by,
            created_at=key.created_at,
            last_used_at=key.last_used_at,
            expires_at=key.expires_at,
            revoked=key.revoked,
        )
        for key in keys
    ]


@router.post(
    "",
    response_model=WorkflowKeyCreatedResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new API key",
    description="Create a new workflow API key (Platform admin only)",
)
async def create_key(
    request: WorkflowKeyCreateRequest,
    ctx: Context,
    user: CurrentSuperuser,
    db: DbSession,
) -> WorkflowKeyCreatedResponse:
    """Create a new workflow API key."""
    raw_key, hashed_key = generate_api_key()

    expires_at = None
    if request.expires_in_days:
        expires_at = datetime.utcnow() + timedelta(days=request.expires_in_days)

    workflow_key = WorkflowKey(
        workflow_name=request.workflow_name,
        hashed_key=hashed_key,
        description=request.description,
        created_by=user.email,
        expires_at=expires_at,
    )
    db.add(workflow_key)
    await db.flush()
    await db.refresh(workflow_key)

    key_type = f"workflow '{request.workflow_name}'" if request.workflow_name else "global"
    logger.info(f"Created {key_type} API key by {user.email}")

    return WorkflowKeyCreatedResponse(
        id=str(workflow_key.id),
        workflow_name=workflow_key.workflow_name,
        masked_key=mask_key(hashed_key),
        raw_key=raw_key,
        description=workflow_key.description,
        created_by=workflow_key.created_by,
        created_at=workflow_key.created_at,
        last_used_at=workflow_key.last_used_at,
        expires_at=workflow_key.expires_at,
        revoked=workflow_key.revoked,
    )


@router.delete(
    "/{key_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke an API key",
    description="Revoke a workflow API key (Platform admin only)",
)
async def revoke_key(
    key_id: UUID,
    ctx: Context,
    user: CurrentSuperuser,
    db: DbSession,
) -> None:
    """Revoke (soft delete) a workflow API key."""
    result = await db.execute(
        select(WorkflowKey).where(WorkflowKey.id == key_id)
    )
    key = result.scalar_one_or_none()

    if not key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found",
        )

    if key.revoked:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="API key already revoked",
        )

    key.revoked = True
    key.revoked_at = datetime.utcnow()
    key.revoked_by = user.email

    await db.flush()
    logger.info(f"Revoked API key {key_id} by {user.email}")


# =============================================================================
# Key Validation (for use by auth middleware)
# =============================================================================


async def validate_workflow_key(
    db: DbSession,
    api_key: str,
    workflow_name: str | None = None,
) -> tuple[bool, UUID | None]:
    """
    Validate an API key for workflow execution.

    Args:
        db: Database session
        api_key: Raw API key to validate
        workflow_name: Optional workflow to validate against

    Returns:
        Tuple of (is_valid, key_id)
    """
    hashed_key = hashlib.sha256(api_key.encode()).hexdigest()
    now = datetime.utcnow()

    # Build query for valid keys
    query = select(WorkflowKey).where(
        WorkflowKey.hashed_key == hashed_key,
        WorkflowKey.revoked == False,  # noqa: E712
        or_(
            WorkflowKey.expires_at.is_(None),
            WorkflowKey.expires_at > now,
        ),
    )

    # If workflow_name provided, check for workflow-specific OR global key
    if workflow_name:
        query = query.where(
            or_(
                WorkflowKey.workflow_name == workflow_name,
                WorkflowKey.workflow_name.is_(None),
            )
        )
    else:
        # Only global keys work for unspecified workflows
        query = query.where(WorkflowKey.workflow_name.is_(None))

    result = await db.execute(query)
    key = result.scalar_one_or_none()

    if not key:
        return (False, None)

    # Update last used timestamp
    key.last_used_at = now
    await db.flush()

    return (True, key.id)
