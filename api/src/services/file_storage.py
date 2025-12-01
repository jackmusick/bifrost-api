"""
File Storage Service

Local filesystem-based storage service for files, uploads, and assets.
Replaces Azure Blob Storage with simple filesystem operations.

Directory structure under /mounts:
- /mounts/files/branding/{org_id}/    - Organization branding assets (logos, etc.)
- /mounts/files/uploads/{uuid}_*      - User-uploaded files
- /mounts/workspace/                   - Workflow workspace files
- /mounts/temp/                        - Temporary files

This can be extended later to support S3/MinIO/Azure Blob as a backend.
"""

import aiofiles
import aiofiles.os
import logging
import mimetypes
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Base mount path - configurable via environment
MOUNTS_BASE = os.environ.get("BIFROST_MOUNTS_PATH", "/mounts")

# Subdirectories
FILES_DIR = "files"
UPLOADS_DIR = "uploads"
BRANDING_DIR = "branding"
WORKSPACE_DIR = "workspace"
TEMP_DIR = "temp"


class FileStorageService:
    """
    Filesystem-based storage service.

    Provides async file operations for storing and retrieving files.
    Compatible interface with the old BlobStorageService where possible.
    """

    def __init__(self, base_path: str | None = None):
        """
        Initialize file storage service.

        Args:
            base_path: Optional base path override (defaults to MOUNTS_BASE)
        """
        self.base_path = Path(base_path or MOUNTS_BASE)
        self._initialized = False

    async def initialize(self) -> None:
        """Ensure all required directories exist."""
        if self._initialized:
            return

        directories = [
            self.base_path / FILES_DIR / UPLOADS_DIR,
            self.base_path / FILES_DIR / BRANDING_DIR,
            self.base_path / WORKSPACE_DIR,
            self.base_path / TEMP_DIR,
        ]

        for directory in directories:
            await aiofiles.os.makedirs(directory, exist_ok=True)
            logger.debug(f"Ensured directory exists: {directory}")

        self._initialized = True
        logger.info(f"FileStorageService initialized at {self.base_path}")

    def _get_path(self, *parts: str) -> Path:
        """Get full path from parts."""
        return self.base_path / Path(*parts)

    # =========================================================================
    # Generic File Operations
    # =========================================================================

    async def write_file(
        self,
        path: str,
        content: bytes | str,
        content_type: str | None = None,
    ) -> str:
        """
        Write content to a file.

        Args:
            path: Relative path within mounts (e.g., "files/uploads/abc.txt")
            content: File content (bytes or string)
            content_type: Optional MIME type (for metadata, not used currently)

        Returns:
            Full path to the written file
        """
        await self.initialize()

        full_path = self._get_path(path)
        await aiofiles.os.makedirs(full_path.parent, exist_ok=True)

        if isinstance(content, str):
            async with aiofiles.open(full_path, "w") as f:
                await f.write(content)
        else:
            async with aiofiles.open(full_path, "wb") as f:
                await f.write(content)

        logger.debug(f"Wrote file: {full_path} ({len(content)} bytes)")
        return str(full_path)

    async def read_file(self, path: str, as_bytes: bool = True) -> bytes | str | None:
        """
        Read content from a file.

        Args:
            path: Relative path within mounts
            as_bytes: If True, return bytes; otherwise return string

        Returns:
            File content or None if not found
        """
        await self.initialize()

        full_path = self._get_path(path)

        try:
            if not await aiofiles.os.path.exists(full_path):
                logger.debug(f"File not found: {full_path}")
                return None

            mode = "rb" if as_bytes else "r"
            async with aiofiles.open(full_path, mode) as f:
                content = await f.read()

            logger.debug(f"Read file: {full_path} ({len(content)} bytes)")
            return content

        except Exception as e:
            logger.error(f"Error reading file {full_path}: {e}")
            return None

    async def delete_file(self, path: str) -> bool:
        """
        Delete a file.

        Args:
            path: Relative path within mounts

        Returns:
            True if deleted, False if not found
        """
        await self.initialize()

        full_path = self._get_path(path)

        try:
            if not await aiofiles.os.path.exists(full_path):
                return False

            await aiofiles.os.remove(full_path)
            logger.debug(f"Deleted file: {full_path}")
            return True

        except Exception as e:
            logger.error(f"Error deleting file {full_path}: {e}")
            return False

    async def file_exists(self, path: str) -> bool:
        """Check if a file exists."""
        await self.initialize()
        full_path = self._get_path(path)
        return await aiofiles.os.path.exists(full_path)

    async def get_file_info(self, path: str) -> dict[str, Any] | None:
        """
        Get file metadata.

        Args:
            path: Relative path within mounts

        Returns:
            Dict with name, size, content_type, modified_at, or None if not found
        """
        await self.initialize()

        full_path = self._get_path(path)

        try:
            if not await aiofiles.os.path.exists(full_path):
                return None

            stat = await aiofiles.os.stat(full_path)
            content_type, _ = mimetypes.guess_type(str(full_path))

            return {
                "name": full_path.name,
                "path": path,
                "size": stat.st_size,
                "content_type": content_type or "application/octet-stream",
                "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            }

        except Exception as e:
            logger.error(f"Error getting file info {full_path}: {e}")
            return None

    # =========================================================================
    # Branding Files (logos, etc.)
    # =========================================================================

    def _branding_path(self, org_id: str, filename: str) -> str:
        """Get branding file path."""
        return f"{FILES_DIR}/{BRANDING_DIR}/{org_id}/{filename}"

    async def save_branding_file(
        self,
        org_id: str,
        filename: str,
        content: bytes,
        content_type: str | None = None,
    ) -> str:
        """
        Save a branding file (logo, etc.) for an organization.

        Args:
            org_id: Organization ID
            filename: File name (e.g., "logo.png")
            content: File content
            content_type: MIME type

        Returns:
            URL path to access the file
        """
        path = self._branding_path(org_id, filename)
        await self.write_file(path, content, content_type)

        # Return a URL-friendly path
        return f"/api/branding/{org_id}/{filename}"

    async def get_branding_file(self, org_id: str, filename: str) -> bytes | None:
        """
        Get a branding file.

        Args:
            org_id: Organization ID
            filename: File name

        Returns:
            File content or None if not found
        """
        path = self._branding_path(org_id, filename)
        content = await self.read_file(path, as_bytes=True)
        return content if isinstance(content, bytes) else None

    async def delete_branding_file(self, org_id: str, filename: str) -> bool:
        """Delete a branding file."""
        path = self._branding_path(org_id, filename)
        return await self.delete_file(path)

    async def list_branding_files(self, org_id: str) -> list[dict[str, Any]]:
        """List all branding files for an organization."""
        await self.initialize()

        branding_dir = self._get_path(FILES_DIR, BRANDING_DIR, org_id)

        if not await aiofiles.os.path.exists(branding_dir):
            return []

        files = []
        for filename in await aiofiles.os.listdir(branding_dir):
            info = await self.get_file_info(self._branding_path(org_id, filename))
            if info:
                files.append(info)

        return files

    # =========================================================================
    # User Uploads
    # =========================================================================

    async def save_upload(
        self,
        content: bytes,
        original_filename: str,
        content_type: str | None = None,
    ) -> dict[str, Any]:
        """
        Save an uploaded file.

        Args:
            content: File content
            original_filename: Original filename from user
            content_type: MIME type

        Returns:
            Dict with upload_id, path, url, filename, size, content_type
        """
        # Generate unique ID for the upload
        upload_id = uuid.uuid4().hex

        # Preserve original extension
        ext = Path(original_filename).suffix
        safe_filename = f"{upload_id}{ext}"

        path = f"{FILES_DIR}/{UPLOADS_DIR}/{safe_filename}"
        await self.write_file(path, content, content_type)

        return {
            "upload_id": upload_id,
            "path": path,
            "url": f"/api/uploads/{safe_filename}",
            "filename": original_filename,
            "size": len(content),
            "content_type": content_type or mimetypes.guess_type(original_filename)[0],
        }

    async def get_upload(self, upload_id_or_filename: str) -> bytes | None:
        """
        Get an uploaded file by ID or filename.

        Args:
            upload_id_or_filename: Upload ID (without extension) or full filename

        Returns:
            File content or None if not found
        """
        await self.initialize()

        uploads_dir = self._get_path(FILES_DIR, UPLOADS_DIR)

        # If it looks like a full filename, use it directly
        if "." in upload_id_or_filename:
            path = f"{FILES_DIR}/{UPLOADS_DIR}/{upload_id_or_filename}"
            content = await self.read_file(path, as_bytes=True)
            return content if isinstance(content, bytes) else None

        # Otherwise, search for file starting with the ID
        if await aiofiles.os.path.exists(uploads_dir):
            for filename in await aiofiles.os.listdir(uploads_dir):
                if filename.startswith(upload_id_or_filename):
                    path = f"{FILES_DIR}/{UPLOADS_DIR}/{filename}"
                    content = await self.read_file(path, as_bytes=True)
                    return content if isinstance(content, bytes) else None

        return None

    async def delete_upload(self, upload_id_or_filename: str) -> bool:
        """Delete an uploaded file."""
        await self.initialize()

        uploads_dir = self._get_path(FILES_DIR, UPLOADS_DIR)

        if "." in upload_id_or_filename:
            path = f"{FILES_DIR}/{UPLOADS_DIR}/{upload_id_or_filename}"
            return await self.delete_file(path)

        if await aiofiles.os.path.exists(uploads_dir):
            for filename in await aiofiles.os.listdir(uploads_dir):
                if filename.startswith(upload_id_or_filename):
                    path = f"{FILES_DIR}/{UPLOADS_DIR}/{filename}"
                    return await self.delete_file(path)

        return False

    # =========================================================================
    # Workspace Files (for workflow file operations)
    # =========================================================================

    async def workspace_write(
        self,
        org_id: str,
        relative_path: str,
        content: bytes | str,
    ) -> str:
        """
        Write a file to the organization's workspace.

        Args:
            org_id: Organization ID
            relative_path: Path relative to org workspace
            content: File content

        Returns:
            Full path to the file
        """
        # Sanitize path to prevent directory traversal
        safe_path = Path(relative_path).as_posix().lstrip("/")
        path = f"{WORKSPACE_DIR}/{org_id}/{safe_path}"
        return await self.write_file(path, content)

    async def workspace_read(
        self,
        org_id: str,
        relative_path: str,
        as_bytes: bool = True,
    ) -> bytes | str | None:
        """Read a file from the organization's workspace."""
        safe_path = Path(relative_path).as_posix().lstrip("/")
        path = f"{WORKSPACE_DIR}/{org_id}/{safe_path}"
        return await self.read_file(path, as_bytes=as_bytes)

    async def workspace_delete(self, org_id: str, relative_path: str) -> bool:
        """Delete a file from the organization's workspace."""
        safe_path = Path(relative_path).as_posix().lstrip("/")
        path = f"{WORKSPACE_DIR}/{org_id}/{safe_path}"
        return await self.delete_file(path)

    async def workspace_list(
        self,
        org_id: str,
        relative_path: str = "",
    ) -> list[dict[str, Any]]:
        """
        List files in the organization's workspace directory.

        Args:
            org_id: Organization ID
            relative_path: Path relative to org workspace (empty for root)

        Returns:
            List of file/directory info dicts
        """
        await self.initialize()

        safe_path = Path(relative_path).as_posix().lstrip("/") if relative_path else ""
        dir_path = self._get_path(WORKSPACE_DIR, org_id, safe_path)

        if not await aiofiles.os.path.exists(dir_path):
            return []

        items = []
        for name in await aiofiles.os.listdir(dir_path):
            item_path = dir_path / name
            stat = await aiofiles.os.stat(item_path)
            is_dir = await aiofiles.os.path.isdir(item_path)

            items.append({
                "name": name,
                "path": f"{safe_path}/{name}".lstrip("/"),
                "is_directory": is_dir,
                "size": stat.st_size if not is_dir else None,
                "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            })

        return sorted(items, key=lambda x: (not x["is_directory"], x["name"]))

    # =========================================================================
    # Temp Files
    # =========================================================================

    async def write_temp(self, filename: str, content: bytes | str) -> str:
        """Write a temporary file. Returns full path."""
        path = f"{TEMP_DIR}/{filename}"
        return await self.write_file(path, content)

    async def read_temp(self, filename: str, as_bytes: bool = True) -> bytes | str | None:
        """Read a temporary file."""
        path = f"{TEMP_DIR}/{filename}"
        return await self.read_file(path, as_bytes=as_bytes)

    async def delete_temp(self, filename: str) -> bool:
        """Delete a temporary file."""
        path = f"{TEMP_DIR}/{filename}"
        return await self.delete_file(path)

    async def cleanup_temp(self, max_age_hours: int = 24) -> int:
        """
        Clean up old temporary files.

        Args:
            max_age_hours: Delete files older than this many hours

        Returns:
            Number of files deleted
        """
        await self.initialize()

        temp_dir = self._get_path(TEMP_DIR)
        if not await aiofiles.os.path.exists(temp_dir):
            return 0

        deleted = 0
        cutoff = datetime.utcnow().timestamp() - (max_age_hours * 3600)

        for filename in await aiofiles.os.listdir(temp_dir):
            file_path = temp_dir / filename
            try:
                stat = await aiofiles.os.stat(file_path)
                if stat.st_mtime < cutoff:
                    await aiofiles.os.remove(file_path)
                    deleted += 1
            except Exception as e:
                logger.warning(f"Error cleaning temp file {file_path}: {e}")

        if deleted > 0:
            logger.info(f"Cleaned up {deleted} old temp files")

        return deleted


# Singleton instance
_file_storage: FileStorageService | None = None


def get_file_storage() -> FileStorageService:
    """Get singleton FileStorageService instance."""
    global _file_storage
    if _file_storage is None:
        _file_storage = FileStorageService()
    return _file_storage
