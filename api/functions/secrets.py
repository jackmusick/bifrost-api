"""
Secret management API endpoints.

Provides REST API for listing secrets from Azure Key Vault
to support secret dropdown selection in configuration UI.
"""

import json
import logging

import azure.functions as func
from pydantic import ValidationError

from shared.decorators import require_platform_admin, with_request_context
from shared.keyvault import KeyVaultClient
from shared.models import ErrorResponse, SecretCreateRequest, SecretListResponse, SecretResponse, SecretUpdateRequest
from shared.openapi_decorators import openapi_endpoint
from shared.storage import get_table_service
from shared.validation import check_key_vault_available

logger = logging.getLogger(__name__)

# Create blueprint for secrets endpoints
bp = func.Blueprint()

# Initialize Key Vault manager
try:
    kv_manager = KeyVaultClient()
except Exception as e:
    logger.error(f"Failed to initialize Key Vault manager: {e}")
    kv_manager = None


@bp.function_name("secrets_list")
@bp.route(route="secrets", methods=["GET"])
@openapi_endpoint(
    path="/secrets",
    method="GET",
    summary="List secrets",
    description="List available secrets from Key Vault, optionally filtered by organization (Platform admin only)",
    tags=["Secrets"],
    response_model=SecretListResponse,
    query_params={
        "org_id": {
            "description": "Filter secrets by organization ID (returns org-scoped + GLOBAL secrets)",
            "schema": {"type": "string"},
            "required": False
        }
    }
)
@with_request_context
@require_platform_admin
async def list_secrets(req: func.HttpRequest) -> func.HttpResponse:
    """
    GET /api/secrets

    List available secrets from Key Vault, optionally filtered by organization.

    Query Parameters:
        org_id (optional): Filter secrets by organization (returns org-scoped + GLOBAL secrets)

    Platform admin only endpoint

    Returns:
        200: SecretListResponse with list of secret names
        500: Key Vault error or service unavailable

    Example:
        GET /api/secrets?org_id=org-123
        Response: {"secrets": ["org-123--api-key", "GLOBAL--smtp-password"], "orgId": "org-123", "count": 2}
    """
    context = req.context
    logger.info(f"User {context.user_id} listing secrets")

    try:
        # Check if Key Vault is available
        is_available, error_response = check_key_vault_available(kv_manager)
        if not is_available:
            return error_response

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
@openapi_endpoint(
    path="/secrets",
    method="POST",
    summary="Create a secret",
    description="Create a new secret in Azure Key Vault (Platform admin only)",
    tags=["Secrets"],
    request_model=SecretCreateRequest,
    response_model=SecretResponse
)
@with_request_context
@require_platform_admin
async def create_secret(req: func.HttpRequest) -> func.HttpResponse:
    """
    POST /api/secrets

    Create a new secret in Azure Key Vault.

    Request Body:
        {
            "orgId": "org-123" or "GLOBAL",
            "secretKey": "api-key",
            "value": "secret-value"
        }

    Platform admin only endpoint

    Returns:
        201: SecretResponse with created secret details
        400: Validation error or invalid request
        409: Secret already exists
        500: Key Vault error

    Example:
        POST /api/secrets
        Body: {"orgId": "org-123", "secretKey": "api-key", "value": "my-secret"}
        Response: {"name": "org-123--api-key", "orgId": "org-123", "secretKey": "api-key", "value": "my-secret", "message": "Secret created successfully"}
    """
    context = req.context
    logger.info(f"User {context.user_id} creating secret")

    try:
        # Check if Key Vault is available
        is_available, error_response = check_key_vault_available(kv_manager)
        if not is_available:
            return error_response

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
        kv_manager.create_secret(
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
            extra={"secret_name": secret_name, "org_id": create_request.orgId, "created_by": context.user_id}
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
@openapi_endpoint(
    path="/secrets/{name}",
    method="PUT",
    summary="Update a secret",
    description="Update an existing secret in Azure Key Vault (Platform admin only)",
    tags=["Secrets"],
    request_model=SecretUpdateRequest,
    response_model=SecretResponse,
    path_params={
        "name": {
            "description": "Full secret name (e.g., 'org-123--api-key' or 'GLOBAL--smtp-password')",
            "schema": {"type": "string"}
        }
    }
)
@with_request_context
@require_platform_admin
async def update_secret(req: func.HttpRequest) -> func.HttpResponse:
    """
    PUT /api/secrets/{name}

    Update an existing secret in Azure Key Vault.

    Path Parameters:
        name: Full secret name (e.g., "org-123--api-key" or "GLOBAL--smtp-password")

    Request Body:
        {
            "value": "new-secret-value"
        }

    Platform admin only endpoint

    Returns:
        200: SecretResponse with updated secret details
        400: Validation error or invalid request
        404: Secret not found
        500: Key Vault error

    Example:
        PUT /api/secrets/org-123--api-key
        Body: {"value": "updated-secret"}
        Response: {"name": "org-123--api-key", "orgId": "org-123", "secretKey": "api-key", "value": "updated-secret", "message": "Secret updated successfully"}
    """
    context = req.context
    secret_name = req.route_params.get('name')
    logger.info(f"User {context.user_id} updating secret {secret_name}")

    try:
        # Check if Key Vault is available
        is_available, error_response = check_key_vault_available(kv_manager)
        if not is_available:
            return error_response

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
        kv_manager.update_secret(
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
            extra={"secret_name": secret_name, "org_id": org_id, "updated_by": context.user_id}
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
@openapi_endpoint(
    path="/secrets/{name}",
    method="DELETE",
    summary="Delete a secret",
    description="Delete a secret from Azure Key Vault. WARNING: This will delete the secret permanently. (Platform admin only)",
    tags=["Secrets"],
    response_model=SecretResponse,
    path_params={
        "name": {
            "description": "Full secret name (e.g., 'org-123--api-key' or 'GLOBAL--smtp-password')",
            "schema": {"type": "string"}
        }
    }
)
@with_request_context
@require_platform_admin
async def delete_secret(req: func.HttpRequest) -> func.HttpResponse:
    """
    DELETE /api/secrets/{name}

    Delete a secret from Azure Key Vault.

    WARNING: This will delete the secret permanently. Ensure no configurations
    reference this secret before deletion.

    Path Parameters:
        name: Full secret name (e.g., "org-123--api-key" or "GLOBAL--smtp-password")

    Platform admin only endpoint

    Returns:
        200: Success message
        404: Secret not found
        409: Secret is referenced by configurations (warning)
        500: Key Vault error

    Example:
        DELETE /api/secrets/org-123--api-key
        Response: {"name": "org-123--api-key", "orgId": "org-123", "secretKey": "api-key", "message": "Secret deleted successfully"}
    """
    context = req.context
    secret_name = req.route_params.get('name')
    logger.info(f"User {context.user_id} deleting secret {secret_name}")

    try:
        # Check if Key Vault is available
        is_available, error_response = check_key_vault_available(kv_manager)
        if not is_available:
            return error_response

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
        # This is a hard block - we check Table Storage for all references
        dependencies = []

        try:
            # Create a context that can query all orgs (platform admin scope)
            # We need to check both GLOBAL and all org-specific configs
            from shared.request_context import RequestContext

            # Check GLOBAL configs
            try:
                global_context = RequestContext(
                    user_id=context.user_id,
                    user_type=context.user_type,
                    org_scope="GLOBAL"
                )
                config_service = get_table_service("Config", global_context)
                global_configs = list(config_service.query_entities(
                    filter="RowKey ge 'config:' and RowKey lt 'config;'"
                ))
                for config in global_configs:
                    if config.get('Type') == 'SECRET_REF' and config.get('Value') == secret_name:
                        config_key = config.get('RowKey', '').replace('config:', '', 1)
                        dependencies.append({
                            "type": "config",
                            "key": config_key,
                            "scope": "GLOBAL"
                        })
            except Exception as e:
                logger.debug(f"Could not check GLOBAL configs: {e}")

            # Check org-specific configs if the secret is org-scoped
            if org_id != "GLOBAL":
                try:
                    org_context = RequestContext(
                        user_id=context.user_id,
                        user_type=context.user_type,
                        org_scope=org_id
                    )
                    config_service = get_table_service("Config", org_context)
                    org_configs = list(config_service.query_entities(
                        filter="RowKey ge 'config:' and RowKey lt 'config;'"
                    ))
                    for config in org_configs:
                        if config.get('Type') == 'SECRET_REF' and config.get('Value') == secret_name:
                            config_key = config.get('RowKey', '').replace('config:', '', 1)
                            dependencies.append({
                                "type": "config",
                                "key": config_key,
                                "scope": org_id
                            })
                except Exception as e:
                    logger.debug(f"Could not check org configs for {org_id}: {e}")

        except Exception as e:
            logger.warning(f"Could not check for secret references: {e}")

        # If there are dependencies, block deletion
        if dependencies:
            dep_list = []
            for dep in dependencies:
                if dep["type"] == "config":
                    dep_list.append(f"Config: {dep['key']} ({dep['scope']})")

            error = ErrorResponse(
                error="Conflict",
                message=f"Cannot delete secret '{secret_name}' because it is referenced by the following:\n" + "\n".join(dep_list) + "\n\nPlease remove all references before deleting this secret.",
                details={"dependencies": dependencies}
            )
            return func.HttpResponse(
                json.dumps(error.model_dump()),
                status_code=409,
                mimetype="application/json"
            )

        # Delete the secret
        kv_manager.delete_secret(
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
            extra={"secret_name": secret_name, "org_id": org_id, "deleted_by": context.user_id}
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
