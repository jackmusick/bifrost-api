"""
OpenAPI decorators for API endpoints.

Provides a decorator-based system for automatically generating OpenAPI
specifications from function metadata. Each endpoint decorated with @openapi_endpoint
will be automatically included in the generated spec.
"""

from collections.abc import Callable
from functools import wraps
from typing import Any

from pydantic import BaseModel

# ==================== REGISTRY ====================

class OpenAPIEndpoint:
    """Metadata for a single OpenAPI endpoint"""

    def __init__(
        self,
        path: str,
        method: str,
        summary: str,
        description: str | None = None,
        tags: list[str] | None = None,
        request_model: type[BaseModel] | None = None,
        response_model: type[BaseModel] | type[list[Any]] | None = None,
        path_params: dict[str, dict[str, Any]] | None = None,
        query_params: dict[str, dict[str, Any]] | None = None,
        responses: dict[int, dict[str, Any]] | None = None,
        function_name: str | None = None
    ):
        self.path = path
        self.method = method.upper()
        self.summary = summary
        self.description = description or summary
        self.tags = tags or []
        self.request_model = request_model
        self.response_model = response_model
        self.path_params = path_params or {}
        self.query_params = query_params or {}
        self.responses = responses or {}
        self.function_name = function_name


class OpenAPIRegistry:
    """Registry for OpenAPI endpoints"""

    def __init__(self):
        self._endpoints: list[OpenAPIEndpoint] = []

    def register(self, endpoint: OpenAPIEndpoint):
        """Register an endpoint"""
        self._endpoints.append(endpoint)

    def get_endpoints(self) -> list[OpenAPIEndpoint]:
        """Get all registered endpoints"""
        return self._endpoints

    def clear(self):
        """Clear all endpoints (useful for testing)"""
        self._endpoints = []


# Global registry instance
_registry = OpenAPIRegistry()


def get_openapi_registry() -> OpenAPIRegistry:
    """Get the global OpenAPI registry"""
    return _registry


# ==================== DECORATOR ====================

def openapi_endpoint(
    path: str,
    method: str,
    summary: str,
    *,
    description: str | None = None,
    tags: list[str] | None = None,
    request_model: type[BaseModel] | None = None,
    response_model: type[BaseModel] | type[list[Any]] | None = None,
    path_params: dict[str, dict[str, Any]] | None = None,
    query_params: dict[str, dict[str, Any]] | None = None,
    responses: dict[int, dict[str, Any]] | None = None
) -> Callable:
    """
    Decorator to mark an API endpoint for OpenAPI documentation.

    Args:
        path: API path (e.g., "/organizations" or "/organizations/{orgId}")
        method: HTTP method (GET, POST, PUT, PATCH, DELETE)
        summary: Short summary of the endpoint
        description: Longer description (optional, defaults to summary)
        tags: OpenAPI tags for grouping (e.g., ["Organizations"])
        request_model: Pydantic model for request body
        response_model: Pydantic model for successful response
        path_params: Path parameter definitions (e.g., {"orgId": {"description": "Organization ID", "schema": {"type": "string"}}})
        query_params: Query parameter definitions
        responses: Custom response definitions (merged with defaults)

    Example:
        @openapi_endpoint(
            path="/organizations",
            method="GET",
            summary="List all organizations",
            tags=["Organizations"],
            response_model=Organization
        )
        async def list_organizations(req: func.HttpRequest) -> func.HttpResponse:
            ...
    """

    def decorator(func: Callable) -> Callable:
        # Extract function name for debugging
        function_name = func.__name__

        # Create endpoint metadata
        endpoint = OpenAPIEndpoint(
            path=path,
            method=method,
            summary=summary,
            description=description,
            tags=tags,
            request_model=request_model,
            response_model=response_model,
            path_params=path_params,
            query_params=query_params,
            responses=responses,
            function_name=function_name
        )

        # Register endpoint
        _registry.register(endpoint)

        # Return original function unchanged
        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await func(*args, **kwargs)

        return wrapper

    return decorator


# ==================== HELPER FUNCTIONS ====================

def build_openapi_spec(
    title: str,
    version: str,
    description: str,
    servers: list[dict[str, Any]],
    models: list[type[BaseModel]]
) -> dict[str, Any]:
    """
    Build complete OpenAPI specification from registry and models.

    Args:
        title: API title
        version: API version
        description: API description
        servers: List of server definitions
        models: List of Pydantic models to include in schemas

    Returns:
        Complete OpenAPI 3.0 specification dictionary
    """
    from enum import Enum

    # Generate schemas from Pydantic models
    schemas = {}

    for model in models:
        # Handle Enums differently
        if isinstance(model, type) and issubclass(model, Enum):
            # Generate enum schema manually
            enum_values = [e.value for e in model]  # type: ignore[misc]
            schemas[model.__name__] = {
                'type': 'string',
                'enum': enum_values
            }
        else:
            # Get JSON schema from Pydantic model
            model_schema = model.model_json_schema(
                ref_template='#/components/schemas/{model}')

            # Extract nested definitions
            if '$defs' in model_schema:
                for def_name, def_schema in model_schema['$defs'].items():
                    if def_name not in schemas:
                        schemas[def_name] = def_schema
                del model_schema['$defs']

            # Add model schema
            schemas[model.__name__] = model_schema

    # Build paths from registry
    paths = {}
    registry = get_openapi_registry()

    for endpoint in registry.get_endpoints():
        path = endpoint.path

        # Initialize path if not exists
        if path not in paths:
            paths[path] = {}

        # Build operation
        operation = {
            'summary': endpoint.summary,
            'description': endpoint.description,
            'tags': endpoint.tags,
            'responses': _build_responses(endpoint, schemas)
        }

        # Add parameters (path + query)
        parameters = []

        # Path parameters
        for param_name, param_def in endpoint.path_params.items():
            parameters.append({
                'name': param_name,
                'in': 'path',
                'required': True,
                **param_def
            })

        # Query parameters
        for param_name, param_def in endpoint.query_params.items():
            parameters.append({
                'name': param_name,
                'in': 'query',
                'required': param_def.get('required', False),
                **{k: v for k, v in param_def.items() if k != 'required'}
            })

        if parameters:
            operation['parameters'] = parameters

        # Add request body (for POST/PUT/PATCH)
        if endpoint.request_model and endpoint.method in ['POST', 'PUT', 'PATCH']:
            operation['requestBody'] = {
                'required': True,
                'content': {
                    'application/json': {
                        'schema': {'$ref': f'#/components/schemas/{endpoint.request_model.__name__}'}
                    }
                }
            }

        # Add to paths
        paths[path][endpoint.method.lower()] = operation

    # Build complete spec
    spec = {
        'openapi': '3.0.3',
        'info': {
            'title': title,
            'version': version,
            'description': description
        },
        'servers': servers,
        'components': {
            'schemas': schemas,
            'securitySchemes': {
                'BearerAuth': {
                    'type': 'http',
                    'scheme': 'bearer',
                    'bearerFormat': 'JWT',
                    'description': 'JWT bearer token'
                }
            },
            'responses': _build_common_responses()
        },
        'security': [
            {'BearerAuth': []}
        ],
        'paths': paths
    }

    return spec


def _build_responses(endpoint: OpenAPIEndpoint, schemas: dict[str, Any]) -> dict[str, Any]:
    """Build responses section for an endpoint"""
    import typing

    responses = {}

    # Default success response based on method
    if endpoint.method == 'POST':
        status_code = 201
        description = 'Resource created'
    elif endpoint.method == 'DELETE':
        status_code = 204
        description = 'No content'
    else:
        status_code = 200
        description = 'Successful operation'

    # Add success response
    if endpoint.method == 'DELETE' and status_code == 204:
        responses[str(status_code)] = {
            'description': description
        }
    elif endpoint.response_model:
        # Check if response_model is a List type
        origin = typing.get_origin(endpoint.response_model)

        if origin is list or origin is list:
            # Handle List[Model] - extract the inner type
            args = typing.get_args(endpoint.response_model)
            if args:
                inner_model = args[0]
                response_schema = {
                    'type': 'array',
                    'items': {'$ref': f'#/components/schemas/{inner_model.__name__}'}
                }
            else:
                # List without type parameter
                response_schema = {'type': 'array', 'items': {}}
        else:
            # Single model response
            response_schema = {'$ref': f'#/components/schemas/{endpoint.response_model.__name__}'}

        responses[str(status_code)] = {
            'description': description,
            'content': {
                'application/json': {
                    'schema': response_schema
                }
            }
        }
    else:
        responses[str(status_code)] = {
            'description': description
        }

    # Add common error responses
    responses['400'] = {'$ref': '#/components/responses/BadRequestError'}
    responses['401'] = {'$ref': '#/components/responses/UnauthorizedError'}
    responses['403'] = {'$ref': '#/components/responses/ForbiddenError'}
    responses['404'] = {'$ref': '#/components/responses/NotFoundError'}
    responses['500'] = {'$ref': '#/components/responses/InternalError'}

    # Merge custom responses
    if endpoint.responses:
        responses.update(endpoint.responses)

    return responses


def _build_common_responses() -> dict[str, Any]:
    """Build common error responses"""
    return {
        'BadRequestError': {
            'description': 'Bad request',
            'content': {
                'application/json': {
                    'schema': {'$ref': '#/components/schemas/ErrorResponse'}
                }
            }
        },
        'UnauthorizedError': {
            'description': 'Unauthorized',
            'content': {
                'application/json': {
                    'schema': {'$ref': '#/components/schemas/ErrorResponse'}
                }
            }
        },
        'ForbiddenError': {
            'description': 'Forbidden',
            'content': {
                'application/json': {
                    'schema': {'$ref': '#/components/schemas/ErrorResponse'}
                }
            }
        },
        'NotFoundError': {
            'description': 'Resource not found',
            'content': {
                'application/json': {
                    'schema': {'$ref': '#/components/schemas/ErrorResponse'}
                }
            }
        },
        'InternalError': {
            'description': 'Internal server error',
            'content': {
                'application/json': {
                    'schema': {'$ref': '#/components/schemas/ErrorResponse'}
                }
            }
        }
    }
