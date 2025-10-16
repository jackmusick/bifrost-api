"""
Config and IntegrationConfig API endpoints
- Manage global and organization-specific configuration key-value pairs
- Manage integration configurations (Microsoft Graph, HaloPSA)
"""

import json
import logging
from datetime import datetime

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
from shared.storage import get_table_service

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
    """

    row_key = f"config:{key}"

    # Try org-specific first (if org_id provided)
    if org_id:
        try:
            config_service = get_table_service("Config", context)
            org_config = config_service.get_entity(org_id, row_key)
            if org_config:
                logger.debug(f"Found org-specific config for key '{key}' in org {org_id}")
                return org_config
        except Exception:
            pass  # Not found in org, will try GLOBAL

    # Fallback to GLOBAL
    try:
        config_service = get_table_service("Config", context)
        global_config = config_service.get_entity("GLOBAL", row_key)
        if global_config:
            logger.debug(f"Found GLOBAL config for key '{key}'")
            return global_config
    except Exception:
        pass  # Not found

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
    response_model=list[Config]
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
    context = req.context

    logger.info(f"User {context.user_id} retrieving config for scope={context.scope}")

    try:
        # Query Config table for current scope
        partition_key = context.scope

        config_service = get_table_service("Config", context)
        config_entities = list(config_service.query_entities(
            filter=f"PartitionKey eq '{partition_key}' and RowKey ge 'config:' and RowKey lt 'config;'"
        ))

        # Convert to response models
        configs = []
        for entity in config_entities:
            # Extract key from RowKey (remove "config:" prefix)
            key = entity["RowKey"].replace("config:", "", 1)

            # Mask sensitive values (but not secret_ref types)
            value = mask_sensitive_value(key, entity["Value"], entity["Type"])

            # Determine scope type for response
            pydantic_scope = "GLOBAL" if partition_key == "GLOBAL" else "org"

            config = Config(
                key=key,
                value=value,
                type=entity["Type"],
                scope=pydantic_scope,
                orgId=context.org_id if pydantic_scope == "org" else None,
                description=entity.get("Description"),
                updatedAt=entity["UpdatedAt"],
                updatedBy=entity["UpdatedBy"]
            )
            configs.append(config.model_dump(mode="json"))

        logger.info(f"Returning {len(configs)} config entries for scope={context.scope}")

        return func.HttpResponse(
            json.dumps(configs),
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
    context = req.context

    logger.info(f"User {context.user_id} setting config for scope={context.scope}")

    try:
        # Parse and validate request body
        request_body = req.get_json()
        set_request = SetConfigRequest(**request_body)

        # Use context.scope as partition key
        # - Platform admin with no X-Organization-Id header → GLOBAL
        # - Platform admin with X-Organization-Id: org-123 → org-123
        # - Regular user → their org_id from database
        partition_key = context.scope

        # Check if this is a new config or update
        config_service = get_table_service("Config", context)
        row_key = f"config:{set_request.key}"

        existing_config = None
        try:
            existing_config = config_service.get_entity(partition_key, row_key)
        except Exception:
            pass  # Config doesn't exist, will create new

        # Create entity for Table Storage
        now = datetime.utcnow()
        entity = {
            "PartitionKey": partition_key,
            "RowKey": row_key,
            "Value": set_request.value,
            "Type": set_request.type.value,
            "Description": set_request.description,
            "UpdatedAt": now.isoformat(),
            "UpdatedBy": context.user_id
        }

        # Insert or update
        if existing_config:
            # Update existing config
            config_service.update_entity(entity)
            status_code = 200
            logger.info(f"Updated config key '{set_request.key}' in partition={partition_key}")
        else:
            # Create new config
            config_service.insert_entity(entity)
            status_code = 201
            logger.info(f"Created config key '{set_request.key}' in partition={partition_key}")

        # Create response model with masked sensitive values
        masked_value = mask_sensitive_value(
            set_request.key,
            set_request.value,
            set_request.type.value
        )

        # Determine scope for response based on partition key
        pydantic_scope = "GLOBAL" if partition_key == "GLOBAL" else "org"

        config = Config(
            key=set_request.key,
            value=masked_value,
            type=set_request.type,
            scope=pydantic_scope,
            orgId=context.org_id if pydantic_scope == "org" else None,
            description=set_request.description,
            updatedAt=now,
            updatedBy=context.user_id
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
    context = req.context
    key = req.route_params.get("key")

    logger.info(f"User {context.user_id} deleting config key '{key}' from scope={context.scope}")

    try:
        # Use context.scope as partition key
        partition_key = context.scope

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
                entities_service = get_table_service("Entities", context)
                try:
                    # Query all OAuth connections for this org (stored as oauth:{name} in Entities table)
                    connections = list(entities_service.query_entities(
                        filter="RowKey ge 'oauth:' and RowKey lt 'oauth;'"
                    ))

                    # Find any connection that references this config key
                    referenced_by = []
                    for conn in connections:
                        client_secret_ref = conn.get("ClientSecretRef", "")
                        oauth_response_ref = conn.get("OAuthResponseRef", "")

                        # Check if this config is referenced by the connection
                        if client_secret_ref == key or oauth_response_ref == key or key.endswith("_metadata"):
                            oauth_name = conn.get("RowKey", "").replace("oauth:", "", 1)
                            referenced_by.append(oauth_name)

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

        # Delete config (idempotent - no error if key doesn't exist)
        config_service = get_table_service("Config", context)
        row_key = f"config:{key}"

        try:
            config_service.delete_entity(partition_key, row_key)
            logger.info(f"Deleted config key '{key}' (scope={partition_key})")
        except Exception:
            # Even if entity doesn't exist, return 204 (idempotent delete)
            logger.debug(f"Config key '{key}' not found (scope={partition_key}), but returning 204")

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
    context = req.context
    org_id = req.route_params.get("orgId")

    logger.info(f"User {context.user_id} retrieving integrations for org {org_id}")

    try:
        # Query Config table for integration configs (stored with "integration:" prefix)
        config_service = get_table_service("Config", context)
        integration_entities = list(config_service.query_entities(
            filter=f"PartitionKey eq '{org_id}' and RowKey ge 'integration:' and RowKey lt 'integration;'"
        ))

        # Convert to response models
        integrations = []
        for entity in integration_entities:
            # Extract type from RowKey (remove "integration:" prefix)
            integration_type = entity["RowKey"].replace("integration:", "", 1)

            integration = IntegrationConfig(
                type=integration_type,
                enabled=entity.get("Enabled", True),
                settings=json.loads(entity["Settings"]) if isinstance(entity["Settings"], str) else entity["Settings"],
                updatedAt=entity["UpdatedAt"],
                updatedBy=entity["UpdatedBy"]
            )
            integrations.append(integration.model_dump(mode="json"))

        logger.info(f"Returning {len(integrations)} integrations for org {org_id}")

        return func.HttpResponse(
            json.dumps(integrations),
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
    context = req.context
    org_id = req.route_params.get("orgId")

    logger.info(f"User {context.user_id} setting integration for org {org_id}")

    try:
        # Parse and validate request body
        request_body = req.get_json()
        set_request = SetIntegrationConfigRequest(**request_body)

        # Check if this is a new integration or update
        config_service = get_table_service("Config", context)
        row_key = f"integration:{set_request.type.value}"

        existing_integration = None
        try:
            existing_integration = config_service.get_entity(org_id, row_key)
        except Exception:
            pass  # Integration doesn't exist, will create new

        # Create entity for Table Storage
        now = datetime.utcnow()
        entity = {
            "PartitionKey": org_id,
            "RowKey": row_key,
            "Enabled": set_request.enabled,
            "Settings": json.dumps(set_request.settings),  # Store as JSON string
            "UpdatedAt": now.isoformat(),
            "UpdatedBy": context.user_id
        }

        # Insert or update
        if existing_integration:
            # Update existing integration
            config_service.update_entity(entity)
            status_code = 200
            logger.info(f"Updated {set_request.type.value} integration for org {org_id}")
        else:
            # Create new integration
            config_service.insert_entity(entity)
            status_code = 201
            logger.info(f"Created {set_request.type.value} integration for org {org_id}")

        # Create response model
        integration = IntegrationConfig(
            type=set_request.type,
            enabled=set_request.enabled,
            settings=set_request.settings,
            updatedAt=now,
            updatedBy=context.user_id
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
    context = req.context
    org_id = req.route_params.get("orgId")
    integration_type = req.route_params.get("type")

    logger.info(f"User {context.user_id} deleting {integration_type} integration for org {org_id}")

    try:
        # Delete integration (idempotent - no error if doesn't exist)
        config_service = get_table_service("Config", context)
        row_key = f"integration:{integration_type}"

        try:
            config_service.delete_entity(org_id, row_key)
            logger.info(f"Deleted {integration_type} integration for org {org_id}")
        except Exception:
            # Even if entity doesn't exist, return 204 (idempotent delete)
            logger.debug(f"{integration_type} integration not found for org {org_id}, but returning 204")

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
