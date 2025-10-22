"""
Clear all data from Bifrost Integrations tables
Deletes all entities from all tables (development storage only)
"""

import logging
import sys

from azure.data.tables import TableClient

logger = logging.getLogger(__name__)

# Table names
TABLE_NAMES = ["Config", "Entities", "Relationships", "Users"]


def is_development_storage(connection_string: str) -> bool:
    """Check if using development storage (Azurite)"""
    return "UseDevelopmentStorage=true" in connection_string or "devstoreaccount1" in connection_string


def clear_all_tables(connection_string: str):
    """Clear all entities from all tables (development storage only)"""
    if not is_development_storage(connection_string):
        logger.error("⚠️  REFUSING TO CLEAR - Not using development storage!")
        logger.error(
            "    This script only works with Azurite (local development)")
        sys.exit(1)

    logger.info("Clearing all tables (development storage only)...")
    logger.info("="*60)

    total_deleted = 0

    for table_name in TABLE_NAMES:
        try:
            table_client = TableClient.from_connection_string(
                connection_string, table_name)

            # Query all entities
            entities = list(table_client.query_entities(query_filter=""))
            entity_count = len(entities)

            if entity_count == 0:
                logger.info(f"  ⊘ {table_name}: Already empty")
                continue

            # Delete all entities
            deleted = 0
            for entity in entities:
                try:
                    table_client.delete_entity(
                        partition_key=entity['PartitionKey'],
                        row_key=entity['RowKey']
                    )
                    deleted += 1
                except Exception as e:
                    logger.warning(f"    ⚠️  Error deleting entity: {e}")

            total_deleted += deleted
            logger.info(f"  ✓ {table_name}: Deleted {deleted} entities")

        except Exception as e:
            if "TableNotFound" in str(e) or "ResourceNotFound" in str(e):
                logger.info(f"  ⊘ {table_name}: Table doesn't exist")
            else:
                logger.error(f"  ✗ {table_name}: Error - {e}")

    logger.info("="*60)
    logger.info(f"Total: {total_deleted} entities deleted")
    logger.info("="*60)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(message)s"
    )

    # Get connection string from environment or command line
    connection_string = "UseDevelopmentStorage=true"

    if not connection_string:
        logger.error("Error: No connection string provided")
        logger.error("Usage: python clear_data.py [connection_string]")
        logger.error("   Or: Set AzureWebJobsStorage environment variable")
        sys.exit(1)

    try:
        clear_all_tables(connection_string)
        logger.info("\n✓ All tables cleared successfully")
        sys.exit(0)
    except Exception as e:
        logger.error(f"\n✗ Fatal error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
