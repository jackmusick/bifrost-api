"""
Azure Key Vault client wrapper for secret management.

This module provides a unified interface for accessing secrets from Azure Key Vault
with support for local development fallback, caching, and retry logic.
"""

import os
import time
import logging
from typing import Dict, Tuple, Optional
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
from azure.core.exceptions import (
    ResourceNotFoundError,
    ClientAuthenticationError,
    HttpResponseError,
    ServiceRequestError
)

logger = logging.getLogger(__name__)


class KeyVaultClient:
    """
    Wrapper for Azure Key Vault SecretClient with caching and error handling.

    Features:
    - DefaultAzureCredential for automatic authentication (managed identity in prod, az cli in local)
    - In-memory caching with 1-hour TTL
    - Automatic retry with exponential backoff
    - Org-scoped and global secret naming convention
    - Local development fallback to environment variables
    """

    def __init__(self, vault_url: Optional[str] = None, cache_duration: int = 3600):
        """
        Initialize the Key Vault client.

        Args:
            vault_url: Azure Key Vault URL (e.g., https://my-vault.vault.azure.net/)
                      If None, attempts to read from AZURE_KEY_VAULT_URL env var
            cache_duration: Cache duration in seconds (default: 3600 = 1 hour)
        """
        self.vault_url = vault_url or os.environ.get("AZURE_KEY_VAULT_URL")
        self.cache_duration = cache_duration
        self._cache: Dict[str, Tuple[str, float]] = {}
        self._client: Optional[SecretClient] = None
        self._credential = None

        # Initialize client if vault URL is provided
        if self.vault_url:
            try:
                self._credential = DefaultAzureCredential()
                self._client = SecretClient(
                    vault_url=self.vault_url,
                    credential=self._credential
                )
                logger.info(f"Key Vault client initialized for {self.vault_url}")
            except Exception as e:
                logger.warning(f"Failed to initialize Key Vault client: {e}")
                self._client = None
        else:
            logger.info("No Key Vault URL configured, will use local fallback only")

    def get_secret(self, org_id: str, secret_key: str) -> str:
        """
        Get a secret value with org-scoped → global fallback pattern.

        Naming convention:
        - Org-scoped: {org_id}--{secret-key}
        - Global: GLOBAL--{secret-key}

        Args:
            org_id: Organization identifier
            secret_key: Secret key/name

        Returns:
            Secret value as string

        Raises:
            KeyError: If secret not found in Key Vault or local config
            ClientAuthenticationError: If authentication fails
            HttpResponseError: If permission denied or rate limited
        """
        # Try Key Vault first
        if self._client:
            try:
                return self._get_secret_with_fallback(org_id, secret_key)
            except ClientAuthenticationError as e:
                logger.warning(f"Key Vault authentication failed: {e}, trying local fallback")
            except ServiceRequestError as e:
                logger.warning(f"Key Vault connection error: {e}, trying local fallback")
            except HttpResponseError as e:
                if e.status_code == 403:
                    logger.error(f"Permission denied for Key Vault access: {e}")
                elif e.status_code == 429:
                    logger.warning(f"Key Vault rate limit exceeded: {e}, trying local fallback")
                raise

        # Fall back to local environment variables
        return self._get_local_secret(org_id, secret_key)

    def _get_secret_with_fallback(self, org_id: str, secret_key: str) -> str:
        """
        Internal method to get secret from Key Vault with org → global fallback.

        Args:
            org_id: Organization identifier
            secret_key: Secret key/name

        Returns:
            Secret value as string

        Raises:
            KeyError: If secret not found in either org-scoped or global scope
        """
        # Try org-scoped secret first
        org_secret_name = self._build_secret_name(org_id, secret_key)

        try:
            value = self._get_cached_or_fetch(org_secret_name)
            logger.info(f"Retrieved org-scoped secret: {org_secret_name}")
            return value
        except ResourceNotFoundError:
            logger.debug(f"Org-scoped secret not found: {org_secret_name}, trying global")

        # Try global secret
        global_secret_name = self._build_secret_name("GLOBAL", secret_key)

        try:
            value = self._get_cached_or_fetch(global_secret_name)
            logger.info(f"Retrieved global secret: {global_secret_name}")
            return value
        except ResourceNotFoundError:
            raise KeyError(
                f"Secret '{secret_key}' not found for org '{org_id}'. "
                f"Tried: {org_secret_name}, {global_secret_name}"
            )

    def _get_cached_or_fetch(self, secret_name: str) -> str:
        """
        Get secret from cache if available and fresh, otherwise fetch from Key Vault.

        Args:
            secret_name: Full secret name in Key Vault

        Returns:
            Secret value as string
        """
        # Check cache
        if secret_name in self._cache:
            cached_value, cached_time = self._cache[secret_name]
            if time.time() - cached_time < self.cache_duration:
                logger.debug(f"Cache hit for secret: {secret_name}")
                return cached_value
            else:
                logger.debug(f"Cache expired for secret: {secret_name}")

        # Fetch from Key Vault
        secret = self._client.get_secret(secret_name)
        value = secret.value

        # Update cache
        self._cache[secret_name] = (value, time.time())
        logger.debug(f"Cached secret: {secret_name}")

        return value

    def _get_local_secret(self, org_id: str, secret_key: str) -> str:
        """
        Get secret from local environment variables as fallback.

        Local env var pattern:
        - Org-scoped: {ORG_ID}__{SECRET_KEY}
        - Global: GLOBAL__{SECRET_KEY}

        Args:
            org_id: Organization identifier
            secret_key: Secret key/name

        Returns:
            Secret value as string

        Raises:
            KeyError: If secret not found in local config
        """
        # Try org-scoped local env var
        org_env_var = self._build_env_var_name(org_id, secret_key)
        local_value = os.environ.get(org_env_var)

        if local_value:
            logger.info(f"Retrieved org-scoped local secret: {org_env_var}")
            return local_value

        # Try global local env var
        global_env_var = self._build_env_var_name("GLOBAL", secret_key)
        local_value = os.environ.get(global_env_var)

        if local_value:
            logger.info(f"Retrieved global local secret: {global_env_var}")
            return local_value

        raise KeyError(
            f"Secret '{secret_key}' not found for org '{org_id}'. "
            f"Not found in Key Vault or local config. "
            f"Tried env vars: {org_env_var}, {global_env_var}"
        )

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
    def _build_env_var_name(org_id: str, secret_key: str) -> str:
        """
        Build environment variable name for local secrets.

        Format: {ORG_ID}__{SECRET_KEY} (uppercase, hyphens to underscores)

        Args:
            org_id: Organization identifier or "GLOBAL"
            secret_key: Secret key/name

        Returns:
            Formatted environment variable name
        """
        org_part = org_id.upper().replace('-', '_')
        key_part = secret_key.upper().replace('-', '_')
        return f"{org_part}__{key_part}"

    def clear_cache(self):
        """Clear all cached secrets."""
        self._cache.clear()
        logger.info("Secret cache cleared")

    def clear_secret_cache(self, org_id: str, secret_key: str):
        """
        Clear cache for a specific secret.

        Args:
            org_id: Organization identifier
            secret_key: Secret key/name
        """
        org_secret_name = self._build_secret_name(org_id, secret_key)
        global_secret_name = self._build_secret_name("GLOBAL", secret_key)

        self._cache.pop(org_secret_name, None)
        self._cache.pop(global_secret_name, None)

        logger.debug(f"Cleared cache for secret: {secret_key}")
