"""
Configuration resolver with transparent secret reference resolution.

This module provides unified configuration access that automatically resolves
secret references from Azure Key Vault based on config type.
"""

import logging
from typing import Any, Dict, Optional
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

    def __init__(self, keyvault_client: Optional[KeyVaultClient] = None):
        """
        Initialize the configuration resolver.

        Args:
            keyvault_client: Optional KeyVaultClient instance
                           If None, will be created automatically
        """
        self.keyvault_client = keyvault_client or KeyVaultClient()

    def get_config(
        self,
        org_id: str,
        key: str,
        config_data: Dict[str, Any],
        default: Any = None
    ) -> Any:
        """
        Get configuration value with transparent secret reference resolution.

        Logic:
        1. Check if key exists in config_data
        2. Determine config type (if available)
        3. If type is secret_ref, resolve from Key Vault
        4. Otherwise, return plain value
        5. If key not found, return default

        Args:
            org_id: Organization identifier
            key: Configuration key
            config_data: Configuration dictionary (from Table Storage)
                        Expected format: {key: {"value": "...", "type": "secret_ref"}}
                        or {key: "plain_value"}
            default: Default value if key not found

        Returns:
            Configuration value (with secret resolved if needed)

        Raises:
            KeyError: If secret reference cannot be resolved
        """
        # Check if key exists
        if key not in config_data:
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
                return self._resolve_secret_ref(org_id, key, config_value)

            # Otherwise return plain value
            logger.debug(f"Retrieved plain config value: {key} (type: {config_type})")
            return self._parse_value(config_value, config_type)

        # Fallback: return value as-is
        logger.debug(f"Retrieved config value: {key}")
        return config_entry

    def _resolve_secret_ref(self, org_id: str, config_key: str, secret_ref: str) -> str:
        """
        Resolve a secret reference from Key Vault.

        Args:
            org_id: Organization identifier
            config_key: Configuration key (for logging)
            secret_ref: Secret reference value (the secret key to look up)

        Returns:
            Secret value from Key Vault

        Raises:
            KeyError: If secret not found in Key Vault or local config
        """
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
            secret_value = self.keyvault_client.get_secret(org_id, secret_ref)

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
                f"Failed to resolve secret reference for config '{config_key}': {e}. "
                f"Secret '{secret_ref}' not found for org '{org_id}'. "
                f"Verify the secret exists in Key Vault or local configuration."
            )
            logger.error(error_msg, extra={
                "org_id": org_id,
                "config_key": config_key,
                "secret_ref": secret_ref
            })
            raise KeyError(error_msg)

    def _parse_value(self, value: str, config_type: Optional[str]) -> Any:
        """
        Parse configuration value based on type.

        Args:
            value: String value from config
            config_type: Config type (string, int, bool, json, secret_ref)

        Returns:
            Parsed value in appropriate type
        """
        if config_type == ConfigType.INT.value or config_type == "int":
            return int(value)
        elif config_type == ConfigType.BOOL.value or config_type == "bool":
            return value.lower() in ("true", "1", "yes")
        elif config_type == ConfigType.JSON.value or config_type == "json":
            import json
            return json.loads(value)
        else:
            # STRING or unknown type - return as string
            return value
