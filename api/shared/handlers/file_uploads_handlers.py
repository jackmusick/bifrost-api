"""
File Upload Handlers
Business logic for generating SAS URLs for direct blob uploads
Extracted from functions/file_uploads.py for unit testability
"""

import logging

from shared.blob_storage import BlobStorageService
from shared.context import OrganizationContext
from shared.exceptions import FileUploadError
from shared.models import FileUploadRequest, FileUploadResponse

logger = logging.getLogger(__name__)


def generate_file_upload_url(
    form_id: str,
    request: FileUploadRequest,
    context: OrganizationContext,
    max_size_bytes: int = 100 * 1024 * 1024,
    allowed_types: list[str] | None = None,
) -> FileUploadResponse:
    """
    Generate a SAS URL for uploading a file directly to blob storage.

    This handler creates a secure, time-limited URL that allows the client
    to upload a file directly to Azure Blob Storage without going through
    the API server. This is more efficient for large files.

    Args:
        form_id: Form ID to associate uploaded file with
        request: FileUploadRequest with file metadata
        context: OrganizationContext with org/user information
        max_size_bytes: Maximum allowed file size (default 100MB)
        allowed_types: List of allowed MIME types (None = all types allowed)

    Returns:
        FileUploadResponse: Contains upload_url, blob_uri, and expires_at

    Raises:
        FileUploadError: If file validation or SAS generation fails
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
            "user": context.caller.email,
        },
    )

    # Validate file request
    _validate_file_request(request, max_size_bytes, allowed_types)

    # Initialize blob storage service
    blob_service = BlobStorageService()

    # Generate SAS URL for upload
    # This creates a secure, time-limited URL for direct upload
    result = blob_service.generate_upload_url(
        file_name=request.file_name,
        content_type=request.content_type,
        file_size=request.file_size,
        max_size_bytes=max_size_bytes,
        allowed_types=allowed_types,
    )

    # Create response
    response = FileUploadResponse(
        upload_url=result["upload_url"],
        blob_uri=result["blob_uri"],
        expires_at=result["expires_at"],
    )

    logger.info(
        f"Successfully generated upload URL for {request.file_name}",
        extra={
            "form_id": form_id,
            "blob_uri": response.blob_uri,
            "user": context.caller.email,
            "org_id": context.org_id,
        },
    )

    return response


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
