"""
Configuration SDK for Bifrost.

Provides Python API for configuration management (get, set, list, delete).
"""

from __future__ import annotations

from typing import Any

from shared.repositories.config import ConfigRepository

from ._internal import get_context


class config:
    """
    Configuration management operations.

    Allows workflows to read and write configuration values scoped to organizations.
    """

    @staticmethod
    def get(key: str, org_id: str | None = None, default: Any = None) -> Any:
        """
        Get configuration value.

        Args:
            key: Configuration key
            org_id: Organization ID (defaults to current org from context)
            default: Default value if key not found (optional)

        Returns:
            Any: Configuration value, or default if not found

        Raises:
            RuntimeError: If no execution context

        Example:
            >>> from bifrost import config
            >>> api_url = config.get("api_url", default="https://api.example.com")
            >>> # Get config for specific org
            >>> other_url = config.get("api_url", org_id="other-org")
        """
        context = get_context()
        target_org = org_id or context.org_id

        repo = ConfigRepository(context)

        # Get config using the repository's actual method
        # Note: Repository is already scoped to target_org via context
        config = repo.get_config(key, fallback_to_global=True)

        if config:
            return config.value

        return default

    @staticmethod
    def set(key: str, value: Any, org_id: str | None = None) -> None:
        """
        Set configuration value.

        Args:
            key: Configuration key
            value: Configuration value (must be JSON-serializable)
            org_id: Organization ID (defaults to current org from context)

        Raises:
            RuntimeError: If no execution context
            ValueError: If value is not JSON-serializable

        Example:
            >>> from bifrost import config
            >>> config.set("api_url", "https://api.example.com")
            >>> # Set config for specific org
            >>> config.set("api_url", "https://other.example.com", org_id="other-org")
        """
        context = get_context()
        target_org = org_id or context.org_id

        repo = ConfigRepository(context)

        # Convert value to string for storage
        # ConfigRepository expects ConfigType, default to string
        from shared.models import ConfigType
        import json

        # Handle different value types
        if isinstance(value, (dict, list)):
            config_type = ConfigType.json
            str_value = json.dumps(value)
        elif isinstance(value, bool):
            config_type = ConfigType.bool
            str_value = str(value).lower()
        elif isinstance(value, int):
            config_type = ConfigType.int
            str_value = str(value)
        else:
            config_type = ConfigType.string
            str_value = str(value)

        repo.set_config(
            key=key,
            value=str_value,
            config_type=config_type,
            updated_by=context.user_id
        )

    @staticmethod
    def list(org_id: str | None = None) -> dict[str, Any]:
        """
        List all configuration key-value pairs.

        Args:
            org_id: Organization ID (defaults to current org from context)

        Returns:
            dict: Configuration key-value pairs

        Raises:
            RuntimeError: If no execution context

        Example:
            >>> from bifrost import config
            >>> all_config = config.list()
            >>> for key, value in all_config.items():
            ...     print(f"{key}: {value}")
        """
        context = get_context()
        target_org = org_id or context.org_id

        repo = ConfigRepository(context)

        # list_config returns list of Config models
        configs = repo.list_config(include_global=True)

        # Convert to dict[str, Any] as advertised in docstring
        config_dict = {}
        for config in configs:
            # Parse value based on type
            if config.type == "json":
                import json
                try:
                    config_dict[config.key] = json.loads(config.value)
                except (json.JSONDecodeError, TypeError):
                    config_dict[config.key] = config.value
            elif config.type == "bool":
                config_dict[config.key] = config.value.lower() == "true"
            elif config.type == "int":
                try:
                    config_dict[config.key] = int(config.value)
                except (ValueError, TypeError):
                    config_dict[config.key] = config.value
            else:
                config_dict[config.key] = config.value

        return config_dict

    @staticmethod
    def delete(key: str, org_id: str | None = None) -> bool:
        """
        Delete configuration value.

        Args:
            key: Configuration key
            org_id: Organization ID (defaults to current org from context)

        Returns:
            bool: True if deleted, False if not found

        Raises:
            RuntimeError: If no execution context

        Example:
            >>> from bifrost import config
            >>> config.delete("old_api_url")
        """
        context = get_context()
        target_org = org_id or context.org_id

        repo = ConfigRepository(context)
        return repo.delete_config(key)
