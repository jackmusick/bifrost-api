"""
Base Repository

Provides common database operations for all repositories.
Uses SQLAlchemy async session for all operations.
"""

from typing import Generic, TypeVar
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import Base

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    """
    Base repository with common CRUD operations.

    Provides a consistent interface for database access across all models.
    """

    model: type[ModelT]

    def __init__(self, session: AsyncSession):
        """
        Initialize repository with database session.

        Args:
            session: SQLAlchemy async session
        """
        self.session = session

    async def get_by_id(self, id: UUID) -> ModelT | None:
        """
        Get entity by ID.

        Args:
            id: Entity UUID

        Returns:
            Entity or None if not found
        """
        result = await self.session.execute(
            select(self.model).where(self.model.id == id)
        )
        return result.scalar_one_or_none()

    async def get_all(self, limit: int = 100, offset: int = 0) -> list[ModelT]:
        """
        Get all entities with pagination.

        Args:
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of entities
        """
        result = await self.session.execute(
            select(self.model).limit(limit).offset(offset)
        )
        return list(result.scalars().all())

    async def create(self, entity: ModelT) -> ModelT:
        """
        Create a new entity.

        Args:
            entity: Entity to create

        Returns:
            Created entity with generated ID
        """
        self.session.add(entity)
        await self.session.flush()
        await self.session.refresh(entity)
        return entity

    async def update(self, entity: ModelT) -> ModelT:
        """
        Update an existing entity.

        Args:
            entity: Entity with updated values

        Returns:
            Updated entity
        """
        await self.session.flush()
        await self.session.refresh(entity)
        return entity

    async def delete(self, entity: ModelT) -> None:
        """
        Delete an entity.

        Args:
            entity: Entity to delete
        """
        # Note: session.delete() is NOT async - it just marks for deletion
        self.session.delete(entity)
        await self.session.flush()

    async def delete_by_id(self, id: UUID) -> bool:
        """
        Delete entity by ID.

        Args:
            id: Entity UUID

        Returns:
            True if deleted, False if not found
        """
        entity = await self.get_by_id(id)
        if entity:
            await self.delete(entity)
            return True
        return False
