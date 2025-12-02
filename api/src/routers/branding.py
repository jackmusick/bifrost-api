"""
Branding Router

Platform and organization branding configuration.

Branding is stored in the configs table with key='branding'.
Logo files are stored in the filesystem under /mounts/files/branding/{org_id}/.
"""

import logging
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import Response
from sqlalchemy import select

from src.models.schemas import BrandingSettings, BrandingUpdateRequest
from src.core.auth import Context, CurrentActiveUser
from src.core.database import AsyncSession, get_db
from src.models import Config as ConfigModel
from src.services.file_storage import get_file_storage

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/branding", tags=["Branding"])

# Branding config key
BRANDING_KEY = "branding"

# Allowed image types for logo upload
ALLOWED_CONTENT_TYPES = {"image/png", "image/jpeg", "image/jpg", "image/svg+xml"}
MAX_LOGO_SIZE = 5 * 1024 * 1024  # 5MB


async def get_branding_config(
    db: AsyncSession,
    org_id: str | None = None
) -> ConfigModel | None:
    """
    Get branding config with cascade logic.

    1. Try org-specific config first
    2. Fall back to global (org_id=NULL) config
    """
    # Try org-specific first
    if org_id:
        query = select(ConfigModel).where(
            ConfigModel.key == BRANDING_KEY,
            ConfigModel.organization_id == org_id,
        )
        result = await db.execute(query)
        config = result.scalar_one_or_none()
        if config:
            return config

    # Fall back to global
    query = select(ConfigModel).where(
        ConfigModel.key == BRANDING_KEY,
        ConfigModel.organization_id.is_(None),
    )
    result = await db.execute(query)
    return result.scalar_one_or_none()


def config_to_branding(config: ConfigModel | None) -> BrandingSettings:
    """Convert config model to BrandingSettings."""
    if not config or not config.value:
        return BrandingSettings(
            org_id="GLOBAL",
            square_logo_url=None,
            rectangle_logo_url=None,
            primary_color=None,
            updated_by="system",
            updated_at=datetime.utcnow(),
        )

    value = config.value
    return BrandingSettings(
        org_id=str(config.organization_id) if config.organization_id else "GLOBAL",
        square_logo_url=value.get("square_logo_url"),
        rectangle_logo_url=value.get("rectangle_logo_url"),
        primary_color=value.get("primary_color"),
        updated_by=value.get("updated_by", "system"),
        updated_at=config.updated_at or datetime.utcnow(),
    )


# =============================================================================
# Public Endpoints (no auth required for branding display)
# =============================================================================


@router.get(
    "",
    response_model=BrandingSettings,
    summary="Get branding settings",
    description="Get platform branding settings. Public endpoint for login page display.",
)
async def get_branding(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> BrandingSettings:
    """
    Get branding settings (public endpoint).

    Returns global branding settings for the platform.
    Used on login page before authentication.
    """
    config = await get_branding_config(db)
    return config_to_branding(config)


# =============================================================================
# Authenticated Endpoints
# =============================================================================


@router.put(
    "",
    response_model=BrandingSettings,
    summary="Update branding settings",
    description="Update platform branding settings (superuser only)",
)
async def update_branding(
    request: BrandingUpdateRequest,
    ctx: Context,
    user: CurrentActiveUser,
) -> BrandingSettings:
    """
    Update branding settings.

    Only superusers can update global branding.
    Org admins can update their org's branding.
    """
    # For now, only allow global branding updates by superusers
    if not user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only superusers can update branding",
        )

    # Get existing config or create new
    config = await get_branding_config(ctx.db, org_id=None)

    now = datetime.utcnow()

    if config:
        # Update existing
        value = config.value or {}
        if request.primary_color is not None:
            value["primary_color"] = request.primary_color
        if request.square_logo_url is not None:
            value["square_logo_url"] = request.square_logo_url
        if request.rectangle_logo_url is not None:
            value["rectangle_logo_url"] = request.rectangle_logo_url
        value["updated_by"] = user.email

        config.value = value
        config.updated_at = now
        config.updated_by = user.email
    else:
        # Create new
        config = ConfigModel(
            key=BRANDING_KEY,
            organization_id=None,  # Global
            value={
                "primary_color": request.primary_color,
                "square_logo_url": request.square_logo_url,
                "rectangle_logo_url": request.rectangle_logo_url,
                "updated_by": user.email,
            },
            updated_by=user.email,
            created_at=now,
            updated_at=now,
        )
        ctx.db.add(config)

    await ctx.db.flush()
    await ctx.db.refresh(config)

    logger.info(f"Branding updated by {user.email}")
    return config_to_branding(config)


@router.post(
    "/logo/{logo_type}",
    response_model=BrandingSettings,
    summary="Upload logo",
    description="Upload a square or rectangle logo (superuser only)",
)
async def upload_logo(
    logo_type: str,
    file: Annotated[UploadFile, File(description="Logo image file")],
    ctx: Context,
    user: CurrentActiveUser,
) -> BrandingSettings:
    """
    Upload a logo file.

    Args:
        logo_type: 'square' or 'rectangle'
        file: Image file (PNG, JPEG, SVG)
    """
    if not user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only superusers can upload logos",
        )

    if logo_type not in ("square", "rectangle"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="logo_type must be 'square' or 'rectangle'",
        )

    # Validate content type
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Allowed: {', '.join(ALLOWED_CONTENT_TYPES)}",
        )

    # Read file content
    content = await file.read()
    if len(content) > MAX_LOGO_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large. Maximum size: {MAX_LOGO_SIZE // 1024 // 1024}MB",
        )

    # Determine file extension
    ext_map = {
        "image/png": "png",
        "image/jpeg": "jpg",
        "image/jpg": "jpg",
        "image/svg+xml": "svg",
    }
    extension = ext_map.get(file.content_type, "png")

    # Use "GLOBAL" for platform-wide branding
    org_id = "GLOBAL"
    filename = f"{logo_type}-logo.{extension}"

    # Save to filesystem storage
    file_storage = get_file_storage()
    await file_storage.save_branding_file(
        org_id=org_id,
        filename=filename,
        content=content,
        content_type=file.content_type,
    )

    # Generate URL - this will be served by the API
    logo_url = f"/api/branding/logo/{logo_type}"

    # Update branding config
    config = await get_branding_config(ctx.db, org_id=None)
    now = datetime.utcnow()

    if config:
        value = config.value or {}
        if logo_type == "square":
            value["square_logo_url"] = logo_url
        else:
            value["rectangle_logo_url"] = logo_url
        value["updated_by"] = user.email

        config.value = value
        config.updated_at = now
        config.updated_by = user.email
    else:
        config = ConfigModel(
            key=BRANDING_KEY,
            organization_id=None,
            value={
                "square_logo_url": logo_url if logo_type == "square" else None,
                "rectangle_logo_url": logo_url if logo_type == "rectangle" else None,
                "updated_by": user.email,
            },
            updated_by=user.email,
            created_at=now,
            updated_at=now,
        )
        ctx.db.add(config)

    await ctx.db.flush()
    await ctx.db.refresh(config)

    logger.info(f"Logo '{logo_type}' uploaded by {user.email}")
    return config_to_branding(config)


@router.get(
    "/logo/{logo_type}",
    summary="Get logo image",
    description="Serve the uploaded logo image",
    responses={
        200: {"content": {"image/png": {}, "image/svg+xml": {}, "image/jpeg": {}}},
        404: {"description": "Logo not found"},
    },
)
async def get_logo(logo_type: str):
    """Serve logo image file from filesystem storage."""
    if logo_type not in ("square", "rectangle"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="logo_type must be 'square' or 'rectangle'",
        )

    try:
        file_storage = get_file_storage()
        org_id = "GLOBAL"

        # Check for logo file with various extensions
        for ext in ["svg", "png", "jpg", "jpeg"]:
            filename = f"{logo_type}-logo.{ext}"
            content = await file_storage.get_branding_file(org_id, filename)
            if content:
                media_type = {
                    "svg": "image/svg+xml",
                    "png": "image/png",
                    "jpg": "image/jpeg",
                    "jpeg": "image/jpeg",
                }.get(ext, "application/octet-stream")
                return Response(content=content, media_type=media_type)

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Logo '{logo_type}' not found",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting logo: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Logo '{logo_type}' not found",
        )
