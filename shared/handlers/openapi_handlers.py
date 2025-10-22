"""
OpenAPI Schema Generation Handlers

Provides business logic for OpenAPI specification generation including:
- Schema generation from Pydantic models
- Endpoint documentation from registry
- Dynamic workflow endpoint generation
- Security scheme configuration
"""

from pydantic import BaseModel
from shared.openapi_decorators import build_openapi_spec
from shared.registry import get_registry
import models.oauth_connection as oauth_models
import shared.models as models_module


def collect_pydantic_models() -> list[type[BaseModel]]:
    """
    Collect all Pydantic models from shared and oauth modules.

    Auto-discovers models from __all__ exports to ensure comprehensive
    schema generation without manual registration.

    Returns:
        list[type[BaseModel]]: All discovered Pydantic model classes
    """
    models: list[type[BaseModel]] = []

    # Add all models from shared.models (auto-discovered from __all__)
    for name in models_module.__all__:
        obj = getattr(models_module, name)
        # Only include BaseModel subclasses (skip regular classes, enums, functions)
        if isinstance(obj, type) and issubclass(obj, BaseModel):
            models.append(obj)

    # Add OAuth models (auto-discovered from __all__)
    for name in oauth_models.__all__:
        obj = getattr(oauth_models, name)
        # Only include BaseModel subclasses
        if isinstance(obj, type) and issubclass(obj, BaseModel):
            models.append(obj)

    # Add Data Provider models (if available)
    try:
        from functions.http.data_providers import DataProviderListResponse
        models.append(DataProviderListResponse)
    except (ImportError, ModuleNotFoundError):
        # Data provider module may not be available in all contexts
        pass

    return models


def map_python_type_to_openapi(python_type: str) -> str:
    """
    Map Python type strings to OpenAPI type strings.

    Args:
        python_type: Python type name (e.g., 'int', 'bool', 'float', 'string')

    Returns:
        str: OpenAPI type name
    """
    if python_type in ['int', 'integer']:
        return 'integer'
    elif python_type == 'bool':
        return 'boolean'
    elif python_type == 'float':
        return 'number'
    else:
        return 'string'


def build_workflow_parameters(metadata) -> list[dict]:
    """
    Build OpenAPI parameter definitions from workflow metadata.

    Parameters are added as query parameters for efficient OpenAPI representation.

    Args:
        metadata: Workflow metadata object with parameters list

    Returns:
        list[dict]: List of OpenAPI parameter definitions
    """
    parameters = []

    for param in metadata.parameters:
        param_name = param.name
        param_type = param.type
        param_required = param.required
        param_description = param.help_text or f"{param_name} parameter"

        # Map Python types to OpenAPI types
        openapi_type = map_python_type_to_openapi(param_type)

        parameters.append({
            "name": param_name,
            "in": "query",
            "required": param_required,
            "description": param_description,
            "schema": {
                "type": openapi_type
            }
        })

    return parameters


def build_workflow_request_body(metadata) -> dict | None:
    """
    Build OpenAPI request body schema for POST/PUT methods.

    Constructs JSON schema for workflow parameters to support
    request body input in addition to query parameters.

    Args:
        metadata: Workflow metadata object with parameters list

    Returns:
        dict | None: Request body definition or None if no parameters
    """
    properties = {}
    required_fields = []

    for param in getattr(metadata, 'parameters', []):
        param_name = getattr(param, 'name', None)
        param_type = getattr(param, 'type', 'string')
        param_required = getattr(param, 'required', False)

        openapi_type = map_python_type_to_openapi(param_type)

        properties[param_name] = {"type": openapi_type}

        if param_required:
            required_fields.append(param_name)

    if not properties:
        return None

    return {
        "content": {
            "application/json": {
                "schema": {
                    "type": "object",
                    "properties": properties,
                    "required": required_fields if required_fields else None
                }
            }
        }
    }


def build_workflow_operation(metadata, method: str) -> dict:
    """
    Build OpenAPI operation definition for a workflow endpoint.

    Creates complete operation object with parameters, request body,
    and response schemas for a single HTTP method.

    Args:
        metadata: Workflow metadata object
        method: HTTP method (GET, POST, PUT, DELETE, etc.)

    Returns:
        dict: OpenAPI operation definition
    """
    method_lower = method.lower()
    workflow_name = metadata.name

    parameters = build_workflow_parameters(metadata)
    request_body = None

    # Build request body for POST/PUT methods
    if method_lower in ['post', 'put']:
        request_body = build_workflow_request_body(metadata)

    operation = {
        "summary": f"{method.upper()} {workflow_name}",
        "description": getattr(
            metadata,
            'description',
            f"Execute {workflow_name} workflow via HTTP endpoint"
        ),
        "tags": ["Workflow Endpoints"],
        "operationId": f"execute_workflow_endpoint_{workflow_name}_{method_lower}",
        "parameters": parameters if parameters else [],
        "security": [{"BearerAuth": []}],
        "responses": {
            "200": {
                "description": "Workflow executed successfully",
                "content": {
                    "application/json": {
                        "schema": {
                            "type": "object",
                            "properties": {
                                "executionId": {"type": "string"},
                                "status": {"type": "string"},
                                "result": {"type": "object"},
                                "durationMs": {"type": "integer"},
                                "startedAt": {"type": "string", "format": "date-time"},
                                "completedAt": {"type": "string", "format": "date-time"}
                            }
                        }
                    }
                }
            },
            "400": {
                "description": "Bad request (invalid input or validation errors)"
            },
            "401": {
                "description": "Unauthorized (invalid or missing API key)"
            },
            "404": {
                "description": "Endpoint not found or not enabled"
            },
            "405": {
                "description": (
                    f"Method not allowed (only "
                    f"{', '.join(metadata.allowed_methods or ['POST'])} "
                    f"allowed for this endpoint)"
                )
            },
            "500": {
                "description": "Server error"
            }
        }
    }

    # Add request body if present
    if request_body:
        operation["requestBody"] = request_body

    return operation


def generate_workflow_endpoints(spec: dict) -> None:
    """
    Generate OpenAPI endpoint definitions for enabled workflows.

    Dynamically adds workflow endpoints to the spec based on registry.
    Updates the spec in-place with /endpoints/{workflow_name} paths.

    Args:
        spec: OpenAPI specification dict to update (modified in-place)
    """
    registry = get_registry()

    # Initialize paths if not present
    if "paths" not in spec:
        spec["paths"] = {}

    # Generate endpoint paths for each enabled workflow
    for metadata in registry.get_all_workflows():
        # Skip workflows that aren't enabled as endpoints
        if not metadata.endpoint_enabled:
            continue

        # Get allowed methods for this workflow
        allowed_methods = metadata.allowed_methods or ['POST']
        workflow_name = metadata.name

        # Create path entry if not already present (might be from decorator)
        path_key = f"/endpoints/{workflow_name}"
        if path_key not in spec["paths"]:
            spec["paths"][path_key] = {}

        # Add definition for each allowed HTTP method
        for method in allowed_methods:
            operation = build_workflow_operation(metadata, method)
            spec["paths"][path_key][method.lower()] = operation


def ensure_security_schemes(spec: dict) -> None:
    """
    Ensure security schemes are properly configured in the spec.

    Adds BearerAuth security scheme for API key authentication.
    Updates the spec in-place.

    Args:
        spec: OpenAPI specification dict to update (modified in-place)
    """
    if "components" not in spec:
        spec["components"] = {}
    if "securitySchemes" not in spec["components"]:
        spec["components"]["securitySchemes"] = {}

    spec["components"]["securitySchemes"]["BearerAuth"] = {
        "type": "http",
        "scheme": "bearer",
        "bearerFormat": "JWT",
        "description": (
            "API key for workflow endpoint access. "
            "Use format: Authorization: Bearer <api_key>"
        )
    }


def generate_openapi_spec() -> dict:
    """
    Generate complete OpenAPI 3.0 specification.

    Combines:
    1. Base spec generation from decorators and models
    2. Dynamic workflow endpoint generation
    3. Security scheme configuration

    Returns:
        dict: Complete OpenAPI specification
    """
    # Collect all Pydantic models
    models = collect_pydantic_models()

    # Build spec using decorator system
    spec = build_openapi_spec(
        title='Bifrost Integrations - Management API',
        version='1.0.0',
        description=(
            'API for managing forms, organizations, permissions, and users. '
            'Auto-generated from decorators and Pydantic models.'
        ),
        servers=[
            {
                'url': 'http://localhost:7071',
                'description': 'Local development server'
            },
            {
                'url': 'https://{environment}.azurewebsites.net',
                'description': 'Azure deployment',
                'variables': {
                    'environment': {
                        'default': 'msp-automation-api-dev',
                        'enum': ['msp-automation-api-dev', 'msp-automation-api-prod']
                    }
                }
            }
        ],
        models=models
    )

    # Generate dynamic workflow endpoints
    generate_workflow_endpoints(spec)

    # Ensure security schemes are configured
    ensure_security_schemes(spec)

    return spec
