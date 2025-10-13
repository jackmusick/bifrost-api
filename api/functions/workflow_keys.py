"""
Workflow Key Management API endpoints
- Generate global and org-specific workflow keys for HTTP-triggered workflows
- Retrieve and revoke workflow keys
"""

import logging
import json
import secrets
from datetime import datetime
from typing import Optional
import azure.functions as func

from shared.auth import require_auth
from shared.storage import TableStorageService
from shared.models import (
    WorkflowKey,
    WorkflowKeyResponse,
    ErrorResponse,
    UserType
)

logger = logging.getLogger(__name__)

# Create blueprint for workflow key endpoints
bp = func.Blueprint()


def generate_workflow_key() -> str:
    """
    Generate a secure random workflow key

    Returns:
        64-character hex string (256 bits of entropy)
    """
    return secrets.token_hex(32)


def mask_workflow_key(key: str) -> str:
    """
    Mask workflow key for safe display

    Args:
        key: Full workflow key

    Returns:
        Masked key showing only first 8 and last 4 characters
    """
    if len(key) > 12:
        return f"{key[:8]}...{key[-4:]}"
    return "***"


def get_workflow_key_entity(scope: str, org_id: Optional[str] = None) -> Optional[dict]:
    """
    Get workflow key entity from Config table

    Args:
        scope: 'GLOBAL' or 'org'
        org_id: Organization ID (required if scope='org')

    Returns:
        Workflow key entity or None if not found
    """
    config_service = TableStorageService("Config")
    partition_key = "GLOBAL" if scope == "GLOBAL" else org_id
    row_key = "config:workflow_key"

    try:
        entity = config_service.get_entity(partition_key, row_key)
        return entity
    except:
        return None


@bp.function_name("workflow_keys_get")
@bp.route(route="workflow-keys", methods=["GET"])
@require_auth
def get_workflow_key(req: func.HttpRequest) -> func.HttpResponse:
    """
    GET /api/workflow-keys?scope=global|org&orgId={id}
    Get workflow key (masked) for global or org-specific scope

    Query params:
        scope: 'global' for GLOBAL keys, 'org' for org-specific (requires orgId)
        orgId: Organization ID (required when scope=org)

    Requires:
        - For global keys: User must be MSP admin
        - For org keys: User must have canManageConfig permission
    """
    user = req.user
    scope = req.params.get("scope", "global").upper()
    org_id = req.params.get("orgId")

    logger.info(f"User {user.email} retrieving workflow key (scope={scope}, orgId={org_id})")

    try:
        # Validate scope parameter
        if scope not in ["GLOBAL", "ORG"]:
            error = ErrorResponse(
                error="BadRequest",
                message="scope parameter must be 'global' or 'org'"
            )
            return func.HttpResponse(
                json.dumps(error.model_dump()),
                status_code=400,
                mimetype="application/json"
            )

        # If scope=org, orgId is required
        if scope == "ORG" and not org_id:
            error = ErrorResponse(
                error="BadRequest",
                message="orgId parameter is required when scope=org"
            )
            return func.HttpResponse(
                json.dumps(error.model_dump()),
                status_code=400,
                mimetype="application/json"
            )

        # Permission checks
        if scope == "GLOBAL":
            # Only MSP admins can access global workflow key
            if not user.is_msp_admin:
                logger.warning(f"User {user.email} is not MSP admin, cannot access global workflow key")
                error = ErrorResponse(
                    error="Forbidden",
                    message="Only MSP administrators can access global workflow keys"
                )
                return func.HttpResponse(
                    json.dumps(error.model_dump()),
                    status_code=403,
                    mimetype="application/json"
                )
        else:
            # Check org permissions
            permissions_service = TableStorageService("UserPermissions")
            permission = permissions_service.get_entity(user.user_id, org_id)

            if not permission:
                logger.warning(f"User {user.email} denied access to org {org_id}")
                error = ErrorResponse(
                    error="Forbidden",
                    message="You don't have access to this organization"
                )
                return func.HttpResponse(
                    json.dumps(error.model_dump()),
                    status_code=403,
                    mimetype="application/json"
                )

            # Check canManageConfig permission
            if not permission.get("CanManageConfig", False):
                logger.warning(f"User {user.email} lacks canManageConfig permission for org {org_id}")
                error = ErrorResponse(
                    error="Forbidden",
                    message="You don't have permission to view workflow keys"
                )
                return func.HttpResponse(
                    json.dumps(error.model_dump()),
                    status_code=403,
                    mimetype="application/json"
                )

        # Get workflow key
        key_entity = get_workflow_key_entity(scope, org_id)

        if not key_entity:
            error = ErrorResponse(
                error="NotFound",
                message=f"No workflow key found for scope={scope.lower()}"
            )
            return func.HttpResponse(
                json.dumps(error.model_dump()),
                status_code=404,
                mimetype="application/json"
            )

        # Return masked key
        workflow_key = WorkflowKey(
            scope=scope,
            orgId=org_id if scope == "ORG" else None,
            key=mask_workflow_key(key_entity["Value"]),
            createdAt=datetime.fromisoformat(key_entity["CreatedAt"]),
            createdBy=key_entity["CreatedBy"],
            lastUsedAt=datetime.fromisoformat(key_entity["LastUsedAt"]) if key_entity.get("LastUsedAt") else None
        )

        logger.info(f"Returning masked workflow key (scope={scope})")

        return func.HttpResponse(
            json.dumps(workflow_key.model_dump(mode="json")),
            status_code=200,
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Error retrieving workflow key: {str(e)}", exc_info=True)
        error = ErrorResponse(
            error="InternalServerError",
            message="Failed to retrieve workflow key"
        )
        return func.HttpResponse(
            json.dumps(error.model_dump()),
            status_code=500,
            mimetype="application/json"
        )


@bp.function_name("workflow_keys_generate")
@bp.route(route="workflow-keys", methods=["POST"])
@require_auth
def generate_workflow_key_endpoint(req: func.HttpRequest) -> func.HttpResponse:
    """
    POST /api/workflow-keys?scope=global|org&orgId={id}
    Generate or regenerate a workflow key for global or org-specific scope

    Query params:
        scope: 'global' for GLOBAL keys, 'org' for org-specific (requires orgId)
        orgId: Organization ID (required when scope=org)

    Requires:
        - For global keys: User must be MSP admin
        - For org keys: User must have canManageConfig permission

    Note: This will REPLACE any existing workflow key for the scope
    """
    user = req.user
    scope = req.params.get("scope", "global").upper()
    org_id = req.params.get("orgId")

    logger.info(f"User {user.email} generating workflow key (scope={scope}, orgId={org_id})")

    try:
        # Validate scope parameter
        if scope not in ["GLOBAL", "ORG"]:
            error = ErrorResponse(
                error="BadRequest",
                message="scope parameter must be 'global' or 'org'"
            )
            return func.HttpResponse(
                json.dumps(error.model_dump()),
                status_code=400,
                mimetype="application/json"
            )

        # If scope=org, orgId is required
        if scope == "ORG" and not org_id:
            error = ErrorResponse(
                error="BadRequest",
                message="orgId parameter is required when scope=org"
            )
            return func.HttpResponse(
                json.dumps(error.model_dump()),
                status_code=400,
                mimetype="application/json"
            )

        # Permission checks
        if scope == "GLOBAL":
            # Only MSP admins can generate global workflow key
            if not user.is_msp_admin:
                logger.warning(f"User {user.email} is not MSP admin, cannot generate global workflow key")
                error = ErrorResponse(
                    error="Forbidden",
                    message="Only MSP administrators can generate global workflow keys"
                )
                return func.HttpResponse(
                    json.dumps(error.model_dump()),
                    status_code=403,
                    mimetype="application/json"
                )
        else:
            # Check org permissions
            permissions_service = TableStorageService("UserPermissions")
            permission = permissions_service.get_entity(user.user_id, org_id)

            if not permission:
                logger.warning(f"User {user.email} denied access to org {org_id}")
                error = ErrorResponse(
                    error="Forbidden",
                    message="You don't have access to this organization"
                )
                return func.HttpResponse(
                    json.dumps(error.model_dump()),
                    status_code=403,
                    mimetype="application/json"
                )

            # Check canManageConfig permission
            if not permission.get("CanManageConfig", False):
                logger.warning(f"User {user.email} lacks canManageConfig permission for org {org_id}")
                error = ErrorResponse(
                    error="Forbidden",
                    message="You don't have permission to manage workflow keys"
                )
                return func.HttpResponse(
                    json.dumps(error.model_dump()),
                    status_code=403,
                    mimetype="application/json"
                )

        # Generate new workflow key
        new_key = generate_workflow_key()

        # Determine partition key
        partition_key = "GLOBAL" if scope == "GLOBAL" else org_id
        row_key = "config:workflow_key"

        # Create entity
        now = datetime.utcnow()
        entity = {
            "PartitionKey": partition_key,
            "RowKey": row_key,
            "Value": new_key,
            "Type": "SECRET_REF",  # Mark as sensitive
            "Description": f"Workflow key for HTTP-triggered workflows ({'global' if scope == 'GLOBAL' else f'org {org_id}'})",
            "CreatedAt": now.isoformat(),
            "CreatedBy": user.user_id,
            "UpdatedAt": now.isoformat(),
            "UpdatedBy": user.user_id,
            "LastUsedAt": None
        }

        # Check if key already exists
        config_service = TableStorageService("Config")
        existing_key = get_workflow_key_entity(scope, org_id)

        if existing_key:
            # Replace existing key
            config_service.update_entity(entity)
            logger.warning(f"REPLACED existing workflow key (scope={scope})")
            status_code = 200
        else:
            # Create new key
            config_service.insert_entity(entity)
            logger.info(f"Created new workflow key (scope={scope})")
            status_code = 201

        # Return full key (only time it's shown)
        response = WorkflowKeyResponse(
            scope=scope,
            orgId=org_id if scope == "ORG" else None,
            key=new_key,
            createdAt=now,
            createdBy=user.user_id
        )

        return func.HttpResponse(
            json.dumps(response.model_dump(mode="json")),
            status_code=status_code,
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Error generating workflow key: {str(e)}", exc_info=True)
        error = ErrorResponse(
            error="InternalServerError",
            message="Failed to generate workflow key"
        )
        return func.HttpResponse(
            json.dumps(error.model_dump()),
            status_code=500,
            mimetype="application/json"
        )


@bp.function_name("workflow_keys_delete")
@bp.route(route="workflow-keys", methods=["DELETE"])
@require_auth
def delete_workflow_key(req: func.HttpRequest) -> func.HttpResponse:
    """
    DELETE /api/workflow-keys?scope=global|org&orgId={id}
    Revoke a workflow key for global or org-specific scope

    Query params:
        scope: 'global' for GLOBAL keys, 'org' for org-specific (requires orgId)
        orgId: Organization ID (required when scope=org)

    Requires:
        - For global keys: User must be MSP admin
        - For org keys: User must have canManageConfig permission

    Note: This will prevent all webhook executions for the scope until a new key is generated
    """
    user = req.user
    scope = req.params.get("scope", "global").upper()
    org_id = req.params.get("orgId")

    logger.info(f"User {user.email} deleting workflow key (scope={scope}, orgId={org_id})")

    try:
        # Validate scope parameter
        if scope not in ["GLOBAL", "ORG"]:
            error = ErrorResponse(
                error="BadRequest",
                message="scope parameter must be 'global' or 'org'"
            )
            return func.HttpResponse(
                json.dumps(error.model_dump()),
                status_code=400,
                mimetype="application/json"
            )

        # If scope=org, orgId is required
        if scope == "ORG" and not org_id:
            error = ErrorResponse(
                error="BadRequest",
                message="orgId parameter is required when scope=org"
            )
            return func.HttpResponse(
                json.dumps(error.model_dump()),
                status_code=400,
                mimetype="application/json"
            )

        # Permission checks
        if scope == "GLOBAL":
            # Only MSP admins can delete global workflow key
            if not user.is_msp_admin:
                logger.warning(f"User {user.email} is not MSP admin, cannot delete global workflow key")
                error = ErrorResponse(
                    error="Forbidden",
                    message="Only MSP administrators can delete global workflow keys"
                )
                return func.HttpResponse(
                    json.dumps(error.model_dump()),
                    status_code=403,
                    mimetype="application/json"
                )
        else:
            # Check org permissions
            permissions_service = TableStorageService("UserPermissions")
            permission = permissions_service.get_entity(user.user_id, org_id)

            if not permission:
                logger.warning(f"User {user.email} denied access to org {org_id}")
                error = ErrorResponse(
                    error="Forbidden",
                    message="You don't have access to this organization"
                )
                return func.HttpResponse(
                    json.dumps(error.model_dump()),
                    status_code=403,
                    mimetype="application/json"
                )

            # Check canManageConfig permission
            if not permission.get("CanManageConfig", False):
                logger.warning(f"User {user.email} lacks canManageConfig permission for org {org_id}")
                error = ErrorResponse(
                    error="Forbidden",
                    message="You don't have permission to delete workflow keys"
                )
                return func.HttpResponse(
                    json.dumps(error.model_dump()),
                    status_code=403,
                    mimetype="application/json"
                )

        # Delete workflow key (idempotent)
        config_service = TableStorageService("Config")
        partition_key = "GLOBAL" if scope == "GLOBAL" else org_id
        row_key = "config:workflow_key"

        try:
            config_service.delete_entity(partition_key, row_key)
            logger.warning(f"DELETED workflow key (scope={scope})")
        except Exception as e:
            # Even if entity doesn't exist, return 204 (idempotent delete)
            logger.debug(f"Workflow key not found (scope={scope}), but returning 204")

        return func.HttpResponse(
            status_code=204  # No Content
        )

    except Exception as e:
        logger.error(f"Error deleting workflow key: {str(e)}", exc_info=True)
        error = ErrorResponse(
            error="InternalServerError",
            message="Failed to delete workflow key"
        )
        return func.HttpResponse(
            json.dumps(error.model_dump()),
            status_code=500,
            mimetype="application/json"
        )
