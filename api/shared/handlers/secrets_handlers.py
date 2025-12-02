"""Business logic handlers for secret management operations.

This module contains the core business logic for:
- Listing secrets from encrypted storage
- Creating new secrets
- Updating existing secrets
- Deleting secrets with dependency checking

All handlers are decoupled from HTTP concerns and can be tested independently.
"""

import logging
from typing import Any

from shared.keyvault import KeyVaultClient
from src.models.schemas import (
    SecretCreateRequest,
    SecretListResponse,
    SecretResponse,
    SecretUpdateRequest,
)
from shared.context import ExecutionContext, Organization
from shared.async_storage import get_async_table_service
from shared.validation import check_key_vault_available
from shared.system_logger import get_system_logger

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
    List available secrets from encrypted storage.

    Args:
        kv_manager: Initialized KeyVaultClient instance
        org_id: Optional org ID to filter secrets (returns org-scoped + GLOBAL)

    Returns:
        SecretListResponse with list of secret names and count

    Raises:
        SecretHandlerError: If secret storage is unavailable
    """
    # Check if Key Vault is available
    is_available, error_response = check_key_vault_available(kv_manager)
    if not is_available:
        raise SecretHandlerError("Key Vault is not available")

    assert kv_manager is not None, "kv_manager must be set when available"

    # List secrets with optional org filter
    secret_names = await kv_manager.list_secrets(org_id=org_id)

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
    Create a new secret in encrypted storage.

    Args:
        kv_manager: Initialized KeyVaultClient instance
        create_request: Request containing secretKey (direct name) and value
        user_id: User ID for audit logging

    Returns:
        SecretResponse with created secret details

    Raises:
        SecretHandlerError: If secret storage is unavailable
        SecretAlreadyExistsError: If secret already exists
    """
    # Check if Key Vault is available
    is_available, error_response = check_key_vault_available(kv_manager)
    if not is_available:
        raise SecretHandlerError("Key Vault is not available")

    assert kv_manager is not None, "kv_manager must be set when available"

    # Use secretKey directly as the Key Vault secret name
    secret_name = create_request.secretKey

    # Check if secret already exists
    try:
        existing_secrets = await kv_manager.list_secrets()
        if secret_name in existing_secrets:
            logger.warning(f"Secret {secret_name} already exists")
            raise SecretAlreadyExistsError(
                f"Secret '{secret_name}' already exists. Use PUT to update."
            )
    except SecretAlreadyExistsError:
        raise
    except Exception as e:
        logger.warning(f"Could not check for existing secret: {e}")

    # Create the secret using direct ref
    await kv_manager.set_secret(
        ref=secret_name,
        value=create_request.value,
    )

    # Build response
    response = SecretResponse(
        name=secret_name,
        orgId=create_request.orgId or "",
        secretKey=secret_name,
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

    # Log to system logger
    system_logger = get_system_logger()
    await system_logger.log_secret_event(
        action="set",
        key=secret_name,
        scope=create_request.orgId or "GLOBAL",
        executed_by=user_id,
        executed_by_name=user_id
    )

    return response


async def handle_update_secret(
    kv_manager: KeyVaultClient | None,
    secret_name: str,
    update_request: SecretUpdateRequest,
    user_id: str,
) -> SecretResponse:
    """
    Update an existing secret in encrypted storage.

    Always creates a new version - never reuses the same ref.

    Args:
        kv_manager: Initialized KeyVaultClient instance
        secret_name: Secret ref/name to update
        update_request: Request containing new value
        user_id: User ID for audit logging

    Returns:
        SecretResponse with updated secret details

    Raises:
        SecretHandlerError: If secret storage is unavailable
        SecretNotFoundError: If secret does not exist
    """
    # Check if Key Vault is available
    is_available, error_response = check_key_vault_available(kv_manager)
    if not is_available:
        raise SecretHandlerError("Key Vault is not available")

    assert kv_manager is not None, "kv_manager must be set when available"

    # Update the secret (creates new version)
    try:
        await kv_manager.set_secret(
            ref=secret_name,
            value=update_request.value
        )
    except Exception as e:
        if "not found" in str(e).lower():
            raise SecretNotFoundError(f"Secret '{secret_name}' not found")
        raise

    # Build response
    response = SecretResponse(
        name=secret_name,
        orgId="",  # No org parsing
        secretKey=secret_name,
        value=update_request.value,  # Show value immediately after update
        message="Secret updated successfully",
    )

    logger.info(
        f"Updated secret {secret_name}",
        extra={
            "secret_name": secret_name,
            "updated_by": user_id,
        },
    )

    # Log to system logger
    system_logger = get_system_logger()
    await system_logger.log_secret_event(
        action="set",
        key=secret_name,
        scope="",  # No scope parsing
        executed_by=user_id,
        executed_by_name=user_id
    )

    return response


async def _find_secret_dependencies(
    context: ExecutionContext, secret_name: str, org_id: str
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
            global_context = ExecutionContext(
                user_id=context.user_id,
                email=context.email,
                name=context.name,
                scope="GLOBAL",
                organization=None,
                is_platform_admin=context.is_platform_admin,
                is_function_key=context.is_function_key,
                execution_id=context.execution_id,
            )
            config_service = get_async_table_service("Config", global_context)
            global_configs = await config_service.query_entities(
                filter="RowKey ge 'config:' and RowKey lt 'config;'"
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
                org_context = ExecutionContext(
                    user_id=context.user_id,
                    email=context.email,
                    name=context.name,
                    scope=org_id,
                    organization=Organization(id=org_id, name=""),
                    is_platform_admin=context.is_platform_admin,
                    is_function_key=context.is_function_key,
                    execution_id=context.execution_id,
                )
                config_service = get_async_table_service("Config", org_context)
                org_configs = await config_service.query_entities(
                    filter="RowKey ge 'config:' and RowKey lt 'config;'"
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
    context: ExecutionContext,
    user_id: str,
) -> SecretResponse:
    """
    Delete a secret from encrypted storage.

    Performs dependency checking to prevent deletion of secrets referenced in configs.

    Args:
        kv_manager: Initialized KeyVaultClient instance
        secret_name: Secret ref/name to delete
        context: Request context for platform admin operations
        user_id: User ID for audit logging

    Returns:
        SecretResponse with deletion confirmation

    Raises:
        SecretHandlerError: If secret storage is unavailable
        SecretNotFoundError: If secret does not exist
        SecretHasDependenciesError: If secret is referenced in configs
    """
    # Check if Key Vault is available
    is_available, error_response = check_key_vault_available(kv_manager)
    if not is_available:
        raise SecretHandlerError("Key Vault is not available")

    assert kv_manager is not None, "kv_manager must be set when available"

    # Check for dependencies (search for this exact secret name in configs/oauth)
    dependencies = await _find_secret_dependencies(context, secret_name, "")

    if dependencies:
        dep_list = [f"Config: {dep['key']} ({dep['scope']})" for dep in dependencies]

        error_message = (
            f"Cannot delete secret '{secret_name}' because it is referenced by the following:\n"
            + "\n".join(dep_list)
            + "\n\nPlease remove all references before deleting this secret."
        )

        # Log error to system logger
        system_logger = get_system_logger()
        await system_logger.log(
            category="secret",
            level="error",
            message=f"Cannot delete secret '{secret_name}': has dependencies",
            executed_by=user_id,
            details={"secret_name": secret_name, "dependencies": dependencies}
        )

        raise SecretHasDependenciesError(error_message, dependencies)

    # Delete the secret
    try:
        await kv_manager.delete_secret(ref=secret_name)
    except Exception as e:
        if "not found" in str(e).lower():
            raise SecretNotFoundError(f"Secret '{secret_name}' not found")
        raise

    # Build response
    response = SecretResponse(
        name=secret_name,
        orgId="",  # No org parsing
        secretKey=secret_name,
        value=None,  # Never show value after deletion
        message="Secret deleted successfully",
    )

    logger.info(
        f"Deleted secret {secret_name}",
        extra={
            "secret_name": secret_name,
            "deleted_by": user_id,
        },
    )

    # Log to system logger
    system_logger = get_system_logger()
    await system_logger.log_secret_event(
        action="delete",
        key=secret_name,
        scope="",  # No scope parsing
        executed_by=user_id,
        executed_by_name=user_id
    )

    return response
