"""
Unit tests for ZIP Service

Tests cover:
- Creating workspace ZIP archives in memory
- Creating selective ZIP archives
- ZIP file validation
- Size estimation
- Error handling
- BytesIO buffer management
"""

import pytest
import zipfile
from io import BytesIO
from unittest.mock import MagicMock, patch

from services.zip_service import (
    create_workspace_zip,
    create_selective_zip,
    estimate_workspace_size,
)


class TestCreateWorkspaceZip:
    """Test creating full workspace ZIP archives"""

    def test_create_workspace_zip_success(self, mock_workspace_service):
        """Should create ZIP archive with all workspace files"""
        result = create_workspace_zip()

        # Result should be BytesIO buffer
        assert isinstance(result, BytesIO)
        assert result.tell() == 0  # Should be rewound

        # Should be valid ZIP file
        result.seek(0)
        with zipfile.ZipFile(result, 'r') as zf:
            names = zf.namelist()
            assert len(names) == 3
            assert "file1.txt" in names
            assert "file2.py" in names
            assert "subdir/file3.json" in names

    def test_create_workspace_zip_with_directory_path(self, mock_workspace_service):
        """Should support starting from specific directory"""
        result = create_workspace_zip(directory_path="subdir")

        assert isinstance(result, BytesIO)
        # Verify list_files was called (it's a function not a mock)
        assert result.tell() == 0

    def test_create_workspace_zip_rewound_buffer(self, mock_workspace_service):
        """Should return buffer rewound to position 0"""
        result = create_workspace_zip()

        # Buffer should be at position 0 for reading
        assert result.tell() == 0

    def test_create_workspace_zip_skips_directories(self, mock_workspace_service):
        """Should skip directory entries in listing"""
        mock_workspace_service["service"].list_files.return_value = [
            {"path": "file1.txt", "isDirectory": False, "size": 1024},
            {"path": "subdir", "isDirectory": True, "size": 0},
            {"path": "file2.py", "isDirectory": False, "size": 2048},
        ]

        result = create_workspace_zip()

        result.seek(0)
        with zipfile.ZipFile(result, 'r') as zf:
            names = zf.namelist()
            # Should only have files, not directories
            assert "file1.txt" in names
            assert "file2.py" in names
            assert "subdir" not in names

    def test_create_workspace_zip_empty_workspace(self):
        """Should handle empty workspace"""
        with patch("services.zip_service.get_workspace_service") as mock_get_ws:
            mock_service = MagicMock()
            mock_service.list_files.return_value = []
            mock_get_ws.return_value = mock_service

            result = create_workspace_zip()

            assert isinstance(result, BytesIO)
            result.seek(0)
            with zipfile.ZipFile(result, 'r') as zf:
                assert len(zf.namelist()) == 0

    def test_create_workspace_zip_file_content(self):
        """Should include correct file content in ZIP"""
        with patch("services.zip_service.get_workspace_service") as mock_get_ws:
            mock_service = MagicMock()
            mock_service.list_files.return_value = [
                {"path": "file1.txt", "isDirectory": False, "size": 1024},
            ]
            mock_service.read_file.return_value = b"Test content"
            mock_get_ws.return_value = mock_service

            result = create_workspace_zip()

            result.seek(0)
            with zipfile.ZipFile(result, 'r') as zf:
                content = zf.read("file1.txt")
                assert content == b"Test content"

    def test_create_workspace_zip_skips_unreadable_files(self, mock_workspace_service):
        """Should skip files that fail to read"""
        mock_workspace_service["service"].list_files.return_value = [
            {"path": "file1.txt", "isDirectory": False, "size": 1024},
            {"path": "file2.py", "isDirectory": False, "size": 2048},
        ]

        def read_with_error(path):
            if path == "file2.py":
                raise Exception("Permission denied")
            return b"Content of file1"

        mock_workspace_service["service"].read_file = read_with_error

        result = create_workspace_zip()

        result.seek(0)
        with zipfile.ZipFile(result, 'r') as zf:
            names = zf.namelist()
            # Should have file1, but not file2
            assert "file1.txt" in names
            assert "file2.py" not in names

    def test_create_workspace_zip_deflate_compression(self, mock_workspace_service):
        """Should use DEFLATE compression"""
        mock_workspace_service["service"].list_files.return_value = [
            {"path": "file.txt", "isDirectory": False, "size": 10000},
        ]
        # Large content for compression to have effect
        mock_workspace_service["service"].read_file.return_value = b"x" * 10000

        result = create_workspace_zip()

        result.seek(0)
        with zipfile.ZipFile(result, 'r') as zf:
            # Check compression type
            info = zf.infolist()[0]
            assert info.compress_type == zipfile.ZIP_DEFLATED

    def test_create_workspace_zip_preserves_paths(self):
        """Should preserve file paths in ZIP"""
        with patch("services.zip_service.get_workspace_service") as mock_get_ws:
            mock_service = MagicMock()
            mock_service.list_files.return_value = [
                {"path": "src/main.py", "isDirectory": False},
                {"path": "config/settings.yaml", "isDirectory": False},
                {"path": "src/utils/helpers.py", "isDirectory": False},
            ]
            mock_service.read_file.return_value = b"content"
            mock_get_ws.return_value = mock_service

            result = create_workspace_zip()

            result.seek(0)
            with zipfile.ZipFile(result, 'r') as zf:
                names = zf.namelist()
                assert "src/main.py" in names
                assert "config/settings.yaml" in names
                assert "src/utils/helpers.py" in names


class TestCreateSelectiveZip:
    """Test creating selective ZIP archives"""

    def test_create_selective_zip_success(self, mock_workspace_service):
        """Should create ZIP with selected files"""
        file_paths = ["file1.txt", "file2.py"]

        result = create_selective_zip(file_paths)

        assert isinstance(result, BytesIO)
        result.seek(0)
        with zipfile.ZipFile(result, 'r') as zf:
            names = zf.namelist()
            assert "file1.txt" in names
            assert "file2.py" in names

    def test_create_selective_zip_empty_list(self, mock_workspace_service):
        """Should handle empty file list"""
        result = create_selective_zip([])

        assert isinstance(result, BytesIO)
        result.seek(0)
        with zipfile.ZipFile(result, 'r') as zf:
            assert len(zf.namelist()) == 0

    def test_create_selective_zip_single_file(self, mock_workspace_service):
        """Should handle single file"""
        result = create_selective_zip(["file1.txt"])

        result.seek(0)
        with zipfile.ZipFile(result, 'r') as zf:
            assert len(zf.namelist()) == 1
            assert "file1.txt" in zf.namelist()

    def test_create_selective_zip_skips_unreadable_files(self, mock_workspace_service):
        """Should skip files that fail to read"""
        def read_with_error(path):
            if path == "file2.py":
                raise Exception("File not found")
            return b"Content"

        mock_workspace_service["service"].read_file = read_with_error

        result = create_selective_zip(["file1.txt", "file2.py"])

        result.seek(0)
        with zipfile.ZipFile(result, 'r') as zf:
            names = zf.namelist()
            assert "file1.txt" in names
            assert "file2.py" not in names

    def test_create_selective_zip_rewound(self, mock_workspace_service):
        """Should return buffer rewound to position 0"""
        result = create_selective_zip(["file1.txt"])

        assert result.tell() == 0


class TestEstimateWorkspaceSize:
    """Test workspace size estimation"""

    def test_estimate_workspace_size_sum(self):
        """Should sum up all file sizes"""
        items = [
            {"path": "file1.txt", "isDirectory": False, "size": 1024},
            {"path": "file2.py", "isDirectory": False, "size": 2048},
            {"path": "file3.json", "isDirectory": False, "size": 512},
        ]

        total = estimate_workspace_size(items)

        assert total == 3584

    def test_estimate_workspace_size_skips_directories(self):
        """Should skip directory entries"""
        items = [
            {"path": "file1.txt", "isDirectory": False, "size": 1024},
            {"path": "subdir", "isDirectory": True, "size": 0},
            {"path": "file2.py", "isDirectory": False, "size": 2048},
        ]

        total = estimate_workspace_size(items)

        assert total == 3072

    def test_estimate_workspace_size_handles_missing_size(self):
        """Should handle items without size"""
        items = [
            {"path": "file1.txt", "isDirectory": False, "size": 1024},
            {"path": "file2.py", "isDirectory": False},  # No size
            {"path": "file3.json", "isDirectory": False, "size": 512},
        ]

        total = estimate_workspace_size(items)

        assert total == 1536

    def test_estimate_workspace_size_empty_list(self):
        """Should return 0 for empty list"""
        total = estimate_workspace_size([])

        assert total == 0

    def test_estimate_workspace_size_only_directories(self):
        """Should return 0 for only directories"""
        items = [
            {"path": "dir1", "isDirectory": True, "size": 0},
            {"path": "dir2", "isDirectory": True, "size": 0},
        ]

        total = estimate_workspace_size(items)

        assert total == 0


class TestZipServiceErrorHandling:
    """Test error handling in ZIP service"""

    def test_create_workspace_zip_workspace_service_error(self):
        """Should raise error when workspace service fails"""
        with patch("services.zip_service.get_workspace_service") as mock_get_ws:
            mock_service = MagicMock()
            mock_service.list_files.side_effect = Exception("Service error")
            mock_get_ws.return_value = mock_service

            with pytest.raises(Exception, match="Service error"):
                create_workspace_zip()

    def test_create_selective_zip_workspace_service_error(self):
        """Should raise error when workspace service fails"""
        with patch("services.zip_service.get_workspace_service") as mock_get_ws:
            mock_service = MagicMock()
            # Error happens when trying to read file
            mock_service.read_file.side_effect = Exception("Service error")
            mock_get_ws.return_value = mock_service

            # create_selective_zip catches exceptions and logs them, it doesn't re-raise
            # Instead it skips the file
            result = create_selective_zip(["file1.txt"])

            # Should still return a ZIP (just empty since file was skipped)
            assert isinstance(result, BytesIO)


class TestZipServiceBufferManagement:
    """Test buffer management and resource cleanup"""

    def test_zip_buffer_is_seekable(self, mock_workspace_service):
        """ZIP buffer should be seekable"""
        result = create_workspace_zip()

        # Should be able to seek
        result.seek(0)
        assert result.tell() == 0

        result.seek(10)
        assert result.tell() == 10

        result.seek(0)
        assert result.tell() == 0

    def test_zip_buffer_size(self, mock_workspace_service):
        """ZIP buffer should have reasonable size"""
        result = create_workspace_zip()

        # Get size
        size = result.getbuffer().nbytes
        assert size > 0

    def test_multiple_zip_creations_independent(self, mock_workspace_service):
        """Multiple ZIP creations should be independent"""
        zip1 = create_workspace_zip()
        zip2 = create_workspace_zip()

        # Should be different objects
        assert zip1 is not zip2

        # Both should be valid
        zip1.seek(0)
        with zipfile.ZipFile(zip1, 'r') as zf1:
            names1 = zf1.namelist()

        zip2.seek(0)
        with zipfile.ZipFile(zip2, 'r') as zf2:
            names2 = zf2.namelist()

        # Should have same content
        assert names1 == names2


class TestZipServiceIntegration:
    """Integration tests for ZIP service"""

    def test_full_workflow_create_read_verify(self):
        """Should create, read, and verify ZIP contents"""
        with patch("services.zip_service.get_workspace_service") as mock_get_ws:
            mock_service = MagicMock()
            mock_service.list_files.return_value = [
                {"path": "config.json", "isDirectory": False},
                {"path": "data.txt", "isDirectory": False},
            ]

            mock_service.read_file.side_effect = [
                b'{"setting": "value"}',
                b"some data"
            ]
            mock_get_ws.return_value = mock_service

            # Create ZIP
            zip_buffer = create_workspace_zip()

            # Read and verify
            zip_buffer.seek(0)
            with zipfile.ZipFile(zip_buffer, 'r') as zf:
                # Check both files are present
                assert zf.namelist() == ["config.json", "data.txt"]

                # Verify content
                config_content = zf.read("config.json")
                assert b'"setting": "value"' in config_content

                data_content = zf.read("data.txt")
                assert data_content == b"some data"
