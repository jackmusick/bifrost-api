"""
E2E test configuration.

E2E tests require additional setup:
- Real KeyVault instance with AZURE_KEY_VAULT_URL environment variable set
- Azure credentials configured (DefaultAzureCredential must work)
- External service dependencies

These tests are automatically skipped if KeyVault is not properly configured.
"""

import os
import pytest
from azure.identity import DefaultAzureCredential
from azure.core.exceptions import ClientAuthenticationError


def pytest_configure(config):
    """Register e2e marker"""
    config.addinivalue_line(
        "markers", "e2e: End-to-end tests requiring external services (auto-skipped if KeyVault not configured)"
    )


def _check_keyvault_available():
    """
    Check if KeyVault is properly configured and accessible.

    Returns:
        tuple: (is_available: bool, reason: str)
    """
    # Check if KeyVault URL is set
    keyvault_url = os.environ.get("AZURE_KEY_VAULT_URL") or os.environ.get("KEY_VAULT_URL")
    if not keyvault_url:
        return False, "AZURE_KEY_VAULT_URL environment variable not set"

    # Check if we can get Azure credentials
    try:
        credential = DefaultAzureCredential()
        # Try to get a token to verify credentials work
        credential.get_token("https://vault.azure.net/.default")
        return True, None
    except ClientAuthenticationError as e:
        return False, f"Azure authentication failed: {str(e)}"
    except Exception as e:
        return False, f"Failed to initialize Azure credentials: {str(e)}"


def pytest_collection_modifyitems(config, items):
    """Skip e2e tests if KeyVault is not properly configured"""
    is_available, reason = _check_keyvault_available()

    if not is_available:
        skip_e2e = pytest.mark.skip(reason=f"E2E tests skipped: {reason}")
        for item in items:
            if "e2e" in item.nodeid:
                item.add_marker(skip_e2e)
