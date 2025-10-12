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

from shared.auth import require_auth, is_platform_admin
from shared.storage import TableStorageService
from shared.models import (
    Config,
    SetConfigRequest,
    IntegrationConfig,
    SetIntegrationConfigRequest,
    IntegrationType,
    ErrorResponse
)
from pydantic import ValidationError

logger = logging.getLogger(__name__)

# Create blueprint for config endpoints
bp = func.Blueprint()


def get_config_value(key: str, org_id: Optional[str] = None) -> Optional[dict]:
    """
    Get config value with fallback pattern: org-specific → GLOBAL → None

    Args:
        key: Config key to lookup
        org_id: Organization ID (optional, will only check GLOBAL if None)

    Returns:
        Config entity dict or None if not found
    """
    config_service = TableStorageService("Config")
    row_key = f"config:{key}"

    # Try org-specific first (if org_id provided)
    if org_id:
        try:
            org_config = config_service.get_entity(org_id, row_key)
            if org_config:
                logger.debug(f"Found org-specific config for key '{key}' in org {org_id}")
                return org_config
        except:
            pass  # Not found in org, will try GLOBAL

    # Fallback to GLOBAL
    try:
        global_config = config_service.get_entity("GLOBAL", row_key)
        if global_config:
            logger.debug(f"Found GLOBAL config for key '{key}'")
            return global_config
    except:
        pass  # Not found

    logger.debug(f"Config key '{key}' not found (checked: {'org + GLOBAL' if org_id else 'GLOBAL only'})")
    return None


def mask_sensitive_value(key: str, value: str) -> str:
    """Mask sensitive config values for API responses"""
    sensitive_keywords = ['secret', 'password', 'token', 'key', 'credential']
    if any(keyword in key.lower() for keyword in sensitive_keywords):
        if len(value) > 8:
            return value[:4] + '***' + value[-4:]
        return '***'
    return value


@bp.function_name("config_get_config")
@bp.route(route="config", methods=["GET"])
@require_auth
def get_config(req: func.HttpRequest) -> func.HttpResponse:
    """
    GET /api/config?scope=global|org&orgId={id}
    Get configuration with scope filtering

    Query params:
        scope: 'global' for GLOBAL configs only, 'org' for org-specific (requires orgId)
        orgId: Organization ID (required when scope=org)

    Requires: User must be authenticated (MSP users can access all, ORG users need org access)
    """
    user = req.user
    scope = req.params.get("scope", "global").lower()
    org_id = req.params.get("orgId")

    logger.info(f"User {user.email} retrieving config with scope={scope}, orgId={org_id}")

    try:
        # Validate scope parameter
        if scope not in ["global", "org"]:
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
        if scope == "org" and not org_id:
            error = ErrorResponse(
                error="BadRequest",
                message="orgId parameter is required when scope=org"
            )
            return func.HttpResponse(
                json.dumps(error.model_dump()),
                status_code=400,
                mimetype="application/json"
            )

        # Query Config table based on scope
        # Note: Access control handled by SWA rules - only PlatformAdmins can reach this endpoint
        config_service = TableStorageService("Config")
        partition_key = "GLOBAL" if scope == "global" else org_id
        config_entities = list(config_service.query_by_org(partition_key, row_key_prefix="config:"))

        # Convert to response models
        configs = []
        for entity in config_entities:
            # Extract key from RowKey (remove "config:" prefix)
            key = entity["RowKey"].replace("config:", "", 1)

            # Mask sensitive values
            value = mask_sensitive_value(key, entity["Value"])

            config = Config(
                key=key,
                value=value,
                type=entity["Type"],
                scope=scope,
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
@require_auth
def set_config(req: func.HttpRequest) -> func.HttpResponse:
    """
    POST /api/config
    Set a configuration key-value pair (global or org-specific)

    Request body includes 'scope' field to determine GLOBAL vs org-specific
    If scope=org, orgId query parameter is required

    Requires: User must have canManageConfig permission (for org configs)
    """
    user = req.user
    org_id = req.params.get("orgId")

    logger.info(f"User {user.email} setting config (orgId={org_id})")

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

            # Access control handled by SWA rules - only PlatformAdmins can reach this endpoint
            partition_key = org_id
        else:
            # GLOBAL config - only PlatformAdmins can set (enforced by SWA rules)
            partition_key = "GLOBAL"

        # Check if this is a new config or update
        config_service = TableStorageService("Config")
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
            "UpdatedBy": user.user_id
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
            updatedBy=user.user_id
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
@require_auth
def delete_config(req: func.HttpRequest) -> func.HttpResponse:
    """
    DELETE /api/config/{key}?scope=global|org&orgId={id}
    Delete a configuration key

    Query params:
        scope: 'global' or 'org'
        orgId: Required when scope=org

    Requires: User must have canManageConfig permission (for org configs)
    """
    user = req.user
    key = req.route_params.get("key")
    scope = req.params.get("scope", "global").lower()
    org_id = req.params.get("orgId")

    logger.info(f"User {user.email} deleting config key '{key}' (scope={scope}, orgId={org_id})")

    try:
        # Validate scope
        if scope not in ["global", "org"]:
            error = ErrorResponse(
                error="BadRequest",
                message="scope parameter must be 'global' or 'org'"
            )
            return func.HttpResponse(
                json.dumps(error.model_dump()),
                status_code=400,
                mimetype="application/json"
            )

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

            # Access control handled by SWA rules - only PlatformAdmins can reach this endpoint
            partition_key = org_id
        else:
            # GLOBAL config - only PlatformAdmins can delete (enforced by SWA rules)
            partition_key = "GLOBAL"

        # Delete config (idempotent - no error if key doesn't exist)
        config_service = TableStorageService("Config")
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
@require_auth
def get_integrations(req: func.HttpRequest) -> func.HttpResponse:
    """
    GET /api/organizations/{orgId}/integrations
    Get all integration configurations for an organization

    Requires: User must have permission to view history (canViewHistory)
    """
    user = req.user
    org_id = req.route_params.get("orgId")

    logger.info(f"User {user.email} retrieving integrations for org {org_id}")

    try:
        # Access control handled by SWA rules - only PlatformAdmins can reach this endpoint

        # Query IntegrationConfig table for this org
        integration_service = TableStorageService("IntegrationConfig")
        integration_entities = list(integration_service.query_by_org(org_id, row_key_prefix="integration:"))

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
@require_auth
def set_integration(req: func.HttpRequest) -> func.HttpResponse:
    """
    POST /api/organizations/{orgId}/integrations
    Create or update an integration configuration

    Requires: User must have permission to manage config (canManageConfig)
    """
    user = req.user
    org_id = req.route_params.get("orgId")

    logger.info(f"User {user.email} setting integration for org {org_id}")

    try:
        # Access control handled by SWA rules - only PlatformAdmins can reach this endpoint

        # Parse and validate request body
        request_body = req.get_json()
        set_request = SetIntegrationConfigRequest(**request_body)

        # Check if this is a new integration or update
        integration_service = TableStorageService("IntegrationConfig")
        row_key = f"integration:{set_request.type.value}"

        existing_integration = None
        try:
            existing_integration = integration_service.get_entity(org_id, row_key)
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
            "UpdatedBy": user.user_id
        }

        # Insert or update
        if existing_integration:
            # Update existing integration
            integration_service.update_entity(entity)
            status_code = 200
            logger.info(f"Updated {set_request.type.value} integration for org {org_id}")
        else:
            # Create new integration
            integration_service.insert_entity(entity)
            status_code = 201
            logger.info(f"Created {set_request.type.value} integration for org {org_id}")

        # Create response model
        integration = IntegrationConfig(
            type=set_request.type,
            enabled=set_request.enabled,
            settings=set_request.settings,
            updatedAt=now,
            updatedBy=user.user_id
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
@require_auth
def delete_integration(req: func.HttpRequest) -> func.HttpResponse:
    """
    DELETE /api/organizations/{orgId}/integrations/{type}
    Delete an integration configuration

    Requires: User must have permission to manage config (canManageConfig)
    Note: This only deletes the config reference, NOT the Key Vault secrets
    """
    user = req.user
    org_id = req.route_params.get("orgId")
    integration_type = req.route_params.get("type")

    logger.info(f"User {user.email} deleting {integration_type} integration for org {org_id}")

    try:
        # Access control handled by SWA rules - only PlatformAdmins can reach this endpoint

        # Delete integration (idempotent - no error if doesn't exist)
        integration_service = TableStorageService("IntegrationConfig")
        row_key = f"integration:{integration_type}"

        try:
            integration_service.delete_entity(org_id, row_key)
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
