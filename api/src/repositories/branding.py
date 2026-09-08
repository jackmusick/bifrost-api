"""
Branding Repository

Global repository for platform-wide branding configuration.
No organization scoping - single global branding record.
"""

import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import GlobalBranding

logger = logging.getLogger(__name__)

# Sentinel distinguishing "argument omitted" (leave field unchanged) from an
# explicit None (clear the field).
_UNSET: Any = object()


class BrandingRepository:
    """
    Repository for global branding configuration.

    Branding is platform-wide (no org scoping).
    Single record for entire platform.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_branding(self) -> GlobalBranding | None:
        """
        Get global branding configuration.

        Returns:
            GlobalBranding object or None if not configured
        """
        query = select(GlobalBranding).limit(1)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def set_branding(
        self,
        square_logo_data: bytes | None = _UNSET,
        square_logo_content_type: str | None = _UNSET,
        rectangle_logo_data: bytes | None = _UNSET,
        rectangle_logo_content_type: str | None = _UNSET,
        primary_color: str | None = _UNSET,
        terminology: dict | None = _UNSET,
        application_name: str | None = _UNSET,
    ) -> GlobalBranding:
        """
        Create or update global branding configuration (upsert).

        Args:
            square_logo_data: Square logo image bytes. Omit to leave unchanged;
                pass None to clear.
            square_logo_content_type: Square logo MIME type (e.g., 'image/png').
                Omit to leave unchanged; pass None to clear.
            rectangle_logo_data: Rectangle logo image bytes. Omit to leave
                unchanged; pass None to clear.
            rectangle_logo_content_type: Rectangle logo MIME type (e.g., 'image/png').
                Omit to leave unchanged; pass None to clear.
            primary_color: Hex color code (e.g., '#0066CC'). Omit to leave
                unchanged; pass None to clear.
            terminology: Fixed product terminology overrides. Omit to leave
                unchanged; pass None to clear.
            application_name: Product name. Omit to leave unchanged; pass None to
                clear it back to the default.

        Returns:
            Created or updated GlobalBranding record
        """
        existing = await self.get_branding()

        if existing:
            # Update existing
            if square_logo_data is not _UNSET:
                existing.square_logo_data = square_logo_data
            if square_logo_content_type is not _UNSET:
                existing.square_logo_content_type = square_logo_content_type
            if rectangle_logo_data is not _UNSET:
                existing.rectangle_logo_data = rectangle_logo_data
            if rectangle_logo_content_type is not _UNSET:
                existing.rectangle_logo_content_type = rectangle_logo_content_type
            if primary_color is not _UNSET:
                existing.primary_color = primary_color
            if terminology is not _UNSET:
                existing.terminology = terminology
            if application_name is not _UNSET:
                existing.application_name = application_name

            await self.session.flush()
            await self.session.refresh(existing)
            logger.info("Global branding updated")
            return existing
        else:
            # Create new
            branding = GlobalBranding(
                square_logo_data=None
                if square_logo_data is _UNSET
                else square_logo_data,
                square_logo_content_type=None
                if square_logo_content_type is _UNSET
                else square_logo_content_type,
                rectangle_logo_data=None
                if rectangle_logo_data is _UNSET
                else rectangle_logo_data,
                rectangle_logo_content_type=None
                if rectangle_logo_content_type is _UNSET
                else rectangle_logo_content_type,
                primary_color=None if primary_color is _UNSET else primary_color,
                terminology=None if terminology is _UNSET else terminology,
                application_name=None
                if application_name is _UNSET
                else application_name,
            )
            self.session.add(branding)
            await self.session.flush()
            await self.session.refresh(branding)
            logger.info("Global branding created")
            return branding

    async def delete_branding(self) -> bool:
        """
        Delete global branding configuration.

        Returns:
            True if branding was deleted, False if it didn't exist
        """
        branding = await self.get_branding()
        if not branding:
            return False

        await self.session.delete(branding)
        await self.session.flush()
        logger.info("Global branding deleted")
        return True
