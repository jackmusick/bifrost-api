"""
Business logic for branding operations
Handles branding configuration storage and retrieval
"""

import logging
from datetime import datetime
from typing import Optional

from shared.models import BrandingSettings, FileUploadResponse
from shared.blob_storage import get_blob_service
from shared.storage import TableStorageService

logger = logging.getLogger(__name__)


def _transform_blob_url_to_proxy(blob_url: str | None, org_id: str) -> str | None:
    """
    Transform direct blob storage URLs to API proxy URLs for CORS compatibility

    Args:
        blob_url: Direct blob storage URL (may be None)
        org_id: Organization ID

    Returns:
        API proxy URL or None
    """
    if not blob_url:
        return None

    # Extract logo type from blob URL
    # Example: http://localhost:10000/devstoreaccount1/branding/GLOBAL/square-logo.svg
    if "/square-logo." in blob_url:
        return f"/api/branding/logo-proxy/{org_id}/square"
    elif "/rectangle-logo." in blob_url:
        return f"/api/branding/logo-proxy/{org_id}/rectangle"

    # If we can't determine type, return original URL
    return blob_url


async def get_branding(org_id: str | None) -> BrandingSettings:
    """
    Get branding settings for an organization.
    Falls back to GLOBAL if org-specific branding not found.

    Args:
        org_id: Organization ID to get branding for (None defaults to GLOBAL)

    Returns:
        BrandingSettings object
    """
    # Default to GLOBAL if no org_id
    org_id = org_id or "GLOBAL"
    table_service = TableStorageService("Config")

    # Try to get org-specific branding first
    try:
        entity = table_service.get_entity(partition_key=org_id, row_key="branding")
        if entity:
            return _entity_to_branding(entity)
    except Exception:
        pass

    # Fall back to GLOBAL branding
    try:
        entity = table_service.get_entity(partition_key="GLOBAL", row_key="branding")
        if entity:
            return _entity_to_branding(entity)
    except Exception:
        pass

    # Return default branding (all None - frontend handles defaults)
    return BrandingSettings(
        orgId=org_id,
        squareLogoUrl=None,
        rectangleLogoUrl=None,
        primaryColor=None,
        updatedBy="system",
        updatedAt=datetime.utcnow()
    )


async def update_branding(
    org_id: str | None,
    primary_color: Optional[str] = None,
    updated_by: str = "system"
) -> BrandingSettings:
    """
    Update branding settings (color only - use upload_logo for logos).

    Args:
        org_id: Organization ID (None defaults to GLOBAL)
        primary_color: Hex color code (e.g., '#0066CC')
        updated_by: User email

    Returns:
        Updated BrandingSettings
    """
    # Default to GLOBAL if no org_id
    org_id = org_id or "GLOBAL"
    table_service = TableStorageService("Config")

    # Get existing branding or create new
    branding_data = None
    try:
        entity = table_service.get_entity(partition_key=org_id, row_key="branding")
        if entity:
            branding_data = _entity_to_dict(entity)
    except Exception:
        pass

    if not branding_data:
        branding_data = {
            "orgId": org_id,
            "squareLogoUrl": None,
            "rectangleLogoUrl": None,
            "primaryColor": None
        }

    # Update fields
    if primary_color is not None:
        branding_data["primaryColor"] = primary_color

    branding_data["updatedBy"] = updated_by
    branding_data["updatedAt"] = datetime.utcnow()

    # Save to table
    entity = {
        "PartitionKey": org_id,
        "RowKey": "branding",
        **_branding_to_dict(branding_data)
    }
    table_service.upsert_entity(entity)

    return BrandingSettings(**branding_data)


async def upload_logo(
    org_id: str | None,
    logo_type: str,
    file_data: bytes,
    content_type: str,
    updated_by: str = "system"
) -> FileUploadResponse:
    """
    Upload logo file to blob storage and update branding.

    Args:
        org_id: Organization ID (None defaults to GLOBAL)
        logo_type: 'square' or 'rectangle'
        file_data: File bytes
        content_type: MIME type
        updated_by: User email

    Returns:
        FileUploadResponse with blob URL
    """
    # Default to GLOBAL if no org_id
    org_id = org_id or "GLOBAL"
    blob_service = get_blob_service()
    table_service = TableStorageService("Config")

    # Determine file extension
    ext_map = {
        "image/png": "png",
        "image/jpeg": "jpg",
        "image/jpg": "jpg",
        "image/svg+xml": "svg"
    }
    extension = ext_map.get(content_type, "png")

    # Upload to blob storage
    blob_name = f"{org_id}/{logo_type}-logo.{extension}"
    blob_url = await blob_service.upload_blob(
        container_name="branding",
        blob_name=blob_name,
        data=file_data,
        content_type=content_type
    )

    # Update branding in Config table
    branding_data = None
    try:
        entity = table_service.get_entity(partition_key=org_id, row_key="branding")
        if entity:
            branding_data = _entity_to_dict(entity)
    except Exception:
        pass

    if not branding_data:
        branding_data = {
            "orgId": org_id,
            "squareLogoUrl": None,
            "rectangleLogoUrl": None,
            "primaryColor": None
        }

    # Update appropriate logo URL
    if logo_type == "square":
        branding_data["squareLogoUrl"] = blob_url
    elif logo_type == "rectangle":
        branding_data["rectangleLogoUrl"] = blob_url

    branding_data["updatedBy"] = updated_by
    branding_data["updatedAt"] = datetime.utcnow()

    # Save to table
    entity = {
        "PartitionKey": org_id,
        "RowKey": "branding",
        **_branding_to_dict(branding_data)
    }
    table_service.upsert_entity(entity)

    return FileUploadResponse(
        upload_url=blob_url,
        blob_uri=blob_url,
        expires_at=datetime.utcnow().isoformat()  # No expiration for direct upload
    )


def _entity_to_branding(entity: dict) -> BrandingSettings:
    """Convert table entity to BrandingSettings model"""
    org_id = entity.get("PartitionKey", "GLOBAL")
    return BrandingSettings(
        orgId=org_id,
        squareLogoUrl=_transform_blob_url_to_proxy(entity.get("SquareLogoUrl"), org_id),
        rectangleLogoUrl=_transform_blob_url_to_proxy(entity.get("RectangleLogoUrl"), org_id),
        primaryColor=entity.get("PrimaryColor"),
        updatedBy=entity.get("UpdatedBy", "system"),
        updatedAt=entity.get("UpdatedAt", datetime.utcnow())
    )


def _entity_to_dict(entity: dict) -> dict:
    """Convert table entity to dict"""
    return {
        "orgId": entity.get("PartitionKey", "GLOBAL"),
        "squareLogoUrl": entity.get("SquareLogoUrl"),
        "rectangleLogoUrl": entity.get("RectangleLogoUrl"),
        "primaryColor": entity.get("PrimaryColor"),
        "updatedBy": entity.get("UpdatedBy", "system"),
        "updatedAt": entity.get("UpdatedAt", datetime.utcnow())
    }


def _branding_to_dict(branding_data: dict) -> dict:
    """Convert branding data to table entity dict"""
    return {
        "SquareLogoUrl": branding_data.get("squareLogoUrl"),
        "RectangleLogoUrl": branding_data.get("rectangleLogoUrl"),
        "PrimaryColor": branding_data.get("primaryColor"),
        "UpdatedBy": branding_data.get("updatedBy", "system"),
        "UpdatedAt": branding_data.get("updatedAt", datetime.utcnow())
    }
