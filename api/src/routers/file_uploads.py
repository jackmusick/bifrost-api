"""
File Uploads Router

Handles file uploads for form submissions and workflow execution.
Files are stored in the local filesystem (can be configured for S3/MinIO).

Usage:
    1. Client calls POST /api/uploads to get upload metadata
    2. Client uploads file directly to the server
    3. Client includes file metadata in form submission
"""

import logging
import mimetypes
from typing import Any
from uuid import UUID

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel

from src.models.schemas import FileUploadRequest, FileUploadResponse, UploadedFileMetadata
from src.core.auth import Context, CurrentActiveUser
from src.services.file_storage import get_file_storage

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/uploads", tags=["File Uploads"])

# Maximum file size (100MB)
MAX_FILE_SIZE = 100 * 1024 * 1024

# Allowed MIME types (None = all types allowed)
ALLOWED_TYPES: list[str] | None = None


# =============================================================================
# Response Models
# =============================================================================


class UploadResponse(BaseModel):
    """Response after successful file upload."""
    upload_id: str
    filename: str
    content_type: str
    size: int
    url: str
    file_metadata: UploadedFileMetadata


class UploadListResponse(BaseModel):
    """Response for listing uploads."""
    uploads: list[dict[str, Any]]
    count: int


# =============================================================================
# HTTP Endpoints
# =============================================================================


@router.post(
    "",
    response_model=UploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a file",
    description="Upload a file to be used in form submissions or workflows",
)
async def upload_file(
    ctx: Context,
    user: CurrentActiveUser,
    file: UploadFile = File(..., description="The file to upload"),
    form_id: str | None = Form(None, alias="formId", description="Optional form ID"),
) -> UploadResponse:
    """
    Upload a file for use in forms or workflows.

    Files are stored with a unique ID and can be referenced by that ID
    in form submissions or workflow parameters.

    Args:
        ctx: Request context
        user: Authenticated user
        file: The file to upload
        form_id: Optional form ID to associate with

    Returns:
        Upload metadata including ID and URL
    """
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename is required",
        )

    # Check content type
    content_type = file.content_type or mimetypes.guess_type(file.filename)[0] or "application/octet-stream"

    if ALLOWED_TYPES and content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type '{content_type}' not allowed",
        )

    # Read file content
    content = await file.read()

    # Check file size
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File size exceeds maximum of {MAX_FILE_SIZE // (1024*1024)}MB",
        )

    if len(content) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File is empty",
        )

    # Save the file
    storage = get_file_storage()
    result = await storage.save_upload(
        content=content,
        original_filename=file.filename,
        content_type=content_type,
    )

    logger.info(
        f"File uploaded: {file.filename} ({len(content)} bytes)",
        extra={
            "upload_id": result["upload_id"],
            "user": user.email,
            "form_id": form_id,
        },
    )

    # Create file metadata for workflows
    file_metadata = UploadedFileMetadata(
        name=file.filename,
        container="uploads",
        path=result["path"],
        content_type=content_type,
        size=len(content),
    )

    return UploadResponse(
        upload_id=result["upload_id"],
        filename=file.filename,
        content_type=content_type,
        size=len(content),
        url=result["url"],
        file_metadata=file_metadata,
    )


@router.get(
    "/{upload_id}",
    summary="Get uploaded file",
    description="Download an uploaded file by ID",
)
async def get_upload(
    upload_id: str,
    ctx: Context,
    user: CurrentActiveUser,
):
    """
    Get an uploaded file by ID.

    Returns the file content with appropriate Content-Type header.
    """
    from fastapi.responses import Response

    storage = get_file_storage()
    content = await storage.get_upload(upload_id)

    if not content:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Upload '{upload_id}' not found",
        )

    # Determine content type from upload ID (which includes extension)
    content_type = mimetypes.guess_type(upload_id)[0] or "application/octet-stream"

    return Response(
        content=content,
        media_type=content_type,
    )


@router.delete(
    "/{upload_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete uploaded file",
    description="Delete an uploaded file by ID",
)
async def delete_upload(
    upload_id: str,
    ctx: Context,
    user: CurrentActiveUser,
) -> None:
    """
    Delete an uploaded file.

    Note: This will fail if the file is referenced in a form submission
    or active workflow execution.
    """
    storage = get_file_storage()
    deleted = await storage.delete_upload(upload_id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Upload '{upload_id}' not found",
        )

    logger.info(f"Upload deleted: {upload_id}", extra={"user": user.email})


# =============================================================================
# Form-specific upload endpoint
# =============================================================================


@router.post(
    "/form/{form_id}",
    response_model=UploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload file for form",
    description="Upload a file associated with a specific form",
)
async def upload_for_form(
    form_id: UUID,
    ctx: Context,
    user: CurrentActiveUser,
    file: UploadFile = File(...),
) -> UploadResponse:
    """
    Upload a file specifically for a form submission.

    This associates the upload with the form for tracking purposes.
    The file can then be referenced in the form submission by its upload ID.
    """
    # Reuse the main upload logic with form_id
    return await upload_file(
        ctx=ctx,
        user=user,
        file=file,
        form_id=str(form_id),
    )


# =============================================================================
# Pre-signed URL endpoint (for larger files or direct upload)
# =============================================================================


@router.post(
    "/presign",
    response_model=FileUploadResponse,
    summary="Get pre-signed upload URL",
    description="Get a URL for direct file upload (for larger files)",
)
async def get_presigned_url(
    request: FileUploadRequest,
    ctx: Context,
    user: CurrentActiveUser,
) -> FileUploadResponse:
    """
    Get a pre-signed URL for direct file upload.

    For the local filesystem backend, this returns a regular upload URL.
    When using S3/MinIO, this would return a true pre-signed URL.

    Args:
        request: File metadata (name, type, size)
        ctx: Request context
        user: Authenticated user

    Returns:
        Upload URL and file metadata
    """
    # Validate file size
    if request.file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File size exceeds maximum of {MAX_FILE_SIZE // (1024*1024)}MB",
        )

    if request.file_size <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File size must be greater than 0",
        )

    # Validate content type
    if ALLOWED_TYPES and request.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type '{request.content_type}' not allowed",
        )

    # For local storage, we just return the upload endpoint
    # In a real S3 setup, this would generate a pre-signed URL
    import uuid
    from datetime import datetime, timedelta

    upload_id = uuid.uuid4().hex
    expires_at = datetime.utcnow() + timedelta(hours=1)

    # Create file metadata
    file_metadata = UploadedFileMetadata(
        name=request.file_name,
        container="uploads",
        path=f"files/uploads/{upload_id}",
        content_type=request.content_type,
        size=request.file_size,
    )

    return FileUploadResponse(
        upload_url=f"/api/uploads?uploadId={upload_id}",
        blob_uri=f"/api/uploads/{upload_id}",
        expires_at=expires_at.isoformat(),
        file_metadata=file_metadata,
    )
