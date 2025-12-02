"""
Blob Storage Service for Bifrost Integrations

Replaced Azure Blob Storage with local file-based storage for execution data.
Stores large execution data (logs, results, snapshots) in the local filesystem.
"""

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Any

import aiofiles
import aiofiles.os

logger = logging.getLogger(__name__)

# Default storage location
DEFAULT_STORAGE_PATH = "/tmp/bifrost/blobs"


class BlobStorageService:
    """
    Service for storing and retrieving execution data in local filesystem.

    Used for data that would exceed PostgreSQL practical limits:
    - Execution logs (can be thousands of entries)
    - Execution results (can be large JSON or HTML)
    - State snapshots (workflow checkpoints)
    """

    def __init__(self, storage_path: str | None = None):
        """
        Initialize Blob Storage client.

        Args:
            storage_path: Optional storage path override
        """
        self.storage_path = Path(
            storage_path or os.environ.get("BIFROST_BLOB_STORAGE_PATH", DEFAULT_STORAGE_PATH)
        )
        self._initialized = False
        self._init_lock = asyncio.Lock()

    async def _ensure_initialized(self):
        """Ensure storage directories exist."""
        if self._initialized:
            return

        async with self._init_lock:
            if self._initialized:
                return

            # Create base directories
            for subdir in ["results", "logs", "variables", "snapshots"]:
                dir_path = self.storage_path / subdir
                dir_path.mkdir(parents=True, exist_ok=True)

            self._initialized = True
            logger.info(f"Blob storage initialized at {self.storage_path}")

    def _get_blob_path(self, category: str, execution_id: str) -> Path:
        """Get the full path for a blob file."""
        return self.storage_path / category / f"{execution_id}.json"

    async def upload_result(self, execution_id: str, result: Any) -> str:
        """
        Upload execution result to blob storage.

        Args:
            execution_id: Execution ID
            result: Result data (dict, list, or string)

        Returns:
            Blob URL (file path)
        """
        await self._ensure_initialized()
        blob_path = self._get_blob_path("results", execution_id)

        content = json.dumps(result) if not isinstance(result, str) else result

        async with aiofiles.open(blob_path, "w", encoding="utf-8") as f:
            await f.write(content)

        logger.debug(f"Uploaded result for execution {execution_id}")
        return str(blob_path)

    async def get_result(self, execution_id: str) -> Any | None:
        """
        Get execution result from blob storage.

        Args:
            execution_id: Execution ID

        Returns:
            Result data or None if not found
        """
        await self._ensure_initialized()
        blob_path = self._get_blob_path("results", execution_id)

        if not blob_path.exists():
            return None

        try:
            async with aiofiles.open(blob_path, "r", encoding="utf-8") as f:
                content = await f.read()
            return json.loads(content)
        except json.JSONDecodeError:
            # Return raw string if not valid JSON
            return content
        except Exception as e:
            logger.error(f"Error reading result for {execution_id}: {e}")
            return None

    async def upload_logs(self, execution_id: str, logs: list) -> str:
        """
        Upload execution logs to blob storage.

        Args:
            execution_id: Execution ID
            logs: List of log entries

        Returns:
            Blob URL (file path)
        """
        await self._ensure_initialized()
        blob_path = self._get_blob_path("logs", execution_id)

        async with aiofiles.open(blob_path, "w", encoding="utf-8") as f:
            await f.write(json.dumps(logs))

        logger.debug(f"Uploaded {len(logs)} log entries for execution {execution_id}")
        return str(blob_path)

    async def get_logs(self, execution_id: str) -> list | None:
        """
        Get execution logs from blob storage.

        Args:
            execution_id: Execution ID

        Returns:
            List of log entries or None if not found
        """
        await self._ensure_initialized()
        blob_path = self._get_blob_path("logs", execution_id)

        if not blob_path.exists():
            return None

        try:
            async with aiofiles.open(blob_path, "r", encoding="utf-8") as f:
                content = await f.read()
            return json.loads(content)
        except Exception as e:
            logger.error(f"Error reading logs for {execution_id}: {e}")
            return None

    async def upload_variables(self, execution_id: str, variables: dict) -> str:
        """
        Upload execution variables to blob storage.

        Args:
            execution_id: Execution ID
            variables: Variables dictionary

        Returns:
            Blob URL (file path)
        """
        await self._ensure_initialized()
        blob_path = self._get_blob_path("variables", execution_id)

        async with aiofiles.open(blob_path, "w", encoding="utf-8") as f:
            await f.write(json.dumps(variables))

        logger.debug(f"Uploaded {len(variables)} variables for execution {execution_id}")
        return str(blob_path)

    async def get_variables(self, execution_id: str) -> dict | None:
        """
        Get execution variables from blob storage.

        Args:
            execution_id: Execution ID

        Returns:
            Variables dictionary or None if not found
        """
        await self._ensure_initialized()
        blob_path = self._get_blob_path("variables", execution_id)

        if not blob_path.exists():
            return None

        try:
            async with aiofiles.open(blob_path, "r", encoding="utf-8") as f:
                content = await f.read()
            return json.loads(content)
        except Exception as e:
            logger.error(f"Error reading variables for {execution_id}: {e}")
            return None

    async def upload_snapshot(self, execution_id: str, snapshot: dict) -> str:
        """
        Upload execution state snapshot.

        Args:
            execution_id: Execution ID
            snapshot: State snapshot dictionary

        Returns:
            Blob URL (file path)
        """
        await self._ensure_initialized()
        blob_path = self._get_blob_path("snapshots", execution_id)

        async with aiofiles.open(blob_path, "w", encoding="utf-8") as f:
            await f.write(json.dumps(snapshot))

        logger.debug(f"Uploaded snapshot for execution {execution_id}")
        return str(blob_path)

    async def get_snapshot(self, execution_id: str) -> dict | None:
        """
        Get execution state snapshot.

        Args:
            execution_id: Execution ID

        Returns:
            Snapshot dictionary or None if not found
        """
        await self._ensure_initialized()
        blob_path = self._get_blob_path("snapshots", execution_id)

        if not blob_path.exists():
            return None

        try:
            async with aiofiles.open(blob_path, "r", encoding="utf-8") as f:
                content = await f.read()
            return json.loads(content)
        except Exception as e:
            logger.error(f"Error reading snapshot for {execution_id}: {e}")
            return None

    async def delete_execution_data(self, execution_id: str) -> None:
        """
        Delete all blob data for an execution.

        Args:
            execution_id: Execution ID
        """
        await self._ensure_initialized()

        for category in ["results", "logs", "variables", "snapshots"]:
            blob_path = self._get_blob_path(category, execution_id)
            if blob_path.exists():
                try:
                    await aiofiles.os.remove(blob_path)
                    logger.debug(f"Deleted {category} blob for execution {execution_id}")
                except Exception as e:
                    logger.error(f"Error deleting {category} for {execution_id}: {e}")


# Singleton instance
_blob_service: BlobStorageService | None = None


def get_blob_service() -> BlobStorageService:
    """Get singleton BlobStorageService instance."""
    global _blob_service
    if _blob_service is None:
        _blob_service = BlobStorageService()
    return _blob_service
