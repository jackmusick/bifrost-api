"""
Config Repository
Manages configuration key-value pairs with org-scoped + GLOBAL fallback
"""

import logging
from datetime import datetime
from typing import TYPE_CHECKING, cast

from shared.models import Config, ConfigType, IntegrationConfig, IntegrationType, SetIntegrationConfigRequest

from .scoped_repository import ScopedRepository

if TYPE_CHECKING:
    from shared.request_context import RequestContext

logger = logging.getLogger(__name__)


class ConfigRepository(ScopedRepository):
    """
    Repository for configuration key-value pairs

    Configuration is stored in Config table with org-scoping and GLOBAL fallback.
    Supports different config types: string, int, bool, json, secret_ref.
    """

    def __init__(self, context: 'RequestContext'):
        super().__init__("Config", context)

    def get_config(
        self,
        key: str,
        fallback_to_global: bool = True
    ) -> Config | None:
        """
        Get configuration value with optional GLOBAL fallback

        Args:
            key: Configuration key
            fallback_to_global: Whether to fallback to GLOBAL if not found in org

        Returns:
            Config model or None if not found
        """
        row_key = f"config:{key}"

        if fallback_to_global:
            entity = self.get_with_fallback(row_key)
        else:
            entity = self.get_by_id(self.scope, row_key)

        if entity:
            return self._entity_to_model(entity, key)

        return None

    def set_config(
        self,
        key: str,
        value: str,
        config_type: ConfigType,
        description: str | None = None,
        updated_by: str = "system"
    ) -> Config:
        """
        Set configuration value (upsert)

        Args:
            key: Configuration key
            value: Configuration value
            config_type: Type of configuration (string, int, bool, json, secret_ref)
            description: Optional description
            updated_by: User ID making the change

        Returns:
            Config model
        """
        now = datetime.utcnow()

        config_entity = {
            "PartitionKey": self.scope,
            "RowKey": f"config:{key}",
            "Value": value,
            "Type": config_type.value,
            "Description": description,
            "UpdatedAt": now.isoformat(),
            "UpdatedBy": updated_by,
        }

        self.upsert(config_entity)

        logger.info(f"Set config {key} in scope {self.scope} (type={config_type.value})")

        return self._entity_to_model(config_entity, key)

    def list_config(self, include_global: bool = True) -> list[Config]:
        """
        List all configuration entries

        Args:
            include_global: Include GLOBAL configuration

        Returns:
            List of Config models
        """
        if include_global:
            entities = self.query_with_fallback("config:")
        else:
            entities = self.query_org_only("config:")

        configs = []
        for entity in entities:
            key = entity["RowKey"].split(":", 1)[1]
            configs.append(self._entity_to_model(entity, key))

        logger.info(f"Found {len(configs)} config entries")
        return configs

    def delete_config(self, key: str) -> bool:
        """
        Delete configuration entry

        Args:
            key: Configuration key

        Returns:
            True if deleted, False if not found
        """
        return self.delete(self.scope, f"config:{key}")

    def list_integrations(self) -> list[IntegrationConfig]:
        """
        List all integration configurations for current scope

        Returns:
            List of IntegrationConfig models
        """
        # Query only current scope (integrations are org-specific, not GLOBAL)
        entities = self.query_org_only("integration:")

        integrations = []
        for entity in entities:
            integrations.append(self._entity_to_integration_model(entity))

        logger.info(f"Found {len(integrations)} integration configs")
        return integrations

    def delete_integration(self, integration_type: IntegrationType | str) -> bool:
        """
        Delete integration configuration

        Args:
            integration_type: Integration type to delete (enum or string)

        Returns:
            True if deleted, False if not found
        """
        # Support both enum and string for flexibility (DELETE should be lenient)
        type_value = integration_type.value if isinstance(integration_type, IntegrationType) else integration_type
        return self.delete(self.scope, f"integration:{type_value}")

    def get_integration_config(
        self,
        integration_type: IntegrationType,
        fallback_to_global: bool = True
    ) -> IntegrationConfig | None:
        """
        Get integration configuration

        Args:
            integration_type: Integration type (msgraph, halopsa, etc.)
            fallback_to_global: Whether to fallback to GLOBAL if not found

        Returns:
            IntegrationConfig model or None if not found
        """
        row_key = f"integration:{integration_type.value}"

        if fallback_to_global:
            entity = self.get_with_fallback(row_key)
        else:
            entity = self.get_by_id(self.scope, row_key)

        if entity:
            return self._entity_to_integration_model(entity)

        return None

    def set_integration_config(
        self,
        request: SetIntegrationConfigRequest,
        updated_by: str
    ) -> IntegrationConfig:
        """
        Set integration configuration

        Args:
            request: Integration config request
            updated_by: User ID making the change

        Returns:
            IntegrationConfig model
        """
        import json

        now = datetime.utcnow()

        config_entity = {
            "PartitionKey": self.scope,
            "RowKey": f"integration:{request.type.value}",
            "Type": request.type.value,
            "Enabled": request.enabled,
            "Settings": json.dumps(request.settings),
            "UpdatedAt": now.isoformat(),
            "UpdatedBy": updated_by,
        }

        self.upsert(config_entity)

        logger.info(
            f"Set integration config {request.type.value} in scope {self.scope} "
            f"(enabled={request.enabled})"
        )

        return self._entity_to_integration_model(config_entity)

    def _entity_to_model(self, entity: dict, key: str) -> Config:
        """
        Convert entity dict to Config model

        Args:
            entity: Entity dictionary from table storage
            key: Configuration key

        Returns:
            Config model
        """
        # Determine scope from partition key
        partition_key = entity.get("PartitionKey")
        if partition_key == "GLOBAL":
            scope = "GLOBAL"
            org_id = None
        else:
            scope = "org"
            org_id = partition_key

        # Parse datetime field
        updated_at = self._parse_datetime(entity.get("UpdatedAt"), datetime.utcnow())

        return Config(
            key=key,
            value=cast(str, entity.get("Value", "")),
            type=ConfigType(entity.get("Type", "string")),
            scope=scope,
            orgId=org_id,
            description=entity.get("Description"),
            updatedAt=updated_at,
            updatedBy=cast(str, entity.get("UpdatedBy", "")),
        )

    def _entity_to_integration_model(self, entity: dict) -> IntegrationConfig:
        """
        Convert entity dict to IntegrationConfig model

        Args:
            entity: Entity dictionary from table storage

        Returns:
            IntegrationConfig model
        """
        import json

        settings = entity.get("Settings")
        if settings and isinstance(settings, str):
            settings = json.loads(settings)
        elif not settings:
            settings = {}

        # Parse datetime field
        updated_at = self._parse_datetime(entity.get("UpdatedAt"), datetime.utcnow())

        return IntegrationConfig(
            type=IntegrationType(entity.get("Type")),
            enabled=entity.get("Enabled", True),
            settings=settings,
            updatedAt=updated_at,
            updatedBy=cast(str, entity.get("UpdatedBy", "")),
        )
