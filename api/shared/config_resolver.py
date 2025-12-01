"""
Configuration resolver with transparent secret handling.

This module provides unified configuration access that automatically decrypts
secret values stored in the Config table.
"""

import logging
from typing import Any, TYPE_CHECKING

from .models import ConfigType

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class ConfigResolver:
    """
    Resolves configuration values with transparent secret handling.

    Features:
    - Automatic config type detection (secret vs plain values)
    - Transparent decryption for secret type configs
    - Type parsing for int, bool, json types
    """

    def __init__(self):
        """Initialize the configuration resolver."""
        pass

    async def get_config(
        self,
        org_id: str,
        key: str,
        config_data: dict[str, Any],
        default: Any = ...,  # Sentinel value to distinguish None from "not provided"
    ) -> Any:
        """
        Get configuration value with transparent secret decryption.

        Logic:
        1. Check if key exists in config_data
        2. Determine config type (if available)
        3. If type is secret, decrypt the value
        4. Otherwise, return/parse plain value
        5. If key not found, return default or raise KeyError

        Args:
            org_id: Organization identifier
            key: Configuration key
            config_data: Configuration dictionary
                        Expected format: {key: {"value": "...", "type": "secret"}}
                        or {key: "plain_value"}
            default: Default value if key not found. If not provided, raises KeyError.

        Returns:
            Configuration value (with secret decrypted if needed)

        Raises:
            KeyError: If key not found and no default provided
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

            if config_value is None:
                raise ValueError(f"Config value is None for key '{key}'")

            # If type is secret, decrypt the value
            if config_type == ConfigType.SECRET.value or config_type == "secret":
                return self._decrypt_secret(key, config_value)

            # Otherwise return parsed plain value
            logger.debug(f"Retrieved plain config value: {key} (type: {config_type})")
            return self._parse_value(config_value, config_type)

        # Fallback: return value as-is
        logger.debug(f"Retrieved config value: {key}")
        return config_entry

    def _decrypt_secret(self, config_key: str, encrypted_value: str) -> str:
        """
        Decrypt a secret value.

        Args:
            config_key: Configuration key (for logging)
            encrypted_value: The encrypted value to decrypt

        Returns:
            Decrypted secret value

        Raises:
            ValueError: If decryption fails
        """
        try:
            from src.core.security import decrypt_secret

            logger.debug(f"Decrypting secret for config '{config_key}'")
            return decrypt_secret(encrypted_value)

        except Exception as e:
            error_msg = f"Failed to decrypt secret for config '{config_key}': {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise ValueError(error_msg) from e

    def _parse_value(self, value: str, config_type: str | None) -> Any:
        """
        Parse configuration value based on type.

        Args:
            value: String value from config
            config_type: Config type (string, int, bool, json, secret)

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
