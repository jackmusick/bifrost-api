"""
File Upload Handlers
Business logic for file uploads to filesystem storage
Extracted from functions/file_uploads.py for unit testability
"""

import logging
import uuid
from datetime import datetime, timedelta

from shared.context import ExecutionContext
from shared.exceptions import FileUploadError
from src.models.schemas import FileUploadRequest, FileUploadResponse, UploadedFileMetadata
from src.services.file_storage import get_file_storage

logger = logging.getLogger(__name__)


async def generate_file_upload_url(
    form_id: str,
    request: FileUploadRequest,
    context: ExecutionContext,
    max_size_bytes: int = 100 * 1024 * 1024,
    allowed_types: list[str] | None = None,
) -> FileUploadResponse:
    """
    Generate upload metadata for file uploads.

    With filesystem storage, files are uploaded directly to the API
    rather than using pre-signed URLs. This function validates the
    request and returns the endpoint URL for uploading.

    Args:
        form_id: Form ID to associate uploaded file with
        request: FileUploadRequest with file metadata
        context: ExecutionContext with org/user information
        max_size_bytes: Maximum allowed file size (default 100MB)
        allowed_types: List of allowed MIME types (None = all types allowed)

    Returns:
        FileUploadResponse: Contains upload_url and file_metadata

    Raises:
        FileUploadError: If file validation fails
        ValueError: If request validation fails
    """
    logger.info(
        f"Generating upload URL for file: {request.file_name}",
        extra={
            "form_id": form_id,
            "file_name": request.file_name,
            "content_type": request.content_type,
            "file_size": request.file_size,
            "org_id": context.org_id,
            "user": context.email,
        },
    )

    # Validate file request
    _validate_file_request(request, max_size_bytes, allowed_types)

    # Generate unique upload ID
    upload_id = uuid.uuid4().hex

    # Sanitize filename and create safe path
    safe_filename = _sanitize_filename(request.file_name)
    blob_name = f"{upload_id}_{safe_filename}"

    # Container for uploads
    container = "uploads"

    # Create file metadata for workflows to access the file
    file_metadata = UploadedFileMetadata(
        name=request.file_name,
        container=container,
        path=blob_name,
        content_type=request.content_type,
        size=request.file_size,
    )

    # Generate the upload endpoint URL
    # With filesystem storage, clients POST directly to this URL
    upload_url = f"/api/files/upload/{upload_id}"

    # Create response
    # Note: blob_uri is now a local path reference, not an Azure URI
    response = FileUploadResponse(
        upload_url=upload_url,
        blob_uri=f"/api/storage/{container}/{blob_name}",
        expires_at=(datetime.utcnow() + timedelta(hours=24)).isoformat(),
        file_metadata=file_metadata,
    )

    logger.info(
        f"Successfully generated upload URL for {request.file_name}",
        extra={
            "form_id": form_id,
            "upload_id": upload_id,
            "user": context.email,
            "org_id": context.org_id,
        },
    )

    return response


async def save_uploaded_file(
    content: bytes,
    original_filename: str,
    content_type: str | None = None,
) -> dict:
    """
    Save an uploaded file to filesystem storage.

    Args:
        content: File content as bytes
        original_filename: Original filename from user
        content_type: MIME type

    Returns:
        Dict with upload details (upload_id, path, url, etc.)
    """
    file_storage = get_file_storage()
    return await file_storage.save_upload(content, original_filename, content_type)


async def get_uploaded_file(upload_id_or_filename: str) -> bytes | None:
    """
    Get an uploaded file by ID or filename.

    Args:
        upload_id_or_filename: Upload ID or full filename

    Returns:
        File content or None if not found
    """
    file_storage = get_file_storage()
    return await file_storage.get_upload(upload_id_or_filename)


async def delete_uploaded_file(upload_id_or_filename: str) -> bool:
    """
    Delete an uploaded file.

    Args:
        upload_id_or_filename: Upload ID or full filename

    Returns:
        True if deleted, False if not found
    """
    file_storage = get_file_storage()
    return await file_storage.delete_upload(upload_id_or_filename)


def _sanitize_filename(filename: str) -> str:
    """
    Sanitize filename to prevent path traversal and ensure safe storage.

    Args:
        filename: Original filename

    Returns:
        Sanitized filename
    """
    import os
    import re

    # Get just the filename part (no path)
    filename = os.path.basename(filename)

    # Remove any non-alphanumeric characters except . - _
    filename = re.sub(r"[^\w.\-]", "_", filename)

    # Limit length
    if len(filename) > 200:
        name, ext = os.path.splitext(filename)
        filename = name[:200 - len(ext)] + ext

    return filename


def _validate_file_request(
    request: FileUploadRequest,
    max_size_bytes: int,
    allowed_types: list[str] | None = None,
) -> None:
    """
    Validate file upload request parameters.

    Args:
        request: FileUploadRequest to validate
        max_size_bytes: Maximum allowed file size
        allowed_types: List of allowed MIME types (None = all allowed)

    Raises:
        FileUploadError: If validation fails
    """
    # Validate file name
    if not request.file_name or not request.file_name.strip():
        raise FileUploadError(
            message="file_name cannot be empty",
            file_name=request.file_name,
        )

    # Validate content type
    if not request.content_type or not request.content_type.strip():
        raise FileUploadError(
            message="content_type cannot be empty",
            file_name=request.file_name,
        )

    # Validate file size
    if request.file_size <= 0:
        raise FileUploadError(
            message="file_size must be greater than 0",
            file_name=request.file_name,
        )

    if request.file_size > max_size_bytes:
        raise FileUploadError(
            message=f"file_size exceeds maximum of {max_size_bytes} bytes",
            file_name=request.file_name,
        )

    # Validate content type against allowed types
    if allowed_types and request.content_type not in allowed_types:
        raise FileUploadError(
            message=f"content_type '{request.content_type}' not in allowed types",
            file_name=request.file_name,
        )

    logger.debug(
        f"File request validation passed for {request.file_name}",
        extra={
            "file_size": request.file_size,
            "content_type": request.content_type,
        },
    )
