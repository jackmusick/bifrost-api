"""
Bifrost Integrations - Convenience import shim

This module allows workflows to use simplified imports:
    from bifrost import workflow, param, OrganizationContext

Instead of:
    from engine.shared.decorators import workflow, param
    from engine.shared.context import OrganizationContext

Both import styles work at runtime. Use bifrost.pyi for development type hints.
"""

# Re-export everything from engine.shared modules
from engine.shared.decorators import workflow, param, data_provider
from engine.shared.context import OrganizationContext, Organization, Caller
from engine.shared.models import (
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
