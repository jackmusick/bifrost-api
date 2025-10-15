#!/usr/bin/env python3
"""
OpenAPI Spec Generator for Workflow Engine

Generates OpenAPI YAML from workflow metadata
"""

import azure.functions as func
import json
import yaml


def generate_openapi_spec() -> dict:
    """
    Generate OpenAPI spec for Workflow Engine.
    This is simpler than the Management API - just metadata endpoint.
    """

    spec = {
        'openapi': '3.0.3',
        'info': {
            'title': 'Bifrost Integrations - Workflow Engine',
            'version': '1.0.0',
            'description': 'Workflow execution and metadata API',
        },
        'servers': [
            {
                'url': 'http://localhost:7071',
                'description': 'Local development server'
            }
        ],
        'paths': {
            '/api/registry/metadata': {
                'get': {
                    'summary': 'Get workflow metadata',
                    'description': 'Get all registered workflows and data providers',
                    'tags': ['Metadata'],
                    'responses': {
                        '200': {
                            'description': 'Workflow and data provider metadata',
                            'content': {
                                'application/json': {
                                    'schema': {'$ref': '#/components/schemas/MetadataResponse'}
                                }
                            }
                        }
                    }
                }
            },
            '/api/workflows/{workflowName}': {
                'post': {
                    'summary': 'Execute workflow',
                    'description': 'Execute a workflow with parameters',
                    'tags': ['Execution'],
                    'parameters': [
                        {
                            'name': 'workflowName',
                            'in': 'path',
                            'required': True,
                            'schema': {'type': 'string'}
                        }
                    ],
                    'requestBody': {
                        'required': True,
                        'content': {
                            'application/json': {
                                'schema': {'$ref': '#/components/schemas/WorkflowExecutionRequest'}
                            }
                        }
                    },
                    'responses': {
                        '200': {
                            'description': 'Workflow executed',
                            'content': {
                                'application/json': {
                                    'schema': {'$ref': '#/components/schemas/WorkflowExecutionResponse'}
                                }
                            }
                        }
                    }
                }
            },
            '/api/data-providers/{providerName}': {
                'get': {
                    'summary': 'Get data provider options',
                    'description': 'Call a data provider and get options',
                    'tags': ['Data Providers'],
                    'parameters': [
                        {
                            'name': 'providerName',
                            'in': 'path',
                            'required': True,
                            'schema': {'type': 'string'}
                        }
                    ],
                    'responses': {
                        '200': {
                            'description': 'Provider options',
                            'content': {
                                'application/json': {
                                    'schema': {'$ref': '#/components/schemas/DataProviderResponse'}
                                }
                            }
                        }
                    }
                }
            }
        },
        'components': {
            'schemas': {
                'MetadataResponse': {
                    'type': 'object',
                    'properties': {
                        'workflows': {
                            'type': 'array',
                            'items': {'$ref': '#/components/schemas/WorkflowMetadata'}
                        },
                        'dataProviders': {
                            'type': 'array',
                            'items': {'$ref': '#/components/schemas/DataProviderMetadata'}
                        }
                    }
                },
                'WorkflowMetadata': {
                    'type': 'object',
                    'properties': {
                        'name': {'type': 'string'},
                        'description': {'type': 'string'},
                        'category': {'type': 'string'},
                        'tags': {
                            'type': 'array',
                            'items': {'type': 'string'}
                        },
                        'parameters': {
                            'type': 'array',
                            'items': {'$ref': '#/components/schemas/WorkflowParameter'}
                        }
                    }
                },
                'WorkflowParameter': {
                    'type': 'object',
                    'properties': {
                        'name': {'type': 'string'},
                        'type': {'type': 'string'},
                        'required': {'type': 'boolean'},
                        'label': {'type': 'string'},
                        'helpText': {'type': 'string'},
                        'defaultValue': {},
                        'dataProvider': {'type': 'string'}
                    }
                },
                'DataProviderMetadata': {
                    'type': 'object',
                    'properties': {
                        'name': {'type': 'string'},
                        'description': {'type': 'string'},
                        'category': {'type': 'string'}
                    }
                },
                'WorkflowExecutionRequest': {
                    'type': 'object',
                    'properties': {
                        'workflowName': {'type': 'string'},
                        'parameters': {'type': 'object'},
                        'orgId': {'type': 'string'}
                    }
                },
                'WorkflowExecutionResponse': {
                    'type': 'object',
                    'properties': {
                        'executionId': {'type': 'string'},
                        'status': {'type': 'string'},
                        'result': {},
                        'error': {'type': 'string'}
                    }
                },
                'DataProviderResponse': {
                    'type': 'object',
                    'properties': {
                        'provider': {'type': 'string'},
                        'options': {
                            'type': 'array',
                            'items': {
                                'type': 'object',
                                'properties': {
                                    'label': {'type': 'string'},
                                    'value': {'type': 'string'},
                                    'metadata': {'type': 'object'}
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    return spec


if __name__ == '__main__':
    spec = generate_openapi_spec()
    yaml_output = yaml.dump(
        spec,
        sort_keys=False,
        default_flow_style=False,
        allow_unicode=True,
        width=120
    )
    print(yaml_output)
