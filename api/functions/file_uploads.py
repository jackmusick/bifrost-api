"""
File Upload API
Handles SAS URL generation for direct-to-blob file uploads
"""

import json
import logging

import azure.functions as func

from shared.exceptions import FileUploadError, error_to_dict
from shared.middleware import with_org_context
from shared.models import FileUploadRequest, FileUploadResponse
from shared.openapi_decorators import openapi_endpoint
from shared.blob_storage import BlobStorageService

logger = logging.getLogger(__name__)

# Create blueprint for file upload endpoints
bp = func.Blueprint()


@bp.route(route="forms/{formId}/files/upload-url", methods=["POST"])
@bp.function_name("generate_file_upload_url")
@openapi_endpoint(
    path="/forms/{formId}/files/upload-url",
    method="POST",
    summary="Generate SAS URL for file upload",
    description="Generate a secure SAS URL for uploading files directly to blob storage",
    tags=["Forms", "File Uploads"],
    request_model=FileUploadRequest,
    response_model=FileUploadResponse,
    path_params={
        "formId": {
            "description": "Form ID to associate uploaded file with",
            "schema": {"type": "string"},
            "required": True
        }
    }
)
@with_org_context
async def generate_file_upload_url(req: func.HttpRequest) -> func.HttpResponse:
    """
    Generate a SAS URL for uploading a file directly to blob storage.

    This endpoint creates a secure, time-limited URL that allows the client
    to upload a file directly to Azure Blob Storage without going through
    the API server. This is more efficient for large files.

    Request body:
    {
        "file_name": "document.pdf",
        "content_type": "application/pdf",
        "file_size": 1024000
    }

    Response:
    {
        "upload_url": "https://storage.blob.core.windows.net/...?sv=...",
        "blob_uri": "https://storage.blob.core.windows.net/uploads/abc-123.pdf",
        "expires_at": "2025-10-18T12:00:00Z"
    }

    The client should:
    1. Call this endpoint to get an upload_url
    2. PUT the file to the upload_url
    3. Store the blob_uri in the form field value
    4. Submit the form with the blob_uri
    """
    form_id = req.route_params.get('formId')
    context = req.org_context  # type: ignore[attr-defined]

    try:
        # Parse request body
        request_data = req.get_json()
        upload_request = FileUploadRequest(**request_data)

        logger.info(
            f"Generating upload URL for file: {upload_request.file_name}",
            extra={
                "form_id": form_id,
                "file_name": upload_request.file_name,
                "content_type": upload_request.content_type,
                "file_size": upload_request.file_size,
                "org_id": context.org.org_id if context.org else "GLOBAL",
                "user": context.caller.email
            }
        )

        # Initialize blob storage service
        blob_service = BlobStorageService()

        # Generate SAS URL for upload
        # This creates a secure, time-limited URL for direct upload
        result = blob_service.generate_upload_url(
            file_name=upload_request.file_name,
            content_type=upload_request.content_type,
            file_size=upload_request.file_size,
            max_size_bytes=100 * 1024 * 1024,  # 100MB limit
            allowed_types=None  # Allow all types for now (could be restricted by form config)
        )

        # Create response
        response = FileUploadResponse(
            upload_url=result['upload_url'],
            blob_uri=result['blob_uri'],
            expires_at=result['expires_at']
        )

        logger.info(
            f"Successfully generated upload URL for {upload_request.file_name}",
            extra={
                "form_id": form_id,
                "blob_uri": response.blob_uri,
                "user": context.caller.email
            }
        )

        return func.HttpResponse(
            json.dumps(response.model_dump()),
            status_code=200,
            mimetype="application/json"
        )

    except FileUploadError as e:
        logger.warning(
            f"File upload validation failed: {e.message}",
            extra={
                "form_id": form_id,
                "error": e.error_code,
                "file_name": e.file_name
            }
        )
        return func.HttpResponse(
            json.dumps(error_to_dict(e)),
            status_code=400,
            mimetype="application/json"
        )

    except ValueError as e:
        # Pydantic validation error
        logger.warning(
            f"Invalid file upload request: {str(e)}",
            extra={"form_id": form_id}
        )
        return func.HttpResponse(
            json.dumps({
                "error": "ValidationError",
                "message": str(e)
            }),
            status_code=400,
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(
            f"Failed to generate upload URL: {str(e)}",
            exc_info=True,
            extra={"form_id": form_id}
        )
        return func.HttpResponse(
            json.dumps({
                "error": "InternalServerError",
                "message": "Failed to generate upload URL"
            }),
            status_code=500,
            mimetype="application/json"
        )
