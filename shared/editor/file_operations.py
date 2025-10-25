"""
File operations for browser-based code editor.
Provides safe file I/O with path validation.
Platform admin resource - no org scoping.
"""

from pathlib import Path
from typing import List
import hashlib
import os
from datetime import datetime, UTC

from shared.models import FileMetadata, FileContentResponse, FileType


def get_base_path() -> Path:
    """
    Get the workspace directory path from BIFROST_WORKSPACE_LOCATION env var.

    Returns:
        Path to workspace directory
    """
    workspace_loc = os.getenv("BIFROST_WORKSPACE_LOCATION")
    if not workspace_loc:
        raise RuntimeError(
            "BIFROST_WORKSPACE_LOCATION environment variable not set. "
            "This should have been validated at startup."
        )
    return Path(workspace_loc)


def validate_and_resolve_path(relative_path: str) -> Path:
    """
    Validate and resolve a relative path within /home.

    Args:
        relative_path: Relative path from /home

    Returns:
        Resolved absolute path

    Raises:
        ValueError: If path is invalid or attempts directory traversal
    """
    # Get base path and resolve it (handle symlinks like /var -> /private/var on macOS)
    base_path = get_base_path().resolve()

    # Remove leading slashes from relative path
    clean_path = relative_path.lstrip("/")

    # Resolve full path
    full_path = (base_path / clean_path).resolve()

    # Security check: Ensure path is within base directory
    try:
        full_path.relative_to(base_path)
    except ValueError:
        raise ValueError(f"Path outside repository: {relative_path}")

    return full_path


def list_directory(relative_path: str = "") -> List[FileMetadata]:
    """
    List files and folders in a directory.

    Args:
        relative_path: Relative path to directory (empty = root)

    Returns:
        List of FileMetadata objects

    Raises:
        ValueError: If path is invalid or not a directory
        FileNotFoundError: If directory doesn't exist
    """
    dir_path = validate_and_resolve_path(relative_path)

    if not dir_path.exists():
        raise FileNotFoundError(f"Directory not found: {relative_path}")

    if not dir_path.is_dir():
        raise ValueError(f"Not a directory: {relative_path}")

    results: List[FileMetadata] = []
    base_path = get_base_path().resolve()

    for item in sorted(dir_path.iterdir()):
        try:
            stat = item.stat()
            relative = str(item.resolve().relative_to(base_path))

            # Determine type
            file_type = FileType.FOLDER if item.is_dir() else FileType.FILE

            # Get extension for files
            extension = item.suffix if item.is_file() and item.suffix else None

            # Size is None for folders
            size = stat.st_size if item.is_file() else None

            # Modified timestamp
            modified = datetime.fromtimestamp(stat.st_mtime, tz=UTC).isoformat()

            results.append(FileMetadata(
                path=relative,
                name=item.name,
                type=file_type,
                size=size,
                extension=extension,
                modified=modified,
                isReadOnly=False  # TODO: Check actual permissions if needed
            ))
        except (PermissionError, OSError):
            # Skip files we can't read
            continue

    return results


def read_file(relative_path: str) -> FileContentResponse:
    """
    Read file content with metadata.
    Automatically detects binary files and returns them base64 encoded.

    Args:
        relative_path: Relative path to file

    Returns:
        FileContentResponse with content and metadata

    Raises:
        ValueError: If path is invalid or not a file
        FileNotFoundError: If file doesn't exist
        PermissionError: If file cannot be read
    """
    file_path = validate_and_resolve_path(relative_path)

    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {relative_path}")

    if not file_path.is_file():
        raise ValueError(f"Not a file: {relative_path}")

    # Get file stats
    stat = file_path.stat()

    # Try to read as UTF-8 text first
    encoding = "utf-8"
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        content_bytes = content.encode('utf-8')
    except UnicodeDecodeError:
        # File is binary, read as bytes and encode to base64
        encoding = "base64"
        try:
            import base64
            with open(file_path, 'rb') as f:
                binary_content = f.read()
            content = base64.b64encode(binary_content).decode('ascii')
            content_bytes = binary_content
        except PermissionError:
            raise PermissionError(f"Permission denied: {relative_path}")
        except Exception as e:
            raise ValueError(f"Error reading file: {str(e)}")
    except PermissionError:
        raise PermissionError(f"Permission denied: {relative_path}")
    except Exception as e:
        raise ValueError(f"Error reading file: {str(e)}")

    # Generate etag from content
    etag = hashlib.md5(content_bytes).hexdigest()

    # Modified timestamp
    modified = datetime.fromtimestamp(stat.st_mtime, tz=UTC).isoformat()

    return FileContentResponse(
        path=relative_path,
        content=content,
        encoding=encoding,
        size=len(content_bytes),
        etag=etag,
        modified=modified
    )


def write_file(relative_path: str, content: str, encoding: str = "utf-8") -> FileContentResponse:
    """
    Write file content atomically.

    Args:
        relative_path: Relative path to file
        content: File content to write (plain text or base64 encoded)
        encoding: Content encoding (utf-8 or base64)

    Returns:
        FileContentResponse with updated metadata

    Raises:
        ValueError: If path is invalid or encoding unsupported
        PermissionError: If file cannot be written
    """
    if encoding not in ("utf-8", "base64"):
        raise ValueError("Only UTF-8 and base64 encodings are supported")

    file_path = validate_and_resolve_path(relative_path)

    # Ensure parent directory exists
    file_path.parent.mkdir(parents=True, exist_ok=True)

    # Atomic write: write to temp file → rename
    temp_path = file_path.with_suffix(file_path.suffix + ".tmp")

    try:
        if encoding == "base64":
            # Decode base64 and write as binary
            import base64
            binary_content = base64.b64decode(content)
            with open(temp_path, 'wb') as f:
                f.write(binary_content)
            # For etag calculation
            content_bytes = binary_content
        else:
            # Write as UTF-8 text
            with open(temp_path, 'w', encoding='utf-8') as f:
                f.write(content)
            content_bytes = content.encode('utf-8')

        # Atomic rename (overwrites existing file)
        temp_path.replace(file_path)
    except PermissionError:
        if temp_path.exists():
            temp_path.unlink()
        raise PermissionError(f"Permission denied: {relative_path}")
    except Exception as e:
        if temp_path.exists():
            temp_path.unlink()
        raise ValueError(f"Error writing file: {str(e)}")

    # Get updated file stats
    stat = file_path.stat()

    # Generate etag from content
    etag = hashlib.md5(content_bytes).hexdigest()

    # Modified timestamp
    modified = datetime.fromtimestamp(stat.st_mtime, tz=UTC).isoformat()

    return FileContentResponse(
        path=relative_path,
        content=content,
        encoding=encoding,
        size=len(content_bytes),
        etag=etag,
        modified=modified
    )


def create_folder(relative_path: str) -> FileMetadata:
    """
    Create a new folder.

    Args:
        relative_path: Relative path to folder to create

    Returns:
        FileMetadata for the created folder

    Raises:
        ValueError: If path is invalid or folder already exists
        PermissionError: If folder cannot be created
    """
    folder_path = validate_and_resolve_path(relative_path)

    # Check if folder already exists
    if folder_path.exists():
        raise ValueError(f"Folder already exists: {relative_path}")

    # Create folder (including parents)
    try:
        folder_path.mkdir(parents=True, exist_ok=False)
    except PermissionError:
        raise PermissionError(f"Permission denied: {relative_path}")
    except Exception as e:
        raise ValueError(f"Error creating folder: {str(e)}")

    # Get folder stats
    stat = folder_path.stat()
    modified = datetime.fromtimestamp(stat.st_mtime, tz=UTC).isoformat()

    return FileMetadata(
        path=relative_path,
        name=folder_path.name,
        type=FileType.FOLDER,
        size=None,
        extension=None,
        modified=modified,
        isReadOnly=False
    )


def delete_path(relative_path: str) -> None:
    """
    Delete a file or folder.

    Args:
        relative_path: Relative path to file or folder to delete

    Raises:
        ValueError: If path is invalid
        FileNotFoundError: If path doesn't exist
        PermissionError: If path cannot be deleted
    """
    path = validate_and_resolve_path(relative_path)

    if not path.exists():
        raise FileNotFoundError(f"Path not found: {relative_path}")

    try:
        if path.is_dir():
            # Remove directory and all contents
            import shutil
            shutil.rmtree(path)
        else:
            # Remove file
            path.unlink()
    except PermissionError:
        raise PermissionError(f"Permission denied: {relative_path}")
    except Exception as e:
        raise ValueError(f"Error deleting path: {str(e)}")


def rename_path(old_path: str, new_path: str) -> FileMetadata:
    """
    Rename or move a file or folder.

    Args:
        old_path: Current relative path
        new_path: New relative path

    Returns:
        FileMetadata for the renamed/moved item

    Raises:
        ValueError: If paths are invalid or new path already exists
        FileNotFoundError: If old path doesn't exist
        PermissionError: If path cannot be renamed
    """
    old_resolved = validate_and_resolve_path(old_path)
    new_resolved = validate_and_resolve_path(new_path)

    if not old_resolved.exists():
        raise FileNotFoundError(f"Path not found: {old_path}")

    if new_resolved.exists():
        raise ValueError(f"Destination already exists: {new_path}")

    # Ensure parent directory of new path exists
    new_resolved.parent.mkdir(parents=True, exist_ok=True)

    try:
        old_resolved.rename(new_resolved)
    except PermissionError:
        raise PermissionError(f"Permission denied: {old_path}")
    except Exception as e:
        raise ValueError(f"Error renaming path: {str(e)}")

    # Get stats of renamed item
    stat = new_resolved.stat()
    modified = datetime.fromtimestamp(stat.st_mtime, tz=UTC).isoformat()

    file_type = FileType.FOLDER if new_resolved.is_dir() else FileType.FILE
    extension = new_resolved.suffix if new_resolved.is_file() and new_resolved.suffix else None
    size = stat.st_size if new_resolved.is_file() else None

    return FileMetadata(
        path=new_path,
        name=new_resolved.name,
        type=file_type,
        size=size,
        extension=extension,
        modified=modified,
        isReadOnly=False
    )
