"""
Table Storage Service for Bifrost Integrations
Provides reusable wrappers around Azure Table Storage operations
"""

import os
import logging
from typing import List, Optional, Dict, Any, Iterator
from datetime import datetime
from azure.data.tables import TableClient, TableServiceClient
from azure.core.exceptions import ResourceNotFoundError, ResourceExistsError

logger = logging.getLogger(__name__)


class TableStorageService:
    """
    Base class for Azure Table Storage operations
    Provides org-scoped query helpers and common CRUD operations
    """

    def __init__(self, table_name: str, connection_string: str = None):
        """
        Initialize Table Storage client

        Args:
            table_name: Name of the table to work with
            connection_string: Optional connection string override
        """
        self.table_name = table_name

        if connection_string is None:
            connection_string = os.environ.get(
                "TABLE_STORAGE_CONNECTION_STRING")

        if not connection_string:
            raise ValueError(
                "TABLE_STORAGE_CONNECTION_STRING environment variable not set")

        self.connection_string = connection_string
        self.table_client = TableClient.from_connection_string(
            connection_string, table_name
        )

        logger.debug(
            f"TableStorageService initialized for table: {table_name}")

    def insert_entity(self, entity: dict) -> dict:
        """
        Insert a new entity into the table

        Args:
            entity: Entity dictionary with PartitionKey and RowKey

        Returns:
            The inserted entity with metadata

        Raises:
            ResourceExistsError: If entity already exists
            ValueError: If PartitionKey or RowKey is missing
        """
        if "PartitionKey" not in entity or "RowKey" not in entity:
            raise ValueError("Entity must have PartitionKey and RowKey")

        try:
            # Serialize datetime fields
            entity = self._serialize_datetime_fields(entity)

            # Insert entity
            self.table_client.create_entity(entity)

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

    def update_entity(self, entity: dict, mode: str = "merge") -> dict:
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
        if "PartitionKey" not in entity or "RowKey" not in entity:
            raise ValueError("Entity must have PartitionKey and RowKey")

        try:
            # Serialize datetime fields
            entity = self._serialize_datetime_fields(entity)

            # Update entity
            if mode == "replace":
                self.table_client.update_entity(entity, mode="replace")
            else:
                self.table_client.update_entity(entity, mode="merge")

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

    def upsert_entity(self, entity: dict, mode: str = "merge") -> dict:
        """
        Insert or update an entity (creates if doesn't exist)

        Args:
            entity: Entity dictionary with PartitionKey and RowKey
            mode: Update mode - "merge" (default) or "replace"

        Returns:
            The upserted entity
        """
        if "PartitionKey" not in entity or "RowKey" not in entity:
            raise ValueError("Entity must have PartitionKey and RowKey")

        try:
            # Serialize datetime fields
            entity = self._serialize_datetime_fields(entity)

            # Upsert entity
            if mode == "replace":
                self.table_client.upsert_entity(entity, mode="replace")
            else:
                self.table_client.upsert_entity(entity, mode="merge")

            logger.info(
                f"Upserted entity ({mode}): {self.table_name} "
                f"PK={entity['PartitionKey']} RK={entity['RowKey']}"
            )

            return entity

        except Exception as e:
            logger.error(f"Failed to upsert entity: {str(e)}")
            raise

    def get_entity(self, partition_key: str, row_key: str) -> Optional[dict]:
        """
        Retrieve a single entity by partition and row key

        Args:
            partition_key: The partition key
            row_key: The row key

        Returns:
            Entity dictionary or None if not found
        """
        try:
            entity = self.table_client.get_entity(
                partition_key=partition_key, row_key=row_key
            )

            # Deserialize datetime fields
            entity = self._deserialize_datetime_fields(dict(entity))

            logger.debug(
                f"Retrieved entity: {self.table_name} PK={partition_key} RK={row_key}"
            )

            return entity

        except ResourceNotFoundError:
            logger.debug(
                f"Entity not found: {self.table_name} PK={partition_key} RK={row_key}"
            )
            return None

        except Exception as e:
            logger.error(f"Failed to get entity: {str(e)}")
            raise

    def query_entities(
        self, filter: str = None, select: List[str] = None
    ) -> Iterator[dict]:
        """
        Query entities with optional filter and select

        Args:
            filter: OData filter string (e.g., "PartitionKey eq 'ORG'")
            select: List of properties to select

        Returns:
            Iterator of entity dictionaries
        """
        try:
            # Query entities using positional argument for filter
            if filter:
                entities = self.table_client.query_entities(
                    query_filter=filter,
                    select=select
                )
            else:
                entities = self.table_client.query_entities(select=select)

            # Yield deserialized entities
            for entity in entities:
                yield self._deserialize_datetime_fields(dict(entity))

        except Exception as e:
            logger.error(f"Failed to query entities: {str(e)}")
            raise

    def delete_entity(self, partition_key: str, row_key: str) -> bool:
        """
        Delete an entity

        Args:
            partition_key: The partition key
            row_key: The row key

        Returns:
            True if deleted, False if not found
        """
        try:
            self.table_client.delete_entity(
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

    def query_by_org(
        self, org_id: str, row_key_prefix: str = None, select: List[str] = None
    ) -> Iterator[dict]:
        """
        Query entities for a specific organization

        Args:
            org_id: Organization ID
            row_key_prefix: Optional row key prefix filter
            select: List of properties to select

        Returns:
            Iterator of entity dictionaries
        """
        # Build filter string
        filter_str = f"PartitionKey eq '{org_id}'"

        if row_key_prefix:
            # Use range query for prefix matching
            # e.g., "config:" matches "config:key1", "config:key2", etc.
            next_char = chr(ord(row_key_prefix[-1]) + 1)
            prefix_end = row_key_prefix[:-1] + next_char
            filter_str += (
                f" and RowKey ge '{row_key_prefix}' and RowKey lt '{prefix_end}'"
            )

        return self.query_entities(filter=filter_str, select=select)

    def insert_dual_indexed(
        self,
        entity1: dict,
        entity2: dict,
        table1_name: str,
        table2_name: str,
    ) -> tuple[dict, dict]:
        """
        Insert entities into two tables atomically (dual-indexing pattern)

        Used for UserPermissions/OrgPermissions and WorkflowExecutions/UserExecutions

        Args:
            entity1: First entity to insert
            entity2: Second entity to insert
            table1_name: Name of first table
            table2_name: Name of second table

        Returns:
            Tuple of (entity1, entity2)

        Note: This is "best effort" atomic - not true transaction.
              If second insert fails, first is NOT rolled back.
        """
        # Insert into first table
        table1_client = TableClient.from_connection_string(
            self.connection_string, table1_name
        )

        entity1 = self._serialize_datetime_fields(entity1)
        table1_client.create_entity(entity1)

        logger.info(
            f"Dual-index insert 1/2: {table1_name} "
            f"PK={entity1['PartitionKey']} RK={entity1['RowKey']}"
        )

        try:
            # Insert into second table
            table2_client = TableClient.from_connection_string(
                self.connection_string, table2_name
            )

            entity2 = self._serialize_datetime_fields(entity2)
            table2_client.create_entity(entity2)

            logger.info(
                f"Dual-index insert 2/2: {table2_name} "
                f"PK={entity2['PartitionKey']} RK={entity2['RowKey']}"
            )

            return (entity1, entity2)

        except Exception as e:
            # Second insert failed - log warning but don't rollback first
            logger.error(
                f"Dual-index insert failed on second table ({table2_name}): {str(e)}. "
                f"First table ({table1_name}) was successfully updated. "
                f"Manual intervention may be required for consistency."
            )
            raise

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
