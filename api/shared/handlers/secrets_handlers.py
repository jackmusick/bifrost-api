"""Business logic handlers for secret management operations.

This module contains the core business logic for:
- Listing secrets from Key Vault
- Creating new secrets
- Updating existing secrets
- Deleting secrets with dependency checking

All handlers are decoupled from HTTP concerns and can be tested independently.
"""

import logging
from typing import Any

from shared.keyvault import KeyVaultClient
from shared.models import (
    SecretCreateRequest,
    SecretListResponse,
    SecretResponse,
    SecretUpdateRequest,
)
from shared.request_context import RequestContext
from shared.storage import get_table_service
from shared.validation import check_key_vault_available

logger = logging.getLogger(__name__)


class SecretHandlerError(Exception):
    """Base exception for secret handler errors."""

    pass


class SecretNotFoundError(SecretHandlerError):
    """Raised when a secret is not found."""

    pass


class SecretAlreadyExistsError(SecretHandlerError):
    """Raised when attempting to create a secret that already exists."""

    pass


class SecretHasDependenciesError(SecretHandlerError):
    """Raised when attempting to delete a secret that has dependencies."""

    def __init__(self, message: str, dependencies: list[dict[str, Any]] | None = None):
        super().__init__(message)
        self.dependencies = dependencies or []


async def handle_list_secrets(
    kv_manager: KeyVaultClient | None, org_id: str | None = None
) -> SecretListResponse:
    """
    List available secrets from Key Vault.

    Args:
        kv_manager: Initialized KeyVaultClient instance
        org_id: Optional org ID to filter secrets (returns org-scoped + GLOBAL)

    Returns:
        SecretListResponse with list of secret names and count

    Raises:
        SecretHandlerError: If Key Vault is unavailable
    """
    # Check if Key Vault is available
    is_available, error_response = check_key_vault_available(kv_manager)
    if not is_available:
        raise SecretHandlerError("Key Vault is not available")

    assert kv_manager is not None, "kv_manager must be set when available"

    # List secrets with optional org filter
    secret_names = kv_manager.list_secrets(org_id=org_id)

    # Build response
    response = SecretListResponse(
        secrets=secret_names,
        orgId=org_id,
        count=len(secret_names),
    )

    logger.info(
        f"Listed {len(secret_names)} secrets"
        + (f" for org {org_id}" if org_id else ""),
        extra={"org_id": org_id, "secret_count": len(secret_names)},
    )

    return response


async def handle_create_secret(
    kv_manager: KeyVaultClient | None,
    create_request: SecretCreateRequest,
    user_id: str,
) -> SecretResponse:
    """
    Create a new secret in Azure Key Vault.

    Args:
        kv_manager: Initialized KeyVaultClient instance
        create_request: Request containing org_id, secret_key, and value
        user_id: User ID for audit logging

    Returns:
        SecretResponse with created secret details

    Raises:
        SecretHandlerError: If Key Vault is unavailable
        SecretAlreadyExistsError: If secret already exists
    """
    # Check if Key Vault is available
    is_available, error_response = check_key_vault_available(kv_manager)
    if not is_available:
        raise SecretHandlerError("Key Vault is not available")

    assert kv_manager is not None, "kv_manager must be set when available"

    # Build secret name
    secret_name = f"{create_request.orgId}--{create_request.secretKey}"

    # Check if secret already exists
    try:
        existing_secrets = kv_manager.list_secrets()
        if secret_name in existing_secrets:
            logger.warning(f"Secret {secret_name} already exists")
            raise SecretAlreadyExistsError(
                f"Secret '{secret_name}' already exists. Use PUT to update."
            )
    except SecretAlreadyExistsError:
        raise
    except Exception as e:
        logger.warning(f"Could not check for existing secret: {e}")

    # Create the secret
    kv_manager.create_secret(
        org_id=create_request.orgId,
        secret_key=create_request.secretKey,
        value=create_request.value,
    )

    # Build response
    response = SecretResponse(
        name=secret_name,
        orgId=create_request.orgId,
        secretKey=create_request.secretKey,
        value=create_request.value,  # Show value immediately after creation
        message="Secret created successfully",
    )

    logger.info(
        f"Created secret {secret_name}",
        extra={
            "secret_name": secret_name,
            "org_id": create_request.orgId,
            "created_by": user_id,
        },
    )

    return response


async def handle_update_secret(
    kv_manager: KeyVaultClient | None,
    secret_name: str,
    update_request: SecretUpdateRequest,
    user_id: str,
) -> SecretResponse:
    """
    Update an existing secret in Azure Key Vault.

    Args:
        kv_manager: Initialized KeyVaultClient instance
        secret_name: Full secret name (e.g., 'org-123--api-key')
        update_request: Request containing new value
        user_id: User ID for audit logging

    Returns:
        SecretResponse with updated secret details

    Raises:
        SecretHandlerError: If Key Vault is unavailable or name format invalid
        SecretNotFoundError: If secret does not exist
    """
    # Check if Key Vault is available
    is_available, error_response = check_key_vault_available(kv_manager)
    if not is_available:
        raise SecretHandlerError("Key Vault is not available")

    assert kv_manager is not None, "kv_manager must be set when available"

    # Validate secret name format
    if not secret_name or "--" not in secret_name:
        raise SecretHandlerError(
            "Invalid secret name format. Expected: 'org-id--secret-key' or 'GLOBAL--secret-key'"
        )

    # Parse org_id and secret_key from name
    parts = secret_name.split("--", 1)
    org_id = parts[0]
    secret_key = parts[1]

    # Update the secret
    try:
        kv_manager.update_secret(
            org_id=org_id, secret_key=secret_key, value=update_request.value
        )
    except Exception as e:
        if "not found" in str(e).lower():
            raise SecretNotFoundError(f"Secret '{secret_name}' not found")
        raise

    # Build response
    response = SecretResponse(
        name=secret_name,
        orgId=org_id,
        secretKey=secret_key,
        value=update_request.value,  # Show value immediately after update
        message="Secret updated successfully",
    )

    logger.info(
        f"Updated secret {secret_name}",
        extra={
            "secret_name": secret_name,
            "org_id": org_id,
            "updated_by": user_id,
        },
    )

    return response


def _find_secret_dependencies(
    context: RequestContext, secret_name: str, org_id: str
) -> list[dict[str, Any]]:
    """
    Find all dependencies (config references) to a secret.

    Args:
        context: Request context for platform admin operations
        secret_name: Full secret name to search for
        org_id: Organization ID of the secret

    Returns:
        List of dependency dicts with type, key, and scope
    """
    dependencies: list[dict[str, Any]] = []

    try:
        # Check GLOBAL configs
        try:
            global_context = RequestContext(
                user_id=context.user_id,
                email=context.email,
                name=context.name,
                org_id="GLOBAL",
                is_platform_admin=context.is_platform_admin,
                is_function_key=context.is_function_key,
            )
            config_service = get_table_service("Config", global_context)
            global_configs = list(
                config_service.query_entities(
                    filter="RowKey ge 'config:' and RowKey lt 'config;'"
                )
            )
            for config in global_configs:
                if (
                    config.get("Type") == "SECRET_REF"
                    and config.get("Value") == secret_name
                ):
                    config_key = config.get("RowKey", "").replace("config:", "", 1)
                    dependencies.append(
                        {
                            "type": "config",
                            "key": config_key,
                            "scope": "GLOBAL",
                        }
                    )
        except Exception as e:
            logger.debug(f"Could not check GLOBAL configs: {e}")

        # Check org-specific configs if the secret is org-scoped
        if org_id != "GLOBAL":
            try:
                org_context = RequestContext(
                    user_id=context.user_id,
                    email=context.email,
                    name=context.name,
                    org_id=org_id,
                    is_platform_admin=context.is_platform_admin,
                    is_function_key=context.is_function_key,
                )
                config_service = get_table_service("Config", org_context)
                org_configs = list(
                    config_service.query_entities(
                        filter="RowKey ge 'config:' and RowKey lt 'config;'"
                    )
                )
                for config in org_configs:
                    if (
                        config.get("Type") == "SECRET_REF"
                        and config.get("Value") == secret_name
                    ):
                        config_key = config.get("RowKey", "").replace("config:", "", 1)
                        dependencies.append(
                            {
                                "type": "config",
                                "key": config_key,
                                "scope": org_id,
                            }
                        )
            except Exception as e:
                logger.debug(f"Could not check org configs for {org_id}: {e}")

    except Exception as e:
        logger.warning(f"Could not check for secret references: {e}")

    return dependencies


async def handle_delete_secret(
    kv_manager: KeyVaultClient | None,
    secret_name: str,
    context: RequestContext,
    user_id: str,
) -> SecretResponse:
    """
    Delete a secret from Azure Key Vault.

    Performs dependency checking to prevent deletion of secrets referenced in configs.

    Args:
        kv_manager: Initialized KeyVaultClient instance
        secret_name: Full secret name (e.g., 'org-123--api-key')
        context: Request context for platform admin operations
        user_id: User ID for audit logging

    Returns:
        SecretResponse with deletion confirmation

    Raises:
        SecretHandlerError: If Key Vault unavailable or name format invalid
        SecretNotFoundError: If secret does not exist
        SecretHasDependenciesError: If secret is referenced in configs
    """
    # Check if Key Vault is available
    is_available, error_response = check_key_vault_available(kv_manager)
    if not is_available:
        raise SecretHandlerError("Key Vault is not available")

    assert kv_manager is not None, "kv_manager must be set when available"

    # Validate secret name format
    if not secret_name or "--" not in secret_name:
        raise SecretHandlerError(
            "Invalid secret name format. Expected: 'org-id--secret-key' or 'GLOBAL--secret-key'"
        )

    # Parse org_id and secret_key from name
    parts = secret_name.split("--", 1)
    org_id = parts[0]
    secret_key = parts[1]

    # Check for dependencies
    dependencies = _find_secret_dependencies(context, secret_name, org_id)

    if dependencies:
        dep_list = [f"Config: {dep['key']} ({dep['scope']})" for dep in dependencies]

        error_message = (
            f"Cannot delete secret '{secret_name}' because it is referenced by the following:\n"
            + "\n".join(dep_list)
            + "\n\nPlease remove all references before deleting this secret."
        )

        raise SecretHasDependenciesError(error_message, dependencies)

    # Delete the secret
    try:
        kv_manager.delete_secret(org_id=org_id, secret_key=secret_key)
    except Exception as e:
        if "not found" in str(e).lower():
            raise SecretNotFoundError(f"Secret '{secret_name}' not found")
        raise

    # Build response
    response = SecretResponse(
        name=secret_name,
        orgId=org_id,
        secretKey=secret_key,
        value=None,  # Never show value after deletion
        message="Secret deleted successfully",
    )

    logger.info(
        f"Deleted secret {secret_name}",
        extra={
            "secret_name": secret_name,
            "org_id": org_id,
            "deleted_by": user_id,
        },
    )

    return response
