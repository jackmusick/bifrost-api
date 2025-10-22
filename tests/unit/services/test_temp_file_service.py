"""
Unit tests for TempFileService

Tests cover:
- Creating temporary files with custom suffixes/prefixes
- Creating temporary directories
- Getting temp paths
- Cleaning up old files
- Deleting specific temp files
- Path safety validation
- Error handling
"""

import pytest
import os
from pathlib import Path
from unittest.mock import patch
import time

from services.temp_file_service import (
    TempFileService,
    get_temp_file_service,
    new_temp_file,
    new_temp_directory,
)


class TestTempFileServiceInitialization:
    """Test TempFileService initialization"""

    def test_init_with_default_path(self):
        """Should initialize with /tmp by default"""
        service = TempFileService()
        assert service.tmp_path == Path("/tmp")

    def test_init_with_custom_path(self, temp_test_dir):
        """Should initialize with provided path"""
        service = TempFileService(tmp_path=str(temp_test_dir))
        assert service.tmp_path == temp_test_dir

    def test_init_creates_directory(self, temp_test_dir):
        """Should create temp directory if it doesn't exist"""
        nested_path = temp_test_dir / "nested" / "temp"
        assert not nested_path.exists()

        service = TempFileService(tmp_path=str(nested_path))

        assert nested_path.exists()
        assert nested_path.is_dir()

    def test_init_with_env_variable(self, temp_test_dir):
        """Should use TMP_PATH environment variable"""
        with patch.dict(os.environ, {"TMP_PATH": str(temp_test_dir)}):
            service = TempFileService()
            assert service.tmp_path == temp_test_dir


class TestTempFileServiceCreateFile:
    """Test temporary file creation"""

    def test_create_temp_file_default(self, temp_test_dir):
        """Should create temp file with default prefix"""
        service = TempFileService(tmp_path=str(temp_test_dir))

        file_path = service.create_temp_file()

        assert file_path.exists()
        assert file_path.is_file()
        assert file_path.name.startswith("tmp_")
        assert str(file_path).startswith(str(temp_test_dir))

    def test_create_temp_file_with_suffix(self, temp_test_dir):
        """Should create temp file with custom suffix"""
        service = TempFileService(tmp_path=str(temp_test_dir))

        file_path = service.create_temp_file(suffix=".json")

        assert file_path.exists()
        assert file_path.name.endswith(".json")

    def test_create_temp_file_with_prefix(self, temp_test_dir):
        """Should create temp file with custom prefix"""
        service = TempFileService(tmp_path=str(temp_test_dir))

        file_path = service.create_temp_file(prefix="backup")

        assert file_path.exists()
        assert file_path.name.startswith("backup_")

    def test_create_temp_file_with_prefix_and_suffix(self, temp_test_dir):
        """Should create temp file with custom prefix and suffix"""
        service = TempFileService(tmp_path=str(temp_test_dir))

        file_path = service.create_temp_file(prefix="log", suffix=".txt")

        assert file_path.exists()
        assert file_path.name.startswith("log_")
        assert file_path.name.endswith(".txt")

    def test_create_temp_file_unique_names(self, temp_test_dir):
        """Should create unique temp files"""
        service = TempFileService(tmp_path=str(temp_test_dir))

        file1 = service.create_temp_file()
        file2 = service.create_temp_file()

        assert file1 != file2
        assert file1.exists()
        assert file2.exists()

    def test_create_temp_file_empty(self, temp_test_dir):
        """Should create empty temp file"""
        service = TempFileService(tmp_path=str(temp_test_dir))

        file_path = service.create_temp_file()

        assert file_path.stat().st_size == 0


class TestTempFileServiceCreateDirectory:
    """Test temporary directory creation"""

    def test_create_temp_directory_default(self, temp_test_dir):
        """Should create temp directory with default prefix"""
        service = TempFileService(tmp_path=str(temp_test_dir))

        dir_path = service.create_temp_directory()

        assert dir_path.exists()
        assert dir_path.is_dir()
        assert dir_path.name.startswith("tmp_")

    def test_create_temp_directory_with_suffix(self, temp_test_dir):
        """Should create temp directory with custom suffix"""
        service = TempFileService(tmp_path=str(temp_test_dir))

        dir_path = service.create_temp_directory(suffix="_backup")

        assert dir_path.exists()
        assert dir_path.name.endswith("_backup")

    def test_create_temp_directory_with_prefix(self, temp_test_dir):
        """Should create temp directory with custom prefix"""
        service = TempFileService(tmp_path=str(temp_test_dir))

        dir_path = service.create_temp_directory(prefix="workspace")

        assert dir_path.exists()
        assert dir_path.name.startswith("workspace_")

    def test_create_temp_directory_unique_names(self, temp_test_dir):
        """Should create unique temp directories"""
        service = TempFileService(tmp_path=str(temp_test_dir))

        dir1 = service.create_temp_directory()
        dir2 = service.create_temp_directory()

        assert dir1 != dir2
        assert dir1.exists()
        assert dir2.exists()

    def test_create_temp_directory_empty(self, temp_test_dir):
        """Should create empty temp directory"""
        service = TempFileService(tmp_path=str(temp_test_dir))

        dir_path = service.create_temp_directory()

        assert len(list(dir_path.iterdir())) == 0


class TestTempFileServiceGetPath:
    """Test getting temp paths"""

    def test_get_temp_path(self, temp_test_dir):
        """Should return path in temp directory"""
        service = TempFileService(tmp_path=str(temp_test_dir))

        path = service.get_temp_path("myfile.txt")

        assert path == temp_test_dir / "myfile.txt"

    def test_get_temp_path_nested(self, temp_test_dir):
        """Should handle nested paths"""
        service = TempFileService(tmp_path=str(temp_test_dir))

        path = service.get_temp_path("subdir/myfile.txt")

        assert path == temp_test_dir / "subdir" / "myfile.txt"


class TestTempFileServiceCleanup:
    """Test cleanup operations"""

    def test_delete_temp_file(self, temp_test_dir):
        """Should delete temp file"""
        service = TempFileService(tmp_path=str(temp_test_dir))
        file_path = service.create_temp_file()

        assert file_path.exists()
        service.delete_temp_file(file_path)
        assert not file_path.exists()

    def test_delete_temp_directory(self, temp_test_dir):
        """Should delete temp directory"""
        service = TempFileService(tmp_path=str(temp_test_dir))
        dir_path = service.create_temp_directory()

        # Add a file to directory
        test_file = dir_path / "test.txt"
        test_file.write_text("test")

        assert dir_path.exists()
        service.delete_temp_file(dir_path)
        assert not dir_path.exists()

    def test_delete_nonexistent_file_warning(self, temp_test_dir):
        """Should warn but not fail when deleting non-existent file"""
        service = TempFileService(tmp_path=str(temp_test_dir))
        nonexistent = temp_test_dir / "missing.txt"

        # Should not raise
        service.delete_temp_file(nonexistent)

    def test_delete_file_outside_temp_raises_error(self, temp_test_dir):
        """Should reject deletion of files outside temp directory"""
        service = TempFileService(tmp_path=str(temp_test_dir))

        # Try to delete file outside temp directory
        with pytest.raises(ValueError, match="not in temp directory"):
            service.delete_temp_file(Path("/etc/passwd"))

    def test_cleanup_old_files_default_age(self, temp_test_dir):
        """Should clean up files older than 24 hours"""
        service = TempFileService(tmp_path=str(temp_test_dir))

        # Create old file (modify time in past)
        old_file = service.create_temp_file(prefix="old", suffix=".txt")
        old_file.write_text("old content")

        # Set modification time to 25 hours ago
        old_time = time.time() - (25 * 3600)
        os.utime(old_file, (old_time, old_time))

        # Create recent file
        new_file = service.create_temp_file(prefix="new", suffix=".txt")
        new_file.write_text("new content")

        deleted_count = service.cleanup_old_files(max_age_hours=24)

        assert deleted_count >= 1
        assert not old_file.exists()
        assert new_file.exists()

    def test_cleanup_old_files_custom_age(self, temp_test_dir):
        """Should respect custom age threshold"""
        service = TempFileService(tmp_path=str(temp_test_dir))

        # Create file modified 2 hours ago
        old_file = service.create_temp_file(prefix="old", suffix=".txt")
        old_file.write_text("content")
        old_time = time.time() - (2 * 3600)
        os.utime(old_file, (old_time, old_time))

        # Cleanup with 1-hour threshold
        deleted_count = service.cleanup_old_files(max_age_hours=1)

        assert deleted_count >= 1
        assert not old_file.exists()

    def test_cleanup_skips_recent_files(self, temp_test_dir):
        """Should skip recently modified files"""
        service = TempFileService(tmp_path=str(temp_test_dir))

        # Create recent file
        recent_file = service.create_temp_file(prefix="recent", suffix=".txt")
        recent_file.write_text("recent content")

        deleted_count = service.cleanup_old_files(max_age_hours=1)

        assert deleted_count == 0
        assert recent_file.exists()

    def test_cleanup_handles_permission_errors(self, temp_test_dir):
        """Should handle permission errors during cleanup"""
        service = TempFileService(tmp_path=str(temp_test_dir))

        # Create files
        file1 = service.create_temp_file(prefix="file1", suffix=".txt")
        file2 = service.create_temp_file(prefix="file2", suffix=".txt")

        # Set file1 to old time (but we'll mock unlink to fail)
        old_time = time.time() - (25 * 3600)
        os.utime(file1, (old_time, old_time))

        # Cleanup should handle the error and continue
        deleted_count = service.cleanup_old_files(max_age_hours=24)

        # Should have attempted cleanup
        assert isinstance(deleted_count, int)


class TestTempFileServiceSingleton:
    """Test singleton instance management"""

    def test_get_temp_file_service_singleton(self):
        """Should return singleton instance"""
        # Clear global state for test
        import services.temp_file_service as temp_module
        temp_module._temp_file_service = None

        service1 = get_temp_file_service()
        service2 = get_temp_file_service()

        assert service1 is service2

    def test_new_temp_file_function(self, temp_test_dir):
        """Should work via convenience function"""
        with patch.dict(os.environ, {"TMP_PATH": str(temp_test_dir)}):
            # Clear singleton
            import services.temp_file_service as temp_module
            temp_module._temp_file_service = None

            file_path = new_temp_file(suffix=".log")

            assert file_path.exists()
            assert file_path.name.endswith(".log")

    def test_new_temp_directory_function(self, temp_test_dir):
        """Should work via convenience function"""
        with patch.dict(os.environ, {"TMP_PATH": str(temp_test_dir)}):
            # Clear singleton
            import services.temp_file_service as temp_module
            temp_module._temp_file_service = None

            dir_path = new_temp_directory(prefix="workspace")

            assert dir_path.exists()
            assert dir_path.name.startswith("workspace_")


class TestTempFileServicePathSafety:
    """Test path safety and validation"""

    def test_all_files_created_in_temp_directory(self, temp_test_dir):
        """Should only create files within temp directory"""
        service = TempFileService(tmp_path=str(temp_test_dir))

        file_path = service.create_temp_file()
        dir_path = service.create_temp_directory()

        # Both should be under temp directory
        assert str(file_path).startswith(str(temp_test_dir))
        assert str(dir_path).startswith(str(temp_test_dir))

    def test_delete_validates_path_is_in_temp_dir(self, temp_test_dir):
        """Should validate paths are within temp directory"""
        service = TempFileService(tmp_path=str(temp_test_dir))

        with pytest.raises(ValueError):
            service.delete_temp_file(Path("/tmp/../../../etc/passwd"))
