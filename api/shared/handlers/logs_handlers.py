"""
System Logs handlers - business logic for viewing system logs
Provides handlers for listing and retrieving system log entries
"""

import base64
import json
import logging
from datetime import datetime

from shared.async_storage import AsyncTableStorageService
from src.models.schemas import SystemLog, SystemLogsListResponse, ErrorResponse

logger = logging.getLogger(__name__)


async def list_system_logs_handler(
    category: str | None = None,
    level: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    limit: int = 50,
    continuation_token: str | None = None,
    connection_string: str | None = None
) -> tuple[SystemLogsListResponse | ErrorResponse, int]:
    """
    List system logs with filtering and pagination.

    Args:
        category: Optional filter by category (discovery, organization, user, etc.)
        level: Optional filter by level (info, warning, error, critical)
        start_date: Optional filter by start date (ISO format, inclusive)
        end_date: Optional filter by end date (ISO format, inclusive)
        limit: Maximum number of results (default 50, max 1000)
        continuation_token: Opaque continuation token from previous page
        connection_string: Database connection string (defaults to env var)

    Returns:
        Tuple of (SystemLogsListResponse, HTTP status code)
    """
    import os

    try:
        # Cap limit at 1000
        limit = min(limit, 1000)

        # Get connection string
        conn_str = connection_string or os.environ.get("AzureWebJobsStorage", "UseDevelopmentStorage=true")

        # Decode continuation token if provided
        decoded_token = None
        if continuation_token:
            try:
                decoded_str = base64.b64decode(continuation_token).decode('utf-8')
                # Try to parse as JSON (dict), otherwise use as string
                try:
                    decoded_token = json.loads(decoded_str)
                except json.JSONDecodeError:
                    decoded_token = decoded_str
                logger.debug("Using continuation token for pagination")
            except Exception as e:
                logger.warning(f"Invalid continuation token provided, ignoring: {e}")
                decoded_token = None

        # Build query filter
        filter_parts = []

        # Filter by category if provided
        if category:
            filter_parts.append(f"PartitionKey eq '{category}'")

        # Filter by level if provided (need to query and filter in memory since Level is not partition/row key)
        # Note: For better performance at scale, consider adding a composite index

        # Filter by date range (RowKey contains timestamp)
        if start_date:
            try:
                start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                filter_parts.append(f"RowKey ge '{start_dt.isoformat()}'")
            except ValueError:
                logger.warning(f"Invalid start_date format: {start_date}")

        if end_date:
            try:
                end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                filter_parts.append(f"RowKey le '{end_dt.isoformat()}_zzzzzzzz'")  # zzzz ensures we get all logs before this timestamp
            except ValueError:
                logger.warning(f"Invalid end_date format: {end_date}")

        # Build query filter - empty string means no filter in Azure Tables
        query_filter_str: str = " and ".join(filter_parts) if filter_parts else ""
        if query_filter_str:
            logger.info(f"Querying system logs with filter: {query_filter_str}, limit: {limit}")
        else:
            logger.info(f"Querying system logs with no filter, limit: {limit}")

        # Query Table Storage using async service
        service = AsyncTableStorageService("SystemLogs", connection_string=conn_str)

        # Query with pagination
        entities, next_token = await service.query_entities_paged(
            filter=query_filter_str if query_filter_str else None,
            results_per_page=limit,
            continuation_token=decoded_token
        )

        # Parse entities to SystemLog models
        logs = []
        for entity in entities:
            # Filter by level in memory if specified
            if level and entity.get("Level") != level:
                continue

            try:
                # Parse details JSON
                details = None
                if entity.get("Details"):
                    details = json.loads(entity["Details"])

                # Get timestamp from TimestampISO field (new format) or parse from RowKey (old format)
                if entity.get("TimestampISO"):
                    timestamp = datetime.fromisoformat(entity["TimestampISO"])
                else:
                    # Legacy format: extract from RowKey
                    row_key = entity["RowKey"]
                    timestamp_str = row_key.split("_")[0]
                    timestamp = datetime.fromisoformat(timestamp_str)

                log = SystemLog(
                    eventId=entity["EventId"],
                    timestamp=timestamp,
                    category=entity["PartitionKey"],
                    level=entity["Level"],
                    message=entity["Message"],
                    executedBy=entity["ExecutedBy"],
                    executedByName=entity["ExecutedByName"],
                    details=details
                )
                logs.append(log)
            except Exception as e:
                logger.error(f"Failed to parse log entity: {e}", exc_info=True)
                continue

        # Encode continuation token for client
        encoded_token = None
        if next_token:
            # Continuation token is a dict, convert to JSON string first
            token_str = json.dumps(next_token) if isinstance(next_token, dict) else next_token
            encoded_token = base64.b64encode(token_str.encode('utf-8')).decode('utf-8')

        logger.info(f"Returning {len(logs)} system logs, has_more={encoded_token is not None}")

        response = SystemLogsListResponse(
            logs=logs,
            continuationToken=encoded_token
        )

        return response, 200

    except Exception as e:
        logger.error(f"Error listing system logs: {str(e)}", exc_info=True)
        error = ErrorResponse(error="InternalServerError", message="Failed to list system logs")
        # Return error as dict with status code
        return error, 500


async def get_system_log_handler(
    category: str,
    row_key: str,
    connection_string: str | None = None
) -> tuple[SystemLog | ErrorResponse, int]:
    """
    Get a single system log entry by category (partition key) and row key.

    Args:
        category: Event category (partition key)
        row_key: Row key (timestamp_eventId)
        connection_string: Database connection string (defaults to env var)

    Returns:
        Tuple of (SystemLog or ErrorResponse, HTTP status code)
    """
    import os

    try:
        # Get connection string
        conn_str = connection_string or os.environ.get("AzureWebJobsStorage", "UseDevelopmentStorage=true")

        # Query Table Storage using async service
        service = AsyncTableStorageService("SystemLogs", connection_string=conn_str)

        # Get entity
        entity = await service.get_entity(partition_key=category, row_key=row_key)

        # Handle not found case
        if entity is None:
            logger.warning(f"System log not found: {category}/{row_key}")
            error = ErrorResponse(error="NotFound", message="System log not found")
            return error, 404

        # Parse details JSON
        details = None
        if entity.get("Details"):
            details = json.loads(entity["Details"])

        # Get timestamp from TimestampISO field (new format) or parse from RowKey (old format)
        if entity.get("TimestampISO"):
            timestamp = datetime.fromisoformat(entity["TimestampISO"])
        else:
            # Legacy format: extract from RowKey
            timestamp_str = row_key.split("_")[0]
            timestamp = datetime.fromisoformat(timestamp_str)

        log = SystemLog(
            eventId=entity["EventId"],
            timestamp=timestamp,
            category=entity["PartitionKey"],
            level=entity["Level"],
            message=entity["Message"],
            executedBy=entity["ExecutedBy"],
            executedByName=entity["ExecutedByName"],
            details=details
        )

        logger.info(f"Retrieved system log: {category}/{row_key}")
        return log, 200

    except Exception as e:
        if "ResourceNotFound" in str(type(e).__name__):
            logger.warning(f"System log not found: {category}/{row_key}")
            error = ErrorResponse(error="NotFound", message="System log not found")
            return error, 404

        logger.error(f"Error retrieving system log: {str(e)}", exc_info=True)
        error = ErrorResponse(error="InternalServerError", message="Failed to retrieve system log")
        return error, 500
