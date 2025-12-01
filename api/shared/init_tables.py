"""
Table initialization script for Bifrost Integrations
Creates all required Azure Table Storage tables for both local (Azurite) and production

Run this script once during initial setup or after resetting Azurite
"""

import logging
import os

from azure.core.exceptions import ResourceExistsError
from azure.data.tables import TableServiceClient

# Table names (consolidated from 14 → 3 tables + SystemLogs + ExecutionLogs)
REQUIRED_TABLES = [
    "Config",        # Consolidated: Config + IntegrationConfig + SystemConfig + OAuth metadata/secrets
                     # PartitionKey: org_id (UUID) or "GLOBAL" or "SYSTEM"
                     # RowKey: config:{key}, oauth_{name}_metadata, oauth_{name}_client_secret, oauth_{name}_oauth_response, jobstatus:{JobName}

    "Entities",      # Consolidated: Organizations + Forms + WorkflowExecutions + AuditLog
                     # PartitionKey: org_id (UUID) or "GLOBAL"
                     # RowKey: org:{uuid}, form:{uuid}, execution:{reverse_ts}_{uuid}, audit:{reverse_ts}_{uuid}

    "Relationships", # Consolidated: Roles + UserRoles + FormRoles + UserPermissions + OrgPermissions + UserExecutions
                     # PartitionKey: "GLOBAL" (all relationships in one partition)
                     # RowKey: role:{uuid}, assignedrole:{uuid}:{id}, userrole:{id}:{uuid}, formrole:{uuid}:{uuid}, etc.

    "SystemLogs",    # Platform-level event logging (not workflow executions)
                     # PartitionKey: event_category (discovery, organization, user, config, secret, form, oauth, execution, system, error)
                     # RowKey: {timestamp}_{eventId} (chronological ordering)

    "ExecutionLogs", # Real-time execution logs for workflows
                     # PartitionKey: execution_id (UUID) - all logs for one execution in same partition
                     # RowKey: {iso_timestamp}-{sequence} (chronological ordering with sub-millisecond resolution)
                     # Each log has ExecutionLogId (UUID) for client-side deduplication
]

logger = logging.getLogger(__name__)


def init_tables(connection_string: str | None = None) -> dict:
    """
    Initialize all required Azure Table Storage tables

    Args:
        connection_string: Azure Storage connection string
                          Defaults to AzureWebJobsStorage env var

    Returns:
        dict: Summary of table creation results
    """
    if connection_string is None:
        connection_string = os.environ.get("AzureWebJobsStorage")

    if not connection_string:
        raise ValueError(
            "AzureWebJobsStorage environment variable not set")

    logger.info("Initializing Azure Table Storage tables...")
    logger.info(f"Connection: {_mask_connection_string(connection_string)}")

    assert connection_string is not None, "connection_string is None"
    service_client = TableServiceClient.from_connection_string(
        connection_string)

    results = {
        "created": [],
        "already_exists": [],
        "failed": []
    }

    for table_name in REQUIRED_TABLES:
        try:
            # Check if table already exists
            tables = list(service_client.query_tables(
                f"TableName eq '{table_name}'"))

            if tables:
                logger.info(f"✓ Table '{table_name}' already exists")
                results["already_exists"].append(table_name)
            else:
                # Create table
                service_client.create_table(table_name)
                logger.info(f"✓ Created table '{table_name}'")
                results["created"].append(table_name)

        except ResourceExistsError:
            # Race condition - table was created between check and create
            logger.info(f"✓ Table '{table_name}' already exists")
            results["already_exists"].append(table_name)

        except Exception as e:
            logger.error(f"✗ Failed to create table '{table_name}': {str(e)}")
            results["failed"].append({"table": table_name, "error": str(e)})

    # Summary
    logger.info("\n" + "="*60)
    logger.info("Table Initialization Summary")
    logger.info("="*60)
    logger.info(f"Created: {len(results['created'])} tables")
    if results["created"]:
        for table in results["created"]:
            logger.info(f"  - {table}")

    logger.info(f"\nAlready existed: {len(results['already_exists'])} tables")
    if results["already_exists"]:
        for table in results["already_exists"]:
            logger.info(f"  - {table}")

    if results["failed"]:
        logger.error(f"\nFailed: {len(results['failed'])} tables")
        for failure in results["failed"]:
            logger.error(f"  - {failure['table']}: {failure['error']}")

    logger.info("="*60 + "\n")

    return results


def _mask_connection_string(conn_str: str) -> str:
    """Mask sensitive parts of connection string for logging"""
    if "UseDevelopmentStorage=true" in conn_str:
        return "UseDevelopmentStorage=true (Azurite)"

    # Mask the account key
    if "AccountKey=" in conn_str:
        parts = conn_str.split("AccountKey=")
        if len(parts) == 2:
            key_part = parts[1].split(";")[0]
            masked_key = key_part[:8] + "..." + \
                key_part[-4:] if len(key_part) > 12 else "***"
            return conn_str.replace(key_part, masked_key)

    return conn_str


# CLI support - can run directly
if __name__ == "__main__":
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Allow override via command line argument
    conn_str: str | None = sys.argv[1] if len(sys.argv) > 1 else None

    try:
        results = init_tables(conn_str)

        # Exit code based on failures
        if results["failed"]:
            sys.exit(1)
        else:
            sys.exit(0)

    except Exception as e:
        logger.error(f"Fatal error during table initialization: {str(e)}")
        sys.exit(1)
