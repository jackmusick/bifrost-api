"""
Data Provider Repository

Database operations for data provider registry.
Replaces scan_all_data_providers() with efficient database queries.
"""

from typing import Sequence

from sqlalchemy import func, select

from src.models import DataProvider
from src.repositories.base import BaseRepository


class DataProviderRepository(BaseRepository[DataProvider]):
    """Repository for data provider registry operations."""

    model = DataProvider

    async def get_by_name(self, name: str) -> DataProvider | None:
        """Get data provider by name."""
        result = await self.session.execute(
            select(DataProvider).where(DataProvider.name == name)
        )
        return result.scalar_one_or_none()

    async def get_all_active(self) -> Sequence[DataProvider]:
        """Get all active data providers."""
        result = await self.session.execute(
            select(DataProvider)
            .where(DataProvider.is_active.is_(True))
            .order_by(DataProvider.name)
        )
        return result.scalars().all()

    async def count_active(self) -> int:
        """Count all active data providers."""
        result = await self.session.execute(
            select(func.count(DataProvider.id))
            .where(DataProvider.is_active.is_(True))
        )
        return result.scalar() or 0

    async def search(
        self,
        query: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Sequence[DataProvider]:
        """Search data providers with filters."""
        stmt = select(DataProvider).where(DataProvider.is_active.is_(True))

        if query:
            stmt = stmt.where(
                DataProvider.name.ilike(f"%{query}%") |
                DataProvider.description.ilike(f"%{query}%")
            )

        stmt = stmt.order_by(DataProvider.name).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return result.scalars().all()
