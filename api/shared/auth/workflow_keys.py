"""
Workflow API Key Authentication Utilities

Provides utilities for generating, validating, and managing workflow API keys
"""

import secrets
import hashlib
from datetime import datetime
from typing import Optional

from azure.data.tables import TableServiceClient
from azure.core.exceptions import ResourceNotFoundError

from ..models import WorkflowKey

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
        HashedKey=hashed_key,
        WorkflowId=workflow_id,
        CreatedBy=created_by,
        CreatedAt=datetime.utcnow(),
        LastUsedAt=None,
        Revoked=False
    )

    return raw_key, workflow_key


def validate_workflow_key(
    connection_str: str,
    api_key: str,
    workflow_id: Optional[str] = None
) -> bool:
    """
    Validate an API key against WorkflowKeys table

    Args:
        connection_str: Azure Table Storage connection string
        api_key: Raw API key to validate
        workflow_id: Optional workflow-specific scope to check

    Returns:
        True if key is valid and active, False otherwise
    """
    # Compute hash of provided key
    hashed_key = hashlib.sha256(api_key.encode()).hexdigest()

    try:
        # Create TableClient
        table_client = TableServiceClient.from_connection_string(
            conn_str=connection_str
        ).get_table_client("WorkflowKeys")

        # Query for the key
        key_filter = f"HashedKey eq '{hashed_key}'"

        # If workflow_id is provided, add additional filter
        if workflow_id:
            key_filter += f" and WorkflowId eq '{workflow_id}'"

        results = list(table_client.query_entities(key_filter))

        if not results:
            return False

        # Get the first (and should be only) match
        key_entity = results[0]

        # Check if key is revoked
        if key_entity.get('Revoked', False):
            return False

        # Update last used timestamp
        key_entity['LastUsedAt'] = datetime.utcnow().isoformat()
        table_client.update_entity(key_entity)

        return True

    except ResourceNotFoundError:
        return False
    except Exception:
        # Log the error in a real implementation
        return False


def revoke_workflow_key(
    connection_str: str,
    hashed_key: str
) -> bool:
    """
    Revoke a workflow API key

    Args:
        connection_str: Azure Table Storage connection string
        hashed_key: Hashed key to revoke

    Returns:
        True if key was successfully revoked, False otherwise
    """
    try:
        table_client = TableServiceClient.from_connection_string(
            conn_str=connection_str
        ).get_table_client("WorkflowKeys")

        key_filter = f"HashedKey eq '{hashed_key}'"
        results = list(table_client.query_entities(key_filter))

        if not results:
            return False

        key_entity = results[0]
        key_entity['Revoked'] = True
        key_entity['RevokedAt'] = datetime.utcnow().isoformat()

        table_client.update_entity(key_entity)

        return True

    except Exception:
        # Log error in a real implementation
        return False


def list_workflow_keys(
    connection_str: str,
    user_id: str,
    workflow_id: Optional[str] = None
) -> list[WorkflowKey]:
    """
    List workflow keys for a user or specific workflow

    Args:
        connection_str: Azure Table Storage connection string
        user_id: User creating/owning the keys
        workflow_id: Optional workflow-specific filter

    Returns:
        List of WorkflowKey models
    """
    try:
        table_client = TableServiceClient.from_connection_string(
            conn_str=connection_str
        ).get_table_client("WorkflowKeys")

        # Build query filter
        key_filter = f"CreatedBy eq '{user_id}'"

        if workflow_id:
            key_filter += f" and WorkflowId eq '{workflow_id}'"

        results = list(table_client.query_entities(key_filter))

        return [WorkflowKey(**{
            'HashedKey': r['HashedKey'],
            'WorkflowId': r.get('WorkflowId'),
            'CreatedBy': r['CreatedBy'],
            'CreatedAt': datetime.fromisoformat(r['CreatedAt']),
            'LastUsedAt': datetime.fromisoformat(r['LastUsedAt']) if r.get('LastUsedAt') else None,
            'Revoked': r.get('Revoked', False)
        }) for r in results]

    except Exception:
        # Log error in a real implementation
        return []