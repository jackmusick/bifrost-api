"""
Business logic for branding operations
Handles branding configuration storage and retrieval
"""

import logging
from datetime import datetime, timedelta
from typing import Optional

from shared.models import BrandingSettings, FileUploadResponse, UploadedFileMetadata
from shared.blob_storage import get_blob_service
from shared.async_storage import AsyncTableStorageService

logger = logging.getLogger(__name__)

# In-memory cache for branding lookups to reduce database calls
# Cache key: org_id, Value: (BrandingSettings, timestamp)
_branding_cache: dict[str, tuple[BrandingSettings, datetime]] = {}
_cache_ttl = timedelta(seconds=300)  # Cache branding for 5 minutes


def _get_cached_branding(org_id: str) -> BrandingSettings | None:
    """
    Get branding from cache if present and not expired.

    Args:
        org_id: Organization ID

    Returns:
        Cached BrandingSettings or None if not cached or expired
    """
    if org_id in _branding_cache:
        branding, cached_at = _branding_cache[org_id]
        age = datetime.utcnow() - cached_at

        if age < _cache_ttl:
            logger.debug(f"Branding cache hit for {org_id} (age: {age.total_seconds():.1f}s)")
            return branding
        else:
            # Expired - remove from cache
            del _branding_cache[org_id]
            logger.debug(f"Branding cache expired for {org_id}")

    return None


def _cache_branding(org_id: str, branding: BrandingSettings) -> None:
    """
    Cache branding with current timestamp.

    Args:
        org_id: Organization ID
        branding: BrandingSettings to cache
    """
    _branding_cache[org_id] = (branding, datetime.utcnow())
    logger.debug(f"Cached branding for {org_id}")


def invalidate_branding_cache(org_id: str) -> None:
    """
    Invalidate cached branding for an organization.

    Args:
        org_id: Organization ID
    """
    if org_id in _branding_cache:
        del _branding_cache[org_id]
        logger.debug(f"Invalidated branding cache for {org_id}")


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


async def get_branding() -> BrandingSettings:
    """
    Get GLOBAL branding settings for the platform.
    Uses in-memory cache (5 min TTL) to reduce database calls.

    Returns:
        BrandingSettings object
    """
    # Check cache first
    cached_branding = _get_cached_branding("GLOBAL")
    if cached_branding:
        return cached_branding

    # Cache miss - query database
    table_service = AsyncTableStorageService("Config")

    # Get GLOBAL branding
    try:
        entity = await table_service.get_entity(partition_key="GLOBAL", row_key="branding")
        if entity:
            branding = _entity_to_branding(entity)
            _cache_branding("GLOBAL", branding)
            return branding
    except Exception:
        pass

    # Return default branding (all None - frontend handles defaults)
    default_branding = BrandingSettings(
        orgId="GLOBAL",
        squareLogoUrl=None,
        rectangleLogoUrl=None,
        primaryColor=None,
        updatedBy="system",
        updatedAt=datetime.utcnow()
    )
    _cache_branding("GLOBAL", default_branding)  # Cache default to avoid repeated queries
    return default_branding


async def update_branding(
    org_id: str | None,
    primary_color: Optional[str] = None,
    updated_by: str = "system"
) -> BrandingSettings:
    """
    Update branding settings (color only - use upload_logo for logos).
    Invalidates cache after update.

    Args:
        org_id: Organization ID (None defaults to GLOBAL)
        primary_color: Hex color code (e.g., '#0066CC')
        updated_by: User email

    Returns:
        Updated BrandingSettings
    """
    # Default to GLOBAL if no org_id
    org_id = org_id or "GLOBAL"
    table_service = AsyncTableStorageService("Config")

    # Get existing branding or create new
    branding_data = None
    try:
        entity = await table_service.get_entity(partition_key=org_id, row_key="branding")
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
    await table_service.upsert_entity(entity)

    # Invalidate cache
    invalidate_branding_cache(org_id)

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
    Invalidates cache after update.

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
    table_service = AsyncTableStorageService("Config")

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
        entity = await table_service.get_entity(partition_key=org_id, row_key="branding")
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
    await table_service.upsert_entity(entity)

    # Invalidate cache
    invalidate_branding_cache(org_id)

    # Create file metadata for the uploaded logo
    file_metadata = UploadedFileMetadata(
        name=f"{logo_type}-logo.{extension}",
        container="branding",
        path=blob_name,
        content_type=content_type,
        size=len(file_data)
    )

    return FileUploadResponse(
        upload_url=blob_url,
        blob_uri=blob_url,
        expires_at=datetime.utcnow().isoformat(),  # No expiration for direct upload
        file_metadata=file_metadata
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
