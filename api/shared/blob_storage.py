"""
Blob Storage Service for Bifrost Integrations
Handles large execution data (logs, results, snapshots) that exceed Table Storage limits
"""

import json
import logging
import os
from typing import Any

from azure.storage.blob import BlobServiceClient, ContainerClient

logger = logging.getLogger(__name__)

# Container for execution-related data
EXECUTION_CONTAINER = "execution-data"


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
        """
        if connection_string is None:
            connection_string = os.environ.get("AzureWebJobsStorage")

        if not connection_string:
            raise ValueError("AzureWebJobsStorage environment variable not set")

        self.connection_string = connection_string
        self.blob_service_client = BlobServiceClient.from_connection_string(connection_string)

        # Ensure container exists
        self._ensure_container_exists(EXECUTION_CONTAINER)

        logger.debug(f"BlobStorageService initialized for container: {EXECUTION_CONTAINER}")

    def _ensure_container_exists(self, container_name: str) -> ContainerClient:
        """
        Ensure blob container exists, create if it doesn't

        Args:
            container_name: Name of the container

        Returns:
            ContainerClient instance
        """
        try:
            container_client = self.blob_service_client.get_container_client(container_name)

            # Check if exists
            if not container_client.exists():
                container_client = self.blob_service_client.create_container(container_name)
                logger.info(f"Created blob container: {container_name}")

            return container_client
        except Exception as e:
            logger.error(f"Failed to ensure container exists: {str(e)}")
            raise

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


# Singleton instance
_blob_storage_service = None


def get_blob_service() -> BlobStorageService:
    """Get singleton BlobStorageService instance."""
    global _blob_storage_service
    if _blob_storage_service is None:
        _blob_storage_service = BlobStorageService()
    return _blob_storage_service
