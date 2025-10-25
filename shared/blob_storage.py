"""
Blob Storage Service for Bifrost Integrations
Handles large execution data (logs, results, snapshots) that exceed Table Storage limits
"""

import json
import logging
import os
import threading
import uuid
from datetime import datetime, timedelta
from typing import Any

from azure.core.exceptions import ResourceExistsError
from azure.storage.blob import BlobServiceClient, BlobSasPermissions, ContainerClient, ContentSettings, generate_blob_sas

logger = logging.getLogger(__name__)

# Container for execution-related data
EXECUTION_CONTAINER = "execution-data"

# Lock for thread-safe container creation
_container_locks: dict[str, threading.Lock] = {}
_container_locks_lock = threading.Lock()


class BlobStorageService:
    """
    Service for storing and retrieving execution data in Azure Blob Storage.

    Used for data that exceeds Azure Table Storage limits (64KB per entity):
    - Execution logs (can be thousands of entries)
    - Execution results (can be large JSON or HTML)
    - State snapshots (workflow checkpoints)
    """

    def __init__(self, connection_string: str | None = None):
        """
        Initialize Blob Storage client

        Args:
            connection_string: Optional connection string override (uses AzureWebJobsStorage if not provided)

        Note:
            Container creation uses try/except pattern instead of exists() check
            to avoid SDK logging benign "ContainerAlreadyExists" warnings.
        """
        if connection_string is None:
            connection_string = os.environ.get("AzureWebJobsStorage")

        if not connection_string:
            raise ValueError("AzureWebJobsStorage environment variable not set")

        # Expand UseDevelopmentStorage=true shorthand for blob storage
        if connection_string == "UseDevelopmentStorage=true":
            connection_string = "DefaultEndpointsProtocol=http;AccountName=devstoreaccount1;AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;BlobEndpoint=http://127.0.0.1:10000/devstoreaccount1;QueueEndpoint=http://127.0.0.1:10001/devstoreaccount1;TableEndpoint=http://127.0.0.1:10002/devstoreaccount1;"

        self.connection_string = connection_string
        self.blob_service_client = BlobServiceClient.from_connection_string(connection_string)

        # Ensure container exists
        self._ensure_container_exists(EXECUTION_CONTAINER)

        logger.debug(f"BlobStorageService initialized for container: {EXECUTION_CONTAINER}")

    @staticmethod
    def _make_url_browser_accessible(url: str) -> str:
        """
        Convert internal Docker URLs to browser-accessible URLs

        Args:
            url: Blob URL (may contain internal Docker hostnames)

        Returns:
            Browser-accessible URL with localhost
        """
        # Replace azurite Docker hostname with localhost for browser access
        return url.replace('azurite:10000', 'localhost:10000')

    def _ensure_container_exists(self, container_name: str) -> ContainerClient:
        """
        Ensure blob container exists, create if it doesn't.
        Thread-safe to handle concurrent initialization.

        Args:
            container_name: Name of the container

        Returns:
            ContainerClient instance
        """
        container_client = self.blob_service_client.get_container_client(container_name)

        # Get or create a lock for this specific container
        with _container_locks_lock:
            if container_name not in _container_locks:
                _container_locks[container_name] = threading.Lock()
            container_lock = _container_locks[container_name]

        # Use the container-specific lock to prevent race conditions
        with container_lock:
            # Check if container exists first to avoid 409 warnings in logs
            if not container_client.exists():
                try:
                    container_client.create_container()
                    logger.info(f"Created blob container: {container_name}")
                except ResourceExistsError:
                    # Race condition: container was created between exists() and create_container()
                    # This should be rare now with locks, but keeping for safety
                    logger.debug(f"Blob container already exists (race condition): {container_name}")
                except Exception as e:
                    logger.error(f"Failed to create container: {str(e)}")
                    raise
            else:
                logger.debug(f"Blob container already exists: {container_name}")

        return container_client

    def upload_logs(self, execution_id: str, logs: list[dict[str, Any]]) -> str:
        """
        Upload execution logs to blob storage

        Args:
            execution_id: Execution ID (UUID)
            logs: List of log entries (each with timestamp, level, message, data)

        Returns:
            Blob path (e.g., "abc-123/logs.json")
        """
        blob_path = f"{execution_id}/logs.json"

        try:
            container_client = self.blob_service_client.get_container_client(EXECUTION_CONTAINER)
            blob_client = container_client.get_blob_client(blob_path)

            # Upload as JSON
            logs_json = json.dumps(logs, indent=2)
            blob_client.upload_blob(logs_json, overwrite=True)

            logger.info(
                f"Uploaded logs to blob storage: {blob_path}",
                extra={"execution_id": execution_id, "log_count": len(logs)}
            )

            return blob_path

        except Exception as e:
            logger.error(
                f"Failed to upload logs to blob storage: {str(e)}",
                extra={"execution_id": execution_id},
                exc_info=True
            )
            raise

    def get_logs(self, execution_id: str) -> list[dict[str, Any]] | None:
        """
        Retrieve execution logs from blob storage

        Args:
            execution_id: Execution ID (UUID)

        Returns:
            List of log entries or None if not found
        """
        blob_path = f"{execution_id}/logs.json"

        try:
            container_client = self.blob_service_client.get_container_client(EXECUTION_CONTAINER)
            blob_client = container_client.get_blob_client(blob_path)

            if not blob_client.exists():
                logger.debug(f"Logs blob not found: {blob_path}")
                return None

            # Download and parse JSON
            blob_data = blob_client.download_blob().readall()
            logs = json.loads(blob_data)

            logger.debug(
                f"Retrieved logs from blob storage: {blob_path}",
                extra={"execution_id": execution_id, "log_count": len(logs)}
            )

            return logs

        except Exception as e:
            logger.error(
                f"Failed to retrieve logs from blob storage: {str(e)}",
                extra={"execution_id": execution_id},
                exc_info=True
            )
            return None

    def upload_result(self, execution_id: str, result: dict[str, Any] | str) -> str:
        """
        Upload execution result to blob storage

        Args:
            execution_id: Execution ID (UUID)
            result: Result data (dict for JSON, str for HTML/text)

        Returns:
            Blob path (e.g., "abc-123/result.json" or "abc-123/result.html")
        """
        # Determine file extension based on content type
        if isinstance(result, str):
            # Check if it looks like HTML
            if result.strip().startswith('<') and '>' in result:
                blob_path = f"{execution_id}/result.html"
                content = result
            else:
                blob_path = f"{execution_id}/result.txt"
                content = result
        else:
            blob_path = f"{execution_id}/result.json"
            content = json.dumps(result, indent=2)

        try:
            container_client = self.blob_service_client.get_container_client(EXECUTION_CONTAINER)
            blob_client = container_client.get_blob_client(blob_path)

            # Upload content
            blob_client.upload_blob(content, overwrite=True)

            logger.info(
                f"Uploaded result to blob storage: {blob_path}",
                extra={"execution_id": execution_id}
            )

            return blob_path

        except Exception as e:
            logger.error(
                f"Failed to upload result to blob storage: {str(e)}",
                extra={"execution_id": execution_id},
                exc_info=True
            )
            raise

    def get_result(self, execution_id: str) -> dict[str, Any] | str | None:
        """
        Retrieve execution result from blob storage

        Tries result.json, result.html, and result.txt in that order

        Args:
            execution_id: Execution ID (UUID)

        Returns:
            Result data (dict for JSON, str for HTML/text) or None if not found
        """
        # Try different file types
        for ext in ['json', 'html', 'txt']:
            blob_path = f"{execution_id}/result.{ext}"

            try:
                container_client = self.blob_service_client.get_container_client(EXECUTION_CONTAINER)
                blob_client = container_client.get_blob_client(blob_path)

                if not blob_client.exists():
                    continue

                # Download content
                blob_data = blob_client.download_blob().readall()

                # Parse based on extension
                if ext == 'json':
                    result = json.loads(blob_data)
                else:
                    result = blob_data.decode('utf-8')

                logger.debug(
                    f"Retrieved result from blob storage: {blob_path}",
                    extra={"execution_id": execution_id}
                )

                return result

            except Exception as e:
                logger.error(
                    f"Failed to retrieve result from blob storage: {str(e)}",
                    extra={"execution_id": execution_id, "blob_path": blob_path},
                    exc_info=True
                )
                continue

        logger.debug(f"Result blob not found for execution: {execution_id}")
        return None

    def upload_snapshot(self, execution_id: str, snapshot: list[dict[str, Any]]) -> str:
        """
        Upload state snapshot to blob storage

        Args:
            execution_id: Execution ID (UUID)
            snapshot: State snapshot data

        Returns:
            Blob path (e.g., "abc-123/snapshot.json")
        """
        blob_path = f"{execution_id}/snapshot.json"

        try:
            container_client = self.blob_service_client.get_container_client(EXECUTION_CONTAINER)
            blob_client = container_client.get_blob_client(blob_path)

            # Upload as JSON
            snapshot_json = json.dumps(snapshot, indent=2)
            blob_client.upload_blob(snapshot_json, overwrite=True)

            logger.info(
                f"Uploaded snapshot to blob storage: {blob_path}",
                extra={"execution_id": execution_id}
            )

            return blob_path

        except Exception as e:
            logger.error(
                f"Failed to upload snapshot to blob storage: {str(e)}",
                extra={"execution_id": execution_id},
                exc_info=True
            )
            raise

    def get_snapshot(self, execution_id: str) -> list[dict[str, Any]] | None:
        """
        Retrieve state snapshot from blob storage

        Args:
            execution_id: Execution ID (UUID)

        Returns:
            State snapshot data or None if not found
        """
        blob_path = f"{execution_id}/snapshot.json"

        try:
            container_client = self.blob_service_client.get_container_client(EXECUTION_CONTAINER)
            blob_client = container_client.get_blob_client(blob_path)

            if not blob_client.exists():
                logger.debug(f"Snapshot blob not found: {blob_path}")
                return None

            # Download and parse JSON
            blob_data = blob_client.download_blob().readall()
            snapshot = json.loads(blob_data)

            logger.debug(
                f"Retrieved snapshot from blob storage: {blob_path}",
                extra={"execution_id": execution_id}
            )

            return snapshot

        except Exception as e:
            logger.error(
                f"Failed to retrieve snapshot from blob storage: {str(e)}",
                extra={"execution_id": execution_id},
                exc_info=True
            )
            return None

    def upload_variables(self, execution_id: str, variables: dict[str, Any]) -> str:
        """
        Upload execution variables to blob storage

        Args:
            execution_id: Execution ID (UUID)
            variables: Dictionary of captured variables

        Returns:
            Blob path (e.g., "abc-123/variables.json")
        """
        blob_path = f"{execution_id}/variables.json"

        try:
            container_client = self.blob_service_client.get_container_client(EXECUTION_CONTAINER)
            blob_client = container_client.get_blob_client(blob_path)

            # Upload as JSON
            variables_json = json.dumps(variables, indent=2)
            blob_client.upload_blob(variables_json, overwrite=True)

            logger.info(
                f"Uploaded variables to blob storage: {blob_path}",
                extra={"execution_id": execution_id, "variable_count": len(variables)}
            )

            return blob_path

        except Exception as e:
            logger.error(
                f"Failed to upload variables to blob storage: {str(e)}",
                extra={"execution_id": execution_id},
                exc_info=True
            )
            raise

    def get_variables(self, execution_id: str) -> dict[str, Any] | None:
        """
        Retrieve execution variables from blob storage

        Args:
            execution_id: Execution ID (UUID)

        Returns:
            Dictionary of variables or None if not found
        """
        blob_path = f"{execution_id}/variables.json"

        try:
            container_client = self.blob_service_client.get_container_client(EXECUTION_CONTAINER)
            blob_client = container_client.get_blob_client(blob_path)

            if not blob_client.exists():
                logger.debug(f"Variables blob not found: {blob_path}")
                return None

            # Download and parse JSON
            blob_data = blob_client.download_blob().readall()
            variables = json.loads(blob_data)

            logger.debug(
                f"Retrieved variables from blob storage: {blob_path}",
                extra={"execution_id": execution_id, "variable_count": len(variables)}
            )

            return variables

        except Exception as e:
            logger.error(
                f"Failed to retrieve variables from blob storage: {str(e)}",
                extra={"execution_id": execution_id},
                exc_info=True
            )
            return None

    def generate_upload_url(
        self,
        file_name: str,
        content_type: str,
        file_size: int | None = None,
        max_size_bytes: int = 100 * 1024 * 1024,  # 100MB default
        allowed_types: list[str] | None = None
    ) -> dict:
        """
        Generate a Shared Access Signature (SAS) URL for direct file upload

        Args:
            file_name: Original filename
            content_type: MIME type of the file
            file_size: Size of the file in bytes
            max_size_bytes: Maximum allowed file size
            allowed_types: List of allowed MIME types

        Returns:
            Dictionary with upload URL, blob URI, and expiration

        Raises:
            ValueError: If file type or size is invalid
        """
        # Validate file type
        if allowed_types and content_type not in allowed_types:
            raise ValueError(f"File type {content_type} is not allowed")

        # Validate file size
        if file_size and file_size > max_size_bytes:
            raise ValueError(f"File exceeds maximum size of {max_size_bytes/1024/1024} MB")

        # Generate unique blob name with original filename preserved
        safe_filename = uuid.uuid4().hex + '_' + file_name
        container_name = "uploads"
        blob_name = safe_filename

        # Ensure container exists
        container_client = self._ensure_container_exists(container_name)
        blob_client = container_client.get_blob_client(blob_name)

        # Generate SAS token with write permission
        account_name = self.blob_service_client.account_name
        if not account_name:
            raise ValueError("Blob storage account name not available")

        # Extract account key from connection string
        # Parse connection string to get account key
        conn_parts = dict(item.split('=', 1) for item in self.connection_string.split(';') if '=' in item)
        account_key = conn_parts.get('AccountKey')

        sas_token = generate_blob_sas(
            account_name=account_name,
            container_name=container_name,
            blob_name=blob_name,
            account_key=account_key,
            permission=BlobSasPermissions(write=True, create=True),
            expiry=datetime.utcnow() + timedelta(minutes=15)
        )

        logger.info(
            f"Generated upload URL for file: {file_name}",
            extra={
                "blob_name": blob_name,
                "content_type": content_type,
                "file_size": file_size
            }
        )

        return {
            "upload_url": f"{self._make_url_browser_accessible(blob_client.url)}?{sas_token}",
            "blob_uri": self._make_url_browser_accessible(blob_client.url),
            "blob_name": blob_name,
            "expires_at": (datetime.utcnow() + timedelta(minutes=15)).isoformat(),
            "file_name": file_name,
            "content_type": content_type
        }

    def get_blob_metadata(self, blob_uri: str) -> dict:
        """
        Retrieve metadata for a blob

        Args:
            blob_uri: Full URI of the blob

        Returns:
            Dictionary of blob metadata
        """
        try:
            # Parse blob URI to get container and blob name
            # URI format: https://account.blob.core.windows.net/container/blob
            parts = blob_uri.replace('https://', '').replace('http://', '').split('/')
            if len(parts) < 3:
                raise ValueError(f"Invalid blob URI: {blob_uri}")

            container_name = parts[1]
            blob_name = '/'.join(parts[2:])

            container_client = self.blob_service_client.get_container_client(container_name)
            blob_client = container_client.get_blob_client(blob_name)
            properties = blob_client.get_blob_properties()

            return {
                "name": properties.name,
                "size": properties.size,
                "content_type": properties.content_settings.content_type,
                "last_modified": properties.last_modified.isoformat() if properties.last_modified else None,
                "etag": properties.etag
            }
        except Exception as e:
            logger.error(
                f"Failed to get blob metadata: {str(e)}",
                extra={"blob_uri": blob_uri},
                exc_info=True
            )
            return {
                "error": str(e),
                "blob_uri": blob_uri
            }

    def delete_blob(self, blob_uri: str) -> bool:
        """
        Delete a blob from storage

        Args:
            blob_uri: Full URI of the blob to delete

        Returns:
            True if deletion successful, False otherwise
        """
        try:
            # Parse blob URI to get container and blob name
            parts = blob_uri.replace('https://', '').replace('http://', '').split('/')
            if len(parts) < 3:
                raise ValueError(f"Invalid blob URI: {blob_uri}")

            container_name = parts[1]
            blob_name = '/'.join(parts[2:])

            container_client = self.blob_service_client.get_container_client(container_name)
            blob_client = container_client.get_blob_client(blob_name)
            blob_client.delete_blob()

            logger.info(
                f"Deleted blob: {blob_uri}",
                extra={"blob_name": blob_name}
            )
            return True
        except Exception as e:
            logger.error(
                f"Failed to delete blob: {str(e)}",
                extra={"blob_uri": blob_uri},
                exc_info=True
            )
            return False

    async def upload_blob(
        self,
        container_name: str,
        blob_name: str,
        data: bytes,
        content_type: str = "application/octet-stream"
    ) -> str:
        """
        Generic blob upload method

        Args:
            container_name: Name of the container
            blob_name: Name of the blob (path within container)
            data: Binary data to upload
            content_type: MIME type of the content

        Returns:
            Full URL of the uploaded blob
        """
        try:
            # Ensure container exists
            container_client = self._ensure_container_exists(container_name)
            blob_client = container_client.get_blob_client(blob_name)

            # Upload with content type
            blob_client.upload_blob(
                data,
                overwrite=True,
                content_settings=ContentSettings(content_type=content_type)
            )

            logger.info(
                f"Uploaded blob to storage: {container_name}/{blob_name}",
                extra={
                    "container": container_name,
                    "blob_name": blob_name,
                    "content_type": content_type,
                    "size": len(data)
                }
            )

            return self._make_url_browser_accessible(blob_client.url)

        except Exception as e:
            logger.error(
                f"Failed to upload blob: {str(e)}",
                extra={
                    "container": container_name,
                    "blob_name": blob_name
                },
                exc_info=True
            )
            raise

    async def download_blob(self, container_name: str, blob_name: str) -> bytes:
        """
        Download a blob from storage

        Args:
            container_name: Name of the container
            blob_name: Name of the blob

        Returns:
            Blob data as bytes
        """
        try:
            container_client = self.blob_service_client.get_container_client(container_name)
            blob_client = container_client.get_blob_client(blob_name)

            # Download blob
            download_stream = blob_client.download_blob()
            blob_data = download_stream.readall()

            logger.info(
                f"Downloaded blob from storage: {container_name}/{blob_name}",
                extra={
                    "container": container_name,
                    "blob_name": blob_name,
                    "size": len(blob_data)
                }
            )

            return blob_data

        except Exception as e:
            logger.error(
                f"Failed to download blob: {str(e)}",
                extra={
                    "container": container_name,
                    "blob_name": blob_name
                },
                exc_info=True
            )
            raise


# Singleton instance with thread-safe initialization
_blob_storage_service = None
_blob_storage_service_lock = threading.Lock()


def get_blob_service() -> BlobStorageService:
    """Get thread-safe singleton BlobStorageService instance."""
    global _blob_storage_service
    if _blob_storage_service is None:
        with _blob_storage_service_lock:
            # Double-check pattern to prevent race condition
            if _blob_storage_service is None:
                _blob_storage_service = BlobStorageService()
    return _blob_storage_service
