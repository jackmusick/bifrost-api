"""
Organization Configuration Handlers
Business logic for config and integration management
Extracted from functions/org_config.py for unit testability
"""

import json
import logging

import azure.functions as func
from pydantic import ValidationError

from shared.models import (
    ErrorResponse,
    SetConfigRequest,
    SetIntegrationConfigRequest,
)
from shared.repositories.config import ConfigRepository
from shared.keyvault import KeyVaultClient
from shared.secret_naming import (
    generate_secret_name,
    SecretNameTooLongError,
    InvalidSecretComponentError,
)
from shared.system_logger import get_system_logger

logger = logging.getLogger(__name__)


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


async def get_config_handler(req: func.HttpRequest) -> func.HttpResponse:
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
        configs = await config_repo.list_config(include_global=False)  # Only get configs for current scope

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


async def set_config_handler(req: func.HttpRequest) -> func.HttpResponse:
    """
    POST /api/config
    Set a configuration key-value pair for current scope

    Request body includes 'scope' field to determine GLOBAL vs org-specific
    Scope is determined by:
    - If scope='GLOBAL' in request body: Save to GLOBAL partition
    - If scope='org' in request body: Save to context.scope (from X-Organization-Id header)

    Special handling for secret_ref type:
    - If value is a secret reference (existing secret name), store it as-is
    - If value is NOT a secret reference, treat it as the actual secret value:
      1. Generate a unique secret name: bifrost_{scope}_{config_key}_{uuid}
      2. Store the secret value in Key Vault
      3. Store the generated secret name as the config value

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
        existing_config = await config_repo.get_config(set_request.key, fallback_to_global=False)
        status_code = 200 if existing_config else 201

        # Handle secret_ref type with explicit value vs secretRef
        config_value = set_request.value
        if set_request.type.value == "secret_ref":
            # Check which field is provided
            if set_request.value:
                # Value provided - create or update secret in Key Vault
                try:
                    keyvault = KeyVaultClient()
                    if keyvault._client is None:
                        raise ValueError("Key Vault client not initialized - cannot create inline secret")

                    # Check if we're updating an existing config with a secret
                    if existing_config and existing_config.type.value == "secret_ref":
                        # Updating existing secret - reuse the same secret name (creates new version)
                        secret_name = existing_config.value
                        logger.info(f"Updating existing secret '{secret_name}' for config key '{set_request.key}'")
                    else:
                        # Creating new secret - generate unique name
                        secret_name = generate_secret_name(
                            scope=context.scope,
                            name_component=set_request.key
                        )
                        logger.info(f"Creating new secret for config key '{set_request.key}'")

                    # Store/update secret in Key Vault (creates new version if secret exists)
                    await keyvault._client.set_secret(secret_name, set_request.value)
                    logger.info(f"Stored secret in Key Vault: {secret_name}")

                    # Use the secret name as the config value
                    config_value = secret_name

                except SecretNameTooLongError as e:
                    logger.error(f"Generated secret name too long: {e}")
                    error = ErrorResponse(
                        error="ValidationError",
                        message=str(e),
                        details={"key": set_request.key, "scope": context.scope}
                    )
                    return func.HttpResponse(
                        json.dumps(error.model_dump()),
                        status_code=400,
                        mimetype="application/json"
                    )

                except InvalidSecretComponentError as e:
                    logger.error(f"Invalid secret component: {e}")
                    error = ErrorResponse(
                        error="ValidationError",
                        message=str(e),
                        details={"key": set_request.key, "scope": context.scope}
                    )
                    return func.HttpResponse(
                        json.dumps(error.model_dump()),
                        status_code=400,
                        mimetype="application/json"
                    )

                except ValueError as e:
                    logger.error(f"Key Vault not available: {e}")
                    error = ErrorResponse(
                        error="ServiceUnavailable",
                        message="Key Vault is not available - cannot create inline secret"
                    )
                    return func.HttpResponse(
                        json.dumps(error.model_dump()),
                        status_code=503,
                        mimetype="application/json"
                    )

                except Exception as e:
                    logger.error(f"Failed to create secret in Key Vault: {e}", exc_info=True)
                    error = ErrorResponse(
                        error="InternalServerError",
                        message="Failed to create secret in Key Vault"
                    )
                    return func.HttpResponse(
                        json.dumps(error.model_dump()),
                        status_code=500,
                        mimetype="application/json"
                    )
            else:
                # secretRef provided - use it directly
                config_value = set_request.secretRef
                logger.info(f"Using existing secret reference '{config_value}' for config key '{set_request.key}'")

        # Ensure config_value is set
        if config_value is None:
            raise ValueError("Either 'value' or 'secretRef' must be provided")

        # Set config using repository
        config = await config_repo.set_config(
            key=set_request.key,
            value=config_value,  # Use potentially modified value (secret name)
            config_type=set_request.type,
            description=set_request.description,
            updated_by=context.user_id
        )

        # Mask sensitive values in response
        config.value = mask_sensitive_value(
            set_request.key,
            config_value or "",
            set_request.type.value
        )

        logger.info(
            f"{'Updated' if existing_config else 'Created'} config key '{set_request.key}' "
            f"in scope={context.scope}"
        )

        # Log to system logger
        system_logger = get_system_logger()
        await system_logger.log_config_event(
            action="set",
            key=set_request.key,
            scope=context.scope,
            executed_by=context.user_id,
            executed_by_name=context.name or context.user_id
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


async def delete_config_handler(req: func.HttpRequest) -> func.HttpResponse:
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
        await config_repo.delete_config(key)
        logger.info(f"Deleted config key '{key}' (scope={context.scope})")

        # Log to system logger
        system_logger = get_system_logger()
        await system_logger.log_config_event(
            action="delete",
            key=key,
            scope=context.scope,
            executed_by=context.user_id,
            executed_by_name=context.name or context.user_id
        )

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


async def get_integrations_handler(req: func.HttpRequest) -> func.HttpResponse:
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
        integrations = await config_repo.list_integrations()

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


async def set_integration_handler(req: func.HttpRequest) -> func.HttpResponse:
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
        existing_integration = await config_repo.get_integration_config(set_request.type, fallback_to_global=False)
        status_code = 200 if existing_integration else 201

        # Set integration using repository
        integration = await config_repo.set_integration_config(
            request=set_request,
            updated_by=context.user_id
        )

        logger.info(
            f"{'Updated' if existing_integration else 'Created'} {set_request.type.value} integration for org {org_id}"
        )

        # Log to system logger
        system_logger = get_system_logger()
        await system_logger.log_config_event(
            action="set",
            key=set_request.type.value,
            config_type="integration",
            scope=context.scope,
            executed_by=context.user_id,
            executed_by_name=context.name or context.user_id
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


async def delete_integration_handler(req: func.HttpRequest) -> func.HttpResponse:
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
    assert integration_type is not None, "type is required"

    logger.info(f"User {context.user_id} deleting {integration_type} integration for org {org_id}")

    try:
        # Delete integration using repository (idempotent - no error if doesn't exist)
        config_repo = ConfigRepository(context)
        await config_repo.delete_integration(integration_type)  # Pass string directly - repository handles it
        logger.info(f"Deleted {integration_type} integration for org {org_id}")

        # Log to system logger
        system_logger = get_system_logger()
        await system_logger.log_config_event(
            action="delete",
            key=integration_type,
            config_type="integration",
            scope=context.scope,
            executed_by=context.user_id,
            executed_by_name=context.name or context.user_id
        )

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
