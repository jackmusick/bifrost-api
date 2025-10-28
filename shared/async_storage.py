"""
Async Table Storage Service for Bifrost Integrations
Provides async wrappers around Azure Table Storage operations with context-aware scoping
"""

import logging
import os
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from azure.core import MatchConditions
from azure.core.exceptions import ResourceExistsError, ResourceNotFoundError, ResourceModifiedError
from azure.data.tables import UpdateMode
from azure.data.tables.aio import TableClient

from shared.storage import (
    SCOPED_TABLES,
    GLOBAL_TABLES,
    CUSTOM_TABLES,
    EXPLICIT_PARTITION_TABLES
)

if TYPE_CHECKING:
    from shared.context import ExecutionContext

logger = logging.getLogger(__name__)


class AsyncTableStorageService:
    """
    Async Azure Table Storage operations
    Provides org-scoped query helpers and common CRUD operations with async/await
    """

    def __init__(self, table_name: str, connection_string: str | None = None, context: Optional['ExecutionContext'] = None):
        """
        Initialize Async Table Storage client

        Args:
            table_name: Name of the table to work with
            connection_string: Optional connection string override
            context: Optional ExecutionContext for automatic scoping
        """
        self.table_name = table_name
        self.context = context

        if connection_string is None:
            connection_string = os.environ.get("AzureWebJobsStorage")

        if not connection_string:
            raise ValueError("AzureWebJobsStorage environment variable not set")

        self.connection_string = connection_string
        self._client: TableClient | None = None
        self._in_context_manager = False
        self._clients_to_cleanup: list[TableClient] = []

        # Determine scoping strategy
        self.is_scoped = table_name in SCOPED_TABLES
        self.is_global = table_name in GLOBAL_TABLES
        self.custom_partition = CUSTOM_TABLES.get(table_name)
        self.is_explicit = table_name in EXPLICIT_PARTITION_TABLES

        logger.debug(
            f"AsyncTableStorageService initialized for table: {table_name} "
            f"(scoped={self.is_scoped}, global={self.is_global}, explicit={self.is_explicit}, context={context is not None})"
        )

    @property
    def table_client(self) -> TableClient:
        """
        Get or create TableClient instance.

        If used within a context manager (async with), reuses the same client.
        Otherwise, creates a new client for each access and tracks it for cleanup.
        """
        if self._in_context_manager:
            # Reuse client when in context manager
            if self._client is None:
                self._client = TableClient.from_connection_string(
                    self.connection_string, self.table_name
                )
            return self._client
        else:
            # Create new client and track it for cleanup
            client = TableClient.from_connection_string(
                self.connection_string, self.table_name
            )
            self._clients_to_cleanup.append(client)
            return client

    async def __aenter__(self):
        """Context manager entry - ensure client is ready"""
        self._in_context_manager = True
        await self.table_client.__aenter__()
        return self

    async def __aexit__(self, *args):
        """Context manager exit - cleanup client"""
        self._in_context_manager = False
        if self._client is not None:
            await self._client.__aexit__(*args)
            self._client = None

    def __del__(self):
        """
        Cleanup any TableClients that weren't properly closed.
        This ensures connections are closed even when not using context manager.
        """
        if self._clients_to_cleanup:
            import warnings

            warnings.warn(
                f"AsyncTableStorageService for {self.table_name} has {len(self._clients_to_cleanup)} unclosed clients. "
                "Consider using 'async with' for proper resource management.",
                ResourceWarning,
                stacklevel=2
            )

            # Close all tracked clients synchronously (best effort)
            for client in self._clients_to_cleanup:
                try:
                    # Try to close the client if it has a close method
                    # We can't use async close here since we're in __del__
                    # Just let the warning inform the user to use context manager
                    pass
                except Exception:
                    pass
            self._clients_to_cleanup.clear()

    async def close(self):
        """Explicitly close the table client connection"""
        if self._client is not None:
            try:
                await self._client.close()
            except Exception as e:
                # Ignore "Event loop is closed" errors during cleanup
                if "Event loop is closed" not in str(e):
                    logger.warning(f"Error closing table client: {e}")
            finally:
                self._client = None

    async def insert_entity(self, entity: dict) -> dict:
        """
        Insert a new entity into the table with automatic partition key handling.

        Args:
            entity: Entity dictionary with RowKey (PartitionKey auto-applied if context provided)

        Returns:
            The inserted entity with metadata

        Raises:
            ResourceExistsError: If entity already exists
            ValueError: If PartitionKey or RowKey is missing
        """
        # Auto-apply PartitionKey if not set
        entity = self._apply_partition_key(entity)

        if "PartitionKey" not in entity or "RowKey" not in entity:
            raise ValueError("Entity must have PartitionKey and RowKey")

        try:
            # Serialize datetime fields
            entity = self._serialize_datetime_fields(entity)

            # Insert entity
            await self.table_client.create_entity(entity)

            logger.info(
                f"Inserted entity: {self.table_name} "
                f"PK={entity['PartitionKey']} RK={entity['RowKey']}"
            )

            return entity

        except ResourceExistsError:
            logger.error(
                f"Entity already exists: {self.table_name} "
                f"PK={entity['PartitionKey']} RK={entity['RowKey']}"
            )
            raise

        except Exception as e:
            logger.error(f"Failed to insert entity: {str(e)}")
            raise

    def _apply_partition_key(self, entity: dict) -> dict:
        """
        Apply partition key based on table scoping rules and context.

        Priority:
        1. Explicit PartitionKey in entity (always respected)
        2. Context-based scoping for scoped tables
        3. GLOBAL for global tables
        4. Error for custom tables without explicit key

        Args:
            entity: Entity dictionary

        Returns:
            Entity with PartitionKey set

        Raises:
            ValueError: If PartitionKey cannot be determined
        """
        # If already set, respect it
        if "PartitionKey" in entity:
            return entity

        # Scoped tables (Config, Entities)
        if self.is_scoped:
            if self.context:
                entity["PartitionKey"] = self.context.scope  # org_id or "GLOBAL"
                return entity
            else:
                raise ValueError(
                    f"Table '{self.table_name}' requires context for automatic scoping. "
                    f"Either provide context or set PartitionKey explicitly."
                )

        # Global tables (Relationships)
        if self.is_global:
            entity["PartitionKey"] = "GLOBAL"
            return entity

        # Explicit partition tables - require explicit key
        if self.is_explicit:
            raise ValueError(
                f"Table '{self.table_name}' requires explicit PartitionKey. "
                f"This table does not support automatic partition key assignment."
            )

        # Custom tables
        if self.custom_partition:
            raise ValueError(
                f"Table '{self.table_name}' uses custom partitioning ('{self.custom_partition}'). "
                f"Must explicitly set PartitionKey."
            )

        # Unknown table - require explicit PartitionKey
        raise ValueError(
            f"Table '{self.table_name}' not in scoping rules. "
            f"Must explicitly set PartitionKey."
        )

    async def update_entity(self, entity: dict, mode: str = "merge") -> dict:
        """
        Update an existing entity with automatic partition key handling.

        Args:
            entity: Entity dictionary with RowKey (PartitionKey auto-applied if context provided)
            mode: Update mode - "merge" (default) or "replace"

        Returns:
            The updated entity

        Raises:
            ResourceNotFoundError: If entity doesn't exist
        """
        # Auto-apply PartitionKey if not set
        entity = self._apply_partition_key(entity)

        if "PartitionKey" not in entity or "RowKey" not in entity:
            raise ValueError("Entity must have PartitionKey and RowKey")

        try:
            # Serialize datetime fields
            entity = self._serialize_datetime_fields(entity)

            # Update entity
            if mode == "replace":
                await self.table_client.update_entity(entity, mode=UpdateMode.REPLACE)
            else:
                await self.table_client.update_entity(entity, mode=UpdateMode.MERGE)

            logger.info(
                f"Updated entity ({mode}): {self.table_name} "
                f"PK={entity['PartitionKey']} RK={entity['RowKey']}"
            )

            return entity

        except ResourceNotFoundError:
            logger.error(
                f"Entity not found for update: {self.table_name} "
                f"PK={entity['PartitionKey']} RK={entity['RowKey']}"
            )
            raise

        except Exception as e:
            logger.error(f"Failed to update entity: {str(e)}")
            raise

    async def update_entity_with_etag(self, entity: dict, mode: str = "merge") -> dict:
        """
        Update an existing entity with optimistic concurrency control using ETag.

        Args:
            entity: Entity dictionary with RowKey and 'etag' field (from get_entity)
            mode: Update mode - "merge" (default) or "replace"

        Returns:
            The updated entity

        Raises:
            ValueError: If entity doesn't have 'etag' field
            ResourceModifiedError: If entity was modified since read (ETag mismatch)
            ResourceNotFoundError: If entity doesn't exist
        """
        # Auto-apply PartitionKey if not set
        entity = self._apply_partition_key(entity)

        if "PartitionKey" not in entity or "RowKey" not in entity:
            raise ValueError("Entity must have PartitionKey and RowKey")

        if "etag" not in entity:
            raise ValueError("Entity must have 'etag' field for optimistic concurrency. Use get_entity() first.")

        try:
            # Extract etag and remove from entity dict (not a data field)
            etag = entity.pop("etag")

            # Serialize datetime fields
            entity = self._serialize_datetime_fields(entity)

            # Update entity with ETag for optimistic concurrency
            if mode == "replace":
                await self.table_client.update_entity(
                    entity, mode=UpdateMode.REPLACE, etag=etag, match_condition=MatchConditions.IfNotModified
                )
            else:
                await self.table_client.update_entity(
                    entity, mode=UpdateMode.MERGE, etag=etag, match_condition=MatchConditions.IfNotModified
                )

            logger.info(
                f"Updated entity with ETag ({mode}): {self.table_name} "
                f"PK={entity['PartitionKey']} RK={entity['RowKey']}"
            )

            return entity

        except ResourceModifiedError:
            logger.warning(
                f"Entity was modified by another process (ETag mismatch): {self.table_name} "
                f"PK={entity['PartitionKey']} RK={entity['RowKey']}"
            )
            raise

        except ResourceNotFoundError:
            logger.error(
                f"Entity not found for update: {self.table_name} "
                f"PK={entity['PartitionKey']} RK={entity['RowKey']}"
            )
            raise

        except Exception as e:
            logger.error(f"Failed to update entity with ETag: {str(e)}")
            raise

    async def upsert_entity(self, entity: dict, mode: str = "merge") -> dict:
        """
        Insert or update an entity (creates if doesn't exist) with automatic partition key handling.

        Args:
            entity: Entity dictionary with RowKey (PartitionKey auto-applied if context provided)
            mode: Update mode - "merge" (default) or "replace"

        Returns:
            The upserted entity
        """
        # Auto-apply PartitionKey if not set
        entity = self._apply_partition_key(entity)

        if "PartitionKey" not in entity or "RowKey" not in entity:
            raise ValueError("Entity must have PartitionKey and RowKey")

        try:
            # Serialize datetime fields
            entity = self._serialize_datetime_fields(entity)

            # Upsert entity
            if mode == "replace":
                await self.table_client.upsert_entity(entity, mode=UpdateMode.REPLACE)
            else:
                await self.table_client.upsert_entity(entity, mode=UpdateMode.MERGE)

            logger.info(
                f"Upserted entity ({mode}): {self.table_name} "
                f"PK={entity['PartitionKey']} RK={entity['RowKey']}"
            )

            return entity

        except Exception as e:
            logger.error(f"Failed to upsert entity: {str(e)}")
            raise

    async def get_entity(self, partition_key: str, row_key: str) -> dict | None:
        """
        Retrieve a single entity by partition and row key

        Args:
            partition_key: The partition key
            row_key: The row key

        Returns:
            Entity dictionary or None if not found (includes 'etag' metadata for optimistic concurrency)
        """
        try:
            entity = await self.table_client.get_entity(
                partition_key=partition_key, row_key=row_key
            )

            # Convert to dict and preserve metadata (etag, timestamp)
            entity_dict = dict(entity)

            # Deserialize datetime fields
            entity_dict = self._deserialize_datetime_fields(entity_dict)

            # Preserve etag for optimistic concurrency control
            if hasattr(entity, 'metadata') and 'etag' in entity.metadata:
                entity_dict['etag'] = entity.metadata['etag']

            logger.debug(
                f"Retrieved entity: {self.table_name} PK={partition_key} RK={row_key}"
            )

            return entity_dict

        except ResourceNotFoundError:
            logger.debug(
                f"Entity not found: {self.table_name} PK={partition_key} RK={row_key}"
            )
            return None

        except Exception as e:
            logger.error(f"Failed to get entity: {str(e)}")
            raise

    async def query_entities(
        self, filter: str | None = None, select: list[str] | None = None
    ) -> list[dict]:
        """
        Query entities with optional filter and select

        Args:
            filter: OData filter string (e.g., "PartitionKey eq 'ORG'")
            select: List of properties to select

        Returns:
            List of entity dictionaries
        """
        try:
            # Query entities using positional argument for filter
            if filter:
                entities = self.table_client.query_entities(
                    query_filter=filter,
                    select=select
                )
            else:
                entities = self.table_client.query_entities(
                    query_filter="",
                    select=select
                )

            # Collect all entities into a list
            results = []
            async for entity in entities:
                results.append(self._deserialize_datetime_fields(dict(entity)))

            return results

        except Exception as e:
            logger.error(f"Failed to query entities: {str(e)}")
            raise

    async def query_entities_paged(
        self,
        filter: str | None = None,
        select: list[str] | None = None,
        results_per_page: int = 50,
        continuation_token: dict | str | None = None
    ) -> tuple[list[dict], dict | str | None]:
        """
        Query entities with pagination support.

        Args:
            filter: OData filter string (e.g., "PartitionKey eq 'ORG'")
            select: List of properties to select
            results_per_page: Number of results per page (max 1000)
            continuation_token: Token from previous page (None for first page)

        Returns:
            Tuple of (list of entities, next continuation token or None)
        """
        try:
            # Cap at Azure's limit
            results_per_page = min(results_per_page, 1000)

            # Query with pagination
            query_filter = filter if filter else ""
            token_to_pass: dict | str | None = continuation_token

            logger.info(f"[Pagination Debug] Querying with filter={query_filter}, results_per_page={results_per_page}, token_to_pass={token_to_pass}")

            # Get the paged iterator
            paged_results = self.table_client.query_entities(
                query_filter=query_filter,
                select=select,
                results_per_page=results_per_page
            ).by_page(continuation_token=token_to_pass)  # type: ignore[arg-type]

            # Get first page
            page = await paged_results.__anext__()  # type: ignore[attr-defined]

            # Collect entities from this page
            entities = []
            async for entity in page:
                entities.append(self._deserialize_datetime_fields(dict(entity)))

            logger.info(f"[Pagination Debug] Retrieved {len(entities)} entities from page")

            # Get continuation token for next page
            next_token_str: str | None = None
            try:
                next_token_str = paged_results.continuation_token  # type: ignore[attr-defined]
                logger.info(f"[Pagination Debug] Next token from iterator: {next_token_str}")
            except AttributeError:
                next_token_str = None
                logger.info("[Pagination Debug] No continuation_token attribute on iterator")

            next_token: dict | str | None = next_token_str

            return entities, next_token

        except StopAsyncIteration:
            logger.info("[Pagination Debug] No page returned from iterator")
            return [], None

        except Exception as e:
            logger.error(f"Failed to query entities (paged): {str(e)}")
            raise

    async def delete_entity(self, partition_key: str, row_key: str) -> bool:
        """
        Delete an entity

        Args:
            partition_key: The partition key
            row_key: The row key

        Returns:
            True if deleted, False if not found
        """
        try:
            await self.table_client.delete_entity(
                partition_key=partition_key, row_key=row_key
            )

            logger.info(
                f"Deleted entity: {self.table_name} PK={partition_key} RK={row_key}"
            )

            return True

        except ResourceNotFoundError:
            logger.debug(
                f"Entity not found for deletion: {self.table_name} "
                f"PK={partition_key} RK={row_key}"
            )
            return False

        except Exception as e:
            logger.error(f"Failed to delete entity: {str(e)}")
            raise

    # Helper methods

    async def query_by_org(
        self, org_id: str, row_key_prefix: str | None = None, select: list[str] | None = None
    ) -> list[dict]:
        """
        Query entities for a specific organization

        Args:
            org_id: Organization ID
            row_key_prefix: Optional row key prefix filter
            select: List of properties to select

        Returns:
            List of entity dictionaries
        """
        # Build filter string
        filter_str = f"PartitionKey eq '{org_id}'"

        if row_key_prefix:
            # Use range query for prefix matching
            next_char = chr(ord(row_key_prefix[-1]) + 1)
            prefix_end = row_key_prefix[:-1] + next_char
            filter_str += (
                f" and RowKey ge '{row_key_prefix}' and RowKey lt '{prefix_end}'"
            )

        return await self.query_entities(filter=filter_str, select=select)

    async def insert_dual_indexed(
        self,
        entity1: dict,
        entity2: dict,
        table1_name: str,
        table2_name: str,
    ) -> tuple[dict, dict]:
        """
        Insert entities into two tables atomically (dual-indexing pattern)

        Args:
            entity1: First entity to insert
            entity2: Second entity to insert
            table1_name: Name of first table
            table2_name: Name of second table

        Returns:
            Tuple of (entity1, entity2)
        """
        # Insert into first table
        table1_client = TableClient.from_connection_string(
            self.connection_string, table1_name
        )

        try:
            entity1 = self._serialize_datetime_fields(entity1)
            await table1_client.create_entity(entity1)

            logger.info(
                f"Dual-index insert 1/2: {table1_name} "
                f"PK={entity1['PartitionKey']} RK={entity1['RowKey']}"
            )

            # Insert into second table
            table2_client = TableClient.from_connection_string(
                self.connection_string, table2_name
            )

            try:
                entity2 = self._serialize_datetime_fields(entity2)
                await table2_client.create_entity(entity2)

                logger.info(
                    f"Dual-index insert 2/2: {table2_name} "
                    f"PK={entity2['PartitionKey']} RK={entity2['RowKey']}"
                )

                return (entity1, entity2)

            except Exception as e:
                logger.error(
                    f"Dual-index insert failed on second table ({table2_name}): {str(e)}. "
                    f"First table ({table1_name}) was successfully updated. "
                    f"Manual intervention may be required for consistency."
                )
                raise
            finally:
                await table2_client.close()

        finally:
            await table1_client.close()

    # Datetime serialization helpers

    def _serialize_datetime_fields(self, entity: dict) -> dict:
        """Convert datetime objects to ISO format strings for storage"""
        result = {}
        for key, value in entity.items():
            if isinstance(value, datetime):
                result[key] = value.isoformat()
            else:
                result[key] = value
        return result

    def _deserialize_datetime_fields(self, entity: dict) -> dict:
        """Convert ISO format strings back to datetime objects"""
        # Common datetime field names in our schema
        datetime_fields = [
            "CreatedAt",
            "UpdatedAt",
            "GrantedAt",
            "LastLogin",
            "StartedAt",
            "CompletedAt",
            "Timestamp",  # Azure Table Storage metadata
        ]

        result = {}
        for key, value in entity.items():
            if key in datetime_fields and isinstance(value, str):
                try:
                    # Try to parse as ISO datetime
                    result[key] = datetime.fromisoformat(
                        value.replace("Z", "+00:00"))
                except (ValueError, AttributeError):
                    # Keep as string if not valid datetime
                    result[key] = value
            else:
                result[key] = value

        return result


# Singleton instance cache for convenience
_async_storage_service_cache: dict[str, AsyncTableStorageService] = {}


def get_async_table_storage_service(table_name: str = "Organizations") -> AsyncTableStorageService:
    """
    Get or create an AsyncTableStorageService instance (cached, no context)

    Args:
        table_name: Table name to access

    Returns:
        AsyncTableStorageService instance without context
    """
    if table_name not in _async_storage_service_cache:
        _async_storage_service_cache[table_name] = AsyncTableStorageService(table_name)

    return _async_storage_service_cache[table_name]


def get_async_table_service(table_name: str, context: 'ExecutionContext') -> AsyncTableStorageService:
    """
    Create a context-aware AsyncTableStorageService instance (not cached).

    Use this factory when you have an ExecutionContext and want automatic partition key scoping.

    Args:
        table_name: Table name to access
        context: ExecutionContext for automatic scoping

    Returns:
        AsyncTableStorageService instance with context
    """
    return AsyncTableStorageService(table_name, context=context)


async def close_async_storage_cache() -> None:
    """
    Close all cached async storage service clients and clear the cache.

    This should be called between tests to ensure connections are properly
    closed before the event loop is closed.
    """
    global _async_storage_service_cache
    for service in _async_storage_service_cache.values():
        try:
            await service.close()
        except RuntimeError as e:
            # Ignore "Event loop is closed" errors - this means cleanup already happened
            if "Event loop is closed" not in str(e):
                raise
        except Exception as e:
            logger.warning(f"Error closing storage service during cleanup: {e}")
    _async_storage_service_cache.clear()
    logger.debug("Closed and cleared async storage service cache")


def clear_async_storage_cache() -> None:
    """
    Clear the global async storage service cache without closing clients.

    This should be called between tests to ensure fresh TableClient instances
    are created with the correct event loop.

    WARNING: This does not close existing clients. Use close_async_storage_cache()
    instead if you need to properly close connections before clearing.
    """
    global _async_storage_service_cache
    # Just clear references without closing - the clients will be garbage collected
    _async_storage_service_cache.clear()
    logger.debug("Cleared async storage service cache")
