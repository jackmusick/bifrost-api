"""
Pytest configuration for integration tests

Sets up the test environment to use Azurite on custom ports (10100-10102)
"""

import os
import pytest
from unittest.mock import MagicMock, patch
from azure.data.tables import TableServiceClient


@pytest.fixture(scope="session", autouse=True)
def setup_azurite_connection():
    """
    Configure Azure Storage connection string for integration tests.

    Uses Azurite running on custom ports (from docker-compose.yml):
    - Blob: 10100
    - Queue: 10101
    - Table: 10102

    Also creates required tables.
    """
    connection_string = (
        "DefaultEndpointsProtocol=http;"
        "AccountName=devstoreaccount1;"
        "AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;"
        "BlobEndpoint=http://localhost:10100/devstoreaccount1;"
        "QueueEndpoint=http://localhost:10101/devstoreaccount1;"
        "TableEndpoint=http://localhost:10102/devstoreaccount1;"
    )

    # Set environment variable for all tests in this session
    os.environ["AzureWebJobsStorage"] = connection_string

    # Create tables needed for testing
    table_service = TableServiceClient.from_connection_string(connection_string)
    required_tables = ["Config", "Entities", "Relationships", "Organizations"]

    for table_name in required_tables:
        try:
            table_service.create_table(table_name)
        except Exception:
            # Table might already exist (if not using in-memory persistence)
            pass

    yield

    # Cleanup (optional - tables will be cleared since azurite-test uses --inMemoryPersistence)


@pytest.fixture(scope="session", autouse=True)
def mock_keyvault():
    """
    Mock Azure Key Vault for integration tests.

    Returns a mock that simulates a healthy Key Vault with basic secret operations.
    This prevents integration tests from requiring actual Azure Key Vault connectivity.
    """
    # Create a mock secrets dictionary to store test secrets
    mock_secrets = {}

    def mock_get_secret(name):
        """Mock getting a secret"""
        if name not in mock_secrets:
            raise Exception(f"Secret '{name}' not found")
        mock_secret = MagicMock()
        mock_secret.value = mock_secrets[name]
        mock_secret.name = name
        return mock_secret

    def mock_set_secret(name, value):
        """Mock setting a secret"""
        mock_secrets[name] = value
        mock_secret = MagicMock()
        mock_secret.value = value
        mock_secret.name = name
        return mock_secret

    def mock_list_properties():
        """Mock listing secret properties"""
        return [MagicMock(name=name) for name in mock_secrets.keys()]

    def mock_delete_secret(name):
        """Mock deleting a secret"""
        if name in mock_secrets:
            del mock_secrets[name]
        return MagicMock(name=name)

    # Create mock Key Vault client
    mock_kv_client = MagicMock()
    mock_kv_client.vault_url = "https://test-vault.vault.azure.net/"
    mock_kv_client.get_secret.side_effect = mock_get_secret
    mock_kv_client.set_secret.side_effect = mock_set_secret
    mock_kv_client.list_properties_of_secrets.side_effect = mock_list_properties
    mock_kv_client.begin_delete_secret.side_effect = mock_delete_secret
    mock_kv_client.health_check.return_value = {
        "status": "healthy",
        "can_connect": True,
        "can_list_secrets": True,
        "can_get_secrets": True,
        "secret_count": len(mock_secrets)
    }

    # Patch the KeyVaultClient class to return our mock
    with patch('shared.keyvault.KeyVaultClient') as mock_class:
        mock_class.return_value = mock_kv_client
        yield mock_kv_client
