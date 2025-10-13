"""
Workflow Engine Proxy Endpoints
- Proxy requests to the workflows engine with authorization
- Validate workflows engine configuration
"""

import logging
import json
import os
import requests
from typing import Optional
import azure.functions as func

from shared.auth import require_auth, is_platform_admin, has_form_access
from shared.models import ErrorResponse
from shared.auth_headers import get_scope_context
from functions.org_config import get_config_value

logger = logging.getLogger(__name__)

# Create blueprint for workflow proxy endpoints
bp = func.Blueprint()


def get_workflows_engine_config() -> tuple[Optional[str], Optional[str]]:
    """
    Get workflows engine URL and function key

    For URL:
    - Uses environment variable WORKFLOWS_ENGINE_URL if set
    - Falls back to http://localhost:7072 for local development
    - Can be overridden by global config 'workflows_engine_url'

    For function key:
    - Uses environment variable WORKFLOWS_ENGINE_FUNCTION_KEY if set
    - Otherwise reads from global config 'workflows_engine_function_key'

    Returns:
        Tuple of (url, function_key) or (url, None) if key not configured
    """
    # Get URL - environment var > config > default
    url = os.environ.get("WORKFLOWS_ENGINE_URL")
    if not url:
        url_config = get_config_value("workflows_engine_url")
        if url_config:
            url = url_config.get("Value")
        else:
            # Default for local development
            url = "http://localhost:7072"

    url = url.rstrip("/") if url else None

    # Get function key - environment var > config
    function_key = os.environ.get("WORKFLOWS_ENGINE_FUNCTION_KEY")
    if not function_key:
        key_config = get_config_value("workflows_engine_function_key")
        if key_config:
            function_key = key_config.get("Value")

    return url, function_key


@bp.function_name("workflows_validate_engine")
@bp.route(route="config/validate-workflows-engine", methods=["POST"])
@require_auth
def validate_workflows_engine(req: func.HttpRequest) -> func.HttpResponse:
    """
    POST /api/config/validate-workflows-engine
    Validate workflows engine configuration by testing health and metadata endpoints

    Request body:
    {
        "url": "http://localhost:7072",
        "functionKey": "your-function-key"
    }

    Returns:
    {
        "status": "healthy" | "failed",
        "error": "..." (if failed),
        "metadata": {...} (if healthy)
    }

    Authorization: SWA enforces PlatformAdmin role via /api/config* route
    """
    user = req.user

    logger.info(f"User {user.email} validating workflows engine configuration")

    try:

        # Parse request body
        request_body = req.get_json()
        url = request_body.get("url", "").rstrip("/")
        function_key = request_body.get("functionKey", "")

        if not url or not function_key:
            error = ErrorResponse(
                error="BadRequest",
                message="Both 'url' and 'functionKey' are required"
            )
            return func.HttpResponse(
                json.dumps(error.model_dump()),
                status_code=400,
                mimetype="application/json"
            )

        # Test 1: Health endpoint (anonymous, no key needed)
        try:
            health_response = requests.get(
                f"{url}/api/health",
                timeout=5
            )

            if health_response.status_code != 200:
                return func.HttpResponse(
                    json.dumps({
                        "status": "failed",
                        "error": f"Health endpoint returned {health_response.status_code}"
                    }),
                    status_code=200,
                    mimetype="application/json"
                )

            health_data = health_response.json()
            if health_data.get("service") != "Workflow Engine":
                return func.HttpResponse(
                    json.dumps({
                        "status": "failed",
                        "error": f"Health endpoint returned unexpected service: {health_data.get('service')}"
                    }),
                    status_code=200,
                    mimetype="application/json"
                )

            logger.info("Health endpoint check passed")

        except requests.exceptions.Timeout:
            return func.HttpResponse(
                json.dumps({
                    "status": "failed",
                    "error": "Health endpoint request timed out"
                }),
                status_code=200,
                mimetype="application/json"
            )
        except requests.exceptions.RequestException as e:
            return func.HttpResponse(
                json.dumps({
                    "status": "failed",
                    "error": f"Failed to connect to health endpoint: {str(e)}"
                }),
                status_code=200,
                mimetype="application/json"
            )

        # Test 2: Metadata endpoint (requires function key)
        try:
            metadata_response = requests.get(
                f"{url}/api/registry/metadata?code={function_key}",
                timeout=10
            )

            if metadata_response.status_code != 200:
                return func.HttpResponse(
                    json.dumps({
                        "status": "failed",
                        "error": f"Metadata endpoint returned {metadata_response.status_code}"
                    }),
                    status_code=200,
                    mimetype="application/json"
                )

            metadata = metadata_response.json()

            # Validate metadata structure
            if "workflows" not in metadata or "data_providers" not in metadata:
                return func.HttpResponse(
                    json.dumps({
                        "status": "failed",
                        "error": "Metadata endpoint returned invalid structure (missing 'workflows' or 'data_providers')"
                    }),
                    status_code=200,
                    mimetype="application/json"
                )

            logger.info(f"Metadata endpoint check passed - found {len(metadata.get('workflows', []))} workflows")

            # Success - workflows engine is healthy
            return func.HttpResponse(
                json.dumps({
                    "status": "healthy",
                    "metadata": metadata
                }),
                status_code=200,
                mimetype="application/json"
            )

        except requests.exceptions.Timeout:
            return func.HttpResponse(
                json.dumps({
                    "status": "failed",
                    "error": "Metadata endpoint request timed out"
                }),
                status_code=200,
                mimetype="application/json"
            )
        except requests.exceptions.RequestException as e:
            return func.HttpResponse(
                json.dumps({
                    "status": "failed",
                    "error": f"Failed to connect to metadata endpoint: {str(e)}"
                }),
                status_code=200,
                mimetype="application/json"
            )

    except ValueError as e:
        logger.error(f"Error parsing request: {str(e)}")
        error = ErrorResponse(
            error="BadRequest",
            message="Invalid JSON in request body"
        )
        return func.HttpResponse(
            json.dumps(error.model_dump()),
            status_code=400,
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Error validating workflows engine: {str(e)}", exc_info=True)
        error = ErrorResponse(
            error="InternalServerError",
            message="Failed to validate workflows engine"
        )
        return func.HttpResponse(
            json.dumps(error.model_dump()),
            status_code=500,
            mimetype="application/json"
        )


@bp.function_name("workflows_health")
@bp.route(route="workflows/health", methods=["GET"])
def workflows_health(req: func.HttpRequest) -> func.HttpResponse:
    """
    GET /api/workflows/health
    Check workflow engine health status

    This endpoint does NOT require authentication to allow health checks
    even when auth is broken.

    Returns:
    {
        "status": "healthy" | "unhealthy",
        "service": "Workflow Engine"
    }
    """
    try:
        # Get workflows engine config
        url, function_key = get_workflows_engine_config()

        # Call workflows engine health endpoint (no auth required)
        try:
            response = requests.get(
                f"{url}/api/health",
                timeout=5
            )

            if response.status_code != 200:
                return func.HttpResponse(
                    json.dumps({
                        "status": "unhealthy",
                        "service": "Workflow Engine"
                    }),
                    status_code=200,
                    mimetype="application/json"
                )

            health_data = response.json()
            return func.HttpResponse(
                json.dumps(health_data),
                status_code=200,
                mimetype="application/json"
            )

        except (requests.exceptions.Timeout, requests.exceptions.RequestException):
            return func.HttpResponse(
                json.dumps({
                    "status": "unhealthy",
                    "service": "Workflow Engine"
                }),
                status_code=200,
                mimetype="application/json"
            )

    except Exception as e:
        logger.error(f"Error checking workflows health: {str(e)}", exc_info=True)
        return func.HttpResponse(
            json.dumps({
                "status": "unhealthy",
                "service": "Workflow Engine"
            }),
            status_code=200,
            mimetype="application/json"
        )


@bp.function_name("workflows_get_metadata")
@bp.route(route="workflows/metadata", methods=["GET"])
@require_auth
def get_metadata(req: func.HttpRequest) -> func.HttpResponse:
    """
    GET /api/workflows/metadata
    Get all workflows and data providers metadata from workflows engine

    Requires: User must be authenticated
    Note: Metadata endpoint doesn't require org context
    """
    user = req.user

    logger.info(f"User {user.email} retrieving workflows metadata")

    try:
        # Get workflows engine config
        url, function_key = get_workflows_engine_config()

        # Call workflows engine
        try:
            # Build headers - only include function key if configured (not needed locally)
            headers = {}
            if function_key:
                headers["x-functions-key"] = function_key
                logger.info(f"Calling workflows engine: GET {url}/api/registry/metadata (with function key)")
            else:
                logger.info(f"Calling workflows engine: GET {url}/api/registry/metadata (no function key - local mode)")

            response = requests.get(
                f"{url}/api/registry/metadata",
                headers=headers,
                timeout=10
            )

            logger.info(f"Workflows engine response: {response.status_code}")
            if response.status_code != 200:
                logger.error(f"Workflows engine returned {response.status_code}: {response.text}")
                error = ErrorResponse(
                    error="ServiceUnavailable",
                    message="Failed to retrieve workflows metadata"
                )
                return func.HttpResponse(
                    json.dumps(error.model_dump()),
                    status_code=503,
                    mimetype="application/json"
                )

            metadata = response.json()
            logger.info(f"Retrieved metadata with {len(metadata.get('workflows', []))} workflows")

            return func.HttpResponse(
                json.dumps(metadata),
                status_code=200,
                mimetype="application/json"
            )

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to connect to workflows engine: {e}", exc_info=True)
            error = ErrorResponse(
                error="ServiceUnavailable",
                message="Failed to connect to workflows engine"
            )
            return func.HttpResponse(
                json.dumps(error.model_dump()),
                status_code=503,
                mimetype="application/json"
            )

    except Exception as e:
        logger.error(f"Error retrieving workflows metadata: {str(e)}", exc_info=True)
        error = ErrorResponse(
            error="InternalServerError",
            message="Failed to retrieve workflows metadata"
        )
        return func.HttpResponse(
            json.dumps(error.model_dump()),
            status_code=500,
            mimetype="application/json"
        )


@bp.function_name("workflows_execute")
@bp.route(route="workflows/{workflowName}", methods=["POST"])
@require_auth
def execute_workflow(req: func.HttpRequest) -> func.HttpResponse:
    """
    POST /api/workflows/{workflowName}
    Execute a workflow directly (not via form)

    Headers:
    - X-Organization-Id: Organization ID (optional - derived from user if not provided)
    - X-User-Id: User ID (optional - derived from auth if not provided)

    Request Body: Workflow parameters (JSON)

    Authorization: SWA enforces PlatformAdmin role before reaching this code

    Security:
    - Non-admin users: headers derived from database automatically
    - Admin users: can override headers to act on behalf of other users/orgs
    """
    user = req.user
    workflow_name = req.route_params.get("workflowName")

    logger.info(f"User {user.email} executing workflow {workflow_name}")

    try:
        # Get scope context - platform admins can have org_id=None for GLOBAL scope
        org_id, user_id, error = get_scope_context(req)
        if error:
            return error

        logger.info(f"Executing workflow with context: org={org_id or 'GLOBAL'}, user={user_id}")

        # Get workflows engine config
        url, function_key = get_workflows_engine_config()

        # Parse request body (workflow parameters)
        request_body = req.get_json()

        # Call workflows engine
        try:
            # Build URL - only add code parameter if function key is configured (not needed locally)
            workflow_url = f"{url}/api/workflows/{workflow_name}"
            if function_key:
                workflow_url += f"?code={function_key}"
                logger.info(f"Executing workflow with function key")
            else:
                logger.info(f"Executing workflow without function key (local mode)")

            # Build headers - only include X-Organization-Id if org_id is provided
            # When org_id is None, the workflow engine will use GLOBAL context
            request_headers = {
                "Content-Type": "application/json",
                "X-User-Id": user_id
            }
            if org_id:
                request_headers["X-Organization-Id"] = org_id

            response = requests.post(
                workflow_url,
                json=request_body,
                headers=request_headers,
                timeout=60  # Workflows can take longer
            )

            if response.status_code != 200:
                logger.error(f"Workflow execution failed: {response.status_code} - {response.text}")
                error = ErrorResponse(
                    error="WorkflowExecutionFailed",
                    message=f"Workflow execution failed: {response.text}"
                )
                return func.HttpResponse(
                    json.dumps(error.model_dump()),
                    status_code=500,
                    mimetype="application/json"
                )

            # Return workflow execution result
            execution_result = response.json()
            logger.info(f"Workflow execution completed: {execution_result.get('executionId')}")

            return func.HttpResponse(
                json.dumps(execution_result),
                status_code=200,
                mimetype="application/json"
            )

        except requests.exceptions.Timeout:
            logger.error("Workflow execution timed out")
            error = ErrorResponse(
                error="RequestTimeout",
                message="Workflow execution timed out"
            )
            return func.HttpResponse(
                json.dumps(error.model_dump()),
                status_code=504,
                mimetype="application/json"
            )
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to connect to workflows engine: {e}", exc_info=True)
            error = ErrorResponse(
                error="ServiceUnavailable",
                message="Failed to connect to workflows engine"
            )
            return func.HttpResponse(
                json.dumps(error.model_dump()),
                status_code=503,
                mimetype="application/json"
            )

    except ValueError as e:
        logger.error(f"Error parsing request: {str(e)}")
        error = ErrorResponse(
            error="BadRequest",
            message="Invalid JSON in request body"
        )
        return func.HttpResponse(
            json.dumps(error.model_dump()),
            status_code=400,
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Error executing workflow: {str(e)}", exc_info=True)
        error = ErrorResponse(
            error="InternalServerError",
            message="Failed to execute workflow"
        )
        return func.HttpResponse(
            json.dumps(error.model_dump()),
            status_code=500,
            mimetype="application/json"
        )


@bp.function_name("workflows_get_data_provider")
@bp.route(route="data-providers/{providerName}", methods=["GET"])
@require_auth
def get_data_provider(req: func.HttpRequest) -> func.HttpResponse:
    """
    GET /api/data-providers/{providerName}
    Get options from a data provider

    Headers:
    - X-Organization-Id: Organization ID (optional - derived from user if not provided)
    - X-User-Id: User ID (optional - derived from auth if not provided)

    Authorization: SWA enforces authenticated role before reaching this code

    Security:
    - Non-admin users: headers derived from database automatically
    - Admin users: can override headers to act on behalf of other users/orgs
    """
    user = req.user
    provider_name = req.route_params.get("providerName")

    logger.info(f"User {user.email} retrieving data provider {provider_name}")

    try:
        # Get scope context - platform admins can have org_id=None for GLOBAL scope
        org_id, user_id, error = get_scope_context(req)
        if error:
            return error

        logger.info(f"Fetching data provider with context: org={org_id or 'GLOBAL'}, user={user_id}")

        # Get workflows engine config
        url, function_key = get_workflows_engine_config()

        # Call workflows engine
        try:
            # Build URL - only add code parameter if function key is configured (not needed locally)
            provider_url = f"{url}/api/data-providers/{provider_name}"
            if function_key:
                provider_url += f"?code={function_key}"
                logger.info(f"Fetching data provider with function key")
            else:
                logger.info(f"Fetching data provider without function key (local mode)")

            response = requests.get(
                provider_url,
                headers={
                    "X-Organization-Id": org_id,
                    "X-User-Id": user_id
                },
                timeout=10
            )

            if response.status_code != 200:
                logger.error(f"Data provider request failed: {response.status_code} - {response.text}")
                error = ErrorResponse(
                    error="DataProviderFailed",
                    message=f"Failed to fetch data provider options: {response.text}"
                )
                return func.HttpResponse(
                    json.dumps(error.model_dump()),
                    status_code=500,
                    mimetype="application/json"
                )

            # Return data provider result
            provider_data = response.json()
            logger.info(f"Data provider returned {len(provider_data.get('options', []))} options")

            return func.HttpResponse(
                json.dumps(provider_data),
                status_code=200,
                mimetype="application/json"
            )

        except requests.exceptions.Timeout:
            logger.error("Data provider request timed out")
            error = ErrorResponse(
                error="RequestTimeout",
                message="Data provider request timed out"
            )
            return func.HttpResponse(
                json.dumps(error.model_dump()),
                status_code=504,
                mimetype="application/json"
            )
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to connect to workflows engine: {e}", exc_info=True)
            error = ErrorResponse(
                error="ServiceUnavailable",
                message="Failed to connect to workflows engine"
            )
            return func.HttpResponse(
                json.dumps(error.model_dump()),
                status_code=503,
                mimetype="application/json"
            )

    except Exception as e:
        logger.error(f"Error retrieving data provider: {str(e)}", exc_info=True)
        error = ErrorResponse(
            error="InternalServerError",
            message="Failed to retrieve data provider options"
        )
        return func.HttpResponse(
            json.dumps(error.model_dump()),
            status_code=500,
            mimetype="application/json"
        )
