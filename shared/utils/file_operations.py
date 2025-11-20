"""
File Operation Utilities

Utilities for file operations that work with Azure Files SMB limitations.
"""

import logging
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)


def manual_copy_tree(src: Path, dst: Path, exclude_patterns: list[str] | None = None) -> None:
    """
    Recursively copy directory tree without preserving metadata.

    This function copies files using simple read/write operations without
    attempting to preserve permissions, timestamps, or other metadata.
    This is necessary for Azure Files SMB mounts which don't support
    POSIX permission operations.

    Args:
        src: Source directory path
        dst: Destination directory path
        exclude_patterns: Optional list of file/directory names to exclude
                         (e.g., ['.DS_Store', '._*'] for macOS metadata)

    Raises:
        FileNotFoundError: If source directory doesn't exist
        OSError: If copy operations fail

    Example:
        >>> manual_copy_tree(Path('/tmp/repo'), Path('/mounts/workspace/repo'))
    """
    if exclude_patterns is None:
        exclude_patterns = []

    if not src.exists():
        raise FileNotFoundError(f"Source directory does not exist: {src}")

    # Create destination directory
    dst.mkdir(parents=True, exist_ok=True)

    # Copy all items
    for item in src.iterdir():
        # Skip excluded patterns
        if any(item.name.startswith(pattern.rstrip('*')) if pattern.endswith('*')
               else item.name == pattern
               for pattern in exclude_patterns):
            logger.debug(f"Skipping excluded item: {item.name}")
            continue

        src_item = src / item.name
        dst_item = dst / item.name

        if item.is_dir():
            # Recursively copy subdirectory
            manual_copy_tree(src_item, dst_item, exclude_patterns)
        else:
            # Copy file with simple read/write (no metadata)
            try:
                with open(src_item, 'rb') as f_src:
                    content = f_src.read()
                with open(dst_item, 'wb') as f_dst:
                    f_dst.write(content)
            except OSError as e:
                logger.error(f"Failed to copy {src_item} to {dst_item}: {e}")
                raise


def get_system_tmp() -> Path:
    """
    Get the system's actual temp directory.

    Returns the real /tmp directory (local ephemeral storage), NOT the
    BIFROST_TEMP_LOCATION environment variable which may point to Azure Files.

    This is important for operations that require local disk (like Git clones
    with Dulwich) that don't work on Azure Files SMB mounts.

    Returns:
        Path to system temp directory (e.g., /tmp on Linux)

    Example:
        >>> tmp_dir = get_system_tmp()
        >>> print(tmp_dir)
        /tmp
    """
    return Path(tempfile.gettempdir())


def is_smb_metadata_file(filename: str) -> bool:
    """
    Check if a file is SMB/macOS metadata file that should be ignored.

    These files are created by macOS and Windows SMB clients and should
    generally be excluded from Git operations.

    Args:
        filename: Name of the file to check

    Returns:
        True if the file is a metadata file, False otherwise

    Examples:
        >>> is_smb_metadata_file('.DS_Store')
        True
        >>> is_smb_metadata_file('._myfile.txt')
        True
        >>> is_smb_metadata_file('myfile.txt')
        False
    """
    return (
        filename == '.DS_Store' or
        filename.startswith('._') or
        filename == 'Thumbs.db' or
        filename == 'desktop.ini'
    )
