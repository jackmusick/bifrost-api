"""
Workflow Keys Handlers
Business logic for workflow API key management
Extracted from functions/workflow_keys.py for unit testability
"""

import json
import logging
from datetime import datetime, timedelta

import azure.functions as func

from shared.models import (
    ErrorResponse,
    WorkflowKey,
    WorkflowKeyCreateRequest,
    WorkflowKeyResponse,
)
from shared.repositories.config import get_global_config_repository
from shared.workflow_keys import generate_workflow_key

logger = logging.getLogger(__name__)


def _mask_key(hashed_key: str) -> str:
    """Mask a hashed key to show only last 4 characters"""
    if len(hashed_key) < 4:
        return "****"
    return f"****{hashed_key[-4:]}"


def _parse_datetime(value: str | datetime | None) -> datetime | None:
    """
    Parse a datetime value that could be either a string or datetime object.
    Azure Table Storage returns datetime objects, but test fixtures use strings.

    Args:
        value: The value to parse (string, datetime, or None)

    Returns:
        datetime object or None
    """
    if value is None:
        return None

    if isinstance(value, datetime):
        return value

    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value)
        except (ValueError, TypeError) as e:
            logger.warning(f"Failed to parse datetime from string '{value}': {e}")
            return None

    logger.warning(f"Unexpected datetime type: {type(value)} for value {value}")
    return None


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
        user_email = context.email

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

        # Store in Config table using repository
        repo = get_global_config_repository()

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

        repo.create_workflow_key(entity)

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
        user_email = context.email

        # Get query parameters
        workflow_id_filter = req.params.get('workflowId')
        include_revoked = req.params.get('includeRevoked', 'false').lower() == 'true'

        # Query Config table for workflow keys using repository
        repo = get_global_config_repository()
        entities = repo.list_workflow_keys(user_email, workflow_id_filter, include_revoked)

        # Convert entities to response models
        responses = []
        for entity in entities:
            # Parse datetime fields (Azure Table Storage returns datetime objects, tests use strings)
            created_at = _parse_datetime(entity['CreatedAt'])
            if created_at is None:
                logger.error(f"Invalid CreatedAt for workflow key {entity['RowKey']}")
                continue

            response = WorkflowKeyResponse(
                id=entity.get('KeyId', entity['RowKey'].split(':')[1]),
                rawKey=None,  # Never show raw key after creation
                maskedKey=_mask_key(entity['HashedKey']),
                workflowId=entity.get('WorkflowId'),
                createdBy=entity['CreatedBy'],
                createdAt=created_at,
                lastUsedAt=_parse_datetime(entity.get('LastUsedAt')),
                revoked=entity.get('Revoked', False),
                expiresAt=_parse_datetime(entity.get('ExpiresAt')),
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
        user_email = context.email

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

        # Get key from Config table using repository
        repo = get_global_config_repository()
        entity = repo.get_workflow_key_by_id(key_id)

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

        # Revoke using repository
        success = repo.revoke_workflow_key(key_id, user_email)
        if not success:
            error = ErrorResponse(
                error="InternalError",
                message="Failed to revoke workflow key"
            )
            return func.HttpResponse(
                json.dumps(error.model_dump()),
                status_code=500,
                mimetype="application/json"
            )

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
