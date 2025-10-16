"""
Azure Key Vault client wrapper for secret management with full CRUD operations.

This module provides comprehensive secret management capabilities including
create, read, update, delete, and list operations for the client API.
"""

import logging
import os

from azure.core.exceptions import (
    ClientAuthenticationError,
    HttpResponseError,
    ResourceNotFoundError,
    ServiceRequestError,
)
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

logger = logging.getLogger(__name__)


class KeyVaultClient:
    """
    Manager for Azure Key Vault with full CRUD operations.

    Features:
    - DefaultAzureCredential for automatic authentication
    - Create, read, update, delete, and list secrets
    - Org-scoped and global secret naming convention
    - Comprehensive error handling with actionable messages
    - Health check capabilities
    """

    def __init__(self, vault_url: str | None = None):
        """
        Initialize the Key Vault manager.

        Args:
            vault_url: Azure Key Vault URL (e.g., https://my-vault.vault.azure.net/)
                      If None, attempts to read from AZURE_KEY_VAULT_URL env var
        """
        self.vault_url = vault_url or os.environ.get("AZURE_KEY_VAULT_URL")
        self._client: SecretClient | None = None
        self._credential = None

        # Initialize client if vault URL is provided
        if self.vault_url:
            try:
                self._credential = DefaultAzureCredential()
                logger.info("Using DefaultAzureCredential for Key Vault")

                self._client = SecretClient(
                    vault_url=self.vault_url,
                    credential=self._credential
                )
                logger.info(f"Key Vault manager initialized for {self.vault_url}")
            except Exception as e:
                logger.error(f"Failed to initialize Key Vault client: {e}")
                raise
        else:
            raise ValueError("AZURE_KEY_VAULT_URL environment variable is required")

    def create_secret(self, org_id: str, secret_key: str, value: str) -> dict[str, str]:
        """
        Create a new secret in Key Vault.

        Args:
            org_id: Organization identifier or "GLOBAL" for platform-wide
            secret_key: Secret key/name
            value: Secret value to store

        Returns:
            Dict with secret name and creation confirmation

        Raises:
            ValueError: If secret name is invalid
            HttpResponseError: If secret already exists or permission denied
        """
        secret_name = self._build_secret_name(org_id, secret_key)

        # Validate secret name against Key Vault naming rules
        if not self._is_valid_secret_name(secret_name):
            raise ValueError(
                f"Invalid secret name: {secret_name}. "
                "Names must contain only alphanumeric characters and hyphens"
            )

        try:
            assert self._client is not None, "Key Vault client not initialized"
            self._client.set_secret(secret_name, value)
            logger.info(f"Created secret: {secret_name}")
            return {
                "name": secret_name,
                "message": "Secret created successfully"
            }
        except HttpResponseError as e:
            if e.status_code == 403:
                raise HttpResponseError(
                    "Permission denied: Insufficient permissions to create secrets in Key Vault"
                ) from e
            raise

    def update_secret(self, org_id: str, secret_key: str, value: str) -> dict[str, str]:
        """
        Update an existing secret in Key Vault.

        Note: set_secret will create a new version if the secret exists.

        Args:
            org_id: Organization identifier or "GLOBAL" for platform-wide
            secret_key: Secret key/name
            value: New secret value

        Returns:
            Dict with secret name and update confirmation

        Raises:
            HttpResponseError: If permission denied
        """
        secret_name = self._build_secret_name(org_id, secret_key)

        try:
            assert self._client is not None, "Key Vault client not initialized"
            self._client.set_secret(secret_name, value)
            logger.info(f"Updated secret: {secret_name}")
            return {
                "name": secret_name,
                "message": "Secret updated successfully"
            }
        except HttpResponseError as e:
            if e.status_code == 403:
                raise HttpResponseError(
                    "Permission denied: Insufficient permissions to update secrets in Key Vault"
                ) from e
            raise

    def delete_secret(self, org_id: str, secret_key: str) -> dict[str, str]:
        """
        Delete a secret from Key Vault.

        Note: Deletion initiates a soft-delete (recoverable for 90 days by default).

        Args:
            org_id: Organization identifier or "GLOBAL" for platform-wide
            secret_key: Secret key/name

        Returns:
            Dict with secret name and deletion confirmation

        Raises:
            ResourceNotFoundError: If secret doesn't exist
            HttpResponseError: If permission denied
        """
        secret_name = self._build_secret_name(org_id, secret_key)

        try:
            assert self._client is not None, "Key Vault client not initialized"
            deleted_secret = self._client.begin_delete_secret(secret_name)
            deleted_secret.wait()  # Wait for deletion to complete
            logger.info(f"Deleted secret: {secret_name}")
            return {
                "name": secret_name,
                "message": "Secret deleted successfully (soft-delete, recoverable for 90 days)"
            }
        except ResourceNotFoundError:
            raise ResourceNotFoundError(f"Secret not found: {secret_name}") from None
        except HttpResponseError as e:
            if e.status_code == 403:
                raise HttpResponseError(
                    "Permission denied: Insufficient permissions to delete secrets in Key Vault"
                ) from e
            raise

    def get_secret(self, org_id: str, secret_key: str) -> str:
        """
        Get a secret value from Key Vault.

        Args:
            org_id: Organization identifier or "GLOBAL" for platform-wide
            secret_key: Secret key/name

        Returns:
            Secret value as string

        Raises:
            ResourceNotFoundError: If secret doesn't exist
        """
        secret_name = self._build_secret_name(org_id, secret_key)

        try:
            assert self._client is not None, "Key Vault client not initialized"
            secret = self._client.get_secret(secret_name)
            logger.info(f"Retrieved secret: {secret_name}")
            assert secret.value is not None, "Secret value is None"
            return secret.value
        except ResourceNotFoundError:
            raise ResourceNotFoundError(f"Secret not found: {secret_name}") from None

    def list_secrets(self, org_id: str | None = None) -> list[str]:
        """
        List all secrets in Key Vault, optionally filtered by organization.

        Args:
            org_id: Optional organization identifier to filter secrets
                   If provided, returns org-scoped + GLOBAL secrets
                   If None, returns all secrets

        Returns:
            List of secret names

        Raises:
            HttpResponseError: If permission denied (list permission required)
        """
        try:
            assert self._client is not None, "Key Vault client not initialized"
            secret_properties = self._client.list_properties_of_secrets()
            secret_names = [prop.name for prop in secret_properties if prop.name is not None]

            # Filter by org if specified
            if org_id:
                prefix_org = f"{org_id}--"
                prefix_global = "GLOBAL--"
                secret_names = [
                    name for name in secret_names
                    if name.startswith(prefix_org) or name.startswith(prefix_global)
                ]

            logger.info(f"Listed {len(secret_names)} secrets" + (f" for org {org_id}" if org_id else ""))
            return secret_names

        except HttpResponseError as e:
            if e.status_code == 403:
                logger.warning("Permission denied for list_secrets, returning empty list")
                return []
            raise

    def health_check(self) -> dict:
        """
        Perform a comprehensive health check on Key Vault connectivity and permissions.

        Tests:
        - Connection to Key Vault
        - List secrets permission
        - Get secret permission (test with dummy secret)

        Returns:
            Dict with detailed health status including:
            - status: "healthy", "degraded", or "unhealthy"
            - can_connect: bool
            - can_list_secrets: bool
            - can_get_secrets: bool
            - secret_count: int (if list permission available)
            - error: str (if any errors)
        """
        result = {
            "can_connect": False,
            "can_list_secrets": False,
            "can_get_secrets": False,
            "secret_count": None,
            "status": "unhealthy",
            "error": None
        }

        # Test 1: Connection + List secrets
        try:
            assert self._client is not None, "Key Vault client not initialized"
            secrets_list = list(self._client.list_properties_of_secrets())
            result["can_connect"] = True
            result["can_list_secrets"] = True
            result["secret_count"] = len(secrets_list)
            logger.info(f"Key Vault connection successful, found {len(secrets_list)} secrets")

            # Test 2: Get secret permission (try to get first secret if available)
            if secrets_list:
                try:
                    # Try to get the first secret to test get permission
                    first_secret_name = secrets_list[0].name
                    assert first_secret_name is not None, "Secret name is None"
                    assert self._client is not None, "Key Vault client not initialized"
                    self._client.get_secret(first_secret_name)
                    result["can_get_secrets"] = True
                    logger.info("Key Vault get secret permission verified")
                except HttpResponseError as e:
                    if e.status_code == 403:
                        logger.warning("Key Vault get permission denied")
                        result["can_get_secrets"] = False
                    else:
                        raise
                except Exception as e:
                    logger.warning(f"Error testing get secret: {e}")
                    result["can_get_secrets"] = False
            else:
                # No secrets to test with, assume get permission is available
                result["can_get_secrets"] = True

            # Determine overall status
            if result["can_connect"] and result["can_list_secrets"] and result["can_get_secrets"]:
                result["status"] = "healthy"
            elif result["can_connect"]:
                result["status"] = "degraded"
            else:
                result["status"] = "unhealthy"

            return result

        except ClientAuthenticationError as e:
            logger.error(f"Key Vault authentication failed: {e}")
            result["error"] = f"Authentication failed: {str(e)}"
            result["status"] = "unhealthy"
            return result

        except HttpResponseError as e:
            result["can_connect"] = True  # Connection works, but permission issue
            if e.status_code == 403:
                logger.warning("Key Vault list permission denied")
                result["error"] = "Permission denied for list operation"
                result["status"] = "degraded"
            else:
                logger.error(f"Key Vault HTTP error: {e}")
                result["error"] = f"HTTP error {e.status_code}"
                result["status"] = "unhealthy"
            return result

        except ServiceRequestError as e:
            logger.error(f"Key Vault connection error: {e}")
            result["error"] = f"Network error: {str(e)}"
            result["status"] = "unhealthy"
            return result

        except Exception as e:
            logger.error(f"Unexpected Key Vault error: {e}")
            result["error"] = f"Unexpected error: {str(e)}"
            result["status"] = "unhealthy"
            return result

    @staticmethod
    def _build_secret_name(org_id: str, secret_key: str) -> str:
        """
        Build Key Vault secret name following naming convention.

        Format: {org_id}--{secret-key}

        Args:
            org_id: Organization identifier or "GLOBAL"
            secret_key: Secret key/name

        Returns:
            Formatted secret name
        """
        return f"{org_id}--{secret_key}"

    @staticmethod
    def _is_valid_secret_name(secret_name: str) -> bool:
        """
        Validate secret name against Key Vault naming rules.

        Rules:
        - Must contain only alphanumeric characters and hyphens
        - Must be 1-127 characters

        Args:
            secret_name: Secret name to validate

        Returns:
            True if valid, False otherwise
        """
        if not secret_name or len(secret_name) > 127:
            return False

        return all(c.isalnum() or c == '-' for c in secret_name)
