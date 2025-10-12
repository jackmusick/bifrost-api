"""
Base Integration Client
Abstract base class for all integration clients
"""

from abc import ABC, abstractmethod
from typing import Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from shared.context import OrganizationContext


class BaseIntegration(ABC):
    """
    Abstract base class for integration clients.

    All integration clients (Microsoft Graph, HaloPSA, etc.) inherit from this
    class and implement the authenticate() method.

    Provides helper methods for accessing organization config and secrets.
    """

    def __init__(self, context: "OrganizationContext"):
        """
        Initialize integration client with organization context.

        Args:
            context: OrganizationContext with org data, config, and secrets
        """
        self.context = context

    @abstractmethod
    async def authenticate(self) -> str:
        """
        Authenticate to the external service and return access token.

        This method must be implemented by each integration client.

        Returns:
            Access token string

        Raises:
            IntegrationError: If authentication fails
        """
        pass

    # Helper methods for accessing context

    def get_config(self, key: str, default: Any = None) -> Any:
        """
        Get organization-specific configuration value.

        Args:
            key: Configuration key
            default: Default value if key not found

        Returns:
            Configuration value or default
        """
        return self.context.get_config(key, default)

    async def get_secret(self, key: str) -> str:
        """
        Get secret from Azure Key Vault.

        Args:
            key: Secret key

        Returns:
            Secret value

        Raises:
            KeyError: If secret not found
        """
        return await self.context.get_secret(key)
