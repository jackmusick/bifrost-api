"""
Workflow and Data Provider Registry
Singleton registry for storing workflow and data provider metadata
"""

import logging
import threading
from dataclasses import dataclass, field
from typing import Any, Literal, Optional

logger = logging.getLogger(__name__)


@dataclass
class WorkflowParameter:
    """Workflow parameter metadata"""
    name: str
    type: str  # string, int, bool, float, json, list
    label: str | None = None
    required: bool = False
    validation: dict[str, Any] | None = None
    data_provider: str | None = None
    default_value: Any | None = None
    help_text: str | None = None


@dataclass
class WorkflowMetadata:
    """Workflow metadata from @workflow decorator"""
    # Identity
    name: str
    description: str
    category: str = "General"
    tags: list[str] = field(default_factory=list)

    # Execution
    execution_mode: Literal["sync", "async"] = "sync"
    timeout_seconds: int = 300

    # Retry (for future use)
    retry_policy: dict[str, Any] | None = None

    # Scheduling (for future use)
    schedule: str | None = None

    # HTTP Endpoint Configuration
    endpoint_enabled: bool = False
    allowed_methods: list[str] = field(default_factory=lambda: ["POST"])
    disable_global_key: bool = False
    public_endpoint: bool = False

    # Source tracking (home, platform, workspace)
    source: Literal["home", "platform", "workspace"] | None = None

    # Parameters and function
    parameters: list[WorkflowParameter] = field(default_factory=list)
    function: Any = None


@dataclass
class DataProviderMetadata:
    """Data provider metadata from @data_provider decorator"""
    name: str
    description: str
    category: str = "General"
    cache_ttl_seconds: int = 300  # Default 5 minutes
    function: Any = None  # The actual Python function


class WorkflowRegistry:
    """
    Singleton registry for workflows and data providers
    Thread-safe storage of workflow metadata
    """

    _instance: Optional['WorkflowRegistry'] = None
    _lock = threading.Lock()

    def __new__(cls):
        """Singleton pattern - only one instance exists"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Initialize registry storage (only runs once)"""
        if self._initialized:
            return

        self._workflows: dict[str, WorkflowMetadata] = {}
        self._data_providers: dict[str, DataProviderMetadata] = {}
        self._initialized = True
        logger.info("WorkflowRegistry initialized")

    # ==================== WORKFLOW METHODS ====================

    def register_workflow(self, metadata: WorkflowMetadata) -> None:
        """
        Register a workflow in the registry

        Args:
            metadata: WorkflowMetadata object
        """
        with self._lock:
            if metadata.name in self._workflows:
                logger.warning(f"Workflow '{metadata.name}' already registered - overwriting")

            self._workflows[metadata.name] = metadata
            logger.info(
                f"Registered workflow: {metadata.name} "
                f"({len(metadata.parameters)} parameters, execution_mode={metadata.execution_mode})"
            )

    def get_workflow(self, name: str) -> WorkflowMetadata | None:
        """
        Retrieve workflow metadata by name

        Args:
            name: Workflow name

        Returns:
            WorkflowMetadata or None if not found
        """
        return self._workflows.get(name)

    def get_all_workflows(self) -> list[WorkflowMetadata]:
        """
        Get all registered workflows

        Returns:
            List of WorkflowMetadata objects
        """
        return list(self._workflows.values())

    def has_workflow(self, name: str) -> bool:
        """Check if workflow exists in registry"""
        return name in self._workflows

    def get_workflow_count(self) -> int:
        """Get total number of registered workflows"""
        return len(self._workflows)

    # ==================== DATA PROVIDER METHODS ====================

    def register_data_provider(self, metadata: DataProviderMetadata) -> None:
        """
        Register a data provider in the registry

        Args:
            metadata: DataProviderMetadata object
        """
        with self._lock:
            if metadata.name in self._data_providers:
                logger.warning(f"Data provider '{metadata.name}' already registered - overwriting")

            self._data_providers[metadata.name] = metadata
            logger.info(
                f"Registered data provider: {metadata.name} "
                f"(cache_ttl={metadata.cache_ttl_seconds}s)"
            )

    def get_data_provider(self, name: str) -> DataProviderMetadata | None:
        """
        Retrieve data provider metadata by name

        Args:
            name: Data provider name

        Returns:
            DataProviderMetadata or None if not found
        """
        return self._data_providers.get(name)

    def get_all_data_providers(self) -> list[DataProviderMetadata]:
        """
        Get all registered data providers

        Returns:
            List of DataProviderMetadata objects
        """
        return list(self._data_providers.values())

    def has_data_provider(self, name: str) -> bool:
        """Check if data provider exists in registry"""
        return name in self._data_providers

    def get_data_provider_count(self) -> int:
        """Get total number of registered data providers"""
        return len(self._data_providers)

    # ==================== UTILITY METHODS ====================

    def clear_all(self) -> None:
        """Clear all registered workflows and data providers (for testing)"""
        with self._lock:
            self._workflows.clear()
            self._data_providers.clear()
            logger.info("Registry cleared")

    def get_summary(self) -> dict[str, Any]:
        """Get summary of registry contents"""
        return {
            "workflows_count": self.get_workflow_count(),
            "data_providers_count": self.get_data_provider_count(),
            "workflows": [w.name for w in self.get_all_workflows()],
            "data_providers": [dp.name for dp in self.get_all_data_providers()]
        }


# Convenience function to get singleton instance
def get_registry() -> WorkflowRegistry:
    """Get the singleton WorkflowRegistry instance"""
    return WorkflowRegistry()
