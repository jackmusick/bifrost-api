"""
Base Repository
Provides common CRUD operations for all repositories
"""

import logging
from datetime import datetime
from typing import TYPE_CHECKING

from shared.async_storage import AsyncTableStorageService

if TYPE_CHECKING:
    from shared.context import ExecutionContext

logger = logging.getLogger(__name__)


class BaseRepository:
    """
    Base repository with common CRUD patterns

    Provides low-level database operations that can be used by
    all entity-specific repositories.

    This class abstracts AsyncTableStorageService to make future
    database swaps easier (e.g., Table Storage → Cosmos DB)
    """

    def __init__(self, table_name: str, context: 'ExecutionContext | None' = None):
        """
        Initialize repository

        Args:
            table_name: Name of the Azure Table to work with
            context: Optional ExecutionContext for automatic scoping
        """
        self.table_name = table_name
        self.context = context
        self._service = AsyncTableStorageService(table_name, context=context)

        logger.debug(f"Initialized {self.__class__.__name__} for table: {table_name}")

    async def get_by_id(self, partition_key: str, row_key: str) -> dict | None:
        """
        Get a single entity by partition and row key

        Args:
            partition_key: Partition key
            row_key: Row key

        Returns:
            Entity dictionary or None if not found
        """
        return await self._service.get_entity(partition_key, row_key)

    async def query(self, filter_query: str, select: list[str] | None = None) -> list[dict]:
        """
        Query entities with optional filter and column selection

        Args:
            filter_query: OData filter string
            select: List of properties to select (None = all properties)

        Returns:
            List of entity dictionaries
        """
        return await self._service.query_entities(filter=filter_query, select=select)

    async def query_paged(
        self,
        filter_query: str,
        select: list[str] | None = None,
        results_per_page: int = 50,
        continuation_token: dict | str | None = None
    ) -> tuple[list[dict], dict | str | None]:
        """
        Query entities with pagination support.

        Args:
            filter_query: OData filter string
            select: List of properties to select (None = all properties)
            results_per_page: Number of results per page (default 50, max 1000)
            continuation_token: Token from previous page (None for first page)

        Returns:
            Tuple of (list of entities, next continuation token or None)
        """
        return await self._service.query_entities_paged(
            filter=filter_query,
            select=select,
            results_per_page=results_per_page,
            continuation_token=continuation_token
        )

    async def insert(self, entity: dict) -> dict:
        """
        Insert a new entity

        Args:
            entity: Entity dictionary with PartitionKey and RowKey

        Returns:
            The inserted entity

        Raises:
            ResourceExistsError: If entity already exists
            ValueError: If PartitionKey or RowKey missing
        """
        return await self._service.insert_entity(entity)

    async def update(self, entity: dict, mode: str = "merge") -> dict:
        """
        Update an existing entity

        Args:
            entity: Entity dictionary with PartitionKey and RowKey
            mode: Update mode - "merge" (default) or "replace"

        Returns:
            The updated entity

        Raises:
            ResourceNotFoundError: If entity doesn't exist
        """
        return await self._service.update_entity(entity, mode=mode)

    async def upsert(self, entity: dict, mode: str = "merge") -> dict:
        """
        Insert or update an entity (creates if doesn't exist)

        Args:
            entity: Entity dictionary with PartitionKey and RowKey
            mode: Update mode - "merge" (default) or "replace"

        Returns:
            The upserted entity
        """
        return await self._service.upsert_entity(entity, mode=mode)

    async def delete(self, partition_key: str, row_key: str) -> bool:
        """
        Delete an entity

        Args:
            partition_key: Partition key
            row_key: Row key

        Returns:
            True if deleted, False if not found
        """
        return await self._service.delete_entity(partition_key, row_key)

    def _get_partition_key_for_scope(self, scope: str | None = None) -> str:
        """
        Get partition key from scope

        Args:
            scope: Explicit scope (org_id or "GLOBAL"), or None to use context

        Returns:
            Partition key to use for queries
        """
        if scope is not None:
            return scope

        if self.context:
            return self.context.scope

        return "GLOBAL"

    @staticmethod
    def _parse_datetime(value: str | datetime | None, default: datetime | None = None) -> datetime | None:
        """
        Safely parse datetime from entity field

        Azure Table Storage may return datetime fields as:
        1. datetime objects (automatic deserialization)
        2. ISO format strings (manual insertion or older SDKs)
        3. None (missing field)

        Args:
            value: Value from entity.get() - could be datetime, str, or None
            default: Default value if value is None (defaults to None)

        Returns:
            Parsed datetime object, default, or None

        Examples:
            # From test fixtures (string)
            dt = _parse_datetime("2024-01-15T10:30:00")

            # From Azure SDK (already datetime)
            dt = _parse_datetime(datetime(2024, 1, 15, 10, 30))

            # Missing field
            dt = _parse_datetime(None, datetime.utcnow())
        """
        if value is None:
            return default

        if isinstance(value, datetime):
            return value

        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value)
            except (ValueError, TypeError) as e:
                logger.warning(f"Failed to parse datetime from string '{value}': {e}")
                return default

        logger.warning(f"Unexpected datetime type: {type(value)} for value {value}")
        return default
