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
    """Dynamically load SDK classes when accessed."""
    sdk_modules = [
        'config', 'executions', 'files', 'forms', 'oauth',
        'organizations', 'roles', 'secrets', 'workflows'
    ]
    # Internal/private modules are loaded as-is (not classes)
    internal_modules = ['_context', '_internal']

    if name in sdk_modules:
        import importlib
        module = importlib.import_module(f'sdk.{name}')
        # Get the class from the module (class name matches module name)
        cls = getattr(module, name)
        globals()[name] = cls
        return cls
    elif name in internal_modules:
        import importlib
        module = importlib.import_module(f'sdk.{name}')
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
    # SDK (lazy-loaded via __getattr__)
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
