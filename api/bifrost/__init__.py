"""
Bifrost Platform SDK

Provides Python API access to platform features from workflows.

All methods interacting with database services (secrets, config, organizations,
roles, executions, forms, oauth) are async and must be called with await.

Usage:
    from bifrost import organizations, workflows, files, forms, executions, roles
    from bifrost import config, secrets, oauth

Example:
    # Create an organization (async)
    org = await organizations.create("Acme Corp", domain="acme.com")

    # Execute a workflow
    result = workflows.execute("process_order", {"order_id": "12345"})

    # Local filesystem operations (async with aiofiles)
    await files.write("data/temp.txt", "content", location="temp")
    data = await files.read("data/customers.csv", location="workspace")

    # List executions (async)
    recent = await executions.list(limit=10)

    # Create a role (async)
    role = await roles.create("Manager", permissions=["users.read", "users.write"])

    # Manage configuration (async)
    await config.set("api_url", "https://api.example.com")
    url = await config.get("api_url")

    # Manage secrets (async)
    await secrets.set("api_key", "sk_live_xxxxx")
    key = await secrets.get("api_key")

    # Manage OAuth tokens (async)
    token = await oauth.get_token("microsoft")
"""

from dataclasses import dataclass

from .config import config
from .executions import executions
from .files import files
from .forms import forms
from .oauth import oauth
from .organizations import organizations
from .roles import roles
from .secrets import secrets
from .workflows import workflows

# Import decorators and context from shared module
from shared.decorators import workflow, param, data_provider
from shared.context import ExecutionContext, Organization
from shared.errors import UserError, WorkflowError, ValidationError, IntegrationError, ConfigurationError
from src.models.schemas import (
    ExecutionStatus,
    OAuthCredentials,
    ConfigType,
    FormFieldType,
    IntegrationType,
    Role,
    Form,
)

# For backwards compatibility with type stubs
@dataclass
class Caller:
    """User who triggered the workflow execution."""
    user_id: str
    email: str
    name: str

__all__ = [
    'organizations',
    'workflows',
    'files',
    'forms',
    'executions',
    'roles',
    'config',
    'secrets',
    'oauth',
    'workflow',
    'param',
    'data_provider',
    'ExecutionContext',
    'Organization',
    'Caller',
    'ExecutionStatus',
    'OAuthCredentials',
    'ConfigType',
    'FormFieldType',
    'IntegrationType',
    'Role',
    'Form',
    'UserError',
    'WorkflowError',
    'ValidationError',
    'IntegrationError',
    'ConfigurationError',
]

__version__ = '1.0.0'
