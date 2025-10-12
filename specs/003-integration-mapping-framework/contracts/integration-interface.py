"""
Integration Interface Contract for Organization Mapping

This file defines the abstract base class that all integrations MUST implement
to support organization mapping functionality.

Place this file in: workflows/shared/integrations/base.py
"""

from abc import ABC, abstractmethod
from typing import List, Any, Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class ExternalOrganization:
    """
    External organization discovered from integration API.

    This is a standardized format that all integrations return from list_organizations().
    """
    id: str  # External org ID (tenant ID, customer ID, etc.)
    name: str  # Human-readable organization name
    metadata: dict[str, Any]  # Integration-specific extra data

    class Config:
        frozen = True  # Immutable


@dataclass
class OrganizationMapping:
    """
    Mapping between MSP organization and external organization.

    This entity is persisted in Table Storage and passed to integrations
    when they need org-specific configuration.
    """
    id: str  # Mapping UUID
    org_id: str  # MSP organization UUID
    integration_name: str  # Integration identifier (e.g., 'halopsa')
    external_org_id: str  # External org ID from integration
    external_org_name: str  # External org display name
    mapping_data: dict[str, Any]  # Integration-specific config
    is_active: bool  # Soft delete flag
    created_at: datetime
    created_by: str  # User UUID
    updated_at: datetime
    updated_by: Optional[str]
    last_tested_at: Optional[datetime]
    last_test_result: Optional[str]


@dataclass
class TestResult:
    """
    Result of testing an integration mapping connection.

    Integrations return this from test_connection() to indicate
    whether the mapping is correctly configured.
    """
    success: bool  # Test succeeded
    message: str  # Human-readable result message
    details: dict[str, Any]  # Additional diagnostic info

    class Config:
        frozen = True


class IntegrationInterface(ABC):
    """
    Abstract base class for integrations with organization mapping support.

    All integrations that want to support organization mapping MUST:
    1. Inherit from this class
    2. Implement all abstract methods
    3. Return True from supports_org_mapping()

    Example:
    ```python
    from shared.integrations.base import IntegrationInterface
    from shared.context import OrganizationContext

    class HaloPSAIntegration(IntegrationInterface):
        def __init__(self, context: OrganizationContext):
            self.context = context

        def supports_org_mapping(self) -> bool:
            return True  # Enable mapping support

        async def list_organizations(self) -> List[ExternalOrganization]:
            # Fetch customers from HaloPSA API
            api_key = self.context.get_secret("halopsa_api_key")
            customers = await self._fetch_customers(api_key)
            return [
                ExternalOrganization(
                    id=str(c["id"]),
                    name=c["name"],
                    metadata={"client_code": c.get("code")}
                )
                for c in customers
            ]

        async def get_client(self, mapping: OrganizationMapping):
            # Return pre-authenticated client
            api_key = self.context.get_secret("halopsa_api_key")
            return HaloPSAClient(
                api_key=api_key,
                client_id=mapping.external_org_id,
                config=mapping.mapping_data
            )

        async def test_connection(self, mapping: OrganizationMapping) -> TestResult:
            try:
                client = await self.get_client(mapping)
                await client.ping()
                return TestResult(
                    success=True,
                    message=f"Successfully connected to {mapping.external_org_name}"
                )
            except Exception as e:
                return TestResult(
                    success=False,
                    message=f"Connection failed: {str(e)}",
                    details={"error_type": type(e).__name__}
                )
    ```
    """

    @abstractmethod
    def supports_org_mapping(self) -> bool:
        """
        Returns True if this integration supports organization mapping.

        Integrations that return True MUST implement all other abstract methods.
        Integrations that return False can leave other methods unimplemented
        (they will never be called).

        Returns:
            bool: True if mapping supported, False otherwise

        Example:
        ```python
        def supports_org_mapping(self) -> bool:
            return True  # This integration supports mapping
        ```
        """
        pass

    @abstractmethod
    async def list_organizations(self) -> List[ExternalOrganization]:
        """
        Fetch list of organizations from external integration system.

        This method is called when an admin clicks "Discover Organizations"
        in the UI. It should return ALL organizations that the integration
        has access to (not just ones already mapped).

        Returns:
            List[ExternalOrganization]: List of external orgs with id, name, metadata

        Raises:
            NotImplementedError: If integration doesn't support discovery
            AuthenticationError: If credentials are invalid
            APIError: If external API call fails

        Example:
        ```python
        async def list_organizations(self) -> List[ExternalOrganization]:
            api_key = self.context.get_secret("myintegration_api_key")

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    "https://api.example.com/organizations",
                    headers={"Authorization": f"Bearer {api_key}"}
                ) as response:
                    orgs = await response.json()

            return [
                ExternalOrganization(
                    id=org["id"],
                    name=org["name"],
                    metadata=org.get("extra_fields", {})
                )
                for org in orgs
            ]
        ```

        Performance Guidelines:
        - Should complete in <10s for 1000+ organizations
        - Cache credentials for request duration (don't fetch from Key Vault multiple times)
        - Use pagination if API supports it
        - Consider parallel requests for large datasets
        """
        pass

    @abstractmethod
    async def get_client(self, mapping: OrganizationMapping) -> Any:
        """
        Get pre-authenticated client for specific organization mapping.

        This method is called by workflows when they retrieve a mapping via
        context.get_integration_mapping() and need to use the integration.
        It should return a fully configured client that's ready to make
        API calls on behalf of the mapped external organization.

        Args:
            mapping: OrganizationMapping with external_org_id and mapping_data

        Returns:
            Any: Pre-authenticated integration client (type depends on integration)

        Raises:
            AuthenticationError: If credentials are invalid
            ConfigurationError: If mapping_data is invalid

        Example:
        ```python
        async def get_client(self, mapping: OrganizationMapping):
            # Get global integration credentials
            api_key = self.context.get_secret("myintegration_api_key")

            # Get org-specific config from mapping_data
            api_url = mapping.mapping_data.get(
                "api_base_url",
                "https://api.example.com"
            )

            # Return pre-authenticated client
            return MyIntegrationClient(
                api_key=api_key,
                api_url=api_url,
                organization_id=mapping.external_org_id
            )
        ```

        Usage in Workflow:
        ```python
        @workflow(name="sync_users")
        async def sync_users(context: OrganizationContext):
            # Get mapping
            mapping = await context.get_integration_mapping("myintegration")

            # Get pre-authenticated client (calls this method)
            client = await context.get_integration("myintegration")

            # Use client (already scoped to correct org)
            users = await client.list_users()
            return {"user_count": len(users)}
        ```
        """
        pass

    @abstractmethod
    async def test_connection(self, mapping: OrganizationMapping) -> TestResult:
        """
        Test connection with given mapping configuration.

        This method is called when an admin clicks "Test Connection" in the UI.
        It should verify that the mapping is correctly configured by making
        a simple API call to the external system.

        Args:
            mapping: OrganizationMapping to test

        Returns:
            TestResult: Result with success status, message, and details

        Example:
        ```python
        async def test_connection(self, mapping: OrganizationMapping) -> TestResult:
            try:
                # Get client with this mapping
                client = await self.get_client(mapping)

                # Try a simple API call
                org_details = await client.get_organization_details(
                    mapping.external_org_id
                )

                return TestResult(
                    success=True,
                    message=f"Successfully connected to {org_details['name']}",
                    details={
                        "org_name": org_details["name"],
                        "org_id": mapping.external_org_id,
                        "api_version": org_details.get("api_version")
                    }
                )
            except AuthenticationError as e:
                return TestResult(
                    success=False,
                    message=f"Authentication failed: {str(e)}",
                    details={"error_type": "AuthenticationError"}
                )
            except APIError as e:
                return TestResult(
                    success=False,
                    message=f"API error: {str(e)}",
                    details={
                        "error_type": "APIError",
                        "status_code": e.status_code
                    }
                )
            except Exception as e:
                return TestResult(
                    success=False,
                    message=f"Unexpected error: {str(e)}",
                    details={"error_type": type(e).__name__}
                )
        ```

        Best Practices:
        - Use lightweight API call (get org details, not list all users)
        - Return detailed error info in details dict for troubleshooting
        - Catch all exceptions and return TestResult (don't raise)
        - Include external org name in success message for confirmation
        """
        pass


class BaseIntegration(IntegrationInterface):
    """
    Base implementation with common functionality.

    Integrations can inherit from this instead of IntegrationInterface
    to get default implementations of common methods.
    """

    def __init__(self, context):
        """
        Initialize integration with organization context.

        Args:
            context: OrganizationContext with org info, config, secrets
        """
        from shared.context import OrganizationContext
        self.context: OrganizationContext = context

    def supports_org_mapping(self) -> bool:
        """
        Default: organization mapping not supported.

        Override and return True to enable mapping support.
        """
        return False

    async def list_organizations(self) -> List[ExternalOrganization]:
        """
        Default: raise NotImplementedError.

        Override if integration supports organization discovery.
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} does not support organization discovery"
        )

    async def get_client(self, mapping: OrganizationMapping = None) -> Any:
        """
        Default: return self (integration instance is the client).

        Override if integration has separate client class.
        """
        return self

    async def test_connection(self, mapping: OrganizationMapping) -> TestResult:
        """
        Default: basic connection test using get_client().

        Override for integration-specific test logic.
        """
        try:
            client = await self.get_client(mapping)
            # Attempt to use client (integration must override this)
            await client.validate_connection()

            return TestResult(
                success=True,
                message=f"Successfully connected to {mapping.external_org_name}",
                details={}
            )
        except Exception as e:
            return TestResult(
                success=False,
                message=f"Connection failed: {str(e)}",
                details={"error_type": type(e).__name__}
            )


# Example: Integration that doesn't support mapping
class LegacyIntegration(BaseIntegration):
    """
    Example of integration without mapping support.

    Existing integrations can continue to work without implementing
    organization mapping. They simply return False from supports_org_mapping().
    """

    def supports_org_mapping(self) -> bool:
        return False  # No mapping support

    async def do_work(self):
        """Integration-specific functionality"""
        api_key = self.context.get_secret("legacy_api_key")
        # Do work using global credentials
        return {"success": True}


# Example: Integration with mapping support
class ModernIntegration(BaseIntegration):
    """
    Example of integration with full mapping support.

    New integrations should implement all mapping methods to enable
    zero-code setup through the UI.
    """

    def supports_org_mapping(self) -> bool:
        return True  # Enable mapping

    async def list_organizations(self) -> List[ExternalOrganization]:
        """Discover external organizations"""
        api_key = self.context.get_secret("modern_api_key")

        # Fetch orgs from API
        orgs = await self._api_call("/organizations", api_key)

        return [
            ExternalOrganization(
                id=org["id"],
                name=org["name"],
                metadata={"tier": org.get("tier", "standard")}
            )
            for org in orgs
        ]

    async def get_client(self, mapping: OrganizationMapping):
        """Get pre-authenticated client for org"""
        api_key = self.context.get_secret("modern_api_key")

        return ModernAPIClient(
            api_key=api_key,
            org_id=mapping.external_org_id,
            config=mapping.mapping_data
        )

    async def test_connection(self, mapping: OrganizationMapping) -> TestResult:
        """Test connection to external org"""
        try:
            client = await self.get_client(mapping)
            details = await client.get_org_details()

            return TestResult(
                success=True,
                message=f"Connected to {details['name']}",
                details={"org_name": details["name"]}
            )
        except Exception as e:
            return TestResult(
                success=False,
                message=str(e),
                details={"error": str(e)}
            )

    async def _api_call(self, endpoint: str, api_key: str):
        """Helper method for API calls"""
        import aiohttp

        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"https://api.example.com{endpoint}",
                headers={"Authorization": f"Bearer {api_key}"}
            ) as response:
                return await response.json()


# Type aliases for clarity
IntegrationClient = Any  # The type returned by get_client()
