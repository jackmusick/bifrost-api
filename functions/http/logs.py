"""
System Logs API endpoints

Provides access to system log entries (platform events, not workflow executions).
Admin-only access.
"""

import json
import logging
from datetime import datetime

import azure.functions as func

from shared.decorators import with_request_context
from shared.handlers.logs_handlers import list_system_logs_handler, get_system_log_handler
from shared.models import SystemLog, SystemLogsListResponse, ErrorResponse
from shared.openapi_decorators import openapi_endpoint

logger = logging.getLogger(__name__)


class DateTimeEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles datetime objects."""
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


# Create blueprint for logs endpoints
bp = func.Blueprint()


@bp.function_name("logs_list")
@bp.route(route="logs", methods=["GET"])
@openapi_endpoint(
    path="/logs",
    method="GET",
    summary="List system logs",
    description="List system log entries with filtering and pagination. Admin-only access. Logs include platform events like discovery failures, entity CRUD operations, etc.",
    tags=["System Logs"],
    response_model=SystemLogsListResponse,
    query_params={
        "category": {
            "description": "Filter by event category",
            "schema": {"type": "string", "enum": ["discovery", "organization", "user", "role", "config", "secret", "form", "oauth", "execution", "system", "error"]},
            "required": False
        },
        "level": {
            "description": "Filter by severity level",
            "schema": {"type": "string", "enum": ["info", "warning", "error", "critical"]},
            "required": False
        },
        "startDate": {
            "description": "Filter by start date (ISO format, inclusive)",
            "schema": {"type": "string", "format": "date-time"},
            "required": False
        },
        "endDate": {
            "description": "Filter by end date (ISO format, inclusive)",
            "schema": {"type": "string", "format": "date-time"},
            "required": False
        },
        "limit": {
            "description": "Maximum number of results (default: 50, max: 1000)",
            "schema": {"type": "integer", "minimum": 1, "maximum": 1000},
            "required": False
        },
        "continuationToken": {
            "description": "Continuation token from previous page for pagination",
            "schema": {"type": "string"},
            "required": False
        }
    }
)
@with_request_context
async def list_logs(req: func.HttpRequest) -> func.HttpResponse:
    """
    GET /api/logs

    Query parameters:
    - category: Filter by category (optional)
    - level: Filter by level (optional)
    - startDate: Filter by start date (ISO format, inclusive, optional)
    - endDate: Filter by end date (ISO format, inclusive, optional)
    - limit: Max results (optional, default 50, max 1000)
    - continuationToken: Pagination token (optional)

    Returns: List of system log entries (admin-only)
    """
    try:
        context = req.context  # type: ignore[attr-defined]

        # Admin-only access
        if not context.is_platform_admin:
            logger.warning(f"User {context.user_id} attempted to access logs without admin privileges")
            error = ErrorResponse(error="Forbidden", message="Admin access required")
            return func.HttpResponse(
                body=error.model_dump_json(),
                status_code=403,
                mimetype="application/json"
            )

        # Get query parameters
        category = req.params.get('category')
        level = req.params.get('level')
        start_date = req.params.get('startDate')
        end_date = req.params.get('endDate')
        limit = int(req.params.get('limit', '50'))
        continuation_token = req.params.get('continuationToken')

        logger.info(
            f"User {context.user_id} listing system logs: "
            f"category={category}, level={level}, limit={limit}"
        )

        # Call handler
        result, status_code = await list_system_logs_handler(
            category=category,
            level=level,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
            continuation_token=continuation_token
        )

        # Return response
        if isinstance(result, SystemLogsListResponse):
            return func.HttpResponse(
                body=result.model_dump_json(),
                status_code=status_code,
                mimetype="application/json"
            )
        else:
            # Error response
            return func.HttpResponse(
                body=result.model_dump_json(),
                status_code=status_code,
                mimetype="application/json"
            )

    except Exception as e:
        logger.error(f"Error in list_logs endpoint: {str(e)}", exc_info=True)
        error = ErrorResponse(error="InternalServerError", message="Failed to list system logs")
        return func.HttpResponse(
            body=error.model_dump_json(),
            status_code=500,
            mimetype="application/json"
        )


@bp.function_name("logs_get")
@bp.route(route="logs/{category}/{row_key}", methods=["GET"])
@openapi_endpoint(
    path="/logs/{category}/{row_key}",
    method="GET",
    summary="Get system log entry",
    description="Get a single system log entry by category and row key. Admin-only access.",
    tags=["System Logs"],
    response_model=SystemLog,
    path_params={
        "category": {
            "description": "Event category (partition key)",
            "schema": {"type": "string"},
            "required": True
        },
        "row_key": {
            "description": "Row key (timestamp_eventId)",
            "schema": {"type": "string"},
            "required": True
        }
    }
)
@with_request_context
async def get_log(req: func.HttpRequest) -> func.HttpResponse:
    """
    GET /api/logs/{category}/{row_key}

    Path parameters:
    - category: Event category (partition key)
    - row_key: Row key (timestamp_eventId)

    Returns: Single system log entry (admin-only)
    """
    try:
        context = req.context  # type: ignore[attr-defined]

        # Admin-only access
        if not context.is_platform_admin:
            logger.warning(f"User {context.user_id} attempted to access log without admin privileges")
            error = ErrorResponse(error="Forbidden", message="Admin access required")
            return func.HttpResponse(
                body=error.model_dump_json(),
                status_code=403,
                mimetype="application/json"
            )

        # Get path parameters
        category = req.route_params.get('category')
        row_key = req.route_params.get('row_key')

        if not category or not row_key:
            error = ErrorResponse(error="BadRequest", message="Category and row_key are required")
            return func.HttpResponse(
                body=error.model_dump_json(),
                status_code=400,
                mimetype="application/json"
            )

        logger.info(f"User {context.user_id} retrieving system log: {category}/{row_key}")

        # Call handler
        result, status_code = await get_system_log_handler(
            category=category,
            row_key=row_key
        )

        # Return response
        if isinstance(result, SystemLog):
            return func.HttpResponse(
                body=result.model_dump_json(),
                status_code=status_code,
                mimetype="application/json"
            )
        else:
            # Error response
            return func.HttpResponse(
                body=result.model_dump_json(),
                status_code=status_code,
                mimetype="application/json"
            )

    except Exception as e:
        logger.error(f"Error in get_log endpoint: {str(e)}", exc_info=True)
        error = ErrorResponse(error="InternalServerError", message="Failed to retrieve system log")
        return func.HttpResponse(
            body=error.model_dump_json(),
            status_code=500,
            mimetype="application/json"
        )
