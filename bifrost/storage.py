"""
Storage Module - Cloud Blob Storage Operations

Provides access to Azure Blob Storage for workflows.
All methods use consistent (container, path) signature.

Containers:
- uploads: Form-uploaded files (temporary)
- files: Workflow-generated files (persistent)
- execution-data: Execution artifacts (internal)

Usage:
    from bifrost import storage

    # Upload a file
    blob_uri = storage.upload(
        container="files",
        path="exports/report.csv",
        data=csv_content.encode("utf-8"),
        content_type="text/csv"
    )

    # Generate downloadable URL (24 hour expiry by default)
    download_url = storage.generate_url(
        container="files",
        path="exports/report.csv",
        expiry_hours=24
    )

    # Download a file
    file_data = storage.download(
        container="uploads",
        path="user-files/input.xlsx"
    )

    # Get metadata
    metadata = storage.get_metadata(
        container="files",
        path="exports/report.csv"
    )
    # Returns: {name, size, content_type, last_modified, etag}

    # Delete a file
    storage.delete(
        container="files",
        path="exports/old-report.csv"
    )
"""

from typing import Any

from ._internal import get_context
from shared.blob_storage import get_blob_service


class storage:
    """
    Cloud blob storage operations for workflows.

    All methods use (container, path) signature for consistency.
    Validates execution context before performing operations.
    """

    @staticmethod
    def download(container: str, path: str) -> bytes:
        """
        Download a blob from storage.

        Args:
            container: Container name (uploads, files, execution-data)
            path: Blob path within container (e.g., "exports/report.csv")

        Returns:
            Blob content as bytes

        Raises:
            ValueError: If context is invalid
            FileNotFoundError: If blob doesn't exist
            Exception: For storage errors

        Example:
            file_data = storage.download("uploads", "user-files/input.xlsx")
            text_content = file_data.decode("utf-8")
        """
        # Validate execution context
        get_context()

        # Get blob service
        blob_service = get_blob_service()

        # Download blob
        return blob_service.download_blob(container, path)

    @staticmethod
    def upload(
        container: str,
        path: str,
        data: bytes,
        content_type: str = "application/octet-stream"
    ) -> str:
        """
        Upload a blob to storage.

        Args:
            container: Container name (uploads, files, execution-data)
            path: Blob path within container (e.g., "exports/report.csv")
            data: File content as bytes
            content_type: MIME type (default: application/octet-stream)

        Returns:
            Blob URI (e.g., "https://storage.blob.core.windows.net/files/exports/report.csv")

        Raises:
            ValueError: If context is invalid or data is not bytes
            Exception: For storage errors

        Example:
            csv_data = "Name,Value\\nTest,123".encode("utf-8")
            blob_uri = storage.upload(
                container="files",
                path="exports/report.csv",
                data=csv_data,
                content_type="text/csv"
            )
        """
        # Validate execution context
        get_context()

        # Validate data type
        if not isinstance(data, bytes):
            raise ValueError(f"data must be bytes, got {type(data).__name__}")

        # Get blob service
        blob_service = get_blob_service()

        # Upload blob
        return blob_service.upload_blob(container, path, data, content_type)

    @staticmethod
    def generate_url(
        container: str,
        path: str,
        expiry_hours: int = 24
    ) -> str:
        """
        Generate a time-limited SAS URL for downloading a blob.

        Args:
            container: Container name (uploads, files, execution-data)
            path: Blob path within container
            expiry_hours: URL expiry time in hours (default: 24)

        Returns:
            SAS URL with read permission and expiry

        Raises:
            ValueError: If context is invalid or expiry_hours <= 0
            FileNotFoundError: If blob doesn't exist
            Exception: For storage errors

        Example:
            # Generate 7-day download link
            download_url = storage.generate_url(
                container="files",
                path="exports/report.csv",
                expiry_hours=24 * 7
            )
        """
        # Validate execution context
        get_context()

        # Validate expiry
        if expiry_hours <= 0:
            raise ValueError(f"expiry_hours must be positive, got {expiry_hours}")

        # Get blob service
        blob_service = get_blob_service()

        # Generate SAS URL
        return blob_service.generate_sas_url(container, path, expiry_hours)

    @staticmethod
    def get_metadata(container: str, path: str) -> dict[str, Any]:
        """
        Get blob metadata.

        Args:
            container: Container name (uploads, files, execution-data)
            path: Blob path within container

        Returns:
            Metadata dict with keys:
            - name: Blob name
            - size: Size in bytes
            - content_type: MIME type
            - last_modified: Last modified timestamp (ISO 8601)
            - etag: ETag for versioning

        Raises:
            ValueError: If context is invalid
            FileNotFoundError: If blob doesn't exist
            Exception: For storage errors

        Example:
            metadata = storage.get_metadata("files", "exports/report.csv")
            print(f"File size: {metadata['size']} bytes")
            print(f"Modified: {metadata['last_modified']}")
        """
        # Validate execution context
        get_context()

        # Get blob service
        blob_service = get_blob_service()

        # Get metadata
        return blob_service.get_blob_metadata(container, path)

    @staticmethod
    def delete(container: str, path: str) -> bool:
        """
        Delete a blob from storage.

        Args:
            container: Container name (uploads, files, execution-data)
            path: Blob path within container

        Returns:
            True if deleted, False if didn't exist

        Raises:
            ValueError: If context is invalid
            Exception: For storage errors

        Example:
            storage.delete("files", "exports/old-report.csv")
        """
        # Validate execution context
        get_context()

        # Get blob service
        blob_service = get_blob_service()

        # Delete blob
        return blob_service.delete_blob(container, path)
