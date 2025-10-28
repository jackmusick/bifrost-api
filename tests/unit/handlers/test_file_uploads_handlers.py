"""
Unit tests for file upload handlers
Tests upload URL generation logic with mocked dependencies
"""

from unittest.mock import MagicMock, patch

import pytest

from shared.context import Organization, ExecutionContext
from shared.exceptions import FileUploadError
from shared.handlers.file_uploads_handlers import (
    generate_file_upload_url,
    _validate_file_request,
)
from shared.models import FileUploadRequest, FileUploadResponse


class TestValidateFileRequest:
    """Tests for _validate_file_request validation function"""

    def test_valid_request(self):
        """Test validation passes for valid file request"""
        request = FileUploadRequest(
            file_name="document.pdf",
            content_type="application/pdf",
            file_size=1024000,
        )

        # Should not raise
        _validate_file_request(request, max_size_bytes=100 * 1024 * 1024)

    def test_empty_file_name_raises_error(self):
        """Test validation fails for empty file_name"""
        request = FileUploadRequest(
            file_name="",
            content_type="application/pdf",
            file_size=1024000,
        )

        with pytest.raises(FileUploadError) as exc_info:
            _validate_file_request(request, max_size_bytes=100 * 1024 * 1024)

        assert "file_name cannot be empty" in exc_info.value.message
        assert exc_info.value.file_name == ""

    def test_whitespace_only_file_name_raises_error(self):
        """Test validation fails for whitespace-only file_name"""
        request = FileUploadRequest(
            file_name="   ",
            content_type="application/pdf",
            file_size=1024000,
        )

        with pytest.raises(FileUploadError) as exc_info:
            _validate_file_request(request, max_size_bytes=100 * 1024 * 1024)

        assert "file_name cannot be empty" in exc_info.value.message

    def test_empty_content_type_raises_error(self):
        """Test validation fails for empty content_type"""
        request = FileUploadRequest(
            file_name="document.pdf",
            content_type="",
            file_size=1024000,
        )

        with pytest.raises(FileUploadError) as exc_info:
            _validate_file_request(request, max_size_bytes=100 * 1024 * 1024)

        assert "content_type cannot be empty" in exc_info.value.message

    def test_whitespace_only_content_type_raises_error(self):
        """Test validation fails for whitespace-only content_type"""
        request = FileUploadRequest(
            file_name="document.pdf",
            content_type="  ",
            file_size=1024000,
        )

        with pytest.raises(FileUploadError) as exc_info:
            _validate_file_request(request, max_size_bytes=100 * 1024 * 1024)

        assert "content_type cannot be empty" in exc_info.value.message

    def test_zero_file_size_raises_error(self):
        """Test validation fails for zero file_size"""
        request = FileUploadRequest(
            file_name="document.pdf",
            content_type="application/pdf",
            file_size=0,
        )

        with pytest.raises(FileUploadError) as exc_info:
            _validate_file_request(request, max_size_bytes=100 * 1024 * 1024)

        assert "file_size must be greater than 0" in exc_info.value.message

    def test_negative_file_size_raises_error(self):
        """Test validation fails for negative file_size"""
        request = FileUploadRequest(
            file_name="document.pdf",
            content_type="application/pdf",
            file_size=-1024,
        )

        with pytest.raises(FileUploadError) as exc_info:
            _validate_file_request(request, max_size_bytes=100 * 1024 * 1024)

        assert "file_size must be greater than 0" in exc_info.value.message

    def test_file_size_exceeds_max_raises_error(self):
        """Test validation fails when file_size exceeds max_size_bytes"""
        max_size = 1024 * 1024  # 1MB
        request = FileUploadRequest(
            file_name="large_file.zip",
            content_type="application/zip",
            file_size=2 * 1024 * 1024,  # 2MB
        )

        with pytest.raises(FileUploadError) as exc_info:
            _validate_file_request(request, max_size_bytes=max_size)

        assert "file_size exceeds maximum" in exc_info.value.message

    def test_content_type_not_in_allowed_types_raises_error(self):
        """Test validation fails when content_type not in allowed_types"""
        request = FileUploadRequest(
            file_name="document.pdf",
            content_type="application/pdf",
            file_size=1024000,
        )
        allowed_types = ["image/png", "image/jpeg"]

        with pytest.raises(FileUploadError) as exc_info:
            _validate_file_request(request, max_size_bytes=100 * 1024 * 1024, allowed_types=allowed_types)

        assert "not in allowed types" in exc_info.value.message

    def test_content_type_in_allowed_types_passes(self):
        """Test validation passes when content_type in allowed_types"""
        request = FileUploadRequest(
            file_name="image.png",
            content_type="image/png",
            file_size=1024000,
        )
        allowed_types = ["image/png", "image/jpeg"]

        # Should not raise
        _validate_file_request(request, max_size_bytes=100 * 1024 * 1024, allowed_types=allowed_types)

    def test_none_allowed_types_allows_all(self):
        """Test validation passes for any content_type when allowed_types is None"""
        request = FileUploadRequest(
            file_name="document.xyz",
            content_type="application/custom-type",
            file_size=1024000,
        )

        # Should not raise (None means all types allowed)
        _validate_file_request(request, max_size_bytes=100 * 1024 * 1024, allowed_types=None)


class TestGenerateFileUploadUrl:
    """Tests for generate_file_upload_url handler"""

    def _create_mock_context(self, org_id: str = "org-123", email: str = "user@example.com") -> ExecutionContext:
        """Helper to create mock ExecutionContext"""
        org = Organization(id=org_id, name="Test Org", is_active=True)

        context = MagicMock(spec=ExecutionContext)
        context.organization = org
        context.org_id = org_id
        context.email = email
        context.user_id = "user-123"
        context.name = "Test User"
        return context

    def _create_blob_service_response(self) -> dict:
        """Helper to create mock BlobStorageService response"""
        return {
            "upload_url": "https://storage.blob.core.windows.net/uploads/abc-123.pdf?sv=2021-06-08&sig=...",
            "blob_uri": "https://storage.blob.core.windows.net/uploads/abc-123.pdf",
            "blob_name": "abc-123.pdf",
            "expires_at": "2025-10-19T12:00:00Z",
            "file_name": "document.pdf",
            "content_type": "application/pdf",
        }

    @patch("shared.handlers.file_uploads_handlers.get_blob_service")
    def test_successful_url_generation(self, mock_get_blob_service):
        """Test successful SAS URL generation"""
        # Setup
        mock_service = MagicMock()
        mock_get_blob_service.return_value = mock_service
        mock_service.generate_upload_url.return_value = self._create_blob_service_response()

        context = self._create_mock_context()
        request = FileUploadRequest(
            file_name="document.pdf",
            content_type="application/pdf",
            file_size=1024000,
        )

        # Execute
        response = generate_file_upload_url(
            form_id="form-123",
            request=request,
            context=context,
        )

        # Verify
        assert isinstance(response, FileUploadResponse)
        assert response.upload_url == "https://storage.blob.core.windows.net/uploads/abc-123.pdf?sv=2021-06-08&sig=..."
        assert response.blob_uri == "https://storage.blob.core.windows.net/uploads/abc-123.pdf"
        assert response.expires_at == "2025-10-19T12:00:00Z"

        # Verify service was called correctly
        mock_service.generate_upload_url.assert_called_once_with(
            file_name="document.pdf",
            content_type="application/pdf",
            file_size=1024000,
            max_size_bytes=100 * 1024 * 1024,
            allowed_types=None,
        )

    @patch("shared.handlers.file_uploads_handlers.get_blob_service")
    def test_custom_max_size_bytes(self, mock_get_blob_service):
        """Test custom max_size_bytes parameter is passed through"""
        # Setup
        mock_service = MagicMock()
        mock_get_blob_service.return_value = mock_service
        mock_service.generate_upload_url.return_value = self._create_blob_service_response()

        context = self._create_mock_context()
        request = FileUploadRequest(
            file_name="large_file.zip",
            content_type="application/zip",
            file_size=500 * 1024 * 1024,  # 500MB
        )
        custom_max = 1024 * 1024 * 1024  # 1GB

        # Execute
        generate_file_upload_url(
            form_id="form-123",
            request=request,
            context=context,
            max_size_bytes=custom_max,
        )

        # Verify service was called with custom max_size_bytes
        mock_service.generate_upload_url.assert_called_once()
        call_kwargs = mock_service.generate_upload_url.call_args[1]
        assert call_kwargs["max_size_bytes"] == custom_max

    @patch("shared.handlers.file_uploads_handlers.get_blob_service")
    def test_allowed_types_passed_through(self, mock_get_blob_service):
        """Test allowed_types parameter is passed through"""
        # Setup
        mock_service = MagicMock()
        mock_get_blob_service.return_value = mock_service
        mock_service.generate_upload_url.return_value = self._create_blob_service_response()

        context = self._create_mock_context()
        request = FileUploadRequest(
            file_name="image.png",
            content_type="image/png",
            file_size=2048000,
        )
        allowed_types = ["image/png", "image/jpeg", "image/gif"]

        # Execute
        generate_file_upload_url(
            form_id="form-123",
            request=request,
            context=context,
            allowed_types=allowed_types,
        )

        # Verify service was called with allowed_types
        mock_service.generate_upload_url.assert_called_once()
        call_kwargs = mock_service.generate_upload_url.call_args[1]
        assert call_kwargs["allowed_types"] == allowed_types

    def test_invalid_file_name_raises_error(self):
        """Test error handling for invalid file_name"""
        context = self._create_mock_context()
        request = FileUploadRequest(
            file_name="",  # Invalid
            content_type="application/pdf",
            file_size=1024000,
        )

        with pytest.raises(FileUploadError) as exc_info:
            generate_file_upload_url(
                form_id="form-123",
                request=request,
                context=context,
            )

        assert "file_name cannot be empty" in exc_info.value.message

    def test_invalid_content_type_raises_error(self):
        """Test error handling for invalid content_type"""
        context = self._create_mock_context()
        request = FileUploadRequest(
            file_name="document.pdf",
            content_type="",  # Invalid
            file_size=1024000,
        )

        with pytest.raises(FileUploadError) as exc_info:
            generate_file_upload_url(
                form_id="form-123",
                request=request,
                context=context,
            )

        assert "content_type cannot be empty" in exc_info.value.message

    def test_invalid_file_size_raises_error(self):
        """Test error handling for invalid file_size"""
        context = self._create_mock_context()
        request = FileUploadRequest(
            file_name="document.pdf",
            content_type="application/pdf",
            file_size=0,  # Invalid
        )

        with pytest.raises(FileUploadError) as exc_info:
            generate_file_upload_url(
                form_id="form-123",
                request=request,
                context=context,
            )

        assert "file_size must be greater than 0" in exc_info.value.message

    def test_file_size_exceeds_default_max(self):
        """Test error when file_size exceeds default 100MB limit"""
        context = self._create_mock_context()
        request = FileUploadRequest(
            file_name="huge_file.bin",
            content_type="application/octet-stream",
            file_size=150 * 1024 * 1024,  # 150MB (exceeds default 100MB)
        )

        with pytest.raises(FileUploadError) as exc_info:
            generate_file_upload_url(
                form_id="form-123",
                request=request,
                context=context,
            )

        assert "file_size exceeds maximum" in exc_info.value.message

    def test_content_type_not_allowed(self):
        """Test error when content_type not in allowed_types"""
        context = self._create_mock_context()
        request = FileUploadRequest(
            file_name="document.pdf",
            content_type="application/pdf",
            file_size=1024000,
        )
        allowed_types = ["image/png", "image/jpeg"]

        with pytest.raises(FileUploadError) as exc_info:
            generate_file_upload_url(
                form_id="form-123",
                request=request,
                context=context,
                allowed_types=allowed_types,
            )

        assert "not in allowed types" in exc_info.value.message

    @patch("shared.handlers.file_uploads_handlers.get_blob_service")
    def test_multiple_file_uploads_independently(self, mock_get_blob_service):
        """Test multiple file uploads work independently"""
        # Setup
        mock_service = MagicMock()
        mock_get_blob_service.return_value = mock_service

        # Create responses for two calls
        response1 = {
            "upload_url": "https://storage.blob.core.windows.net/uploads/file1.pdf?sv=2021-06-08&sig=abc",
            "blob_uri": "https://storage.blob.core.windows.net/uploads/file1.pdf",
            "blob_name": "file1.pdf",
            "expires_at": "2025-10-19T12:00:00Z",
            "file_name": "file1.pdf",
            "content_type": "application/pdf",
        }
        response2 = {
            "upload_url": "https://storage.blob.core.windows.net/uploads/file2.zip?sv=2021-06-08&sig=xyz",
            "blob_uri": "https://storage.blob.core.windows.net/uploads/file2.zip",
            "blob_name": "file2.zip",
            "expires_at": "2025-10-19T12:00:00Z",
            "file_name": "file2.zip",
            "content_type": "application/zip",
        }
        mock_service.generate_upload_url.side_effect = [response1, response2]

        context = self._create_mock_context()

        # First upload
        request1 = FileUploadRequest(
            file_name="file1.pdf",
            content_type="application/pdf",
            file_size=1024000,
        )
        result1 = generate_file_upload_url(form_id="form-1", request=request1, context=context)

        # Second upload
        request2 = FileUploadRequest(
            file_name="file2.zip",
            content_type="application/zip",
            file_size=5 * 1024 * 1024,
        )
        result2 = generate_file_upload_url(form_id="form-2", request=request2, context=context)

        # Verify both results are correct
        assert result1.blob_uri == "https://storage.blob.core.windows.net/uploads/file1.pdf"
        assert result2.blob_uri == "https://storage.blob.core.windows.net/uploads/file2.zip"
        assert mock_service.generate_upload_url.call_count == 2

    @patch("shared.handlers.file_uploads_handlers.get_blob_service")
    def test_blob_service_exception_propagates(self, mock_get_blob_service):
        """Test that exceptions from BlobStorageService propagate"""
        # Setup
        mock_service = MagicMock()
        mock_get_blob_service.return_value = mock_service
        mock_service.generate_upload_url.side_effect = Exception("Blob service error")

        context = self._create_mock_context()
        request = FileUploadRequest(
            file_name="document.pdf",
            content_type="application/pdf",
            file_size=1024000,
        )

        # Execute and verify exception propagates
        with pytest.raises(Exception, match="Blob service error"):
            generate_file_upload_url(
                form_id="form-123",
                request=request,
                context=context,
            )

    @patch("shared.handlers.file_uploads_handlers.get_blob_service")
    def test_response_model_serialization(self, mock_get_blob_service):
        """Test that FileUploadResponse is properly serialized"""
        # Setup
        mock_service = MagicMock()
        mock_get_blob_service.return_value = mock_service
        mock_service.generate_upload_url.return_value = self._create_blob_service_response()

        context = self._create_mock_context()
        request = FileUploadRequest(
            file_name="test.pdf",
            content_type="application/pdf",
            file_size=512000,
        )

        # Execute
        response = generate_file_upload_url(
            form_id="form-123",
            request=request,
            context=context,
        )

        # Verify we can serialize to dict
        response_dict = response.model_dump()
        assert "upload_url" in response_dict
        assert "blob_uri" in response_dict
        assert "expires_at" in response_dict
        assert isinstance(response_dict["upload_url"], str)
        assert isinstance(response_dict["blob_uri"], str)
        assert isinstance(response_dict["expires_at"], str)
