"""
Base Integration Client
Abstract base class for all integration clients
"""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from shared.context import ExecutionContext


class BaseIntegration(ABC):
    """
    Abstract base class for integration clients.

    All integration clients (Microsoft Graph, HaloPSA, etc.) inherit from this
    class and implement the authenticate() method.

    Provides helper methods for accessing organization config and secrets.
    """

    def __init__(self, context: "ExecutionContext"):
        """
        Initialize integration client with organization context.

        Args:
            context: ExecutionContext with org data, config, and secrets
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

    # Helper methods for accessing config and secrets

    async def get_config(self, key: str, default: Any = None) -> Any:
        """
        Get organization-specific configuration value.

        Args:
            key: Configuration key
            default: Default value if key not found

        Returns:
            Configuration value or default
        """
        from bifrost import config
        return await config.get(key, default=default)

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
        from bifrost import secrets
        secret = await secrets.get(key)
        if secret is None:
            raise KeyError(f"Secret not found: {key}")
        return secret
