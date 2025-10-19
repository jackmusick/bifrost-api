"""
Pytest configuration for integration tests

Sets up the test environment to use Azurite on custom ports (10100-10102)
"""

import os
import pytest
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
