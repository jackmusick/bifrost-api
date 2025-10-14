"""
Config and IntegrationConfig API endpoints
- Manage global and organization-specific configuration key-value pairs
- Manage integration configurations (Microsoft Graph, HaloPSA)
"""

import logging
import json
from datetime import datetime
from typing import List, Optional
import azure.functions as func

from shared.decorators import with_request_context, require_platform_admin
from shared.storage import get_table_service
from shared.models import (
    Config,
    SetConfigRequest,
    IntegrationConfig,
    SetIntegrationConfigRequest,
    IntegrationType,
    ErrorResponse
)
from shared.validation import validate_scope_parameter
from pydantic import ValidationError

logger = logging.getLogger(__name__)

# Create blueprint for config endpoints
bp = func.Blueprint()


def get_config_value(context, key: str, org_id: Optional[str] = None) -> Optional[dict]:
    """
    Get config value with fallback pattern: org-specific → GLOBAL → None

    Args:
        context: Request context
        key: Config key to lookup
        org_id: Organization ID (optional, will only check GLOBAL if None)

    Returns:
        Config entity dict or None if not found
    """
    from shared.request_context import RequestContext

    row_key = f"config:{key}"

    # Try org-specific first (if org_id provided)
    if org_id:
        try:
            org_context = RequestContext(
                user_id=context.user_id,
                user_type=context.user_type,
                org_scope=org_id
            )
            config_service = get_table_service("Config", org_context)
            org_config = config_service.get_entity(org_id, row_key)
            if org_config:
                logger.debug(f"Found org-specific config for key '{key}' in org {org_id}")
                return org_config
        except:
            pass  # Not found in org, will try GLOBAL

    # Fallback to GLOBAL
    try:
        global_context = RequestContext(
            user_id=context.user_id,
            user_type=context.user_type,
            org_scope="GLOBAL"
        )
        config_service = get_table_service("Config", global_context)
        global_config = config_service.get_entity("GLOBAL", row_key)
        if global_config:
            logger.debug(f"Found GLOBAL config for key '{key}'")
            return global_config
    except:
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
@with_request_context
@require_platform_admin
async def get_config(req: func.HttpRequest) -> func.HttpResponse:
    """
    GET /api/config?scope=global|org&orgId={id}
    Get configuration with scope filtering

    Query params:
        scope: 'global' for GLOBAL configs only, 'org' for org-specific (requires orgId)
        orgId: Organization ID (required when scope=org)

    Platform admin only endpoint
    """
    context = req.context
    scope = req.params.get("scope", "global").lower()
    org_id = req.params.get("orgId")

    logger.info(f"User {context.user_id} retrieving config with scope={scope}, orgId={org_id}")

    try:
        # Validate scope parameter
        is_valid, error_response = validate_scope_parameter(scope, org_id)
        if not is_valid:
            return error_response

        # Query Config table based on scope
        from shared.request_context import RequestContext

        # Create context for the requested scope
        scoped_context = RequestContext(
            user_id=context.user_id,
            user_type=context.user_type,
            org_scope="GLOBAL" if scope == "global" else org_id
        )

        config_service = get_table_service("Config", scoped_context)
        config_entities = list(config_service.query_entities(
            filter="RowKey ge 'config:' and RowKey lt 'config;'"
        ))

        # Convert to response models
        configs = []
        for entity in config_entities:
            # Extract key from RowKey (remove "config:" prefix)
            key = entity["RowKey"].replace("config:", "", 1)

            # Mask sensitive values (but not secret_ref types)
            value = mask_sensitive_value(key, entity["Value"], entity["Type"])

            # Convert scope to uppercase for Pydantic model validation
            pydantic_scope = "GLOBAL" if scope == "global" else "org"

            config = Config(
                key=key,
                value=value,
                type=entity["Type"],
                scope=pydantic_scope,
                orgId=org_id if scope == "org" else None,
                description=entity.get("Description"),
                updatedAt=entity["UpdatedAt"],
                updatedBy=entity["UpdatedBy"]
            )
            configs.append(config.model_dump(mode="json"))

        logger.info(f"Returning {len(configs)} config entries (scope={scope})")

        return func.HttpResponse(
            json.dumps(configs),
            status_code=200,
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Error retrieving org config: {str(e)}", exc_info=True)
        error = ErrorResponse(
            error="InternalServerError",
            message="Failed to retrieve organization configuration"
        )
        return func.HttpResponse(
            json.dumps(error.model_dump()),
            status_code=500,
            mimetype="application/json"
        )


@bp.function_name("config_set_config")
@bp.route(route="config", methods=["POST"])
@with_request_context
@require_platform_admin
async def set_config(req: func.HttpRequest) -> func.HttpResponse:
    """
    POST /api/config
    Set a configuration key-value pair (global or org-specific)

    Request body includes 'scope' field to determine GLOBAL vs org-specific
    If scope=org, orgId query parameter is required

    Platform admin only endpoint
    """
    context = req.context
    org_id = req.params.get("orgId")

    logger.info(f"User {context.user_id} setting config (orgId={org_id})")

    try:
        # Parse and validate request body
        request_body = req.get_json()
        set_request = SetConfigRequest(**request_body)

        # Determine partition key based on scope
        if set_request.scope == "org":
            if not org_id:
                error = ErrorResponse(
                    error="BadRequest",
                    message="orgId parameter is required when scope=org"
                )
                return func.HttpResponse(
                    json.dumps(error.model_dump()),
                    status_code=400,
                    mimetype="application/json"
                )

            partition_key = org_id
        else:
            partition_key = "GLOBAL"

        # Create context for the requested scope
        from shared.request_context import RequestContext
        scoped_context = RequestContext(
            user_id=context.user_id,
            user_type=context.user_type,
            org_scope=partition_key
        )

        # Check if this is a new config or update
        config_service = get_table_service("Config", scoped_context)
        row_key = f"config:{set_request.key}"

        existing_config = None
        try:
            existing_config = config_service.get_entity(partition_key, row_key)
        except:
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
            logger.info(f"Updated config key '{set_request.key}' (scope={set_request.scope})")
        else:
            # Create new config
            config_service.insert_entity(entity)
            status_code = 201
            logger.info(f"Created config key '{set_request.key}' (scope={set_request.scope})")

        # Create response model
        config = Config(
            key=set_request.key,
            value=set_request.value,
            type=set_request.type,
            scope=set_request.scope,
            orgId=org_id if set_request.scope == "org" else None,
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
@with_request_context
@require_platform_admin
async def delete_config(req: func.HttpRequest) -> func.HttpResponse:
    """
    DELETE /api/config/{key}?scope=global|org&orgId={id}
    Delete a configuration key

    Query params:
        scope: 'global' or 'org'
        orgId: Required when scope=org

    Platform admin only endpoint

    Note: Prevents deletion if config is referenced by OAuth connections
    """
    context = req.context
    key = req.route_params.get("key")
    scope = req.params.get("scope", "global").lower()
    org_id = req.params.get("orgId")

    logger.info(f"User {context.user_id} deleting config key '{key}' (scope={scope}, orgId={org_id})")

    try:
        # Validate scope
        is_valid, error_response = validate_scope_parameter(scope, org_id)
        if not is_valid:
            return error_response

        # Determine partition key and check permissions
        if scope == "org":
            if not org_id:
                error = ErrorResponse(
                    error="BadRequest",
                    message="orgId parameter is required when scope=org"
                )
                return func.HttpResponse(
                    json.dumps(error.model_dump()),
                    status_code=400,
                    mimetype="application/json"
                )

            partition_key = org_id
        else:
            partition_key = "GLOBAL"

        # Create context for the requested scope
        from shared.request_context import RequestContext
        scoped_context = RequestContext(
            user_id=context.user_id,
            user_type=context.user_type,
            org_scope=partition_key
        )

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
                entities_service = get_table_service("Entities", scoped_context)
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
        config_service = get_table_service("Config", scoped_context)
        row_key = f"config:{key}"

        try:
            config_service.delete_entity(partition_key, row_key)
            logger.info(f"Deleted config key '{key}' (scope={scope})")
        except Exception as e:
            # Even if entity doesn't exist, return 204 (idempotent delete)
            logger.debug(f"Config key '{key}' not found (scope={scope}), but returning 204")

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
        # Create context for the requested org
        from shared.request_context import RequestContext
        org_context = RequestContext(
            user_id=context.user_id,
            user_type=context.user_type,
            org_scope=org_id
        )

        # Query Config table for integration configs (stored with "integration:" prefix)
        config_service = get_table_service("Config", org_context)
        integration_entities = list(config_service.query_entities(
            filter="RowKey ge 'integration:' and RowKey lt 'integration;'"
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
        # Create context for the requested org
        from shared.request_context import RequestContext
        org_context = RequestContext(
            user_id=context.user_id,
            user_type=context.user_type,
            org_scope=org_id
        )

        # Parse and validate request body
        request_body = req.get_json()
        set_request = SetIntegrationConfigRequest(**request_body)

        # Check if this is a new integration or update
        config_service = get_table_service("Config", org_context)
        row_key = f"integration:{set_request.type.value}"

        existing_integration = None
        try:
            existing_integration = config_service.get_entity(org_id, row_key)
        except:
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
        # Create context for the requested org
        from shared.request_context import RequestContext
        org_context = RequestContext(
            user_id=context.user_id,
            user_type=context.user_type,
            org_scope=org_id
        )

        # Delete integration (idempotent - no error if doesn't exist)
        config_service = get_table_service("Config", org_context)
        row_key = f"integration:{integration_type}"

        try:
            config_service.delete_entity(org_id, row_key)
            logger.info(f"Deleted {integration_type} integration for org {org_id}")
        except Exception as e:
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
