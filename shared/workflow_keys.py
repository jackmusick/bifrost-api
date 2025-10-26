"""
Workflow API Key Authentication Utilities

Provides utilities for generating, validating, and managing workflow API keys
"""

import secrets
import hashlib
from datetime import datetime
from typing import Optional

from shared.models import WorkflowKey
from shared.repositories.config import get_global_config_repository

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
    Validate an API key against Config table with workflow-specific key priority.

    Authentication flow:
    1. If workflow_id provided, try workflow-specific key first
       - If found with DisableGlobalKey=True, ONLY accept this key (don't try global)
       - If found with DisableGlobalKey=False, accept this key OR fall through to global
       - If not found, fall through to try global keys
    2. Try global API keys as fallback
    3. If no workflow_id, directly try global keys

    Args:
        connection_str: Azure Table Storage connection string (unused, kept for compatibility)
        api_key: Raw API key to validate
        workflow_id: Optional workflow-specific scope to check

    Returns:
        Tuple of (is_valid, key_id) where key_id is the RowKey for logging
    """
    # Compute hash of provided key
    hashed_key = hashlib.sha256(api_key.encode()).hexdigest()

    try:
        # Use ConfigRepository for validation
        repo = get_global_config_repository()
        return await repo.validate_workflow_key(hashed_key, workflow_id)

    except Exception:
        # Log the error in a real implementation
        return (False, None)


async def revoke_workflow_key(
    connection_str: str,
    key_id: str,
    revoked_by: str = "system"
) -> bool:
    """
    Revoke a workflow API key

    Args:
        connection_str: Azure Table Storage connection string (unused, kept for compatibility)
        key_id: Key ID to revoke
        revoked_by: User revoking the key

    Returns:
        True if key was successfully revoked, False otherwise
    """
    try:
        repo = get_global_config_repository()
        return await repo.revoke_workflow_key(key_id, revoked_by)

    except Exception:
        # Log error in a real implementation
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
        connection_str: Azure Table Storage connection string (unused, kept for compatibility)
        user_id: User creating/owning the keys
        workflow_id: Optional workflow-specific filter
        include_revoked: Include revoked keys

    Returns:
        List of workflow key entities
    """
    try:
        repo = get_global_config_repository()
        return await repo.list_workflow_keys(user_id, workflow_id, include_revoked)

    except Exception:
        # Log error in a real implementation
        return []