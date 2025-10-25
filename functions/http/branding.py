"""
Branding API
Handles platform branding configuration (logos and colors)
Thin wrapper - business logic is in shared.handlers.branding_handlers
"""

import json
import logging

import azure.functions as func

from shared.blob_storage import get_blob_service
from shared.handlers.branding_handlers import (
    get_branding as get_branding_handler,
    update_branding as update_branding_handler,
    upload_logo as upload_logo_handler,
)
from shared.middleware import with_org_context
from shared.models import BrandingSettings, BrandingUpdateRequest, FileUploadResponse
from shared.openapi_decorators import openapi_endpoint

logger = logging.getLogger(__name__)

# Create blueprint for branding endpoints
bp = func.Blueprint()


@bp.route(route="branding", methods=["GET"])
@bp.function_name("get_branding")
@openapi_endpoint(
    path="/branding",
    method="GET",
    summary="Get branding settings",
    description="Get branding configuration (org-specific or GLOBAL fallback)",
    tags=["Branding"],
    response_model=BrandingSettings,
    query_params={
        "orgId": {
            "description": "Organization ID (defaults to current user's org)",
            "schema": {"type": "string"},
            "required": False
        }
    }
)
@with_org_context
async def get_branding(req: func.HttpRequest) -> func.HttpResponse:
    """
    Get branding settings for an organization.

    Falls back to GLOBAL branding if org-specific branding not found.
    """
    try:
        context = req.org_context  # type: ignore[attr-defined]
        org_id = req.params.get("orgId", context.org_id)

        branding = await get_branding_handler(org_id)

        return func.HttpResponse(
            body=branding.model_dump_json(),
            status_code=200,
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Error fetching branding: {str(e)}", exc_info=True)
        return func.HttpResponse(
            body=json.dumps({
                "error": "InternalServerError",
                "message": f"Failed to fetch branding: {str(e)}"
            }),
            status_code=500,
            mimetype="application/json"
        )


@bp.route(route="branding", methods=["PUT"])
@bp.function_name("update_branding")
@openapi_endpoint(
    path="/branding",
    method="PUT",
    summary="Update branding settings",
    description="Update branding configuration (color only - use logo upload endpoint for logos)",
    tags=["Branding"],
    request_model=BrandingUpdateRequest,
    response_model=BrandingSettings
)
@with_org_context
async def update_branding(req: func.HttpRequest) -> func.HttpResponse:
    """
    Update branding settings.

    Updates primary color. For logos, use the logo upload endpoint.
    """
    try:
        context = req.org_context  # type: ignore[attr-defined]

        # Parse request body
        body = json.loads(req.get_body().decode("utf-8"))
        update_request = BrandingUpdateRequest(**body)

        # Update branding
        branding = await update_branding_handler(
            org_id=update_request.orgId or context.org_id,
            primary_color=update_request.primaryColor,
            updated_by=context.email
        )

        return func.HttpResponse(
            body=branding.model_dump_json(),
            status_code=200,
            mimetype="application/json"
        )

    except json.JSONDecodeError:
        return func.HttpResponse(
            body=json.dumps({"error": "Invalid JSON in request body"}),
            status_code=400,
            mimetype="application/json"
        )
    except Exception as e:
        logger.error(f"Error updating branding: {str(e)}", exc_info=True)
        return func.HttpResponse(
            body=json.dumps({
                "error": "InternalServerError",
                "message": f"Failed to update branding: {str(e)}"
            }),
            status_code=500,
            mimetype="application/json"
        )


@bp.route(route="branding/logo/{logoType}", methods=["POST"])
@bp.function_name("upload_logo")
@openapi_endpoint(
    path="/branding/logo/{logoType}",
    method="POST",
    summary="Upload logo file",
    description="Upload square or rectangle logo to blob storage and update branding",
    tags=["Branding"],
    response_model=FileUploadResponse,
    path_params={
        "logoType": {
            "description": "Logo type: 'square' or 'rectangle'",
            "schema": {"type": "string", "enum": ["square", "rectangle"]},
            "required": True
        }
    },
    query_params={
        "orgId": {
            "description": "Organization ID (defaults to current user's org)",
            "schema": {"type": "string"},
            "required": False
        }
    }
)
@with_org_context
async def upload_logo(req: func.HttpRequest) -> func.HttpResponse:
    """
    Upload a logo file directly to blob storage and update branding.

    Supports PNG, JPG, SVG formats with 5MB max file size.
    """
    try:
        context = req.org_context  # type: ignore[attr-defined]
        logo_type = req.route_params.get("logoType")
        org_id = req.params.get("orgId", context.org_id)

        # Validate logo type
        if logo_type not in ["square", "rectangle"]:
            return func.HttpResponse(
                body=json.dumps({"error": "Logo type must be 'square' or 'rectangle'"}),
                status_code=400,
                mimetype="application/json"
            )

        # Get file from request
        file_data = req.get_body()
        content_type = req.headers.get("Content-Type", "application/octet-stream")

        # Validate file type
        valid_types = ["image/png", "image/jpeg", "image/jpg", "image/svg+xml"]
        if content_type not in valid_types:
            return func.HttpResponse(
                body=json.dumps({"error": f"Invalid file type. Allowed: {', '.join(valid_types)}"}),
                status_code=400,
                mimetype="application/json"
            )

        # Validate file size (5MB max)
        if len(file_data) > 5 * 1024 * 1024:
            return func.HttpResponse(
                body=json.dumps({"error": "File size exceeds 5MB limit"}),
                status_code=400,
                mimetype="application/json"
            )

        # Upload and update branding
        result = await upload_logo_handler(
            org_id=org_id,
            logo_type=logo_type,
            file_data=file_data,
            content_type=content_type,
            updated_by=context.email
        )

        return func.HttpResponse(
            body=result.model_dump_json(),
            status_code=200,
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Error uploading logo: {str(e)}", exc_info=True)
        return func.HttpResponse(
            body=json.dumps({
                "error": "InternalServerError",
                "message": f"Failed to upload logo: {str(e)}"
            }),
            status_code=500,
            mimetype="application/json"
        )


@bp.route(route="branding/logo-proxy/{orgId}/{logoType}", methods=["GET"])
@bp.function_name("proxy_branding_logo")
async def proxy_branding_logo(req: func.HttpRequest) -> func.HttpResponse:
    """
    Proxy endpoint to serve branding logos with proper CORS headers
    Solves CORS issues when accessing Azurite from browser in local dev

    Route: GET /api/branding/logo-proxy/{orgId}/{logoType}
    """
    try:
        org_id = req.route_params.get("orgId")
        logo_type = req.route_params.get("logoType")

        if not org_id or not logo_type:
            return func.HttpResponse(
                body=json.dumps({"error": "Missing orgId or logoType"}),
                status_code=400,
                mimetype="application/json"
            )

        if logo_type not in ["square", "rectangle"]:
            return func.HttpResponse(
                body=json.dumps({"error": "Invalid logoType. Must be 'square' or 'rectangle'"}),
                status_code=400,
                mimetype="application/json"
            )

        # Download blob from storage
        blob_service = get_blob_service()

        # Try common image extensions
        for ext in ["svg", "png", "jpg", "jpeg"]:
            blob_name = f"{org_id}/{logo_type}-logo.{ext}"
            try:
                blob_data = await blob_service.download_blob(
                    container_name="branding",
                    blob_name=blob_name
                )

                # Determine content type
                content_type_map = {
                    "svg": "image/svg+xml",
                    "png": "image/png",
                    "jpg": "image/jpeg",
                    "jpeg": "image/jpeg"
                }
                content_type = content_type_map.get(ext, "application/octet-stream")

                # Return image with CORS headers
                return func.HttpResponse(
                    body=blob_data,
                    status_code=200,
                    mimetype=content_type,
                    headers={
                        "Access-Control-Allow-Origin": "*",
                        "Access-Control-Allow-Methods": "GET, OPTIONS",
                        "Access-Control-Allow-Headers": "Content-Type",
                        "Cache-Control": "public, max-age=3600"
                    }
                )
            except Exception:
                continue  # Try next extension

        # No logo found
        return func.HttpResponse(
            body=json.dumps({"error": "Logo not found"}),
            status_code=404,
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Error proxying logo: {str(e)}", exc_info=True)
        return func.HttpResponse(
            body=json.dumps({"error": f"Failed to proxy logo: {str(e)}"}),
            status_code=500,
            mimetype="application/json"
        )
