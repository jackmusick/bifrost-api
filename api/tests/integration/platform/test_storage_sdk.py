"""
Integration tests for Bifrost Storage SDK

Tests that workflows can use the storage module to upload/download files
from Azure Blob Storage.
"""

import pytest


# Import bifrost context functions directly
# This ensures we use the same ContextVar instance that storage module uses
from bifrost._context import set_execution_context, clear_execution_context


@pytest.fixture(autouse=True, scope="function")
async def ensure_clean_context_and_blob_client():
    """Ensure each test starts with a clean execution context and blob client"""
    import shared.blob_storage

    # Clear context before test
    clear_execution_context()

    # Close and reset blob service singleton before test to get fresh client with new event loop
    if shared.blob_storage._blob_storage_service:
        try:
            await shared.blob_storage._blob_storage_service.blob_service_client.close()
        except Exception:
            pass  # Ignore errors during cleanup
        shared.blob_storage._blob_storage_service = None

    yield

    # Clear context after test
    clear_execution_context()


@pytest.fixture
def test_context():
    """Create a test execution context"""
    from shared.context import ExecutionContext, Organization

    org = Organization(id="test-org", name="Test Org", is_active=True)
    return ExecutionContext(
        user_id="test-user",
        email="test@example.com",
        name="Test User",
        scope="test-org",
        organization=org,
        is_platform_admin=False,
        is_function_key=False,
        execution_id="test-exec-storage"
    )


@pytest.fixture
def storage_module():
    """Import bifrost package to get storage"""
    # Import the entire bifrost package properly to avoid circular imports
    import bifrost
    return bifrost


class TestStorageSDK:
    """Test suite for storage SDK operations"""

    async def test_upload_and_download(self, test_context, storage_module):
        """Test uploading and downloading a file"""
        # Set context
        set_execution_context(test_context)

        try:
            # Test data
            test_data = b"Test storage content for integration test"
            container = "files"
            path = "tests/storage_test.txt"

            # Upload file
            blob_uri = await storage_module.storage.upload(
                container=container,
                path=path,
                data=test_data,
                content_type="text/plain"
            )

            assert blob_uri is not None
            assert container in blob_uri
            assert path in blob_uri

            # Download file
            downloaded_data = await storage_module.storage.download(
                container=container,
                path=path
            )

            assert downloaded_data == test_data

            # Clean up
            await storage_module.storage.delete(container, path)

        finally:
            clear_execution_context()

    async def test_get_metadata(self, test_context, storage_module):
        """Test getting blob metadata"""
        set_execution_context(test_context)

        try:
            # Upload a test file
            test_data = b"Metadata test content"
            container = "files"
            path = "tests/metadata_test.txt"

            await storage_module.storage.upload(
                container=container,
                path=path,
                data=test_data,
                content_type="text/plain"
            )

            # Get metadata
            metadata = await storage_module.storage.get_metadata(container, path)

            assert metadata is not None
            assert "name" in metadata
            assert "size" in metadata
            assert metadata["size"] == len(test_data)
            assert "content_type" in metadata
            assert metadata["content_type"] == "text/plain"
            assert "last_modified" in metadata
            assert "etag" in metadata

            # Clean up
            await storage_module.storage.delete(container, path)

        finally:
            clear_execution_context()

    async def test_generate_sas_url(self, test_context, storage_module):
        """Test generating SAS URL for download"""
        set_execution_context(test_context)

        try:
            # Upload a test file
            test_data = b"SAS URL test content"
            container = "files"
            path = "tests/sas_test.txt"

            await storage_module.storage.upload(
                container=container,
                path=path,
                data=test_data,
                content_type="text/plain"
            )

            # Generate SAS URL
            sas_url = await storage_module.storage.generate_url(
                container=container,
                path=path,
                expiry_hours=1
            )

            assert sas_url is not None
            assert container in sas_url
            assert path in sas_url
            assert "?" in sas_url  # SAS token query string

            # Clean up
            await storage_module.storage.delete(container, path)

        finally:
            clear_execution_context()

    async def test_delete_nonexistent_file(self, test_context, storage_module):
        """Test deleting a file that doesn't exist returns False"""
        set_execution_context(test_context)

        try:
            result = await storage_module.storage.delete(
                container="files",
                path="tests/nonexistent_file.txt"
            )

            assert result is False

        finally:
            clear_execution_context()

    async def test_download_nonexistent_file(self, test_context, storage_module):
        """Test downloading a file that doesn't exist raises FileNotFoundError"""
        set_execution_context(test_context)

        try:
            with pytest.raises(FileNotFoundError):
                await storage_module.storage.download(
                    container="files",
                    path="tests/nonexistent_file.txt"
                )

        finally:
            clear_execution_context()

    async def test_invalid_data_type(self, test_context, storage_module):
        """Test uploading non-bytes data raises ValueError"""
        set_execution_context(test_context)

        try:
            with pytest.raises(ValueError, match="data must be bytes"):
                await storage_module.storage.upload(
                    container="files",
                    path="tests/invalid.txt",
                    data="This is a string, not bytes",  # Wrong type
                    content_type="text/plain"
                )

        finally:
            clear_execution_context()

    async def test_missing_execution_context(self, storage_module):
        """Test that operations require execution context"""
        # Clear any existing context
        clear_execution_context()

        try:
            with pytest.raises(RuntimeError, match="No execution context"):
                await storage_module.storage.upload(
                    container="files",
                    path="tests/test.txt",
                    data=b"test",
                    content_type="text/plain"
                )
        finally:
            # Don't leave the context cleared for other tests
            clear_execution_context()

    async def test_binary_content_upload_download(self, test_context, storage_module):
        """Test uploading and downloading binary content"""
        set_execution_context(test_context)

        try:
            # Create test binary data (PNG header signature)
            test_data = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR' + b'\x00' * 100
            container = "files"
            path = "tests/binary_test.png"

            # Upload
            blob_uri = await storage_module.storage.upload(
                container=container,
                path=path,
                data=test_data,
                content_type="image/png"
            )

            assert blob_uri is not None

            # Download
            downloaded_data = await storage_module.storage.download(container, path)

            assert downloaded_data == test_data
            assert len(downloaded_data) == len(test_data)

            # Clean up
            await storage_module.storage.delete(container, path)

        finally:
            clear_execution_context()

    async def test_csv_workflow_pattern(self, test_context, storage_module):
        """Test the CSV export workflow pattern (like ninjaone_device_export)"""
        set_execution_context(test_context)

        try:
            # Simulate CSV export
            csv_content = "Name,Value\nTest,123\nExample,456"
            filename = "test_export.csv"
            blob_path = f"test-exports/{filename}"

            # Upload CSV
            blob_uri = await storage_module.storage.upload(
                container="files",
                path=blob_path,
                data=csv_content.encode("utf-8"),
                content_type="text/csv"
            )

            assert blob_uri is not None

            # Generate download URL (7 day expiry like in ninjaone workflow)
            download_url = await storage_module.storage.generate_url(
                container="files",
                path=blob_path,
                expiry_hours=24 * 7
            )

            assert download_url is not None
            assert "?" in download_url  # Has SAS token

            # Verify file can be downloaded
            downloaded = await storage_module.storage.download("files", blob_path)
            assert downloaded.decode("utf-8") == csv_content

            # Clean up
            await storage_module.storage.delete("files", blob_path)

        finally:
            clear_execution_context()
