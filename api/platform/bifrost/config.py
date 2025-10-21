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

        repo = ConfigRepository()
        value = repo.get_config_value(key, target_org)

        return value if value is not None else default

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

        repo = ConfigRepository()
        repo.set_config_value(
            key=key,
            value=value,
            org_id=target_org,
            set_by=context.user_id
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

        repo = ConfigRepository()
        configs = repo.list_config(target_org)

        return configs

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

        repo = ConfigRepository()
        return repo.delete_config(key, target_org)
