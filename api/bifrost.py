"""
Bifrost Integrations - Convenience import shim

This module allows workflows to use simplified imports:
    from bifrost import workflow, param, OrganizationContext

Instead of:
    from shared.decorators import workflow, param
    from shared.context import OrganizationContext

Both import styles work at runtime. Use bifrost.pyi for development type hints.
"""

# Re-export everything from shared modules
from shared.context import Caller, Organization, OrganizationContext
from shared.decorators import data_provider, param, workflow
from shared.models import (
    ConfigType,
    ExecutionStatus,
    FormFieldType,
    IntegrationType,
    OAuthCredentials,
)

# Lazy-load SDK modules to avoid import issues
def __getattr__(name):
    """Dynamically load SDK modules when accessed."""
    sdk_modules = [
        'config', 'executions', 'files', 'forms', 'oauth',
        'organizations', 'roles', 'secrets', 'workflows'
    ]
    if name in sdk_modules:
        import importlib
        module = importlib.import_module(f'platform.bifrost.{name}')
        globals()[name] = module
        return module
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

__all__ = [
    # Decorators
    "workflow",
    "param",
    "data_provider",
    # Context
    "OrganizationContext",
    "Organization",
    "Caller",
    # Models
    "ExecutionStatus",
    "OAuthCredentials",
    "ConfigType",
    "FormFieldType",
    "IntegrationType",
    # SDK
    "config",
    "executions",
    "files",
    "forms",
    "oauth",
    "organizations",
    "roles",
    "secrets",
    "workflows",
]
