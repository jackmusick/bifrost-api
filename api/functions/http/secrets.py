"""
Secret management API endpoints.

Provides REST API for listing, creating, updating, and deleting secrets
from Azure Key Vault to support secret management in configuration UI.

All business logic is delegated to shared/handlers/secrets_handlers.py
This module contains only HTTP routing and request/response handling.
"""

import json
import logging

import azure.functions as func
from pydantic import ValidationError  # noqa: F401 - used in except clauses

from shared.decorators import require_platform_admin, with_request_context
from shared.handlers.secrets_handlers import (
    SecretAlreadyExistsError,
    SecretHasDependenciesError,
    SecretHandlerError,
    SecretNotFoundError,
    handle_create_secret,
    handle_delete_secret,
    handle_list_secrets,
    handle_update_secret,
)
from shared.keyvault import KeyVaultClient
from shared.models import (
    ErrorResponse,
    SecretCreateRequest,
    SecretListResponse,
    SecretResponse,
    SecretUpdateRequest,
)
from shared.openapi_decorators import openapi_endpoint

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
    context = req.context  # type: ignore[attr-defined]
    logger.info(f"User {context.user_id} listing secrets")

    try:
        # Get org_id filter from query params
        org_id = req.params.get('org_id')

        # Delegate to handler
        response = await handle_list_secrets(kv_manager, org_id=org_id)

        return func.HttpResponse(
            json.dumps(response.model_dump()),
            status_code=200,
            mimetype="application/json"
        )

    except SecretHandlerError as e:
        logger.warning(f"Handler error listing secrets: {e}")
        error = ErrorResponse(
            error="ServiceUnavailable",
            message=str(e)
        )
        return func.HttpResponse(
            json.dumps(error.model_dump()),
            status_code=503,
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
    context = req.context  # type: ignore[attr-defined]
    logger.info(f"User {context.user_id} creating secret")

    try:
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

        # Delegate to handler
        response = await handle_create_secret(
            kv_manager,
            create_request,
            context.user_id
        )

        return func.HttpResponse(
            json.dumps(response.model_dump()),
            status_code=201,
            mimetype="application/json"
        )

    except SecretAlreadyExistsError as e:
        logger.warning(f"Secret already exists: {e}")
        error = ErrorResponse(
            error="Conflict",
            message=str(e)
        )
        return func.HttpResponse(
            json.dumps(error.model_dump()),
            status_code=409,
            mimetype="application/json"
        )
    except SecretHandlerError as e:
        logger.warning(f"Handler error creating secret: {e}")
        error = ErrorResponse(
            error="ServiceUnavailable",
            message=str(e)
        )
        return func.HttpResponse(
            json.dumps(error.model_dump()),
            status_code=503,
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
    context = req.context  # type: ignore[attr-defined]
    secret_name = req.route_params.get('name')
    logger.info(f"User {context.user_id} updating secret {secret_name}")

    try:
        # Validate that secret_name was provided
        if not secret_name:
            error = ErrorResponse(
                error="BadRequest",
                message="Secret name is required in URL path"
            )
            return func.HttpResponse(
                json.dumps(error.model_dump()),
                status_code=400,
                mimetype="application/json"
            )

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

        # Delegate to handler
        response = await handle_update_secret(
            kv_manager,
            secret_name,
            update_request,
            context.user_id
        )

        return func.HttpResponse(
            json.dumps(response.model_dump()),
            status_code=200,
            mimetype="application/json"
        )

    except SecretNotFoundError as e:
        logger.warning(f"Secret not found: {e}")
        error = ErrorResponse(
            error="NotFound",
            message=str(e)
        )
        return func.HttpResponse(
            json.dumps(error.model_dump()),
            status_code=404,
            mimetype="application/json"
        )
    except SecretHandlerError as e:
        logger.warning(f"Handler error updating secret: {e}")
        error = ErrorResponse(
            error="BadRequest",
            message=str(e)
        )
        return func.HttpResponse(
            json.dumps(error.model_dump()),
            status_code=400,
            mimetype="application/json"
        )
    except Exception as e:
        logger.error(f"Error updating secret: {e}", exc_info=True)
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
    context = req.context  # type: ignore[attr-defined]
    secret_name = req.route_params.get('name')
    logger.info(f"User {context.user_id} deleting secret {secret_name}")

    try:
        # Validate that secret_name was provided
        if not secret_name:
            error = ErrorResponse(
                error="BadRequest",
                message="Secret name is required in URL path"
            )
            return func.HttpResponse(
                json.dumps(error.model_dump()),
                status_code=400,
                mimetype="application/json"
            )

        # Delegate to handler
        response = await handle_delete_secret(
            kv_manager,
            secret_name,
            context,
            context.user_id
        )

        return func.HttpResponse(
            json.dumps(response.model_dump()),
            status_code=200,
            mimetype="application/json"
        )

    except SecretNotFoundError as e:
        logger.warning(f"Secret not found: {e}")
        error = ErrorResponse(
            error="NotFound",
            message=str(e)
        )
        return func.HttpResponse(
            json.dumps(error.model_dump()),
            status_code=404,
            mimetype="application/json"
        )
    except SecretHasDependenciesError as e:
        logger.warning(f"Secret has dependencies: {e}")
        error = ErrorResponse(
            error="Conflict",
            message=str(e),
            details={"dependencies": e.dependencies}
        )
        return func.HttpResponse(
            json.dumps(error.model_dump()),
            status_code=409,
            mimetype="application/json"
        )
    except SecretHandlerError as e:
        logger.warning(f"Handler error deleting secret: {e}")
        error = ErrorResponse(
            error="BadRequest",
            message=str(e)
        )
        return func.HttpResponse(
            json.dumps(error.model_dump()),
            status_code=400,
            mimetype="application/json"
        )
    except Exception as e:
        logger.error(f"Error deleting secret: {e}", exc_info=True)
        error = ErrorResponse(
            error="InternalServerError",
            message=f"Failed to delete secret: {str(e)}"
        )
        return func.HttpResponse(
            json.dumps(error.model_dump()),
            status_code=500,
            mimetype="application/json"
        )
