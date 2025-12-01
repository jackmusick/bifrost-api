"""
Organization Context
Context object passed to all workflows with org data, config, secrets, and integrations

Execution Context - Unified context for all requests, workflows, and scripts

This replaces both ExecutionContext and ExecutionContext with a single,
unified context that works everywhere:
- HTTP endpoint handlers
- Workflows and data providers
- Scripts
- Bifrost SDK
- Repository queries
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from .config_resolver import ConfigResolver

logger = logging.getLogger(__name__)


@dataclass
class Organization:
    """Organization entity."""
    id: str
    name: str
    is_active: bool = True

    @property
    def org_id(self) -> str:
        """Backwards compatibility: alias for id"""
        return self.id


@dataclass
class Caller:
    """User who triggered the execution."""
    user_id: str
    email: str
    name: str


@dataclass
class ExecutionContext:
    """
    Unified execution context for all code execution.

    Provides:
    - User identity (user_id, email, name)
    - Scope (GLOBAL or organization ID)
    - Authorization (is_platform_admin, is_function_key)
    - Configuration and secrets
    - Workflow state tracking (logs, variables, checkpoints)

    Used everywhere:
    - HTTP handlers receive this from middleware
    - Workflows receive this as first parameter
    - Scripts have this available as `context`
    - Bifrost SDK accesses this via ContextVar
    - Repositories use this for scoped queries
    """

    # ==================== IDENTITY ====================
    user_id: str
    email: str
    name: str

    # ==================== SCOPE ====================
    scope: str  # "GLOBAL" or organization ID
    organization: Organization | None  # None for GLOBAL scope

    # ==================== AUTHORIZATION ====================
    is_platform_admin: bool
    is_function_key: bool

    # ==================== EXECUTION ====================
    execution_id: str

    # ==================== WORKFLOW STATE (private) ====================
    _config: dict[str, Any] = field(default_factory=dict)
    _config_resolver: ConfigResolver = field(default_factory=ConfigResolver)
    _integration_cache: dict = field(default_factory=dict)
    _integration_calls: list = field(default_factory=list)

    # ==================== COMPUTED PROPERTIES ====================

    @property
    def org_id(self) -> str | None:
        """Organization ID (None for GLOBAL scope)"""
        return self.organization.id if self.organization else None

    @property
    def org_name(self) -> str | None:
        """Organization name (None for GLOBAL scope)"""
        return self.organization.name if self.organization else None

    @property
    def is_global_scope(self) -> bool:
        """True if executing in GLOBAL scope (no organization)"""
        return self.scope == "GLOBAL"

    @property
    def executed_by(self) -> str:
        """Backwards compatibility: alias for user_id"""
        return self.user_id

    @property
    def executed_by_email(self) -> str:
        """Backwards compatibility: alias for email"""
        return self.email

    @property
    def executed_by_name(self) -> str:
        """Backwards compatibility: alias for name"""
        return self.name


    # ==================== STATE TRACKING ====================

    def _track_integration_call(
        self,
        integration: str,
        method: str,
        endpoint: str,
        status_code: int,
        duration_ms: int,
        error: str | None = None
    ) -> None:
        """
        Track external integration call.

        Called automatically by integration clients.
        """
        call_record = {
            "timestamp": datetime.utcnow().isoformat(),
            "integration": integration,
            "method": method,
            "endpoint": endpoint,
            "status_code": status_code,
            "duration_ms": duration_ms,
            "error": error,
            "success": status_code < 400 and not error
        }
        self._integration_calls.append(call_record)

    async def finalize_execution(self) -> dict[str, Any]:
        """
        Get final execution state for persistence.

        Called automatically at end of execution.

        Returns:
            Dict with integration_calls
        """
        return {
            "integration_calls": self._integration_calls,
        }
