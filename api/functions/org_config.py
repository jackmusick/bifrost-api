"""
Config and IntegrationConfig API endpoints
- Manage global and organization-specific configuration key-value pairs
- Manage integration configurations (Microsoft Graph, HaloPSA)
"""

import json
import logging

import azure.functions as func
from pydantic import ValidationError

from shared.decorators import require_platform_admin, with_request_context
from shared.models import (
    Config,
    ErrorResponse,
    IntegrationConfig,
    SetConfigRequest,
    SetIntegrationConfigRequest,
)
from shared.openapi_decorators import openapi_endpoint
from shared.repositories.config import ConfigRepository

logger = logging.getLogger(__name__)

# Create blueprint for config endpoints
bp = func.Blueprint()


def get_config_value(context, key: str, org_id: str | None = None) -> dict | None:
    """
    Get config value with fallback pattern: org-specific → GLOBAL → None

    Args:
        context: Request context
        key: Config key to lookup
        org_id: Organization ID (optional, will only check GLOBAL if None)

    Returns:
        Config entity dict or None if not found

    Note: This is a legacy helper function. New code should use ConfigRepository directly.
    """
    config_repo = ConfigRepository(context)
    config = config_repo.get_config(key, fallback_to_global=(org_id is not None or context.scope != "GLOBAL"))

    if config:
        # Convert back to entity dict for backward compatibility
        return {
            "PartitionKey": config.orgId if config.scope == "org" else "GLOBAL",
            "RowKey": f"config:{key}",
            "Value": config.value,
            "Type": config.type.value,
            "Description": config.description,
            "UpdatedAt": config.updatedAt,
            "UpdatedBy": config.updatedBy
        }

    logger.debug(f"Config key '{key}' not found (checked: {'org + GLOBAL' if org_id else 'GLOBAL only'})")
    return None


def mask_sensitive_value(key: str, value: str, value_type: str) -> str:
    """
    Mask sensitive config values for API responses.

    Note: secret_ref types are NOT masked since they just reference a secret name,
    not the actual secret value.
    """
    # Don't mask secret_ref types - they're just references to Key Vault secret names
    if value_type == "secret_ref":
        return value

    # Mask other sensitive values based on key name
    sensitive_keywords = ['secret', 'password', 'token', 'key', 'credential']
    if any(keyword in key.lower() for keyword in sensitive_keywords):
        if len(value) > 8:
            return value[:4] + '***' + value[-4:]
        return '***'
    return value


@bp.function_name("config_get_config")
@bp.route(route="config", methods=["GET"])
@openapi_endpoint(
    path="/config",
    method="GET",
    summary="Get configuration values",
    description="Get configuration values for current scope. Platform admins see all configs in their scope (set via X-Organization-Id header). Regular users see configs for their org.",
    tags=["Configuration"],
    response_model=list[Config]  # Now returning bare array of Configs
)
@with_request_context
@require_platform_admin
async def get_config(req: func.HttpRequest) -> func.HttpResponse:
    """
    GET /api/config
    Get configuration for current scope

    Scope is determined by context.scope (from X-Organization-Id header or user's org):
    - Platform admins: context.scope set by X-Organization-Id header (or GLOBAL if not set)
    - Regular users: context.scope is their org_id

    Platform admin only endpoint
    """
    context = req.context  # type: ignore[attr-defined]

    logger.info(f"User {context.user_id} retrieving config for scope={context.scope}")

    try:
        # Get configs using repository
        config_repo = ConfigRepository(context)
        configs = config_repo.list_config(include_global=False)  # Only get configs for current scope

        # Mask sensitive values
        for config in configs:
            config.value = mask_sensitive_value(config.key, config.value, config.type.value)

        # Sort configs by updatedAt descending (most recent first)
        configs.sort(key=lambda c: c.updatedAt, reverse=True)

        logger.info(f"Returning {len(configs)} config entries for scope={context.scope}")

        # Return bare array of configs
        return func.HttpResponse(
            json.dumps([c.model_dump(mode="json") for c in configs]),
            status_code=200,
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Error retrieving config: {str(e)}", exc_info=True)
        error = ErrorResponse(
            error="InternalServerError",
            message="Failed to retrieve configuration"
        )
        return func.HttpResponse(
            json.dumps(error.model_dump()),
            status_code=500,
            mimetype="application/json"
        )


@bp.function_name("config_set_config")
@bp.route(route="config", methods=["POST"])
@openapi_endpoint(
    path="/config",
    method="POST",
    summary="Set configuration value",
    description="Set a configuration value in the current scope (Platform admin only)",
    tags=["Configuration"],
    request_model=SetConfigRequest,
    response_model=Config
)
@with_request_context
@require_platform_admin
async def set_config(req: func.HttpRequest) -> func.HttpResponse:
    """
    POST /api/config
    Set a configuration key-value pair for current scope

    Request body includes 'scope' field to determine GLOBAL vs org-specific
    Scope is determined by:
    - If scope='GLOBAL' in request body: Save to GLOBAL partition
    - If scope='org' in request body: Save to context.scope (from X-Organization-Id header)

    Platform admin only endpoint
    """
    context = req.context  # type: ignore[attr-defined]

    logger.info(f"User {context.user_id} setting config for scope={context.scope}")

    try:
        # Parse and validate request body
        request_body = req.get_json()
        set_request = SetConfigRequest(**request_body)

        # Check if config exists (for status code determination)
        config_repo = ConfigRepository(context)
        existing_config = config_repo.get_config(set_request.key, fallback_to_global=False)
        status_code = 200 if existing_config else 201

        # Set config using repository
        config = config_repo.set_config(
            key=set_request.key,
            value=set_request.value,
            config_type=set_request.type,
            description=set_request.description,
            updated_by=context.user_id
        )

        # Mask sensitive values in response
        config.value = mask_sensitive_value(
            set_request.key,
            set_request.value,
            set_request.type.value
        )

        logger.info(
            f"{'Updated' if existing_config else 'Created'} config key '{set_request.key}' "
            f"in scope={context.scope}"
        )

        return func.HttpResponse(
            json.dumps(config.model_dump(mode="json")),
            status_code=status_code,
            mimetype="application/json"
        )

    except ValidationError as e:
        logger.warning(f"Validation error setting config: {e}")
        error = ErrorResponse(
            error="ValidationError",
            message="Invalid request data",
            details={"errors": e.errors()}
        )
        return func.HttpResponse(
            json.dumps(error.model_dump()),
            status_code=400,
            mimetype="application/json"
        )

    except ValueError as e:
        logger.error(f"Error parsing request: {str(e)}")
        error = ErrorResponse(
            error="BadRequest",
            message="Invalid JSON in request body"
        )
        return func.HttpResponse(
            json.dumps(error.model_dump()),
            status_code=400,
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Error setting org config: {str(e)}", exc_info=True)
        error = ErrorResponse(
            error="InternalServerError",
            message="Failed to set organization configuration"
        )
        return func.HttpResponse(
            json.dumps(error.model_dump()),
            status_code=500,
            mimetype="application/json"
        )


@bp.function_name("config_delete_config")
@bp.route(route="config/{key}", methods=["DELETE"])
@openapi_endpoint(
    path="/config/{key}",
    method="DELETE",
    summary="Delete configuration value",
    description="Delete a configuration value by key from current scope (Platform admin only)",
    tags=["Configuration"],
    path_params={
        "key": {
            "description": "Configuration key to delete",
            "schema": {"type": "string"}
        }
    }
)
@with_request_context
@require_platform_admin
async def delete_config(req: func.HttpRequest) -> func.HttpResponse:
    """
    DELETE /api/config/{key}
    Delete a configuration key from current scope

    Scope is determined by context.scope (from X-Organization-Id header or user's org)

    Platform admin only endpoint

    Note: Prevents deletion if config is referenced by OAuth connections
    """
    context = req.context  # type: ignore[attr-defined]
    key = req.route_params.get("key")
    assert key is not None, "key is required"

    logger.info(f"User {context.user_id} deleting config key '{key}' from scope={context.scope}")

    try:
        # Check if config is referenced by OAuth connections
        # OAuth connection configs follow patterns:
        # - oauth_{connection_name}_client_secret
        # - oauth_{connection_name}_oauth_response
        # - oauth_{connection_name}_metadata
        if key.startswith("oauth_"):
            # Extract connection name from key
            # Key patterns: oauth_{name}_client_secret, oauth_{name}_oauth_response, oauth_{name}_metadata
            parts = key.split("_")
            if len(parts) >= 3:
                # Check if there's an OAuth entity using this config
                from shared.repositories.oauth import OAuthRepository
                oauth_repo = OAuthRepository(context)

                try:
                    # Get all OAuth connections for this org
                    connections = await oauth_repo.list_connections(context.scope)

                    # Find any connection that references this config key
                    referenced_by = []
                    for conn in connections:
                        client_secret_ref = getattr(conn, 'clientSecretRef', None)
                        oauth_response_ref = getattr(conn, 'oauthResponseRef', None)
                        conn_name = getattr(conn, 'name', None)
                        if client_secret_ref == key or oauth_response_ref == key or key.endswith("_metadata"):
                            if conn_name:
                                referenced_by.append(conn_name)

                    if referenced_by:
                        error = ErrorResponse(
                            error="Conflict",
                            message=f"Cannot delete config '{key}' because it is referenced by OAuth connection(s): {', '.join(referenced_by)}",
                            details={"referenced_by": referenced_by}
                        )
                        return func.HttpResponse(
                            json.dumps(error.model_dump()),
                            status_code=409,  # Conflict
                            mimetype="application/json"
                        )
                except Exception as e:
                    logger.warning(f"Could not check OAuth references for config '{key}': {e}")

        # Delete config using repository (idempotent - no error if key doesn't exist)
        config_repo = ConfigRepository(context)
        config_repo.delete_config(key)
        logger.info(f"Deleted config key '{key}' (scope={context.scope})")

        return func.HttpResponse(
            status_code=204  # No Content
        )

    except Exception as e:
        logger.error(f"Error deleting org config: {str(e)}", exc_info=True)
        error = ErrorResponse(
            error="InternalServerError",
            message="Failed to delete organization configuration"
        )
        return func.HttpResponse(
            json.dumps(error.model_dump()),
            status_code=500,
            mimetype="application/json"
        )


# ==================== INTEGRATION CONFIG ENDPOINTS ====================


@bp.function_name("config_get_integrations")
@bp.route(route="organizations/{orgId}/integrations", methods=["GET"])
@openapi_endpoint(
    path="/organizations/{orgId}/integrations",
    method="GET",
    summary="Get organization integrations",
    description="Get all integration configurations for an organization (Platform admin only)",
    tags=["Integrations"],
    response_model=IntegrationConfig,
    path_params={
        "orgId": {
            "description": "Organization ID (UUID)",
            "schema": {"type": "string", "format": "uuid"}
        }
    }
)
@with_request_context
@require_platform_admin
async def get_integrations(req: func.HttpRequest) -> func.HttpResponse:
    """
    GET /api/organizations/{orgId}/integrations
    Get all integration configurations for an organization

    Platform admin only endpoint
    """
    context = req.context  # type: ignore[attr-defined]
    org_id = req.route_params.get("orgId")

    assert org_id is not None, "orgId is required"

    logger.info(f"User {context.user_id} retrieving integrations for org {org_id}")

    try:
        # Get integrations using repository
        config_repo = ConfigRepository(context)
        integrations = config_repo.list_integrations()

        # Convert to JSON response
        integrations_json = [i.model_dump(mode="json") for i in integrations]

        logger.info(f"Returning {len(integrations)} integrations for org {org_id}")

        return func.HttpResponse(
            json.dumps(integrations_json),
            status_code=200,
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Error retrieving integrations: {str(e)}", exc_info=True)
        error = ErrorResponse(
            error="InternalServerError",
            message="Failed to retrieve integrations"
        )
        return func.HttpResponse(
            json.dumps(error.model_dump()),
            status_code=500,
            mimetype="application/json"
        )


@bp.function_name("config_set_integration")
@bp.route(route="organizations/{orgId}/integrations", methods=["POST"])
@openapi_endpoint(
    path="/organizations/{orgId}/integrations",
    method="POST",
    summary="Set organization integration",
    description="Set or update an integration configuration for an organization (Platform admin only)",
    tags=["Integrations"],
    request_model=SetIntegrationConfigRequest,
    response_model=IntegrationConfig,
    path_params={
        "orgId": {
            "description": "Organization ID (UUID)",
            "schema": {"type": "string", "format": "uuid"}
        }
    }
)
@with_request_context
@require_platform_admin
async def set_integration(req: func.HttpRequest) -> func.HttpResponse:
    """
    POST /api/organizations/{orgId}/integrations
    Create or update an integration configuration

    Platform admin only endpoint
    """
    context = req.context  # type: ignore[attr-defined]
    org_id = req.route_params.get("orgId")

    assert org_id is not None, "orgId is required"

    logger.info(f"User {context.user_id} setting integration for org {org_id}")

    try:
        # Parse and validate request body
        request_body = req.get_json()
        set_request = SetIntegrationConfigRequest(**request_body)

        # Check if integration exists (for status code determination)
        config_repo = ConfigRepository(context)
        existing_integration = config_repo.get_integration_config(set_request.type, fallback_to_global=False)
        status_code = 200 if existing_integration else 201

        # Set integration using repository
        integration = config_repo.set_integration_config(
            request=set_request,
            updated_by=context.user_id
        )

        logger.info(
            f"{'Updated' if existing_integration else 'Created'} {set_request.type.value} integration for org {org_id}"
        )

        return func.HttpResponse(
            json.dumps(integration.model_dump(mode="json")),
            status_code=status_code,
            mimetype="application/json"
        )

    except ValidationError as e:
        logger.warning(f"Validation error setting integration: {e}")
        # Convert validation errors to JSON-serializable format
        errors = []
        for err in e.errors():
            error_dict = {"loc": err["loc"], "type": err["type"], "msg": str(err["msg"])}
            if "input" in err:
                error_dict["input"] = str(err["input"])
            errors.append(error_dict)

        error = ErrorResponse(
            error="ValidationError",
            message="Invalid request data",
            details={"errors": errors}
        )
        return func.HttpResponse(
            json.dumps(error.model_dump()),
            status_code=400,
            mimetype="application/json"
        )

    except ValueError as e:
        logger.error(f"Error parsing request: {str(e)}")
        error = ErrorResponse(
            error="BadRequest",
            message="Invalid JSON in request body"
        )
        return func.HttpResponse(
            json.dumps(error.model_dump()),
            status_code=400,
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Error setting integration: {str(e)}", exc_info=True)
        error = ErrorResponse(
            error="InternalServerError",
            message="Failed to set integration configuration"
        )
        return func.HttpResponse(
            json.dumps(error.model_dump()),
            status_code=500,
            mimetype="application/json"
        )


@bp.function_name("config_delete_integration")
@bp.route(route="organizations/{orgId}/integrations/{type}", methods=["DELETE"])
@openapi_endpoint(
    path="/organizations/{orgId}/integrations/{type}",
    method="DELETE",
    summary="Delete organization integration",
    description="Delete an integration configuration for an organization (Platform admin only)",
    tags=["Integrations"],
    path_params={
        "orgId": {
            "description": "Organization ID (UUID)",
            "schema": {"type": "string", "format": "uuid"}
        },
        "type": {
            "description": "Integration type",
            "schema": {"type": "string", "enum": ["msgraph", "halopsa"]}
        }
    }
)
@with_request_context
@require_platform_admin
async def delete_integration(req: func.HttpRequest) -> func.HttpResponse:
    """
    DELETE /api/organizations/{orgId}/integrations/{type}
    Delete an integration configuration

    Platform admin only endpoint
    Note: This only deletes the config reference, NOT the Key Vault secrets
    """
    context = req.context  # type: ignore[attr-defined]
    org_id = req.route_params.get("orgId")
    assert org_id is not None, "orgId is required"
    integration_type = req.route_params.get("type")

    logger.info(f"User {context.user_id} deleting {integration_type} integration for org {org_id}")

    try:
        # Delete integration using repository (idempotent - no error if doesn't exist)
        from shared.models import IntegrationType
        config_repo = ConfigRepository(context)
        config_repo.delete_integration(IntegrationType(integration_type))
        logger.info(f"Deleted {integration_type} integration for org {org_id}")

        return func.HttpResponse(
            status_code=204  # No Content
        )

    except Exception as e:
        logger.error(f"Error deleting integration: {str(e)}", exc_info=True)
        error = ErrorResponse(
            error="InternalServerError",
            message="Failed to delete integration configuration"
        )
        return func.HttpResponse(
            json.dumps(error.model_dump()),
            status_code=500,
            mimetype="application/json"
        )
