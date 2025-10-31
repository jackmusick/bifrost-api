"""
Configuration resolver with transparent secret reference resolution.

This module provides unified configuration access that automatically resolves
secret references from Azure Key Vault based on config type.
"""

import logging
from typing import Any

from .keyvault import KeyVaultClient
from .models import ConfigType

logger = logging.getLogger(__name__)


class ConfigResolver:
    """
    Resolves configuration values with transparent secret reference handling.

    Features:
    - Automatic config type detection (secret_ref vs plain values)
    - Transparent secret resolution from Key Vault
    - Org-scoped → global fallback for secrets
    - Local development fallback support
    - Audit logging for secret access (without logging values)
    """

    def __init__(self, keyvault_client: KeyVaultClient | None = None):
        """
        Initialize the configuration resolver.

        Args:
            keyvault_client: Optional KeyVaultClient instance
                           If None, will be created automatically
        """
        if keyvault_client:
            self.keyvault_client = keyvault_client
        else:
            try:
                self.keyvault_client = KeyVaultClient()
            except Exception as e:
                logger.warning(f"Failed to initialize KeyVaultClient: {e}. Secret references will not be available.")
                self.keyvault_client = None

    async def get_config(
        self,
        org_id: str,
        key: str,
        config_data: dict[str, Any],
        default: Any = ...,  # Sentinel value to distinguish None from "not provided"
    ) -> Any:
        """
        Get configuration value with transparent secret reference resolution.

        Logic:
        1. Check if key exists in config_data
        2. Determine config type (if available)
        3. If type is secret_ref, resolve from Key Vault
        4. Otherwise, return plain value
        5. If key not found, return default or raise KeyError

        Args:
            org_id: Organization identifier
            key: Configuration key
            config_data: Configuration dictionary (from Table Storage)
                        Expected format: {key: {"value": "...", "type": "secret_ref"}}
                        or {key: "plain_value"}
            default: Default value if key not found. If not provided, raises KeyError.

        Returns:
            Configuration value (with secret resolved if needed)

        Raises:
            KeyError: If key not found and no default provided, or if secret reference cannot be resolved
        """
        # Check if key exists
        if key not in config_data:
            if default is ...:  # No default provided
                raise KeyError(f"Configuration key '{key}' not found for org '{org_id}'")
            logger.debug(f"Config key not found: {key}, returning default")
            return default

        config_entry = config_data[key]

        # Handle simple string values (backwards compatibility)
        if isinstance(config_entry, str):
            logger.debug(f"Retrieved plain config value: {key}")
            return config_entry

        # Handle structured config entries
        if isinstance(config_entry, dict):
            config_type = config_entry.get("type")
            config_value = config_entry.get("value")

            # If type is secret_ref, resolve from Key Vault
            if config_type == ConfigType.SECRET_REF.value or config_type == "secret_ref":
                assert config_value is not None, f"secret_ref value is None for key '{key}'"
                return await self._resolve_secret_ref(org_id, key, config_value)

            # Otherwise return plain value
            logger.debug(f"Retrieved plain config value: {key} (type: {config_type})")
            assert config_value is not None, f"config value is None for key '{key}'"
            return self._parse_value(config_value, config_type)

        # Fallback: return value as-is
        logger.debug(f"Retrieved config value: {key}")
        return config_entry

    async def _resolve_secret_ref(self, org_id: str, config_key: str, secret_ref: str) -> str:
        """
        Resolve a secret reference from Key Vault.

        Args:
            org_id: Organization identifier
            config_key: Configuration key (for logging)
            secret_ref: Secret reference value (the secret key to look up)

        Returns:
            Secret value from Key Vault

        Raises:
            ValueError: If secret not found in Key Vault or local config, or if Key Vault client not available
        """
        # Check if Key Vault client is available
        if not self.keyvault_client:
            raise ValueError(
                f"Key Vault client not available for secret reference resolution. "
                f"Cannot resolve secret '{secret_ref}' for config '{config_key}'."
            )

        if not self.keyvault_client._client and not self.keyvault_client.vault_url:
            raise ValueError(
                f"Key Vault client not available for secret reference resolution. "
                f"Cannot resolve secret '{secret_ref}' for config '{config_key}'."
            )

        try:
            # Log access attempt (without value)
            logger.info(
                f"Resolving secret reference for config '{config_key}'",
                extra={
                    "org_id": org_id,
                    "config_key": config_key,
                    "secret_ref": secret_ref
                }
            )

            # Get secret from Key Vault (with org → global fallback)
            secret_value = await self.keyvault_client.get_secret(org_id, secret_ref)

            # Log successful resolution (without value)
            logger.info(
                f"Successfully resolved secret for config '{config_key}'",
                extra={
                    "org_id": org_id,
                    "config_key": config_key,
                    "secret_ref": secret_ref
                }
            )

            return secret_value

        except KeyError as e:
            # Log failure with actionable error message
            error_msg = (
                f"Secret reference not found for config '{config_key}': {secret_ref}. "
                f"Verify the secret exists in Key Vault or local configuration."
            )
            logger.error(error_msg, extra={
                "org_id": org_id,
                "config_key": config_key,
                "secret_ref": secret_ref
            })
            raise ValueError(error_msg) from e

    def _parse_value(self, value: str, config_type: str | None) -> Any:
        """
        Parse configuration value based on type.

        Args:
            value: String value from config
            config_type: Config type (string, int, bool, json, secret_ref)

        Returns:
            Parsed value in appropriate type

        Raises:
            ValueError: If value cannot be parsed for the specified type
        """
        import json

        try:
            if config_type == ConfigType.INT.value or config_type == "int":
                return int(value)
            elif config_type == ConfigType.BOOL.value or config_type == "bool":
                return value.lower() in ("true", "1", "yes")
            elif config_type == ConfigType.JSON.value or config_type == "json":
                return json.loads(value)
            else:
                # STRING or unknown type - return as string
                return value
        except (ValueError, TypeError, json.JSONDecodeError) as e:
            raise ValueError(f"Could not parse value '{value}' as type '{config_type}': {e}") from e
