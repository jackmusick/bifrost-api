"""
Bifrost Platform SDK

Provides Python API access to platform features from workflows.

Usage:
    from bifrost import organizations, workflows, files, storage, forms, executions, roles
    from bifrost import config, secrets, oauth

Example:
    # Create an organization
    org = organizations.create("Acme Corp", domain="acme.com")

    # Execute a workflow
    result = workflows.execute("process_order", {"order_id": "12345"})

    # Cloud storage operations
    blob_uri = storage.upload("files", "exports/report.csv", data, "text/csv")
    download_url = storage.generate_url("files", "exports/report.csv", expiry_hours=24)
    file_data = storage.download("uploads", "user-files/input.xlsx")

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

    # Manage secrets
    secrets.set("api_key", "sk_live_xxxxx")
    key = secrets.get("api_key")

    # Manage OAuth tokens
    token = oauth.get_token("microsoft")
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
from .storage import storage
from .workflows import workflows

# Import decorators and context from shared module
from shared.decorators import workflow, param, data_provider
from shared.context import ExecutionContext, Organization
from shared.models import (
    ExecutionStatus,
    OAuthCredentials,
    ConfigType,
    FormFieldType,
    IntegrationType,
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
    'storage',
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
]

__version__ = '1.0.0'
