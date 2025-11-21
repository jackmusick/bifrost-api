"""
Configuration SDK for Bifrost.

Provides Python API for configuration management (get, set, list, delete).

All methods are async and must be called with await.
"""

from __future__ import annotations

from typing import Any

from shared.repositories.config import ConfigRepository

from ._internal import get_context


class config:
    """
    Configuration management operations.

    Allows workflows to read and write configuration values scoped to organizations.

    All methods are async and must be awaited.
    """

    @staticmethod
    async def get(key: str, org_id: str | None = None, default: Any = None) -> Any:
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

        repo = ConfigRepository(context)

        # Get config using the repository's actual method
        # Note: Repository is already scoped to target_org via context
        config = await repo.get_config(key, fallback_to_global=True)

        if config:
            return config.value

        return default

    @staticmethod
    async def set(key: str, value: Any, org_id: str | None = None) -> None:
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

        await repo.set_config(
            key=key,
            value=str_value,
            config_type=config_type,
            updated_by=context.user_id
        )

    @staticmethod
    async def list(org_id: str | None = None) -> dict[str, Any] | dict[str, dict[str, Any]]:
        """
        List configuration key-value pairs.

        Behavior depends on context and parameters:
        - If org_id is specified: Returns config for that specific org
        - If org_id is None and user is platform admin: Returns all configs across all orgs
        - If org_id is None and user is not admin: Returns config for current org

        Args:
            org_id: Organization ID (optional, defaults to all orgs for admins)

        Returns:
            - Single org: dict[str, Any] - Configuration key-value pairs
            - All orgs (admin): dict[str, dict[str, Any]] - Mapping of org_id to config dict

        Raises:
            RuntimeError: If no execution context

        Example:
            >>> from bifrost import config
            >>> # Get config for current/specific org
            >>> org_config = await config.list(org_id="org-123")
            >>> for key, value in org_config.items():
            ...     print(f"{key}: {value}")
            >>>
            >>> # Platform admin: get all orgs' config
            >>> all_configs = await config.list()
            >>> for org_id, org_config in all_configs.items():
            ...     print(f"Org {org_id}: {org_config}")
        """
        context = get_context()

        # If org_id specified or user is not platform admin, return single org config
        if org_id is not None or not context.is_platform_admin:
            return await config._list_single_org(context, org_id)

        # Platform admin with no org_id: return all orgs' config
        return await config._list_all_orgs(context)

    @staticmethod
    async def _list_single_org(context: Any, org_id: str | None = None) -> dict[str, Any]:
        """List config for a single organization."""
        # If org_id provided, create a context override for that org
        if org_id and org_id != context.org_id:
            # Use existing context but override target org
            from shared.context import ExecutionContext
            scoped_context = ExecutionContext(
                user_id=context.user_id,
                email=context.email,
                name=context.name,
                scope=org_id,
                organization=context.organization,
                is_platform_admin=context.is_platform_admin,
                is_function_key=context.is_function_key,
                execution_id=context.execution_id
            )
            repo = ConfigRepository(scoped_context)
        else:
            repo = ConfigRepository(context)

        # list_config returns list of Config models
        configs = await repo.list_config(include_global=True)

        return config._configs_to_dict(configs)

    @staticmethod
    async def _list_all_orgs(context: Any) -> dict[str, dict[str, Any]]:
        """List config for all organizations (platform admin only)."""
        from shared.handlers.organizations_handlers import list_organizations_logic
        from shared.context import ExecutionContext, Organization as ContextOrganization

        # Get all organizations
        orgs = await list_organizations_logic(context)

        result: dict[str, dict[str, Any]] = {}

        for org in orgs:
            # Convert model Organization to context Organization
            ctx_org = ContextOrganization(
                id=org.id,
                name=org.name,
                is_active=org.isActive
            )
            # Create context scoped to this org
            scoped_context = ExecutionContext(
                user_id=context.user_id,
                email=context.email,
                name=context.name,
                scope=org.id,
                organization=ctx_org,
                is_platform_admin=context.is_platform_admin,
                is_function_key=context.is_function_key,
                execution_id=context.execution_id
            )
            repo = ConfigRepository(scoped_context)

            # Get configs for this org
            configs = await repo.list_config(include_global=False)  # Don't include GLOBAL in each org
            result[org.id] = config._configs_to_dict(configs)

        # Also include GLOBAL configs under "GLOBAL" key
        global_context = ExecutionContext(
            user_id=context.user_id,
            email=context.email,
            name=context.name,
            scope="GLOBAL",
            organization=None,
            is_platform_admin=context.is_platform_admin,
            is_function_key=context.is_function_key,
            execution_id=context.execution_id
        )
        global_repo = ConfigRepository(global_context)
        global_configs = await global_repo.list_config(include_global=False)
        if global_configs:
            result["GLOBAL"] = config._configs_to_dict(global_configs)

        return result

    @staticmethod
    def _configs_to_dict(configs: list) -> dict[str, Any]:
        """Convert list of Config models to dict with parsed values."""
        import json as json_module

        config_dict: dict[str, Any] = {}
        for cfg in configs:
            # Parse value based on type
            if cfg.type == "json":
                try:
                    config_dict[cfg.key] = json_module.loads(cfg.value)
                except (json_module.JSONDecodeError, TypeError):
                    config_dict[cfg.key] = cfg.value
            elif cfg.type == "bool":
                config_dict[cfg.key] = cfg.value.lower() == "true"
            elif cfg.type == "int":
                try:
                    config_dict[cfg.key] = int(cfg.value)
                except (ValueError, TypeError):
                    config_dict[cfg.key] = cfg.value
            else:
                config_dict[cfg.key] = cfg.value

        return config_dict

    @staticmethod
    async def delete(key: str, org_id: str | None = None) -> bool:
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

        repo = ConfigRepository(context)
        return await repo.delete_config(key)
