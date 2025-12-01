"""
Workspace Service

Handles workspace file operations and workflow discovery.
Works with mounted directories (/workspace) - no Azure SDK needed.
"""

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any
import aiofiles
import aiofiles.os

logger = logging.getLogger(__name__)


class WorkspaceService:
    """
    Service for workspace file operations.

    The workspace directory is either:
    - Local directory (dev): ./workspace
    - Mounted Azure Files (prod): /workspace

    No Azure SDK needed - just standard filesystem operations.
    """

    def __init__(self, workspace_path: str | None = None):
        """
        Initialize workspace service.

        Args:
            workspace_path: Path to workspace directory (default: BIFROST_WORKSPACE_LOCATION env var)
        """
        self.workspace_path = Path(workspace_path or os.environ.get('BIFROST_WORKSPACE_LOCATION', '/mounts/workspace'))

        # Workspace directory should already exist (validated at startup)
        if not self.workspace_path.exists():
            raise RuntimeError(
                f"Workspace directory does not exist: {self.workspace_path}. "
                "This should have been validated at startup."
            )

        logger.info(f"Initialized workspace service at: {self.workspace_path}")

    def list_files(self, relative_path: str = '') -> list[dict[str, Any]]:
        """
        Recursively list all files and directories in workspace.

        Args:
            relative_path: Starting path relative to workspace root (default: root)

        Returns:
            List of file/directory metadata dicts
        """
        base_path = self.workspace_path / relative_path

        if not base_path.exists():
            logger.warning(f"Path does not exist: {base_path}")
            return []

        items = []

        for entry in base_path.rglob('*'):
            try:
                stat = entry.stat()
                relative = entry.relative_to(self.workspace_path)

                items.append({
                    'name': entry.name,
                    'path': str(relative),
                    'isDirectory': entry.is_dir(),
                    'size': stat.st_size if entry.is_file() else None,
                    'lastModified': datetime.fromtimestamp(stat.st_mtime).isoformat()
                })
            except (OSError, ValueError) as e:
                logger.warning(f"Error reading {entry}: {e}")
                continue

        logger.debug(f"Listed {len(items)} items from workspace")
        return items

    async def read_file(self, file_path: str) -> bytes:
        """
        Read file content from workspace.

        Args:
            file_path: Path relative to workspace root

        Returns:
            File content as bytes
        """
        full_path = self.workspace_path / file_path

        if not full_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        if not full_path.is_file():
            raise ValueError(f"Path is not a file: {file_path}")

        async with aiofiles.open(full_path, 'rb') as f:
            content = await f.read()

        logger.debug(f"Read {len(content)} bytes from {file_path}")

        return content

    async def write_file(self, file_path: str, content: bytes) -> dict[str, Any]:
        """
        Write file content to workspace.
        Creates parent directories if needed.

        Args:
            file_path: Path relative to workspace root
            content: File content as bytes

        Returns:
            File metadata dict
        """
        full_path = self.workspace_path / file_path

        # Create parent directories
        full_path.parent.mkdir(parents=True, exist_ok=True)

        # Write file
        async with aiofiles.open(full_path, 'wb') as f:
            await f.write(content)

        # Get file stats
        stat = await aiofiles.os.stat(full_path)

        logger.info(f"Wrote {len(content)} bytes to {file_path}")

        return {
            'path': file_path,
            'size': stat.st_size,
            'lastModified': datetime.fromtimestamp(stat.st_mtime).isoformat()
        }

    async def delete_file(self, file_path: str) -> None:
        """
        Delete file from workspace.

        Args:
            file_path: Path relative to workspace root
        """
        full_path = self.workspace_path / file_path

        if not full_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        if not full_path.is_file():
            raise ValueError(f"Path is not a file: {file_path}")

        await aiofiles.os.unlink(full_path)
        logger.info(f"Deleted file: {file_path}")

    def create_directory(self, directory_path: str) -> None:
        """
        Create directory in workspace.

        Args:
            directory_path: Path relative to workspace root
        """
        full_path = self.workspace_path / directory_path

        if full_path.exists():
            raise FileExistsError(f"Directory already exists: {directory_path}")

        full_path.mkdir(parents=True, exist_ok=False)
        logger.info(f"Created directory: {directory_path}")

    async def delete_directory(self, directory_path: str, recursive: bool = True) -> None:
        """
        Delete directory from workspace.

        Args:
            directory_path: Path relative to workspace root
            recursive: If True, delete directory and all contents (default: True)
        """
        full_path = self.workspace_path / directory_path

        if not full_path.exists():
            raise FileNotFoundError(f"Directory not found: {directory_path}")

        if not full_path.is_dir():
            raise ValueError(f"Path is not a directory: {directory_path}")

        if recursive:
            import shutil
            await aiofiles.os.wrap(shutil.rmtree)(full_path)
        else:
            await aiofiles.os.rmdir(full_path)  # Only works if empty

        logger.info(f"Deleted directory: {directory_path}")

    def validate_path(self, file_path: str) -> bool:
        """
        Validate that path is safe (no directory traversal).

        Args:
            file_path: Path to validate

        Returns:
            True if path is safe
        """
        # No ".." traversal
        if '..' in Path(file_path).parts:
            return False

        # No absolute paths
        if Path(file_path).is_absolute():
            return False

        # No invalid characters
        invalid_chars = ['<', '>', ':', '"', '|', '?', '*', '\\']
        if any(char in file_path for char in invalid_chars):
            return False

        return True


# Singleton instance
_workspace_service: WorkspaceService | None = None


def get_workspace_service() -> WorkspaceService:
    """Get singleton instance of workspace service."""
    global _workspace_service
    if _workspace_service is None:
        _workspace_service = WorkspaceService()
    return _workspace_service
