"""
Unit tests for BlobStorageService

Tests cover:
- Uploading logs, results, snapshots
- Downloading stored data
- Generating SAS URLs for direct uploads
- Blob metadata retrieval
- Blob deletion
- Error handling
"""

import json
import os
import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch, call
from io import BytesIO

from shared.blob_storage import BlobStorageService


class TestBlobStorageServiceInitialization:
    """Test BlobStorageService initialization"""

    def test_init_with_connection_string(self, mock_blob_service_client):
        """Should initialize with provided connection string"""
        service = BlobStorageService(connection_string="test-connection")
        assert service.connection_string == "test-connection"

    def test_init_with_env_variable(self, mock_blob_service_client):
        """Should use AzureWebJobsStorage environment variable"""
        with patch.dict(os.environ, {"AzureWebJobsStorage": "env-connection"}):
            service = BlobStorageService()
            assert service.connection_string == "env-connection"

    def test_init_without_connection_raises_error(self):
        """Should raise error when no connection string provided"""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="AzureWebJobsStorage"):
                BlobStorageService()


class TestBlobStorageServiceUploadLogs:
    """Test uploading execution logs"""

    def test_upload_logs_success(self, mock_blob_service_client, sample_logs):
        """Should upload logs and return blob path"""
        service = BlobStorageService(connection_string="test")
        execution_id = "test-exec-123"

        result = service.upload_logs(execution_id, sample_logs)

        assert result == f"{execution_id}/logs.json"
        # Verify blob upload was called
        mock_blob_service_client["blob"].upload_blob.assert_called_once()

    def test_upload_logs_with_metadata(self, mock_blob_service_client, sample_logs):
        """Should handle logs with metadata"""
        service = BlobStorageService(connection_string="test")
        execution_id = "exec-456"
        logs_with_metadata = [
            {
                "timestamp": "2024-01-01T10:00:00Z",
                "level": "DEBUG",
                "message": "Debug info",
                "metadata": {"user": "test", "request_id": "req-789"}
            }
        ]

        result = service.upload_logs(execution_id, logs_with_metadata)

        assert result == f"{execution_id}/logs.json"
        call_args = mock_blob_service_client["blob"].upload_blob.call_args
        assert "metadata" in call_args[0][0] or "metadata" in str(call_args)

    def test_upload_empty_logs(self, mock_blob_service_client):
        """Should handle uploading empty logs array"""
        service = BlobStorageService(connection_string="test")
        execution_id = "exec-empty"

        result = service.upload_logs(execution_id, [])

        assert result == f"{execution_id}/logs.json"
        mock_blob_service_client["blob"].upload_blob.assert_called_once()

    def test_upload_large_logs(self, mock_blob_service_client):
        """Should handle uploading large log arrays"""
        service = BlobStorageService(connection_string="test")
        execution_id = "exec-large"
        large_logs = [
            {
                "timestamp": f"2024-01-01T10:00:{i:02d}Z",
                "level": "INFO",
                "message": f"Log entry {i}",
                "data": {"iteration": i, "value": "x" * 1000}  # Large data
            }
            for i in range(100)
        ]

        result = service.upload_logs(execution_id, large_logs)

        assert result == f"{execution_id}/logs.json"
        mock_blob_service_client["blob"].upload_blob.assert_called_once()


class TestBlobStorageServiceDownloadLogs:
    """Test downloading execution logs"""

    def test_download_logs_success(self, mock_blob_service_client, sample_logs):
        """Should download and parse logs JSON"""
        service = BlobStorageService(connection_string="test")
        execution_id = "test-exec-123"

        # Mock the blob download
        mock_blob_service_client["blob"].exists.return_value = True
        logs_json = json.dumps(sample_logs)
        download_mock = MagicMock()
        download_mock.readall.return_value = logs_json.encode('utf-8')
        mock_blob_service_client["blob"].download_blob.return_value = download_mock

        result = service.get_logs(execution_id)

        assert result == sample_logs
        mock_blob_service_client["blob"].exists.assert_called_once()
        mock_blob_service_client["blob"].download_blob.assert_called_once()

    def test_download_logs_not_found(self, mock_blob_service_client):
        """Should return None when logs blob not found"""
        service = BlobStorageService(connection_string="test")
        execution_id = "exec-missing"

        # Mock blob doesn't exist
        mock_blob_service_client["blob"].exists.return_value = False

        result = service.get_logs(execution_id)

        assert result is None

    def test_download_logs_handles_errors(self, mock_blob_service_client):
        """Should handle download errors gracefully"""
        service = BlobStorageService(connection_string="test")
        execution_id = "exec-error"

        # Mock error during download
        mock_blob_service_client["blob"].exists.return_value = True
        mock_blob_service_client["blob"].download_blob.side_effect = Exception("Download failed")

        result = service.get_logs(execution_id)

        assert result is None


class TestBlobStorageServiceUploadResult:
    """Test uploading execution results"""

    def test_upload_result_dict_as_json(self, mock_blob_service_client, sample_execution_result):
        """Should upload dict result as JSON file"""
        service = BlobStorageService(connection_string="test")
        execution_id = "exec-result-1"

        result = service.upload_result(execution_id, sample_execution_result)

        assert result == f"{execution_id}/result.json"
        # Verify JSON was uploaded
        call_args = mock_blob_service_client["blob"].upload_blob.call_args
        uploaded_content = call_args[0][0]
        assert '"status": "completed"' in uploaded_content

    def test_upload_result_html_string(self, mock_blob_service_client):
        """Should upload HTML content as result.html"""
        service = BlobStorageService(connection_string="test")
        execution_id = "exec-result-html"
        html_result = "<html><body><h1>Result</h1></body></html>"

        result = service.upload_result(execution_id, html_result)

        assert result == f"{execution_id}/result.html"
        mock_blob_service_client["blob"].upload_blob.assert_called_once()

    def test_upload_result_text_string(self, mock_blob_service_client):
        """Should upload plain text as result.txt"""
        service = BlobStorageService(connection_string="test")
        execution_id = "exec-result-txt"
        text_result = "This is a plain text result"

        result = service.upload_result(execution_id, text_result)

        assert result == f"{execution_id}/result.txt"
        mock_blob_service_client["blob"].upload_blob.assert_called_once()

    def test_upload_result_overwrites_existing(self, mock_blob_service_client):
        """Should overwrite existing result"""
        service = BlobStorageService(connection_string="test")
        execution_id = "exec-overwrite"
        result1 = {"status": "in_progress"}
        result2 = {"status": "completed"}

        service.upload_result(execution_id, result1)
        service.upload_result(execution_id, result2)

        # Should have been called twice
        assert mock_blob_service_client["blob"].upload_blob.call_count == 2


class TestBlobStorageServiceDownloadResult:
    """Test downloading execution results"""

    def test_download_result_json(self, mock_blob_service_client, sample_execution_result):
        """Should download JSON result"""
        service = BlobStorageService(connection_string="test")
        execution_id = "exec-result-1"

        # Mock JSON result download
        mock_blob_service_client["blob"].exists.side_effect = [True, False, False]  # .json exists
        download_mock = MagicMock()
        download_mock.readall.return_value = json.dumps(sample_execution_result).encode('utf-8')
        mock_blob_service_client["blob"].download_blob.return_value = download_mock

        result = service.get_result(execution_id)

        assert result == sample_execution_result

    def test_download_result_html(self, mock_blob_service_client):
        """Should download HTML result"""
        service = BlobStorageService(connection_string="test")
        execution_id = "exec-result-html"
        html_content = "<html><body>Report</body></html>"

        # Mock HTML result download
        mock_blob_service_client["blob"].exists.side_effect = [False, True, False]  # .html exists
        download_mock = MagicMock()
        download_mock.readall.return_value = html_content.encode('utf-8')
        mock_blob_service_client["blob"].download_blob.return_value = download_mock

        result = service.get_result(execution_id)

        assert result == html_content

    def test_download_result_not_found(self, mock_blob_service_client):
        """Should return None when result not found"""
        service = BlobStorageService(connection_string="test")
        execution_id = "exec-not-found"

        # Mock all formats don't exist
        mock_blob_service_client["blob"].exists.side_effect = [False, False, False]

        result = service.get_result(execution_id)

        assert result is None


class TestBlobStorageServiceSnapshot:
    """Test uploading and downloading snapshots"""

    def test_upload_snapshot(self, mock_blob_service_client):
        """Should upload state snapshot"""
        service = BlobStorageService(connection_string="test")
        execution_id = "exec-snap-1"
        snapshot = [
            {"step": 1, "state": "initial", "data": {}},
            {"step": 2, "state": "processing", "data": {"items": 10}}
        ]

        result = service.upload_snapshot(execution_id, snapshot)

        assert result == f"{execution_id}/snapshot.json"
        mock_blob_service_client["blob"].upload_blob.assert_called_once()

    def test_download_snapshot(self, mock_blob_service_client):
        """Should download state snapshot"""
        service = BlobStorageService(connection_string="test")
        execution_id = "exec-snap-1"
        snapshot = [{"step": 1, "state": "initial"}]

        # Mock snapshot download
        mock_blob_service_client["blob"].exists.return_value = True
        download_mock = MagicMock()
        download_mock.readall.return_value = json.dumps(snapshot).encode('utf-8')
        mock_blob_service_client["blob"].download_blob.return_value = download_mock

        result = service.get_snapshot(execution_id)

        assert result == snapshot

    def test_download_snapshot_not_found(self, mock_blob_service_client):
        """Should return None when snapshot not found"""
        service = BlobStorageService(connection_string="test")
        execution_id = "exec-snap-missing"

        mock_blob_service_client["blob"].exists.return_value = False

        result = service.get_snapshot(execution_id)

        assert result is None


class TestBlobStorageServiceSASUrl:
    """Test SAS URL generation"""

    def test_generate_sas_url(self, mock_blob_service_client):
        """Should generate SAS URL for blob upload"""
        with patch("shared.blob_storage.generate_blob_sas") as mock_gen_sas:
            mock_gen_sas.return_value = "sv=2021-06-08&sig=test_signature"

            # Use a connection string with AccountKey
            conn_str = "DefaultEndpointsProtocol=https;AccountName=teststorage;AccountKey=dGVzdGtleTEyMw==;EndpointSuffix=core.windows.net"
            service = BlobStorageService(connection_string=conn_str)

            # Mock blob client URL
            mock_blob_service_client["blob"].url = "https://teststorage.blob.core.windows.net/uploads/blob123"

            result = service.generate_upload_url(
                file_name="document.pdf",
                content_type="application/pdf",
                file_size=1024 * 1024
            )

            assert "upload_url" in result
            assert "blob_uri" in result
            assert "blob_name" in result
            assert "expires_at" in result
            assert "file_name" in result
            assert result["file_name"] == "document.pdf"
            assert result["content_type"] == "application/pdf"

    def test_generate_sas_url_rejects_invalid_file_type(self, mock_blob_service_client):
        """Should reject disallowed file types"""
        service = BlobStorageService(connection_string="test")

        with pytest.raises(ValueError, match="not allowed"):
            service.generate_upload_url(
                file_name="script.exe",
                content_type="application/x-msdownload",
                allowed_types=["application/pdf", "image/jpeg"]
            )

    def test_generate_sas_url_rejects_large_file(self, mock_blob_service_client):
        """Should reject files exceeding max size"""
        service = BlobStorageService(connection_string="test")

        with pytest.raises(ValueError, match="exceeds maximum size"):
            service.generate_upload_url(
                file_name="huge.zip",
                content_type="application/zip",
                file_size=500 * 1024 * 1024,  # 500MB
                max_size_bytes=100 * 1024 * 1024  # 100MB max
            )

    def test_sas_url_expiry(self, mock_blob_service_client):
        """Should set expiry time for SAS token"""
        with patch("shared.blob_storage.generate_blob_sas") as mock_gen_sas:
            mock_gen_sas.return_value = "sv=2021-06-08&sig=test_signature"

            conn_str = "DefaultEndpointsProtocol=https;AccountName=teststorage;AccountKey=dGVzdGtleTEyMw==;EndpointSuffix=core.windows.net"
            service = BlobStorageService(connection_string=conn_str)

            mock_blob_service_client["blob"].url = "https://teststorage.blob.core.windows.net/uploads/blob123"

            result = service.generate_upload_url(
                file_name="doc.pdf",
                content_type="application/pdf"
            )

            # Check expiry is approximately 15 minutes from now
            expires_at = datetime.fromisoformat(result["expires_at"])
            now = datetime.utcnow()
            time_diff = (expires_at - now).total_seconds()
            assert 14 * 60 < time_diff < 16 * 60  # Within 1 minute of 15 minutes


class TestBlobStorageServiceMetadata:
    """Test blob metadata operations"""

    def test_get_blob_metadata(self, mock_blob_service_client):
        """Should retrieve blob metadata"""
        service = BlobStorageService(connection_string="test")
        blob_uri = "https://teststorage.blob.core.windows.net/uploads/doc.pdf"

        # Mock properties
        props = MagicMock()
        props.name = "doc.pdf"
        props.size = 1024 * 100
        props.content_settings.content_type = "application/pdf"
        props.last_modified = datetime.utcnow()
        props.etag = "0x12345"
        mock_blob_service_client["blob"].get_blob_properties.return_value = props

        result = service.get_blob_metadata(blob_uri)

        assert result["name"] == "doc.pdf"
        assert result["size"] == 1024 * 100
        assert result["content_type"] == "application/pdf"
        assert result["etag"] == "0x12345"

    def test_get_blob_metadata_invalid_uri(self, mock_blob_service_client):
        """Should handle invalid blob URI"""
        service = BlobStorageService(connection_string="test")

        result = service.get_blob_metadata("invalid-uri")

        assert "error" in result
        assert "blob_uri" in result


class TestBlobStorageServiceDelete:
    """Test blob deletion"""

    def test_delete_blob_success(self, mock_blob_service_client):
        """Should delete blob from storage"""
        service = BlobStorageService(connection_string="test")
        blob_uri = "https://teststorage.blob.core.windows.net/uploads/doc.pdf"

        result = service.delete_blob(blob_uri)

        assert result is True
        mock_blob_service_client["blob"].delete_blob.assert_called_once()

    def test_delete_blob_not_found(self, mock_blob_service_client):
        """Should handle deleting non-existent blob gracefully"""
        service = BlobStorageService(connection_string="test")
        blob_uri = "https://teststorage.blob.core.windows.net/uploads/missing.pdf"

        # Mock delete failure
        mock_blob_service_client["blob"].delete_blob.side_effect = Exception("Blob not found")

        result = service.delete_blob(blob_uri)

        assert result is False

    def test_delete_blob_invalid_uri(self, mock_blob_service_client):
        """Should handle invalid URI format"""
        service = BlobStorageService(connection_string="test")

        result = service.delete_blob("not-a-uri")

        assert result is False
