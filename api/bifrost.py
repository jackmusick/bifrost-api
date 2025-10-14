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
from shared.decorators import workflow, param, data_provider
from shared.context import OrganizationContext, Organization, Caller
from shared.models import (
    ExecutionStatus,
    OAuthCredentials,
    ConfigType,
    FormFieldType,
    IntegrationType,
)

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
]
