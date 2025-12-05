"""
Bifrost Platform SDK

Provides Python API access to platform features from workflows.

All methods are synchronous and can be called directly (no await needed).

Usage:
    from bifrost import organizations, workflows, files, forms, executions, roles
    from bifrost import config, oauth

Example:
    # Create an organization
    org = organizations.create("Acme Corp", domain="acme.com")

    # List workflows
    wf_list = workflows.list()

    # Local filesystem operations
    files.write("data/temp.txt", "content", location="temp")
    data = files.read("data/customers.csv", location="workspace")

    # List executions
    recent = executions.list(limit=10)

    # Create a role
    role = roles.create("Manager", permissions=["users.read", "users.write"])

    # Manage configuration
    config.set("api_url", "https://api.example.com")
    url = config.get("api_url")

    # Get OAuth tokens (for secrets, use config with is_secret=True)
    conn = oauth.get("microsoft")
"""

from dataclasses import dataclass

from .config import config
from .executions import executions
from .files import files
from .forms import forms
from .oauth import oauth
from .organizations import organizations
from .roles import roles
from .workflows import workflows

# Import decorators and context from shared module
from shared.decorators import workflow, param, data_provider
from shared.context import ExecutionContext, Organization
from shared.errors import UserError, WorkflowError, ValidationError, IntegrationError, ConfigurationError
from shared.models import (
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
