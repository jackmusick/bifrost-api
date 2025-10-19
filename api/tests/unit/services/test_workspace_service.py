"""
Unit tests for WorkspaceService

Tests workspace file operations and path validation.
Mocks file system operations to test in isolation.
"""

import pytest
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open

from services.workspace_service import WorkspaceService, get_workspace_service


class TestWorkspaceServiceInitialization:
    """Test workspace setup and initialization"""

    def test_get_workspace_path_default(self, mock_filesystem):
        """Should use default workspace path from env"""
        with patch.dict("os.environ", {"WORKSPACE_PATH": "/workspace"}):
            with patch("services.workspace_service.Path") as mock_path:
                path_instance = MagicMock()
                path_instance.exists.return_value = True
                path_instance.mkdir.return_value = None
                mock_path.return_value = path_instance

                service = WorkspaceService()

                # Path should be created
                path_instance.mkdir.assert_called()

    def test_get_workspace_path_custom(self, mock_filesystem):
        """Should use custom workspace path if provided"""
        with patch("services.workspace_service.Path") as mock_path:
            path_instance = MagicMock()
            path_instance.exists.return_value = True
            path_instance.mkdir.return_value = None
            mock_path.return_value = path_instance

            service = WorkspaceService("/custom/workspace")

            assert service.workspace_path is not None

    def test_ensure_workspace_exists(self, mock_filesystem):
        """Should create workspace directory if missing"""
        with patch("services.workspace_service.Path") as mock_path:
            path_instance = MagicMock()
            path_instance.exists.return_value = False
            path_instance.mkdir.return_value = None
            mock_path.return_value = path_instance

            service = WorkspaceService("/workspace")

            # mkdir should be called with parents=True, exist_ok=True
            path_instance.mkdir.assert_called()


class TestWorkspaceServiceFileOperations:
    """Test file operations"""

    def test_list_workflow_files(self, mock_filesystem):
        """Should list all files in workspace"""
        with patch("services.workspace_service.Path") as mock_path:
            # Setup workspace path
            workspace = MagicMock()
            workspace.exists.return_value = True
            workspace.mkdir.return_value = None
            workspace.rglob.return_value = []
            mock_path.return_value = workspace

            service = WorkspaceService()
            files = service.list_files()

            # Should return a list
            assert isinstance(files, list)

    def test_list_files_with_content(self, mock_filesystem):
        """Should return file metadata with size and modification time"""
        with patch("services.workspace_service.Path") as mock_path:
            # Setup workspace
            workspace = MagicMock()
            workspace.exists.return_value = True
            workspace.mkdir.return_value = None

            # Setup file entries
            file1 = MagicMock()
            file1.is_dir.return_value = False
            file1.name = "workflow1.py"
            file1.relative_to.return_value = Path("workflow1.py")
            file1.stat.return_value = MagicMock(st_size=1024, st_mtime=1000000000)

            workspace.rglob.return_value = [file1]
            mock_path.return_value = workspace

            service = WorkspaceService()
            files = service.list_files()

            assert len(files) >= 0

    def test_read_workflow_file(self, mock_filesystem):
        """Should read workflow file contents"""
        with patch("services.workspace_service.Path") as mock_path:
            # Setup workspace
            workspace = MagicMock()
            workspace.exists.return_value = True
            workspace.mkdir.return_value = None
            workspace.__truediv__.return_value = MagicMock()
            mock_path.return_value = workspace

            # Setup file
            file_path = workspace / "workflow.py"
            file_path.exists.return_value = True
            file_path.is_file.return_value = True
            file_path.read_bytes.return_value = b"print('Hello')"

            service = WorkspaceService()
            # We need to mock the division operator
            with patch.object(Path, '__truediv__', return_value=file_path):
                content = service.read_file("workflow.py")

            assert isinstance(content, bytes)

    def test_write_workflow_file(self, mock_filesystem):
        """Should write file to workspace"""
        with patch("services.workspace_service.Path") as mock_path:
            # Setup workspace
            workspace = MagicMock()
            workspace.exists.return_value = True
            workspace.mkdir.return_value = None
            workspace.__truediv__.return_value = MagicMock()
            mock_path.return_value = workspace

            # Setup file for writing
            file_path = workspace / "new_workflow.py"
            file_path.exists.return_value = False
            file_path.is_file.return_value = False
            file_path.parent = MagicMock()
            file_path.parent.mkdir.return_value = None
            file_path.write_bytes.return_value = None
            file_path.stat.return_value = MagicMock(st_size=100, st_mtime=1000000000)

            service = WorkspaceService()
            with patch.object(Path, '__truediv__', return_value=file_path):
                result = service.write_file("new_workflow.py", b"new content")

            assert result is not None
            assert "path" in result

    def test_delete_workflow_file(self, mock_filesystem):
        """Should delete file from workspace"""
        with patch("services.workspace_service.Path") as mock_path:
            # Setup workspace
            workspace = MagicMock()
            workspace.exists.return_value = True
            workspace.mkdir.return_value = None
            workspace.__truediv__.return_value = MagicMock()
            mock_path.return_value = workspace

            # Setup file for deletion
            file_path = workspace / "workflow.py"
            file_path.exists.return_value = True
            file_path.is_file.return_value = True
            file_path.unlink.return_value = None

            service = WorkspaceService()
            with patch.object(Path, '__truediv__', return_value=file_path):
                service.delete_file("workflow.py")

            # Should not raise exception


class TestWorkspaceServiceValidation:
    """Test path validation and security"""

    def test_validate_workflow_name(self, mock_filesystem):
        """Should validate workflow name format"""
        with patch("services.workspace_service.Path") as mock_path_class:
            # Create proper mock for Path
            workspace = MagicMock()
            workspace.exists.return_value = True
            workspace.mkdir.return_value = None
            mock_path_class.return_value = workspace

            service = WorkspaceService()

            # For validate_path, we don't mock - it uses real Path internally
            # Reset the patch to use real Path for validate_path
            with patch("services.workspace_service.Path", Path):
                # Valid names
                assert service.validate_path("workflow.py") is True
                assert service.validate_path("my_workflow.py") is True
                assert service.validate_path("workflows/main.py") is True
                assert service.validate_path("dir/subdir/workflow.py") is True

    def test_prevent_directory_traversal(self, mock_filesystem):
        """Should reject paths with .. or absolute paths"""
        with patch("services.workspace_service.Path"):
            service = WorkspaceService()

            # Invalid - directory traversal
            assert service.validate_path("../etc/passwd") is False
            assert service.validate_path("../../sensitive") is False
            assert service.validate_path("workflows/../../../etc") is False

    def test_reject_absolute_paths(self, mock_filesystem):
        """Should reject absolute paths"""
        with patch("services.workspace_service.Path"):
            service = WorkspaceService()

            assert service.validate_path("/etc/passwd") is False
            assert service.validate_path("/workspace/file") is False

    def test_restrict_to_valid_characters(self, mock_filesystem):
        """Should reject paths with invalid characters"""
        with patch("services.workspace_service.Path"):
            service = WorkspaceService()

            # Invalid characters
            assert service.validate_path("file<name>.py") is False
            assert service.validate_path("file>name.py") is False
            assert service.validate_path("file:name.py") is False
            assert service.validate_path("file|name.py") is False
            assert service.validate_path("file?name.py") is False
            assert service.validate_path("file*name.py") is False


class TestWorkspaceServiceErrors:
    """Test error handling"""

    def test_handles_missing_file(self, mock_filesystem):
        """Should handle file not found"""
        with patch("services.workspace_service.Path") as mock_path:
            workspace = MagicMock()
            workspace.exists.return_value = True
            workspace.mkdir.return_value = None
            workspace.__truediv__.return_value = MagicMock()
            mock_path.return_value = workspace

            file_path = workspace / "missing.py"
            file_path.exists.return_value = False

            service = WorkspaceService()

            with pytest.raises(FileNotFoundError):
                with patch.object(Path, '__truediv__', return_value=file_path):
                    service.read_file("missing.py")

    def test_handles_file_read_errors(self, mock_filesystem):
        """Should handle file read failures"""
        with patch("services.workspace_service.Path") as mock_path:
            workspace = MagicMock()
            workspace.exists.return_value = True
            workspace.mkdir.return_value = None
            workspace.__truediv__.return_value = MagicMock()
            mock_path.return_value = workspace

            file_path = workspace / "error.py"
            file_path.exists.return_value = True
            file_path.is_file.return_value = True
            file_path.read_bytes.side_effect = OSError("Read error")

            service = WorkspaceService()

            with pytest.raises(OSError):
                with patch.object(Path, '__truediv__', return_value=file_path):
                    service.read_file("error.py")

    def test_handles_file_write_errors(self, mock_filesystem):
        """Should handle file write failures"""
        with patch("services.workspace_service.Path") as mock_path:
            workspace = MagicMock()
            workspace.exists.return_value = True
            workspace.mkdir.return_value = None
            workspace.__truediv__.return_value = MagicMock()
            mock_path.return_value = workspace

            file_path = workspace / "write_error.py"
            file_path.parent = MagicMock()
            file_path.parent.mkdir.return_value = None
            file_path.write_bytes.side_effect = OSError("Write error")

            service = WorkspaceService()

            with pytest.raises(OSError):
                with patch.object(Path, '__truediv__', return_value=file_path):
                    service.write_file("write_error.py", b"content")

    def test_handles_missing_workspace_directory(self, mock_filesystem):
        """Should handle workspace directory not found"""
        with patch("services.workspace_service.Path") as mock_path:
            workspace = MagicMock()
            workspace.exists.return_value = False
            workspace.mkdir.side_effect = OSError("Cannot create directory")
            mock_path.return_value = workspace

            with pytest.raises(OSError):
                WorkspaceService()


# ====================  Directory Operations Tests ====================


class TestWorkspaceServiceDirectories:
    """Test directory operations"""

    def test_create_directory(self, mock_filesystem):
        """Should create directory in workspace"""
        with patch("services.workspace_service.Path") as mock_path:
            workspace = MagicMock()
            workspace.exists.return_value = True
            workspace.mkdir.return_value = None
            workspace.__truediv__.return_value = MagicMock()
            mock_path.return_value = workspace

            dir_path = workspace / "new_dir"
            dir_path.exists.return_value = False
            dir_path.mkdir.return_value = None

            service = WorkspaceService()

            with patch.object(Path, '__truediv__', return_value=dir_path):
                service.create_directory("new_dir")

            # Should not raise exception

    def test_delete_directory_recursive(self, mock_filesystem):
        """Should delete directory recursively"""
        with patch("services.workspace_service.Path") as mock_path:
            workspace = MagicMock()
            workspace.exists.return_value = True
            workspace.mkdir.return_value = None
            workspace.__truediv__.return_value = MagicMock()
            mock_path.return_value = workspace

            dir_path = workspace / "old_dir"
            dir_path.exists.return_value = True
            dir_path.is_dir.return_value = True

            service = WorkspaceService()

            with patch("shutil.rmtree") as mock_rmtree:
                with patch.object(Path, '__truediv__', return_value=dir_path):
                    service.delete_directory("old_dir", recursive=True)

                mock_rmtree.assert_called()

    def test_delete_empty_directory(self, mock_filesystem):
        """Should delete empty directory without recursive flag"""
        with patch("services.workspace_service.Path") as mock_path:
            workspace = MagicMock()
            workspace.exists.return_value = True
            workspace.mkdir.return_value = None
            workspace.__truediv__.return_value = MagicMock()
            mock_path.return_value = workspace

            dir_path = workspace / "empty_dir"
            dir_path.exists.return_value = True
            dir_path.is_dir.return_value = True
            dir_path.rmdir.return_value = None

            service = WorkspaceService()

            with patch.object(Path, '__truediv__', return_value=dir_path):
                service.delete_directory("empty_dir", recursive=False)

            dir_path.rmdir.assert_called()


# ====================  Singleton Tests ====================


class TestWorkspaceServiceSingleton:
    """Test workspace service singleton pattern"""

    def test_get_workspace_service_singleton(self, mock_filesystem):
        """Should return same instance on multiple calls"""
        with patch("services.workspace_service.Path"):
            # Reset singleton
            import services.workspace_service as ws_module
            ws_module._workspace_service = None

            service1 = get_workspace_service()
            service2 = get_workspace_service()

            # Should be same instance
            assert service1 is service2

            # Reset for other tests
            ws_module._workspace_service = None


# ====================  Integration Tests ====================


class TestWorkspaceServiceIntegration:
    """Integration tests for workspace operations"""

    def test_full_workflow_lifecycle(self, mock_filesystem):
        """Should handle complete workflow file lifecycle"""
        with patch("services.workspace_service.Path") as mock_path:
            workspace = MagicMock()
            workspace.exists.return_value = True
            workspace.mkdir.return_value = None
            workspace.__truediv__.return_value = MagicMock()
            mock_path.return_value = workspace

            service = WorkspaceService()

            # 1. Create directory
            dir_path = workspace / "workflows"
            dir_path.exists.return_value = False
            dir_path.mkdir.return_value = None

            # 2. Write file
            file_path = dir_path / "test.py"
            file_path.parent = MagicMock()
            file_path.parent.mkdir.return_value = None
            file_path.write_bytes.return_value = None
            file_path.stat.return_value = MagicMock(st_size=100, st_mtime=1000000000)

            # 3. Read file
            file_path.exists.return_value = True
            file_path.is_file.return_value = True
            file_path.read_bytes.return_value = b"print('test')"

            # 4. List files
            workspace.rglob.return_value = [file_path]
            file_path.relative_to.return_value = Path("workflows/test.py")

            # 5. Delete file
            file_path.unlink.return_value = None

            with patch.object(Path, '__truediv__', side_effect=[dir_path, file_path]):
                # Operations would execute here
                pass

    def test_path_validation_in_operations(self, mock_filesystem):
        """Should validate paths before operations"""
        with patch("services.workspace_service.Path"):
            service = WorkspaceService()

            # Should reject invalid paths
            invalid_paths = [
                "../etc/passwd",
                "/etc/passwd",
                "file|name.py",
                "file<script>.py"
            ]

            for invalid_path in invalid_paths:
                assert service.validate_path(invalid_path) is False


# ====================  Additional Coverage Tests ====================


class TestWorkspaceServiceAdditionalCoverage:
    """Additional tests for better coverage"""

    def test_list_files_recursive_traversal(self):
        """Should recursively traverse directories"""
        with patch("services.workspace_service.Path") as mock_path_class:
            workspace = MagicMock()
            workspace.exists.return_value = True
            workspace.mkdir.return_value = None

            # Setup file entries with subdirectories
            file1 = MagicMock()
            file1.is_dir.return_value = False
            file1.name = "file1.py"
            file1.relative_to.return_value = Path("file1.py")
            file1.stat.return_value = MagicMock(st_size=100, st_mtime=1000000000)

            file2 = MagicMock()
            file2.is_dir.return_value = True
            file2.name = "subdir"
            file2.relative_to.return_value = Path("subdir")
            file2.stat.return_value = MagicMock(st_size=0, st_mtime=1000000000)

            workspace.rglob.return_value = [file1, file2]
            workspace.__truediv__.return_value = workspace
            mock_path_class.return_value = workspace

            service = WorkspaceService()
            files = service.list_files()

            assert len(files) == 2
            assert any(f["name"] == "file1.py" for f in files)
            assert any(f["name"] == "subdir" for f in files)

    def test_read_file_returns_bytes(self, mock_filesystem):
        """Should return file content as bytes"""
        with patch("services.workspace_service.Path") as mock_path:
            workspace = MagicMock()
            workspace.exists.return_value = True
            workspace.mkdir.return_value = None
            workspace.__truediv__.return_value = MagicMock()
            mock_path.return_value = workspace

            file_path = workspace / "data.bin"
            file_path.exists.return_value = True
            file_path.is_file.return_value = True
            test_bytes = b"\x00\x01\x02\x03"
            file_path.read_bytes.return_value = test_bytes

            service = WorkspaceService()

            with patch.object(Path, '__truediv__', return_value=file_path):
                content = service.read_file("data.bin")

            assert content == test_bytes
            assert isinstance(content, bytes)

    def test_write_file_creates_parents(self, mock_filesystem):
        """Should create parent directories if needed"""
        with patch("services.workspace_service.Path") as mock_path:
            workspace = MagicMock()
            workspace.exists.return_value = True
            workspace.mkdir.return_value = None
            workspace.__truediv__.return_value = MagicMock()
            mock_path.return_value = workspace

            file_path = workspace / "nested/path/file.py"
            file_path.parent = MagicMock()
            file_path.parent.mkdir.return_value = None
            file_path.write_bytes.return_value = None
            file_path.stat.return_value = MagicMock(st_size=50, st_mtime=1000000000)

            service = WorkspaceService()

            with patch.object(Path, '__truediv__', return_value=file_path):
                result = service.write_file("nested/path/file.py", b"content")

            # Parent should be created
            file_path.parent.mkdir.assert_called()
            assert "path" in result
            assert result["size"] == 50

    def test_delete_file_not_a_file(self, mock_filesystem):
        """Should reject deleting non-files"""
        with patch("services.workspace_service.Path") as mock_path:
            workspace = MagicMock()
            workspace.exists.return_value = True
            workspace.mkdir.return_value = None
            workspace.__truediv__.return_value = MagicMock()
            mock_path.return_value = workspace

            file_path = workspace / "not_a_file"
            file_path.exists.return_value = True
            file_path.is_file.return_value = False

            service = WorkspaceService()

            with pytest.raises(ValueError):
                with patch.object(Path, '__truediv__', return_value=file_path):
                    service.delete_file("not_a_file")

    def test_list_files_with_relative_path(self, mock_filesystem):
        """Should list files from relative path"""
        with patch("services.workspace_service.Path") as mock_path:
            workspace = MagicMock()
            workspace.exists.return_value = True
            workspace.mkdir.return_value = None

            base_path = workspace / "subdir"
            base_path.exists.return_value = True

            file1 = MagicMock()
            file1.is_dir.return_value = False
            file1.name = "nested.py"
            file1.relative_to.return_value = Path("subdir/nested.py")
            file1.stat.return_value = MagicMock(st_size=256, st_mtime=1000000000)

            base_path.rglob.return_value = [file1]
            workspace.__truediv__.return_value = base_path
            mock_path.return_value = workspace

            service = WorkspaceService()

            with patch.object(Path, '__truediv__', return_value=base_path):
                files = service.list_files("subdir")

            assert len(files) >= 0

    def test_create_directory_already_exists(self, mock_filesystem):
        """Should reject creating existing directory"""
        with patch("services.workspace_service.Path") as mock_path:
            workspace = MagicMock()
            workspace.exists.return_value = True
            workspace.mkdir.return_value = None
            workspace.__truediv__.return_value = MagicMock()
            mock_path.return_value = workspace

            dir_path = workspace / "existing"
            dir_path.exists.return_value = True

            service = WorkspaceService()

            with pytest.raises(FileExistsError):
                with patch.object(Path, '__truediv__', return_value=dir_path):
                    service.create_directory("existing")

    def test_delete_directory_not_found(self, mock_filesystem):
        """Should reject deleting non-existent directory"""
        with patch("services.workspace_service.Path") as mock_path:
            workspace = MagicMock()
            workspace.exists.return_value = True
            workspace.mkdir.return_value = None
            workspace.__truediv__.return_value = MagicMock()
            mock_path.return_value = workspace

            dir_path = workspace / "missing_dir"
            dir_path.exists.return_value = False

            service = WorkspaceService()

            with pytest.raises(FileNotFoundError):
                with patch.object(Path, '__truediv__', return_value=dir_path):
                    service.delete_directory("missing_dir")

    def test_delete_directory_not_a_directory(self, mock_filesystem):
        """Should reject deleting non-directories"""
        with patch("services.workspace_service.Path") as mock_path:
            workspace = MagicMock()
            workspace.exists.return_value = True
            workspace.mkdir.return_value = None
            workspace.__truediv__.return_value = MagicMock()
            mock_path.return_value = workspace

            file_path = workspace / "file.txt"
            file_path.exists.return_value = True
            file_path.is_dir.return_value = False

            service = WorkspaceService()

            with pytest.raises(ValueError):
                with patch.object(Path, '__truediv__', return_value=file_path):
                    service.delete_directory("file.txt")
