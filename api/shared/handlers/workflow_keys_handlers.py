"""
Workflow Keys Handlers
Business logic for workflow API key management
Extracted from functions/workflow_keys.py for unit testability
"""

import json
import logging
import os
from datetime import datetime, timedelta

import azure.functions as func
from azure.data.tables import TableServiceClient

from shared.models import (
    ErrorResponse,
    WorkflowKey,
    WorkflowKeyCreateRequest,
    WorkflowKeyResponse,
)
from shared.workflow_keys import generate_workflow_key

logger = logging.getLogger(__name__)


def _get_config_table_client():
    """Get Config table client for workflow keys"""
    connection_str = os.environ.get("AzureWebJobsStorage", "UseDevelopmentStorage=true")
    table_service = TableServiceClient.from_connection_string(conn_str=connection_str)
    return table_service.get_table_client("Config")


def _mask_key(hashed_key: str) -> str:
    """Mask a hashed key to show only last 4 characters"""
    if len(hashed_key) < 4:
        return "****"
    return f"****{hashed_key[-4:]}"


async def create_workflow_key_handler(req: func.HttpRequest) -> func.HttpResponse:
    """
    Create a new workflow API key.

    Returns the raw key ONCE - it will not be shown again.
    Store this key securely as it cannot be recovered.

    Body (WorkflowKeyCreateRequest):
        {
            "workflowId": "workflows.specific_workflow",  // Optional: null for global key
            "expiresInDays": 90,                          // Optional: null for no expiration
            "description": "Production API Key"           // Optional
        }

    Response (WorkflowKeyResponse):
        200: {
            "id": "uuid",
            "rawKey": "wk_abc123...",  // Only shown on creation
            "workflowId": "workflows.test",
            "createdBy": "user@example.com",
            "createdAt": "ISO8601",
            "revoked": false,
            "expiresAt": "ISO8601",
            "description": "Production API Key"
        }

        400: Invalid request
        500: Server error
    """
    try:
        # Get context from request
        context = req.org_context  # type: ignore[attr-defined]
        user_email = context.caller.email

        # Parse request body
        body = req.get_json()
        if body is None:
            body = {}

        request = WorkflowKeyCreateRequest(**body)

        # Calculate expiration if specified
        expires_at = None
        if request.expiresInDays:
            expires_at = datetime.utcnow() + timedelta(days=request.expiresInDays)

        # Generate cryptographically secure key
        raw_key, workflow_key_data = generate_workflow_key(
            created_by=user_email,
            workflow_id=request.workflowId,
            expires_in_days=request.expiresInDays or 0
        )

        # Create a new WorkflowKey with all fields (Pydantic models are immutable)
        workflow_key = WorkflowKey(
            id=workflow_key_data.id,
            hashedKey=workflow_key_data.hashedKey,
            workflowId=workflow_key_data.workflowId,
            createdBy=workflow_key_data.createdBy,
            createdAt=workflow_key_data.createdAt,
            lastUsedAt=workflow_key_data.lastUsedAt,
            revoked=workflow_key_data.revoked,
            revokedAt=workflow_key_data.revokedAt,
            revokedBy=workflow_key_data.revokedBy,
            expiresAt=expires_at,
            description=request.description,
            disableGlobalKey=request.disableGlobalKey
        )

        # Store in Config table using existing pattern
        table_client = _get_config_table_client()

        # Use systemconfig:globalkey prefix for global keys, workflowkey prefix for workflow-specific
        if workflow_key.workflowId:
            row_key = f"workflowkey:{workflow_key.id}"
        else:
            row_key = f"systemconfig:globalkey:{workflow_key.id}"

        entity = {
            "PartitionKey": "GLOBAL",
            "RowKey": row_key,
            "KeyId": workflow_key.id,
            "HashedKey": workflow_key.hashedKey,
            "WorkflowId": workflow_key.workflowId,
            "CreatedBy": workflow_key.createdBy,
            "CreatedAt": workflow_key.createdAt.isoformat(),
            "LastUsedAt": None,
            "Revoked": False,
            "RevokedAt": None,
            "RevokedBy": None,
            "ExpiresAt": workflow_key.expiresAt.isoformat() if workflow_key.expiresAt else None,
            "Description": workflow_key.description,
            "DisableGlobalKey": workflow_key.disableGlobalKey
        }

        table_client.create_entity(entity)

        logger.info(
            "Created workflow API key",
            extra={
                "key_id": workflow_key.id,
                "workflow_id": workflow_key.workflowId,
                "created_by": user_email,
                "expires_at": workflow_key.expiresAt
            }
        )

        # Build response with raw key (ONLY TIME IT'S SHOWN)
        response = WorkflowKeyResponse(
            id=workflow_key.id,
            rawKey=raw_key,  # Show raw key on creation only
            maskedKey=None,
            workflowId=workflow_key.workflowId,
            createdBy=workflow_key.createdBy,
            createdAt=workflow_key.createdAt,
            lastUsedAt=None,
            revoked=False,
            expiresAt=workflow_key.expiresAt,
            description=workflow_key.description,
            disableGlobalKey=workflow_key.disableGlobalKey
        )

        return func.HttpResponse(
            json.dumps(response.model_dump(), default=str),
            status_code=201,
            mimetype="application/json"
        )

    except ValueError as e:
        logger.error(f"Validation error creating workflow key: {str(e)}")
        # Provide user-friendly error messages for common validation errors
        error_msg = str(e)
        if "Field required" in error_msg or "missing" in error_msg.lower():
            error_msg = "Required fields are missing. Please ensure all required fields are filled in."

        error = ErrorResponse(
            error="ValidationError",
            message=error_msg
        )
        return func.HttpResponse(
            json.dumps(error.model_dump()),
            status_code=400,
            mimetype="application/json"
        )
    except Exception as e:
        logger.error(f"Error creating workflow key: {str(e)}", exc_info=True)
        error = ErrorResponse(
            error="InternalError",
            message="Failed to create workflow key. Please try again or contact support."
        )
        return func.HttpResponse(
            json.dumps(error.model_dump()),
            status_code=500,
            mimetype="application/json"
        )


async def list_workflow_keys_handler(req: func.HttpRequest) -> func.HttpResponse:
    """
    List all workflow API keys for the current user.

    Keys are returned with masked values (last 4 characters only).
    Raw keys are never shown after creation.

    Query Parameters:
        workflowId (optional): Filter by workflow ID
        includeRevoked (optional): Include revoked keys (default: false)

    Response:
        200: [
            {
                "id": "uuid",
                "rawKey": null,
                "maskedKey": "****6789",
                "workflowId": "workflows.test",
                "createdBy": "user@example.com",
                "createdAt": "ISO8601",
                "lastUsedAt": "ISO8601",
                "revoked": false,
                "expiresAt": "ISO8601",
                "description": "Production Key"
            }
        ]
    """
    try:
        # Get context from request
        context = req.org_context  # type: ignore[attr-defined]
        user_email = context.caller.email

        # Get query parameters
        workflow_id_filter = req.params.get('workflowId')
        include_revoked = req.params.get('includeRevoked', 'false').lower() == 'true'

        # Query Config table for workflow keys
        table_client = _get_config_table_client()

        # Build query filter - query both prefixes
        # Note: We need to query separately for global and workflow-specific keys due to RowKey prefix
        entities = []

        # Query for workflow-specific keys
        workflow_query = f"PartitionKey eq 'GLOBAL' and RowKey ge 'workflowkey:' and RowKey lt 'workflowkey;' and CreatedBy eq '{user_email}'"
        if not include_revoked:
            workflow_query += " and Revoked eq false"
        if workflow_id_filter:
            workflow_query += f" and WorkflowId eq '{workflow_id_filter}'"

        entities.extend(list(table_client.query_entities(workflow_query)))

        # Query for global keys (systemconfig:globalkey prefix)
        if not workflow_id_filter:  # Global keys have no workflow_id
            global_query = f"PartitionKey eq 'GLOBAL' and RowKey ge 'systemconfig:globalkey:' and RowKey lt 'systemconfig:globalkey;' and CreatedBy eq '{user_email}'"
            if not include_revoked:
                global_query += " and Revoked eq false"

            entities.extend(list(table_client.query_entities(global_query)))

        # Convert entities to response models
        responses = []
        for entity in entities:
            response = WorkflowKeyResponse(
                id=entity.get('KeyId', entity['RowKey'].split(':')[1]),
                rawKey=None,  # Never show raw key after creation
                maskedKey=_mask_key(entity['HashedKey']),
                workflowId=entity.get('WorkflowId'),
                createdBy=entity['CreatedBy'],
                createdAt=datetime.fromisoformat(entity['CreatedAt']),
                lastUsedAt=datetime.fromisoformat(entity['LastUsedAt']) if entity.get('LastUsedAt') else None,
                revoked=entity.get('Revoked', False),
                expiresAt=datetime.fromisoformat(entity['ExpiresAt']) if entity.get('ExpiresAt') else None,
                description=entity.get('Description'),
                disableGlobalKey=entity.get('DisableGlobalKey', False)
            )
            responses.append(response)

        logger.info(
            f"Listed {len(responses)} workflow keys",
            extra={
                "user_email": user_email,
                "workflow_id_filter": workflow_id_filter,
                "include_revoked": include_revoked
            }
        )

        return func.HttpResponse(
            json.dumps([r.model_dump() for r in responses], default=str),
            status_code=200,
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Error listing workflow keys: {str(e)}", exc_info=True)
        error = ErrorResponse(
            error="InternalError",
            message=f"Failed to list workflow keys: {str(e)}"
        )
        return func.HttpResponse(
            json.dumps(error.model_dump()),
            status_code=500,
            mimetype="application/json"
        )


async def revoke_workflow_key_handler(req: func.HttpRequest) -> func.HttpResponse:
    """
    Revoke a workflow API key.

    Once revoked, the key can no longer be used for authentication.
    This action cannot be undone.

    Response:
        204: Key revoked successfully
        404: Key not found
        500: Server error
    """
    try:
        # Get context from request
        context = req.org_context  # type: ignore[attr-defined]
        user_email = context.caller.email

        # Get key ID from route params
        key_id = req.route_params.get('keyId')
        if not key_id:
            error = ErrorResponse(
                error="BadRequest",
                message="keyId is required"
            )
            return func.HttpResponse(
                json.dumps(error.model_dump()),
                status_code=400,
                mimetype="application/json"
            )

        # Get key from Config table
        # Try both possible prefixes
        table_client = _get_config_table_client()

        entity = None
        try:
            # Try workflow-specific prefix first
            entity = table_client.get_entity(
                partition_key="GLOBAL",
                row_key=f"workflowkey:{key_id}"
            )
        except Exception:
            try:
                # Try global key prefix
                entity = table_client.get_entity(
                    partition_key="GLOBAL",
                    row_key=f"systemconfig:globalkey:{key_id}"
                )
            except Exception:
                pass

        if not entity:
            error = ErrorResponse(
                error="NotFound",
                message=f"Workflow key '{key_id}' not found"
            )
            return func.HttpResponse(
                json.dumps(error.model_dump()),
                status_code=404,
                mimetype="application/json"
            )

        # Verify ownership
        if entity['CreatedBy'] != user_email:
            error = ErrorResponse(
                error="Forbidden",
                message="You can only revoke your own keys"
            )
            return func.HttpResponse(
                json.dumps(error.model_dump()),
                status_code=403,
                mimetype="application/json"
            )

        # Mark as revoked
        entity['Revoked'] = True
        entity['RevokedAt'] = datetime.utcnow().isoformat()
        entity['RevokedBy'] = user_email

        from azure.data.tables import UpdateMode
        table_client.update_entity(entity, mode=UpdateMode.MERGE)

        logger.info(
            "Revoked workflow API key",
            extra={
                "key_id": key_id,
                "revoked_by": user_email
            }
        )

        # Return 204 No Content
        return func.HttpResponse(
            status_code=204
        )

    except Exception as e:
        logger.error(f"Error revoking workflow key: {str(e)}", exc_info=True)
        error = ErrorResponse(
            error="InternalError",
            message=f"Failed to revoke workflow key: {str(e)}"
        )
        return func.HttpResponse(
            json.dumps(error.model_dump()),
            status_code=500,
            mimetype="application/json"
        )
