"""Unit tests for BrandingRepository.set_branding application_name handling.

Exercises the three application_name states the sentinel must distinguish:
set-a-value, leave-unchanged (omitted), and clear-to-None.
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.repositories.branding import BrandingRepository


@pytest.mark.asyncio
async def test_set_application_name_creates_and_persists(db_session: AsyncSession):
    repo = BrandingRepository(db_session)

    branding = await repo.set_branding(application_name="Acme Portal")
    assert branding.application_name == "Acme Portal"

    # Re-read to confirm it persisted on the single global row
    reloaded = await repo.get_branding()
    assert reloaded is not None
    assert reloaded.application_name == "Acme Portal"


@pytest.mark.asyncio
async def test_omitting_application_name_leaves_it_unchanged(db_session: AsyncSession):
    repo = BrandingRepository(db_session)
    await repo.set_branding(application_name="Acme Portal")

    # Update a different field without passing application_name; it must survive.
    branding = await repo.set_branding(primary_color="#123456")
    assert branding.primary_color == "#123456"
    assert branding.application_name == "Acme Portal"


@pytest.mark.asyncio
async def test_explicit_none_clears_primary_color(db_session: AsyncSession):
    repo = BrandingRepository(db_session)
    await repo.set_branding(primary_color="#123456")

    branding = await repo.set_branding(primary_color=None)
    assert branding.primary_color is None

    reloaded = await repo.get_branding()
    assert reloaded is not None
    assert reloaded.primary_color is None


@pytest.mark.asyncio
async def test_omitting_logo_fields_leaves_them_unchanged(db_session: AsyncSession):
    repo = BrandingRepository(db_session)
    await repo.set_branding(
        square_logo_data=b"square",
        square_logo_content_type="image/png",
        rectangle_logo_data=b"rectangle",
        rectangle_logo_content_type="image/jpeg",
    )

    branding = await repo.set_branding(primary_color="#123456")

    assert branding.square_logo_data == b"square"
    assert branding.square_logo_content_type == "image/png"
    assert branding.rectangle_logo_data == b"rectangle"
    assert branding.rectangle_logo_content_type == "image/jpeg"


@pytest.mark.asyncio
async def test_explicit_none_clears_logo_fields(db_session: AsyncSession):
    repo = BrandingRepository(db_session)
    await repo.set_branding(
        square_logo_data=b"square",
        square_logo_content_type="image/png",
        rectangle_logo_data=b"rectangle",
        rectangle_logo_content_type="image/jpeg",
    )

    branding = await repo.set_branding(
        square_logo_data=None,
        square_logo_content_type=None,
        rectangle_logo_data=None,
        rectangle_logo_content_type=None,
    )

    assert branding.square_logo_data is None
    assert branding.square_logo_content_type is None
    assert branding.rectangle_logo_data is None
    assert branding.rectangle_logo_content_type is None


@pytest.mark.asyncio
async def test_explicit_none_clears_application_name(db_session: AsyncSession):
    repo = BrandingRepository(db_session)
    await repo.set_branding(application_name="Acme Portal")

    branding = await repo.set_branding(application_name=None)
    assert branding.application_name is None

    reloaded = await repo.get_branding()
    assert reloaded is not None
    assert reloaded.application_name is None
