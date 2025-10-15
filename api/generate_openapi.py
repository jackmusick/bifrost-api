#!/usr/bin/env python3
"""
OpenAPI Spec Generator for Bifrost Integrations Management API

Generates OpenAPI YAML from:
1. Decorator registry (endpoints with @openapi_endpoint)
2. Pydantic models (request/response schemas)

This provides a single source of truth for types across Python and TypeScript.

Usage:
    python generate_openapi.py > ../specs/001-complete-mvp-for/contracts/management-api.yaml
"""

from pydantic import BaseModel
import yaml
from typing import Type
from shared.openapi_decorators import build_openapi_spec
import shared.models as models_module
import models.oauth_connection as oauth_models
from functions.data_providers import DataProviderListResponse


def generate_openapi_spec() -> dict:
    """
    Generate OpenAPI 3.0 spec using decorator registry + Pydantic models.

    Returns:
        dict: OpenAPI specification
    """

    # Import all endpoint modules to ensure decorators are executed
    # This triggers the @openapi_endpoint decorators and populates the registry
    import functions.organizations
    import functions.roles
    import functions.permissions
    import functions.forms
    import functions.executions
    import functions.org_config
    import functions.oauth_api
    import functions.secrets
    import functions.metrics
    import functions.health

    # Import engine endpoints (now unified in functions/)
    import functions.data_providers
    import functions.discovery
    import functions.workflows

    # Auto-collect all models from shared.models.__all__
    # This ensures we never forget to add new models to the spec!
    models: list[Type[BaseModel]] = []

    # Add all models from shared.models (auto-discovered from __all__)
    for name in models_module.__all__:
        obj = getattr(models_module, name)
        # Only include BaseModel subclasses (skip regular classes, enums, and functions)
        if isinstance(obj, type) and issubclass(obj, BaseModel):
            models.append(obj)

    # Add OAuth models (auto-discovered from __all__)
    for name in oauth_models.__all__:
        obj = getattr(oauth_models, name)
        # Only include BaseModel subclasses
        if isinstance(obj, type) and issubclass(obj, BaseModel):
            models.append(obj)

    # Add Data Provider models
    models.append(DataProviderListResponse)

    # Build spec using decorator system
    spec = build_openapi_spec(
        title='Bifrost Integrations - Management API',
        version='1.0.0',
        description='API for managing forms, organizations, permissions, and users. Auto-generated from decorators and Pydantic models.',
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

    return spec


if __name__ == '__main__':
    spec = generate_openapi_spec()

    # Output as YAML with nice formatting
    yaml_output = yaml.dump(
        spec,
        sort_keys=False,
        default_flow_style=False,
        allow_unicode=True,
        width=120
    )

    print(yaml_output)
