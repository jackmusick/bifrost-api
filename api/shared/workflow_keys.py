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
        revoked=False
    )

    return raw_key, workflow_key


def validate_workflow_key(
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
        connection_str: Azure Table Storage connection string
        api_key: Raw API key to validate
        workflow_id: Optional workflow-specific scope to check

    Returns:
        Tuple of (is_valid, key_id) where key_id is the RowKey for logging
    """
    # Compute hash of provided key
    hashed_key = hashlib.sha256(api_key.encode()).hexdigest()

    try:
        # Create TableClient for Config table
        table_client = TableServiceClient.from_connection_string(
            conn_str=connection_str
        ).get_table_client("Config")

        # Step 1: If workflow_id provided, try workflow-specific key first
        if workflow_id:
            # Note: Azure Table Storage doesn't support 'like', so we filter by exact PartitionKey
            # and then check other conditions in code or use ge/lt for prefix matching
            workflow_key_filter = f"PartitionKey eq 'GLOBAL' and RowKey ge 'workflowkey:' and RowKey lt 'workflowkey;' and HashedKey eq '{hashed_key}' and WorkflowId eq '{workflow_id}' and Revoked eq false"
            workflow_results = list(table_client.query_entities(workflow_key_filter))

            if workflow_results:
                # Found a workflow-specific key
                key_entity = workflow_results[0]

                # Check if key is revoked (extra check, already filtered)
                if key_entity.get('Revoked', False):
                    return (False, None)

                # Check if this key has DisableGlobalKey flag
                disable_global_key = key_entity.get('DisableGlobalKey', False)

                # Get the key ID for logging
                key_id = key_entity.get('RowKey', 'unknown')

                if disable_global_key:
                    # This workflow-specific key forbids global keys
                    # Update last used timestamp and return success
                    key_entity['LastUsedAt'] = datetime.utcnow().isoformat()
                    table_client.update_entity(key_entity)
                    return (True, key_id)
                else:
                    # This workflow-specific key allows global keys as fallback
                    # Accept this key
                    key_entity['LastUsedAt'] = datetime.utcnow().isoformat()
                    table_client.update_entity(key_entity)
                    return (True, key_id)

        # Step 2: Try global API keys
        # Use ge/lt for prefix matching since 'like' is not supported
        global_key_filter = f"PartitionKey eq 'GLOBAL' and RowKey ge 'systemconfig:globalkey:' and RowKey lt 'systemconfig:globalkey;' and HashedKey eq '{hashed_key}' and Revoked eq false"
        global_results = list(table_client.query_entities(global_key_filter))

        if not global_results:
            return (False, None)

        # Get the first (and should be only) match
        key_entity = global_results[0]

        # Check if key is revoked
        if key_entity.get('Revoked', False):
            return (False, None)

        # Get the key ID for logging
        key_id = key_entity.get('RowKey', 'unknown')

        # Update last used timestamp
        key_entity['LastUsedAt'] = datetime.utcnow().isoformat()
        table_client.update_entity(key_entity)

        return (True, key_id)

    except ResourceNotFoundError:
        return (False, None)
    except Exception:
        # Log the error in a real implementation
        return (False, None)


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
            'hashedKey': r['HashedKey'],
            'workflowId': r.get('WorkflowId'),
            'createdBy': r['CreatedBy'],
            'createdAt': datetime.fromisoformat(r['CreatedAt']),
            'lastUsedAt': datetime.fromisoformat(r['LastUsedAt']) if r.get('LastUsedAt') else None,
            'revoked': r.get('Revoked', False)
        }) for r in results]

    except Exception:
        # Log error in a real implementation
        return []