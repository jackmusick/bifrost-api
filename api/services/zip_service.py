"""
ZIP Service Layer

Provides in-memory ZIP generation for workspace backups.
Per research.md Decision 8: Generate ZIP in memory using BytesIO buffer.
"""

import logging
import zipfile
from io import BytesIO
from typing import List, Dict, Any
from services.workspace_service import get_workspace_service

logger = logging.getLogger(__name__)


def create_workspace_zip(directory_path: str = '') -> BytesIO:
    """
    Create in-memory ZIP archive of workspace files.

    Per research.md Decision 8:
    - Uses BytesIO buffer for in-memory generation
    - Streams directly to HTTP response
    - Works for workspaces up to ~500MB (typical: 10-50MB)
    - Memory usage: ~2x uncompressed size during generation

    Args:
        directory_path: Starting directory path relative to workspace root (default: root)

    Returns:
        BytesIO buffer containing ZIP file (rewound to position 0)
    """
    try:
        workspace_service = get_workspace_service()
        zip_buffer = BytesIO()

        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            # List all files in workspace
            items = workspace_service.list_files(directory_path)

            # Filter to only files (skip directories)
            files = [item for item in items if not item['isDirectory']]

            logger.info(f"Creating ZIP archive with {len(files)} files from workspace")

            # Add each file to ZIP
            for file_item in files:
                file_path = file_item['path']

                try:
                    # Read file content
                    content = workspace_service.read_file(file_path)

                    # Add to ZIP with original path
                    zip_file.writestr(file_path, content)

                    logger.debug(f"Added to ZIP: {file_path} ({len(content)} bytes)")

                except Exception as e:
                    logger.warning(f"Skipping file {file_path} due to error: {e}")
                    continue

        # Rewind buffer to beginning for reading
        zip_buffer.seek(0)

        zip_size = zip_buffer.getbuffer().nbytes
        logger.info(f"ZIP archive created successfully: {zip_size} bytes ({len(files)} files)")

        return zip_buffer

    except Exception as e:
        logger.error(f"Error creating workspace ZIP: {e}", exc_info=True)
        raise


def create_selective_zip(file_paths: List[str]) -> BytesIO:
    """
    Create in-memory ZIP archive of specific files.

    Useful for selective backups or exports.

    Args:
        file_paths: List of file paths relative to workspace root to include in ZIP

    Returns:
        BytesIO buffer containing ZIP file (rewound to position 0)
    """
    try:
        workspace_service = get_workspace_service()
        zip_buffer = BytesIO()

        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            logger.info(f"Creating selective ZIP archive with {len(file_paths)} files from workspace")

            for file_path in file_paths:
                try:
                    # Read file content
                    content = workspace_service.read_file(file_path)

                    # Add to ZIP with original path
                    zip_file.writestr(file_path, content)

                    logger.debug(f"Added to ZIP: {file_path} ({len(content)} bytes)")

                except Exception as e:
                    logger.warning(f"Skipping file {file_path} due to error: {e}")
                    continue

        # Rewind buffer to beginning for reading
        zip_buffer.seek(0)

        zip_size = zip_buffer.getbuffer().nbytes
        logger.info(f"Selective ZIP archive created: {zip_size} bytes ({len(file_paths)} files)")

        return zip_buffer

    except Exception as e:
        logger.error(f"Error creating selective ZIP: {e}", exc_info=True)
        raise


def estimate_workspace_size(items: List[Dict[str, Any]]) -> int:
    """
    Estimate total size of workspace files.

    Args:
        items: List of file items from list_all_files()

    Returns:
        Total size in bytes
    """
    total_size = 0
    for item in items:
        if not item['isDirectory'] and item.get('size'):
            total_size += item['size']

    return total_size
