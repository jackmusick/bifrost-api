#!/usr/bin/env python3
"""
OpenAPI Spec Generator for Bifrost Integrations Management API

Generates OpenAPI YAML from Pydantic models in shared/models.py
This provides a single source of truth for types across Python and TypeScript.

Usage:
    python generate_openapi.py > ../specs/001-complete-mvp-for/contracts/management-api.yaml
"""

from pydantic import BaseModel
import yaml
from typing import Type
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
    Generate OpenAPI 3.0 spec from Pydantic models.

    Returns:
        dict: OpenAPI specification
    """

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

    # Generate schemas from Pydantic models
    schemas = {}
    from enum import Enum

    for model in models:
        # Handle Enums differently
        if isinstance(model, type) and issubclass(model, Enum):
            # Generate enum schema manually
            enum_values = [e.value for e in model]
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

    # Build OpenAPI spec
    spec = {
        'openapi': '3.0.3',
        'info': {
            'title': 'Bifrost Integrations - Management API',
            'version': '1.0.0',
            'description': 'API for managing forms, organizations, permissions, and users. Auto-generated from Pydantic models.',
            'contact': {
                'name': 'Bifrost Integrations',
                'email': 'jack@gocovi.com'
            }
        },
        'servers': [
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
        'components': {
            'schemas': schemas,
            'securitySchemes': {
                'BearerAuth': {
                    'type': 'http',
                    'scheme': 'bearer',
                    'bearerFormat': 'JWT',
                    'description': 'Azure AD JWT token'
                }
            }
        },
        'security': [
            {'BearerAuth': []}
        ],
        'paths': {
            '/api/health': {
                'get': {
                    'summary': 'Health check',
                    'description': 'Check if the API is running',
                    'tags': ['Health'],
                    'responses': {
                        '200': {
                            'description': 'API is healthy',
                            'content': {
                                'application/json': {
                                    'schema': {
                                        'type': 'object',
                                        'properties': {
                                            'status': {'type': 'string', 'example': 'healthy'},
                                            'timestamp': {'type': 'string', 'format': 'date-time'}
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            },
            '/api/forms': {
                'get': {
                    'summary': 'List forms',
                    'description': 'Get all forms for an organization',
                    'tags': ['Forms'],
                    'parameters': [
                        {
                            'name': 'orgId',
                            'in': 'query',
                            'schema': {'type': 'string'},
                            'description': 'Filter by organization ID'
                        }
                    ],
                    'responses': {
                        '200': {
                            'description': 'List of forms',
                            'content': {
                                'application/json': {
                                    'schema': {
                                        'type': 'array',
                                        'items': {'$ref': '#/components/schemas/Form'}
                                    }
                                }
                            }
                        },
                        '401': {'$ref': '#/components/responses/UnauthorizedError'},
                        '500': {'$ref': '#/components/responses/InternalError'}
                    }
                },
                'post': {
                    'summary': 'Create form',
                    'description': 'Create a new form',
                    'tags': ['Forms'],
                    'requestBody': {
                        'required': True,
                        'content': {
                            'application/json': {
                                'schema': {'$ref': '#/components/schemas/CreateFormRequest'}
                            }
                        }
                    },
                    'responses': {
                        '201': {
                            'description': 'Form created',
                            'content': {
                                'application/json': {
                                    'schema': {'$ref': '#/components/schemas/Form'}
                                }
                            }
                        },
                        '400': {'$ref': '#/components/responses/BadRequestError'},
                        '401': {'$ref': '#/components/responses/UnauthorizedError'},
                        '500': {'$ref': '#/components/responses/InternalError'}
                    }
                }
            },
            '/api/forms/{formId}': {
                'get': {
                    'summary': 'Get form',
                    'description': 'Get form by ID',
                    'tags': ['Forms'],
                    'parameters': [
                        {'name': 'formId', 'in': 'path', 'required': True,
                            'schema': {'type': 'string'}}
                    ],
                    'responses': {
                        '200': {
                            'description': 'Form details',
                            'content': {
                                'application/json': {
                                    'schema': {'$ref': '#/components/schemas/Form'}
                                }
                            }
                        },
                        '404': {'$ref': '#/components/responses/NotFoundError'},
                        '500': {'$ref': '#/components/responses/InternalError'}
                    }
                },
                'put': {
                    'summary': 'Update form',
                    'description': 'Update an existing form',
                    'tags': ['Forms'],
                    'parameters': [
                        {'name': 'formId', 'in': 'path', 'required': True,
                            'schema': {'type': 'string'}}
                    ],
                    'requestBody': {
                        'required': True,
                        'content': {
                            'application/json': {
                                'schema': {'$ref': '#/components/schemas/UpdateFormRequest'}
                            }
                        }
                    },
                    'responses': {
                        '200': {
                            'description': 'Form updated',
                            'content': {
                                'application/json': {
                                    'schema': {'$ref': '#/components/schemas/Form'}
                                }
                            }
                        },
                        '404': {'$ref': '#/components/responses/NotFoundError'},
                        '500': {'$ref': '#/components/responses/InternalError'}
                    }
                },
                'delete': {
                    'summary': 'Delete form',
                    'description': 'Delete a form (soft delete)',
                    'tags': ['Forms'],
                    'parameters': [
                        {'name': 'formId', 'in': 'path', 'required': True,
                            'schema': {'type': 'string'}}
                    ],
                    'responses': {
                        '204': {'description': 'Form deleted'},
                        '404': {'$ref': '#/components/responses/NotFoundError'},
                        '500': {'$ref': '#/components/responses/InternalError'}
                    }
                }
            }
        }
    }

    # Add common responses
    spec['components']['responses'] = {
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
