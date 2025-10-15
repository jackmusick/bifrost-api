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
from shared.models import (
    # Enums
    ConfigType,
    ExecutionStatus,
    FormFieldType,
    IntegrationType,
    UserType,

    # Organizations
    Organization,
    CreateOrganizationRequest,
    UpdateOrganizationRequest,

    # Config
    Config,
    SetConfigRequest,

    # Integration Config
    IntegrationConfig,
    SetIntegrationConfigRequest,

    # Users & Roles
    User,
    Role,
    CreateRoleRequest,
    UpdateRoleRequest,
    UserRole,
    FormRole,
    AssignUsersToRoleRequest,
    AssignFormsToRoleRequest,

    # Permissions
    UserPermission,
    PermissionsData,
    GrantPermissionsRequest,

    # Forms
    FormFieldValidation,
    FormField,
    FormSchema,
    Form,
    CreateFormRequest,
    UpdateFormRequest,

    # Executions
    WorkflowExecution,

    # Common
    ErrorResponse,
)


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
    import functions.dashboard
    # Note: health endpoint is in function_app.py and doesn't use decorators yet

    # List of all models to include in the spec
    models: list[Type[BaseModel]] = [
        # Enums
        ConfigType,
        ExecutionStatus,
        FormFieldType,
        IntegrationType,
        UserType,

        # Organizations
        Organization,
        CreateOrganizationRequest,
        UpdateOrganizationRequest,

        # Config
        Config,
        SetConfigRequest,

        # Integration Config
        IntegrationConfig,
        SetIntegrationConfigRequest,

        # Users & Roles
        User,
        Role,
        CreateRoleRequest,
        UpdateRoleRequest,
        UserRole,
        FormRole,
        AssignUsersToRoleRequest,
        AssignFormsToRoleRequest,

        # Permissions
        UserPermission,
        PermissionsData,
        GrantPermissionsRequest,

        # Forms
        FormFieldValidation,
        FormField,
        FormSchema,
        Form,
        CreateFormRequest,
        UpdateFormRequest,

        # Executions
        WorkflowExecution,

        # Common
        ErrorResponse,
    ]

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
