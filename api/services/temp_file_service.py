"""
Temporary File Service

Provides temporary file/directory creation (similar to PowerShell's New-TemporaryFile).
Works with mounted /tmp directory.
"""

import logging
import os
import tempfile
import uuid
from typing import Optional
from pathlib import Path
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class TempFileService:
    """
    Service for creating temporary files and directories.

    Uses /tmp which is either:
    - Local /tmp (dev)
    - Mounted Azure Files /tmp (prod)
    """

    def __init__(self, tmp_path: Optional[str] = None):
        """
        Initialize temp file service.

        Args:
            tmp_path: Path to temp directory (default: /tmp)
        """
        self.tmp_path = Path(tmp_path or os.environ.get('TMP_PATH', '/tmp'))

        # Ensure temp directory exists
        self.tmp_path.mkdir(parents=True, exist_ok=True)

        logger.info(f"Initialized temp file service at: {self.tmp_path}")

    def create_temp_file(self, suffix: str = '', prefix: str = 'tmp', text_mode: bool = False) -> Path:
        """
        Create a temporary file and return its path.

        Similar to PowerShell's New-TemporaryFile.

        Args:
            suffix: File suffix (e.g., '.txt', '.json')
            prefix: File prefix (default: 'tmp')
            text_mode: If True, open in text mode (default: False for binary)

        Returns:
            Path to created temporary file
        """
        # Create unique filename
        filename = f"{prefix}_{uuid.uuid4().hex}{suffix}"
        file_path = self.tmp_path / filename

        # Create empty file
        file_path.touch()

        logger.debug(f"Created temporary file: {file_path}")

        return file_path

    def create_temp_directory(self, suffix: str = '', prefix: str = 'tmp') -> Path:
        """
        Create a temporary directory and return its path.

        Args:
            suffix: Directory suffix
            prefix: Directory prefix (default: 'tmp')

        Returns:
            Path to created temporary directory
        """
        # Create unique directory name
        dirname = f"{prefix}_{uuid.uuid4().hex}{suffix}"
        dir_path = self.tmp_path / dirname

        # Create directory
        dir_path.mkdir(parents=True, exist_ok=False)

        logger.debug(f"Created temporary directory: {dir_path}")

        return dir_path

    def get_temp_path(self, filename: str) -> Path:
        """
        Get path for a temporary file with specific name.

        Args:
            filename: Desired filename

        Returns:
            Full path in temp directory
        """
        return self.tmp_path / filename

    def cleanup_old_files(self, max_age_hours: int = 24) -> int:
        """
        Clean up temporary files older than specified age.

        Args:
            max_age_hours: Maximum age in hours (default: 24)

        Returns:
            Number of files deleted
        """
        cutoff_time = datetime.now().timestamp() - (max_age_hours * 3600)
        deleted_count = 0

        try:
            for entry in self.tmp_path.iterdir():
                try:
                    # Skip if modified recently
                    if entry.stat().st_mtime > cutoff_time:
                        continue

                    # Delete file or directory
                    if entry.is_file():
                        entry.unlink()
                        deleted_count += 1
                    elif entry.is_dir():
                        import shutil
                        shutil.rmtree(entry)
                        deleted_count += 1

                except (OSError, PermissionError) as e:
                    logger.warning(f"Could not delete {entry}: {e}")
                    continue

            if deleted_count > 0:
                logger.info(f"Cleaned up {deleted_count} old temporary files/directories")

        except Exception as e:
            logger.error(f"Error during temp file cleanup: {e}", exc_info=True)

        return deleted_count

    def delete_temp_file(self, file_path: Path) -> None:
        """
        Delete a specific temporary file.

        Args:
            file_path: Path to temporary file
        """
        if not file_path.exists():
            logger.warning(f"Temp file does not exist: {file_path}")
            return

        # Verify it's in our temp directory (security check)
        if not file_path.is_relative_to(self.tmp_path):
            raise ValueError(f"Path is not in temp directory: {file_path}")

        if file_path.is_file():
            file_path.unlink()
        elif file_path.is_dir():
            import shutil
            shutil.rmtree(file_path)

        logger.debug(f"Deleted temporary file: {file_path}")


# Singleton instance
_temp_file_service: Optional[TempFileService] = None


def get_temp_file_service() -> TempFileService:
    """Get singleton instance of temp file service."""
    global _temp_file_service
    if _temp_file_service is None:
        _temp_file_service = TempFileService()
    return _temp_file_service


# Convenience functions (like PowerShell cmdlets)

def new_temp_file(suffix: str = '', prefix: str = 'tmp') -> Path:
    """
    Create a new temporary file (like PowerShell's New-TemporaryFile).

    Returns:
        Path to the temporary file
    """
    return get_temp_file_service().create_temp_file(suffix=suffix, prefix=prefix)


def new_temp_directory(suffix: str = '', prefix: str = 'tmp') -> Path:
    """
    Create a new temporary directory.

    Returns:
        Path to the temporary directory
    """
    return get_temp_file_service().create_temp_directory(suffix=suffix, prefix=prefix)
