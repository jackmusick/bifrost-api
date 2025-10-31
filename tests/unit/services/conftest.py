"""
Pytest fixtures for infrastructure service tests.

Provides mocks for:
- BlobServiceClient and related blob operations
- SecretClient for Key Vault operations
- Temporary file and directory setup
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture
def mock_blob_service_client():
    """Mock BlobServiceClient with full blob operations support"""
    with patch("shared.blob_storage.BlobServiceClient") as mock_service_class:
        # Create mock instances
        mock_service = MagicMock()
        mock_blob_client = MagicMock()
        mock_container_client = MagicMock()

        # Setup service class to return mock instance
        mock_service_class.from_connection_string.return_value = mock_service

        # Setup blob and container client returns
        mock_service.get_blob_client.return_value = mock_blob_client
        mock_service.get_container_client.return_value = mock_container_client
        mock_service.create_container.return_value = mock_container_client
        mock_container_client.get_blob_client.return_value = mock_blob_client

        # Setup account name for SAS URL generation
        mock_service.account_name = "teststorage"

        yield {
            "service_class": mock_service_class,
            "service": mock_service,
            "blob": mock_blob_client,
            "container": mock_container_client,
        }


@pytest.fixture
def mock_secret_client():
    """Mock SecretClient for Key Vault operations"""
    with patch("shared.keyvault.SecretClient") as mock_client_class:
        # Create mock instance
        mock_instance = MagicMock()
        mock_client_class.return_value = mock_instance

        # In-memory secret storage for testing
        secrets_store = {}

        async def mock_set_secret(name, value):
            secrets_store[name] = value
            secret_obj = MagicMock()
            secret_obj.name = name
            secret_obj.value = value
            return secret_obj

        async def mock_get_secret(name):
            if name not in secrets_store:
                from azure.core.exceptions import ResourceNotFoundError
                raise ResourceNotFoundError(f"Secret not found: {name}")
            secret_obj = MagicMock()
            secret_obj.name = name
            secret_obj.value = secrets_store[name]
            return secret_obj

        async def mock_list_properties():
            props_list = []
            for name in secrets_store:
                prop = MagicMock()
                prop.name = name
                props_list.append(prop)
            # Return async generator
            for prop in props_list:
                yield prop

        async def mock_delete_secret(name):
            if name in secrets_store:
                del secrets_store[name]
            return MagicMock()

        # Attach async methods to mock
        mock_instance.set_secret = AsyncMock(side_effect=mock_set_secret)
        mock_instance.get_secret = AsyncMock(side_effect=mock_get_secret)
        mock_instance.list_properties_of_secrets = mock_list_properties
        mock_instance.delete_secret = AsyncMock(side_effect=mock_delete_secret)

        # Store secrets dictionary for test access
        mock_instance._secrets_store = secrets_store

        yield {
            "client_class": mock_client_class,
            "instance": mock_instance,
            "secrets_store": secrets_store,
        }


@pytest.fixture
def mock_default_credential():
    """Mock DefaultAzureCredential"""
    with patch("shared.keyvault.DefaultAzureCredential") as mock:
        yield mock


@pytest.fixture
def sample_blob_data():
    """Sample blob content for upload/download tests"""
    return b"Test blob content for execution logs"


@pytest.fixture
def sample_json_blob():
    """Sample JSON blob data"""
    import json
    data = {
        "execution_id": "test-exec-123",
        "status": "completed",
        "result": "success",
        "data": {"key": "value"}
    }
    return json.dumps(data).encode('utf-8')


@pytest.fixture
def sample_logs():
    """Sample execution logs"""
    return [
        {
            "timestamp": "2024-01-01T10:00:00Z",
            "level": "INFO",
            "message": "Execution started",
            "data": {}
        },
        {
            "timestamp": "2024-01-01T10:00:01Z",
            "level": "INFO",
            "message": "Processing item 1",
            "data": {"item": 1}
        },
        {
            "timestamp": "2024-01-01T10:00:02Z",
            "level": "INFO",
            "message": "Execution completed",
            "data": {"result": "success"}
        }
    ]


@pytest.fixture
def sample_execution_result():
    """Sample execution result data"""
    return {
        "status": "completed",
        "duration_seconds": 15.5,
        "items_processed": 100,
        "errors": 0,
        "warnings": 2
    }


@pytest.fixture
def sample_secret():
    """Sample secret for Key Vault tests"""
    return {
        "name": "test-secret",
        "value": "super-secret-value-123",
        "enabled": True
    }


@pytest.fixture
def temp_test_dir(tmp_path):
    """Provides a temporary directory for file operations tests"""
    return tmp_path


@pytest.fixture
def mock_workspace_service():
    """Mock WorkspaceService for zip service tests"""
    with patch("shared.services.zip_service.get_workspace_service") as mock:
        service = MagicMock()

        # Sample files for listing
        sample_files = [
            {"path": "file1.txt", "isDirectory": False, "size": 1024},
            {"path": "file2.py", "isDirectory": False, "size": 2048},
            {"path": "subdir/file3.json", "isDirectory": False, "size": 512},
        ]

        def mock_list_files(directory_path=""):
            return sample_files

        # Use AsyncMock for async method
        service.list_files = mock_list_files
        service.read_file = AsyncMock(return_value=b"Sample file content")

        mock.return_value = service
        yield {"service": service, "mock": mock}


# ====================  OAuth Storage Service Fixtures ====================


@pytest.fixture
def mock_table_service():
    """Mock AsyncTableStorageService for OAuth storage"""
    with patch("shared.services.oauth_storage_service.AsyncTableStorageService") as mock:
        instance = AsyncMock()
        instance.insert_entity = AsyncMock()  # Async
        instance.get_entity = AsyncMock()     # Async
        instance.upsert_entity = AsyncMock()  # Async
        instance.delete_entity = AsyncMock()  # Async
        instance.query_entities = AsyncMock() # Async
        mock.return_value = instance
        yield instance


@pytest.fixture
def mock_keyvault_client():
    """Mock KeyVaultClient for OAuth storage"""
    with patch("shared.services.oauth_storage_service.KeyVaultClient") as mock_kv_class:
        # Create mock instance that will be returned when KeyVaultClient() is called
        mock_instance = MagicMock()
        mock_instance._client = MagicMock()

        # When KeyVaultClient() is instantiated, return our mock instance
        mock_kv_class.return_value = mock_instance

        yield mock_kv_class


@pytest.fixture
def sample_oauth_connection():
    """Sample OAuth connection data for testing"""
    from datetime import datetime
    return {
        "connection_id": "conn-123",
        "connection_name": "test_connection",
        "name": "Test Connection",
        "oauth_flow_type": "authorization_code",
        "client_id": "client-id-123",
        "client_secret": "client-secret-456",
        "org_id": "org-123",
        "authorization_url": "https://oauth.example.com/authorize",
        "token_url": "https://oauth.example.com/token",
        "scopes": "openid profile email",
        "redirect_uri": "/oauth/callback/test_connection",
        "status": "not_connected",
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
        "created_by": "user@example.com"
    }


@pytest.fixture
def sample_oauth_request():
    """Sample create OAuth connection request"""
    return {
        "connection_name": "test_connection",
        "description": "Test OAuth Connection",
        "oauth_flow_type": "authorization_code",
        "client_id": "client-123",
        "client_secret": "secret-456",
        "authorization_url": "https://oauth.example.com/authorize",
        "token_url": "https://oauth.example.com/token",
        "scopes": "openid profile email"
    }


@pytest.fixture
def sample_oauth_update_request():
    """Sample update OAuth connection request"""
    return {
        "client_id": "new-client-id",
        "client_secret": "new-secret",
        "authorization_url": "https://oauth.example.com/authorize",
        "token_url": "https://oauth.example.com/token",
        "scopes": "openid profile email offline_access"
    }


@pytest.fixture
def mock_config_table_response():
    """Sample Config table entity response"""
    from datetime import datetime
    import json
    return {
        "PartitionKey": "org-123",
        "RowKey": "config:oauth_test_connection_metadata",
        "Value": json.dumps({
            "oauth_flow_type": "authorization_code",
            "client_id": "client-123",
            "authorization_url": "https://oauth.example.com/authorize",
            "token_url": "https://oauth.example.com/token",
            "scopes": "openid profile email",
            "redirect_uri": "/oauth/callback/test_connection",
            "status": "not_connected"
        }),
        "Type": "json",
        "Description": "OAuth metadata for test_connection",
        "UpdatedAt": datetime.utcnow().isoformat(),
        "UpdatedBy": "user@example.com"
    }


# ====================  Workspace Service Fixtures ====================


@pytest.fixture
def mock_filesystem():
    """Mock file system operations for workspace service"""
    with patch("shared.services.workspace_service.Path") as mock_path:
        # Create mock path instance
        path_instance = MagicMock()
        mock_path.return_value = path_instance

        # Setup default behaviors
        path_instance.exists.return_value = True
        path_instance.is_dir.return_value = True
        path_instance.is_file.return_value = True
        path_instance.mkdir.return_value = None
        path_instance.parent = MagicMock()
        path_instance.parent.mkdir.return_value = None
        path_instance.stat.return_value = MagicMock(st_size=1024, st_mtime=1000000000)
        path_instance.name = "test_file.py"
        path_instance.rglob.return_value = []
        path_instance.read_bytes.return_value = b"print('Hello')"
        path_instance.write_bytes.return_value = None
        path_instance.unlink.return_value = None
        path_instance.rmdir.return_value = None

        yield {"path": mock_path, "instance": path_instance}


@pytest.fixture
def workspace_test_data():
    """Sample workspace test data"""
    return {
        "workspace_path": "/workspace",
        "test_files": [
            "workflow1.py",
            "workflow2.py",
            "subdir/workflow3.py",
            "config.yaml"
        ],
        "file_contents": {
            "workflow1.py": b"def workflow_1():\n    print('Workflow 1')",
            "workflow2.py": b"def workflow_2():\n    print('Workflow 2')",
            "subdir/workflow3.py": b"def workflow_3():\n    print('Workflow 3')"
        }
    }


@pytest.fixture
def mock_shutil():
    """Mock shutil for directory operations"""
    with patch("shutil.rmtree") as mock_rmtree:
        yield {"rmtree": mock_rmtree}


# ====================  OAuth Token Fixtures ====================


@pytest.fixture
def sample_oauth_tokens():
    """Sample OAuth tokens for testing"""
    from datetime import datetime, timedelta
    expires_at = datetime.utcnow() + timedelta(hours=1)
    return {
        "access_token": "access_token_xyz123",
        "refresh_token": "refresh_token_xyz456",
        "token_type": "Bearer",
        "expires_at": expires_at,
        "expires_in": 3600
    }


@pytest.fixture
def sample_oauth_response_metadata():
    """Sample OAuth response metadata"""
    from datetime import datetime, timedelta
    expires_at = datetime.utcnow() + timedelta(hours=1)
    return {
        "access_token": "access_token_xyz123",
        "refresh_token": "refresh_token_xyz456",
        "token_type": "Bearer",
        "expires_at": expires_at.isoformat(),
        "scope": "openid profile email"
    }


# ====================  Helper Fixtures ====================


@pytest.fixture
def test_org_id():
    """Test organization ID"""
    return "org-test-123"


@pytest.fixture
def test_user_id():
    """Test user ID"""
    return "user@example.com"


@pytest.fixture
def test_connection_name():
    """Test connection name"""
    return "test_oauth_connection"
