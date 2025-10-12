"""
Secret management API endpoints.

Provides REST API for listing secrets from Azure Key Vault
to support secret dropdown selection in configuration UI.
"""

import logging
import json
from typing import Optional
import azure.functions as func
from pydantic import ValidationError
from shared.models import (
    SecretListResponse,
    SecretCreateRequest,
    SecretUpdateRequest,
    SecretResponse,
    ErrorResponse
)
from shared.keyvault import KeyVaultManager
from shared.auth import require_auth, is_platform_admin
from shared.storage import TableStorageService

logger = logging.getLogger(__name__)

# Create blueprint for secrets endpoints
bp = func.Blueprint()

# Initialize Key Vault manager
try:
    kv_manager = KeyVaultManager()
except Exception as e:
    logger.error(f"Failed to initialize Key Vault manager: {e}")
    kv_manager = None


@bp.function_name("secrets_list")
@bp.route(route="secrets", methods=["GET"])
@require_auth
def list_secrets(req: func.HttpRequest) -> func.HttpResponse:
    """
    GET /api/secrets

    List available secrets from Key Vault, optionally filtered by organization.

    Query Parameters:
        org_id (optional): Filter secrets by organization (returns org-scoped + GLOBAL secrets)

    Returns:
        200: SecretListResponse with list of secret names
        403: Permission denied (not platform admin)
        500: Key Vault error or service unavailable

    Example:
        GET /api/secrets?org_id=org-123
        Response: {"secrets": ["org-123--api-key", "GLOBAL--smtp-password"], "orgId": "org-123", "count": 2}
    """
    user = req.user
    logger.info(f"User {user.email} listing secrets")

    try:
        # Check if user is platform admin
        if not is_platform_admin(user.user_id):
            logger.warning(f"User {user.email} is not a platform admin - denied secrets list access")
            error = ErrorResponse(
                error="Forbidden",
                message="Only platform administrators can list secrets"
            )
            return func.HttpResponse(
                json.dumps(error.model_dump()),
                status_code=403,
                mimetype="application/json"
            )

        # Check if Key Vault is available
        if not kv_manager:
            logger.error("Key Vault manager not initialized")
            error = ErrorResponse(
                error="ServiceUnavailable",
                message="Key Vault service is not configured"
            )
            return func.HttpResponse(
                json.dumps(error.model_dump()),
                status_code=503,
                mimetype="application/json"
            )

        # Get org_id filter from query params
        org_id = req.params.get('org_id')

        # List secrets with optional org filter
        secret_names = kv_manager.list_secrets(org_id=org_id)

        # Build response
        response = SecretListResponse(
            secrets=secret_names,
            orgId=org_id,
            count=len(secret_names)
        )

        logger.info(
            f"Listed {len(secret_names)} secrets" + (f" for org {org_id}" if org_id else ""),
            extra={"org_id": org_id, "secret_count": len(secret_names)}
        )

        return func.HttpResponse(
            json.dumps(response.model_dump()),
            status_code=200,
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Error listing secrets: {e}", exc_info=True)
        error = ErrorResponse(
            error="InternalServerError",
            message=f"Failed to list secrets: {str(e)}"
        )
        return func.HttpResponse(
            json.dumps(error.model_dump()),
            status_code=500,
            mimetype="application/json"
        )


@bp.function_name("secrets_create")
@bp.route(route="secrets", methods=["POST"])
@require_auth
def create_secret(req: func.HttpRequest) -> func.HttpResponse:
    """
    POST /api/secrets

    Create a new secret in Azure Key Vault.

    Request Body:
        {
            "orgId": "org-123" or "GLOBAL",
            "secretKey": "api-key",
            "value": "secret-value"
        }

    Returns:
        201: SecretResponse with created secret details
        400: Validation error or invalid request
        403: Permission denied (not platform admin)
        409: Secret already exists
        500: Key Vault error

    Example:
        POST /api/secrets
        Body: {"orgId": "org-123", "secretKey": "api-key", "value": "my-secret"}
        Response: {"name": "org-123--api-key", "orgId": "org-123", "secretKey": "api-key", "value": "my-secret", "message": "Secret created successfully"}
    """
    user = req.user
    logger.info(f"User {user.email} creating secret")

    try:
        # Check if user is platform admin
        if not is_platform_admin(user.user_id):
            logger.warning(f"User {user.email} is not a platform admin - denied secret create access")
            error = ErrorResponse(
                error="Forbidden",
                message="Only platform administrators can create secrets"
            )
            return func.HttpResponse(
                json.dumps(error.model_dump()),
                status_code=403,
                mimetype="application/json"
            )

        # Check if Key Vault is available
        if not kv_manager:
            logger.error("Key Vault manager not initialized")
            error = ErrorResponse(
                error="ServiceUnavailable",
                message="Key Vault service is not configured"
            )
            return func.HttpResponse(
                json.dumps(error.model_dump()),
                status_code=503,
                mimetype="application/json"
            )

        # Parse request body
        try:
            body = json.loads(req.get_body().decode('utf-8'))
            create_request = SecretCreateRequest(**body)
        except json.JSONDecodeError:
            error = ErrorResponse(
                error="BadRequest",
                message="Invalid JSON in request body"
            )
            return func.HttpResponse(
                json.dumps(error.model_dump()),
                status_code=400,
                mimetype="application/json"
            )
        except ValidationError as e:
            error = ErrorResponse(
                error="ValidationError",
                message="Request validation failed",
                details={"errors": e.errors()}
            )
            return func.HttpResponse(
                json.dumps(error.model_dump()),
                status_code=400,
                mimetype="application/json"
            )

        # Check if secret already exists
        secret_name = f"{create_request.orgId}--{create_request.secretKey}"
        try:
            existing_secrets = kv_manager.list_secrets()
            if secret_name in existing_secrets:
                logger.warning(f"Secret {secret_name} already exists")
                error = ErrorResponse(
                    error="Conflict",
                    message=f"Secret '{secret_name}' already exists. Use PUT to update."
                )
                return func.HttpResponse(
                    json.dumps(error.model_dump()),
                    status_code=409,
                    mimetype="application/json"
                )
        except Exception as e:
            logger.warning(f"Could not check for existing secret: {e}")

        # Create the secret
        result = kv_manager.create_secret(
            org_id=create_request.orgId,
            secret_key=create_request.secretKey,
            value=create_request.value
        )

        # Build response
        response = SecretResponse(
            name=secret_name,
            orgId=create_request.orgId,
            secretKey=create_request.secretKey,
            value=create_request.value,  # Show value immediately after creation
            message="Secret created successfully"
        )

        logger.info(
            f"Created secret {secret_name}",
            extra={"secret_name": secret_name, "org_id": create_request.orgId, "created_by": user.email}
        )

        return func.HttpResponse(
            json.dumps(response.model_dump()),
            status_code=201,
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Error creating secret: {e}", exc_info=True)
        error = ErrorResponse(
            error="InternalServerError",
            message=f"Failed to create secret: {str(e)}"
        )
        return func.HttpResponse(
            json.dumps(error.model_dump()),
            status_code=500,
            mimetype="application/json"
        )


@bp.function_name("secrets_update")
@bp.route(route="secrets/{name}", methods=["PUT"])
@require_auth
def update_secret(req: func.HttpRequest) -> func.HttpResponse:
    """
    PUT /api/secrets/{name}

    Update an existing secret in Azure Key Vault.

    Path Parameters:
        name: Full secret name (e.g., "org-123--api-key" or "GLOBAL--smtp-password")

    Request Body:
        {
            "value": "new-secret-value"
        }

    Returns:
        200: SecretResponse with updated secret details
        400: Validation error or invalid request
        403: Permission denied (not platform admin)
        404: Secret not found
        500: Key Vault error

    Example:
        PUT /api/secrets/org-123--api-key
        Body: {"value": "updated-secret"}
        Response: {"name": "org-123--api-key", "orgId": "org-123", "secretKey": "api-key", "value": "updated-secret", "message": "Secret updated successfully"}
    """
    user = req.user
    secret_name = req.route_params.get('name')
    logger.info(f"User {user.email} updating secret {secret_name}")

    try:
        # Check if user is platform admin
        if not is_platform_admin(user.user_id):
            logger.warning(f"User {user.email} is not a platform admin - denied secret update access")
            error = ErrorResponse(
                error="Forbidden",
                message="Only platform administrators can update secrets"
            )
            return func.HttpResponse(
                json.dumps(error.model_dump()),
                status_code=403,
                mimetype="application/json"
            )

        # Check if Key Vault is available
        if not kv_manager:
            logger.error("Key Vault manager not initialized")
            error = ErrorResponse(
                error="ServiceUnavailable",
                message="Key Vault service is not configured"
            )
            return func.HttpResponse(
                json.dumps(error.model_dump()),
                status_code=503,
                mimetype="application/json"
            )

        # Validate secret name format
        if not secret_name or '--' not in secret_name:
            error = ErrorResponse(
                error="BadRequest",
                message="Invalid secret name format. Expected: 'org-id--secret-key' or 'GLOBAL--secret-key'"
            )
            return func.HttpResponse(
                json.dumps(error.model_dump()),
                status_code=400,
                mimetype="application/json"
            )

        # Parse org_id and secret_key from name
        parts = secret_name.split('--', 1)
        org_id = parts[0]
        secret_key = parts[1]

        # Parse request body
        try:
            body = json.loads(req.get_body().decode('utf-8'))
            update_request = SecretUpdateRequest(**body)
        except json.JSONDecodeError:
            error = ErrorResponse(
                error="BadRequest",
                message="Invalid JSON in request body"
            )
            return func.HttpResponse(
                json.dumps(error.model_dump()),
                status_code=400,
                mimetype="application/json"
            )
        except ValidationError as e:
            error = ErrorResponse(
                error="ValidationError",
                message="Request validation failed",
                details={"errors": e.errors()}
            )
            return func.HttpResponse(
                json.dumps(error.model_dump()),
                status_code=400,
                mimetype="application/json"
            )

        # Update the secret
        result = kv_manager.update_secret(
            org_id=org_id,
            secret_key=secret_key,
            value=update_request.value
        )

        # Build response
        response = SecretResponse(
            name=secret_name,
            orgId=org_id,
            secretKey=secret_key,
            value=update_request.value,  # Show value immediately after update
            message="Secret updated successfully"
        )

        logger.info(
            f"Updated secret {secret_name}",
            extra={"secret_name": secret_name, "org_id": org_id, "updated_by": user.email}
        )

        return func.HttpResponse(
            json.dumps(response.model_dump()),
            status_code=200,
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Error updating secret: {e}", exc_info=True)

        # Check if it's a "not found" error
        if "not found" in str(e).lower():
            error = ErrorResponse(
                error="NotFound",
                message=f"Secret '{secret_name}' not found"
            )
            return func.HttpResponse(
                json.dumps(error.model_dump()),
                status_code=404,
                mimetype="application/json"
            )

        error = ErrorResponse(
            error="InternalServerError",
            message=f"Failed to update secret: {str(e)}"
        )
        return func.HttpResponse(
            json.dumps(error.model_dump()),
            status_code=500,
            mimetype="application/json"
        )


@bp.function_name("secrets_delete")
@bp.route(route="secrets/{name}", methods=["DELETE"])
@require_auth
def delete_secret(req: func.HttpRequest) -> func.HttpResponse:
    """
    DELETE /api/secrets/{name}

    Delete a secret from Azure Key Vault.

    WARNING: This will delete the secret permanently. Ensure no configurations
    reference this secret before deletion.

    Path Parameters:
        name: Full secret name (e.g., "org-123--api-key" or "GLOBAL--smtp-password")

    Returns:
        200: Success message
        403: Permission denied (not platform admin)
        404: Secret not found
        409: Secret is referenced by configurations (warning)
        500: Key Vault error

    Example:
        DELETE /api/secrets/org-123--api-key
        Response: {"name": "org-123--api-key", "orgId": "org-123", "secretKey": "api-key", "message": "Secret deleted successfully"}
    """
    user = req.user
    secret_name = req.route_params.get('name')
    logger.info(f"User {user.email} deleting secret {secret_name}")

    try:
        # Check if user is platform admin
        if not is_platform_admin(user.user_id):
            logger.warning(f"User {user.email} is not a platform admin - denied secret delete access")
            error = ErrorResponse(
                error="Forbidden",
                message="Only platform administrators can delete secrets"
            )
            return func.HttpResponse(
                json.dumps(error.model_dump()),
                status_code=403,
                mimetype="application/json"
            )

        # Check if Key Vault is available
        if not kv_manager:
            logger.error("Key Vault manager not initialized")
            error = ErrorResponse(
                error="ServiceUnavailable",
                message="Key Vault service is not configured"
            )
            return func.HttpResponse(
                json.dumps(error.model_dump()),
                status_code=503,
                mimetype="application/json"
            )

        # Validate secret name format
        if not secret_name or '--' not in secret_name:
            error = ErrorResponse(
                error="BadRequest",
                message="Invalid secret name format. Expected: 'org-id--secret-key' or 'GLOBAL--secret-key'"
            )
            return func.HttpResponse(
                json.dumps(error.model_dump()),
                status_code=400,
                mimetype="application/json"
            )

        # Parse org_id and secret_key from name
        parts = secret_name.split('--', 1)
        org_id = parts[0]
        secret_key = parts[1]

        # Check if secret is referenced in configurations
        # This is a best-effort warning - we check Table Storage for references
        try:
            storage_service = TableStorageService()

            # Check global configs
            global_configs = storage_service.query_entities(
                table_name="Configs",
                partition_key="GLOBAL"
            )
            for config in global_configs:
                if config.get('type') == 'secret_ref' and config.get('value') == secret_key:
                    logger.warning(f"Secret {secret_name} is referenced in global config {config.get('key')}")
                    error = ErrorResponse(
                        error="Conflict",
                        message=f"Secret '{secret_name}' is referenced in configuration '{config.get('key')}'. Remove references before deletion.",
                        details={"config_key": config.get('key'), "scope": "GLOBAL"}
                    )
                    return func.HttpResponse(
                        json.dumps(error.model_dump()),
                        status_code=409,
                        mimetype="application/json"
                    )

            # Check org-specific configs if not GLOBAL
            if org_id != "GLOBAL":
                org_configs = storage_service.query_entities(
                    table_name="Configs",
                    partition_key=org_id
                )
                for config in org_configs:
                    if config.get('type') == 'secret_ref' and config.get('value') == secret_key:
                        logger.warning(f"Secret {secret_name} is referenced in org config {config.get('key')}")
                        error = ErrorResponse(
                            error="Conflict",
                            message=f"Secret '{secret_name}' is referenced in configuration '{config.get('key')}' for organization '{org_id}'. Remove references before deletion.",
                            details={"config_key": config.get('key'), "scope": org_id}
                        )
                        return func.HttpResponse(
                            json.dumps(error.model_dump()),
                            status_code=409,
                            mimetype="application/json"
                        )
        except Exception as e:
            logger.warning(f"Could not check for secret references: {e}")

        # Delete the secret
        result = kv_manager.delete_secret(
            org_id=org_id,
            secret_key=secret_key
        )

        # Build response
        response = SecretResponse(
            name=secret_name,
            orgId=org_id,
            secretKey=secret_key,
            value=None,  # Never show value after deletion
            message="Secret deleted successfully"
        )

        logger.info(
            f"Deleted secret {secret_name}",
            extra={"secret_name": secret_name, "org_id": org_id, "deleted_by": user.email}
        )

        return func.HttpResponse(
            json.dumps(response.model_dump()),
            status_code=200,
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Error deleting secret: {e}", exc_info=True)

        # Check if it's a "not found" error
        if "not found" in str(e).lower():
            error = ErrorResponse(
                error="NotFound",
                message=f"Secret '{secret_name}' not found"
            )
            return func.HttpResponse(
                json.dumps(error.model_dump()),
                status_code=404,
                mimetype="application/json"
            )

        error = ErrorResponse(
            error="InternalServerError",
            message=f"Failed to delete secret: {str(e)}"
        )
        return func.HttpResponse(
            json.dumps(error.model_dump()),
            status_code=500,
            mimetype="application/json"
        )
