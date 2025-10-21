"""
File management SDK for Bifrost.

Provides Python API for file operations in /home/files/ and /home/tmp/.
"""

import shutil
from pathlib import Path

from ._internal import get_context


class files:
    """
    File management operations.

    Provides safe file access within /home/files/ and /home/tmp/ directories.
    All paths are sandboxed to prevent access outside allowed directories.
    """

    # Allowed base paths for file operations
    FILES_DIR = Path("/home/files")
    TMP_DIR = Path("/home/tmp")

    @staticmethod
    def _resolve_path(path: str, allow_tmp: bool = False) -> Path:
        """
        Resolve and validate a file path.

        Args:
            path: Relative or absolute path
            allow_tmp: Whether to allow paths in /home/tmp

        Returns:
            Path: Resolved absolute path

        Raises:
            ValueError: If path is outside allowed directories
        """
        # Convert to Path object
        p = Path(path)

        # If relative, resolve against FILES_DIR
        if not p.is_absolute():
            p = files.FILES_DIR / p

        # Resolve to absolute path (handles .. and symlinks)
        try:
            p = p.resolve()
        except Exception as e:
            raise ValueError(f"Invalid path: {path}") from e

        # Check if path is within allowed directories
        try:
            if allow_tmp:
                # Allow /home/files or /home/tmp
                if not (p.is_relative_to(files.FILES_DIR) or p.is_relative_to(files.TMP_DIR)):
                    raise ValueError(
                        f"Path must be within /home/files or /home/tmp: {path}"
                    )
            else:
                # Only allow /home/files
                if not p.is_relative_to(files.FILES_DIR):
                    raise ValueError(f"Path must be within /home/files: {path}")
        except AttributeError:
            # Python < 3.9 doesn't have is_relative_to
            # Fallback to string comparison
            path_str = str(p)
            if allow_tmp:
                if not (path_str.startswith("/home/files") or path_str.startswith("/home/tmp")):
                    raise ValueError(
                        f"Path must be within /home/files or /home/tmp: {path}"
                    )
            else:
                if not path_str.startswith("/home/files"):
                    raise ValueError(f"Path must be within /home/files: {path}")

        return p

    @staticmethod
    def read(path: str) -> str:
        """
        Read a text file.

        Args:
            path: File path (relative to /home/files or absolute)

        Returns:
            str: File contents

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If path is outside allowed directories
            RuntimeError: If no execution context

        Example:
            >>> from bifrost import files
            >>> content = files.read("data/customers.csv")
        """
        get_context()  # Ensure execution context exists

        file_path = files._resolve_path(path, allow_tmp=True)

        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()

    @staticmethod
    def read_bytes(path: str) -> bytes:
        """
        Read a binary file.

        Args:
            path: File path (relative to /home/files or absolute)

        Returns:
            bytes: File contents

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If path is outside allowed directories
            RuntimeError: If no execution context

        Example:
            >>> from bifrost import files
            >>> data = files.read_bytes("reports/report.pdf")
        """
        get_context()  # Ensure execution context exists

        file_path = files._resolve_path(path, allow_tmp=True)

        with open(file_path, 'rb') as f:
            return f.read()

    @staticmethod
    def write(path: str, content: str) -> None:
        """
        Write text to a file.

        Args:
            path: File path (relative to /home/files or absolute)
            content: Text content to write

        Raises:
            ValueError: If path is outside /home/files
            RuntimeError: If no execution context

        Example:
            >>> from bifrost import files
            >>> files.write("output/report.txt", "Report data")
        """
        get_context()  # Ensure execution context exists

        file_path = files._resolve_path(path, allow_tmp=False)

        # Create parent directories if needed
        file_path.parent.mkdir(parents=True, exist_ok=True)

        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)

    @staticmethod
    def write_bytes(path: str, content: bytes) -> None:
        """
        Write binary data to a file.

        Args:
            path: File path (relative to /home/files or absolute)
            content: Binary content to write

        Raises:
            ValueError: If path is outside /home/files
            RuntimeError: If no execution context

        Example:
            >>> from bifrost import files
            >>> files.write_bytes("uploads/image.png", image_data)
        """
        get_context()  # Ensure execution context exists

        file_path = files._resolve_path(path, allow_tmp=False)

        # Create parent directories if needed
        file_path.parent.mkdir(parents=True, exist_ok=True)

        with open(file_path, 'wb') as f:
            f.write(content)

    @staticmethod
    def list(directory: str = "") -> list[str]:
        """
        List files in a directory.

        Args:
            directory: Directory path (relative to /home/files, default: root)

        Returns:
            list[str]: List of file and directory names

        Raises:
            FileNotFoundError: If directory doesn't exist
            ValueError: If path is outside allowed directories
            RuntimeError: If no execution context

        Example:
            >>> from bifrost import files
            >>> items = files.list("uploads")
            >>> for item in items:
            ...     print(item)
        """
        get_context()  # Ensure execution context exists

        dir_path = files._resolve_path(directory, allow_tmp=True)

        if not dir_path.exists():
            raise FileNotFoundError(f"Directory not found: {directory}")

        if not dir_path.is_dir():
            raise ValueError(f"Not a directory: {directory}")

        return [item.name for item in dir_path.iterdir()]

    @staticmethod
    def delete(path: str) -> None:
        """
        Delete a file or directory.

        Args:
            path: File or directory path (relative to /home/files or absolute)

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If path is outside allowed directories
            RuntimeError: If no execution context

        Example:
            >>> from bifrost import files
            >>> files.delete("temp/old_file.txt")
        """
        get_context()  # Ensure execution context exists

        file_path = files._resolve_path(path, allow_tmp=True)

        if not file_path.exists():
            raise FileNotFoundError(f"Path not found: {path}")

        if file_path.is_dir():
            shutil.rmtree(file_path)
        else:
            file_path.unlink()

    @staticmethod
    def exists(path: str) -> bool:
        """
        Check if a file or directory exists.

        Args:
            path: File or directory path (relative to /home/files or absolute)

        Returns:
            bool: True if path exists

        Raises:
            ValueError: If path is outside allowed directories
            RuntimeError: If no execution context

        Example:
            >>> from bifrost import files
            >>> if files.exists("data/customers.csv"):
            ...     data = files.read("data/customers.csv")
        """
        get_context()  # Ensure execution context exists

        try:
            file_path = files._resolve_path(path, allow_tmp=True)
            return file_path.exists()
        except ValueError:
            return False
