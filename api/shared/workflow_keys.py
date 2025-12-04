"""
Workflow API Key Authentication Utilities

Provides utilities for generating, validating, and managing workflow API keys
"""

import hashlib
import secrets
from datetime import datetime
from typing import Optional
from uuid import UUID

from shared.models import WorkflowKey


def generate_workflow_key(
    created_by: str,
    workflow_id: Optional[str] = None,
    expires_in_days: int = 90
) -> tuple[str, WorkflowKey]:
    """
    Generate a cryptographically secure workflow API key

    Args:
        created_by: User ID creating the workflow key
        workflow_id: Optional workflow-specific scope for the key
        expires_in_days: Number of days the key is valid for

    Returns:
        Tuple of (raw key, WorkflowKey model)
    """
    # Generate a secure, URL-safe token
    raw_key = secrets.token_urlsafe(32)

    # Hash the key for secure storage
    hashed_key = hashlib.sha256(raw_key.encode()).hexdigest()

    workflow_key = WorkflowKey(
        hashedKey=hashed_key,
        workflowId=workflow_id,
        createdBy=created_by,
        createdAt=datetime.utcnow(),
        lastUsedAt=None,
        revoked=False,
        expiresAt=None,
        description=None
    )

    return raw_key, workflow_key


async def validate_workflow_key(
    connection_str: str,
    api_key: str,
    workflow_id: Optional[str] = None
) -> tuple[bool, Optional[str]]:
    """
    Validate an API key against workflow_keys table with workflow-specific key priority.

    Authentication flow:
    1. If workflow_id provided, try workflow-specific key first
       - If found with DisableGlobalKey=True, ONLY accept this key (don't try global)
       - If found with DisableGlobalKey=False, accept this key OR fall through to global
       - If not found, fall through to try global keys
    2. Try global API keys as fallback
    3. If no workflow_id, directly try global keys

    Args:
        connection_str: Database connection string (unused, kept for compatibility)
        api_key: Raw API key to validate
        workflow_id: Optional workflow-specific scope to check

    Returns:
        Tuple of (is_valid, key_id) where key_id is the ID for logging
    """
    from sqlalchemy import select, or_
    from src.core.database import get_session_factory
    from src.models import WorkflowKey as WorkflowKeyModel

    # Compute hash of provided key
    hashed_key = hashlib.sha256(api_key.encode()).hexdigest()
    now = datetime.utcnow()

    try:
        session_factory = get_session_factory()

        async with session_factory() as db:
            # Build query for valid keys
            query = select(WorkflowKeyModel).where(
                WorkflowKeyModel.hashed_key == hashed_key,
                WorkflowKeyModel.revoked == False,  # noqa: E712
                or_(
                    WorkflowKeyModel.expires_at.is_(None),
                    WorkflowKeyModel.expires_at > now,
                ),
            )

            # If workflow_id provided, check for workflow-specific OR global key
            if workflow_id:
                query = query.where(
                    or_(
                        WorkflowKeyModel.workflow_name == workflow_id,
                        WorkflowKeyModel.workflow_name.is_(None),
                    )
                )
            else:
                # Only global keys work for unspecified workflows
                query = query.where(WorkflowKeyModel.workflow_name.is_(None))

            result = await db.execute(query)
            key = result.scalar_one_or_none()

            if not key:
                return (False, None)

            # Update last used timestamp
            key.last_used_at = now
            await db.commit()

            return (True, str(key.id))

    except Exception:
        return (False, None)


async def revoke_workflow_key(
    connection_str: str,
    key_id: str,
    revoked_by: str = "system"
) -> bool:
    """
    Revoke a workflow API key

    Args:
        connection_str: Database connection string (unused, kept for compatibility)
        key_id: Key ID to revoke
        revoked_by: User revoking the key

    Returns:
        True if key was successfully revoked, False otherwise
    """
    from sqlalchemy import select
    from src.core.database import get_session_factory
    from src.models import WorkflowKey as WorkflowKeyModel

    try:
        session_factory = get_session_factory()
        key_uuid = UUID(key_id)

        async with session_factory() as db:
            result = await db.execute(
                select(WorkflowKeyModel).where(WorkflowKeyModel.id == key_uuid)
            )
            key = result.scalar_one_or_none()

            if not key:
                return False

            key.revoked = True
            key.revoked_at = datetime.utcnow()
            key.revoked_by = revoked_by
            await db.commit()

            return True

    except Exception:
        return False


async def list_workflow_keys(
    connection_str: str,
    user_id: str,
    workflow_id: Optional[str] = None,
    include_revoked: bool = False
) -> list[dict]:
    """
    List workflow keys for a user or specific workflow

    Args:
        connection_str: Database connection string (unused, kept for compatibility)
        user_id: User creating/owning the keys
        workflow_id: Optional workflow-specific filter
        include_revoked: Include revoked keys

    Returns:
        List of workflow key entities
    """
    from sqlalchemy import select
    from src.core.database import get_session_factory
    from src.models import WorkflowKey as WorkflowKeyModel

    try:
        session_factory = get_session_factory()

        async with session_factory() as db:
            query = select(WorkflowKeyModel)

            if not include_revoked:
                query = query.where(WorkflowKeyModel.revoked == False)  # noqa: E712

            if workflow_id:
                query = query.where(WorkflowKeyModel.workflow_name == workflow_id)

            query = query.order_by(WorkflowKeyModel.created_at.desc())

            result = await db.execute(query)
            keys = result.scalars().all()

            return [
                {
                    "id": str(key.id),
                    "workflow_name": key.workflow_name,
                    "hashed_key": key.hashed_key,
                    "description": key.description,
                    "created_by": key.created_by,
                    "created_at": key.created_at.isoformat() if key.created_at else None,
                    "last_used_at": key.last_used_at.isoformat() if key.last_used_at else None,
                    "expires_at": key.expires_at.isoformat() if key.expires_at else None,
                    "revoked": key.revoked,
                    "revoked_at": key.revoked_at.isoformat() if key.revoked_at else None,
                    "revoked_by": key.revoked_by,
                }
                for key in keys
            ]

    except Exception:
        return []
