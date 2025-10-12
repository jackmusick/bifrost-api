"""
Workflow and Data Provider Decorators
Decorators for registering workflows and data providers with metadata
"""

import functools
import inspect
from typing import Callable, Any, List, Optional, Dict
import logging

from .registry import (
    get_registry,
    WorkflowMetadata,
    WorkflowParameter,
    DataProviderMetadata
)

logger = logging.getLogger(__name__)

# Valid parameter types
VALID_PARAM_TYPES = {"string", "int", "bool", "float", "json", "list", "email"}


def workflow(
    # Identity
    name: str,
    description: str,
    category: str = "General",
    tags: Optional[List[str]] = None,

    # Execution
    execution_mode: str = "sync",  # "sync" | "async" | "scheduled"
    timeout_seconds: int = 300,
    max_duration_seconds: int = 300,

    # Retry
    retry_policy: Optional[Dict[str, Any]] = None,

    # Scheduling
    schedule: Optional[str] = None,  # Cron expression

    # Access Control
    requires_org: bool = True,
    expose_in_forms: bool = True,
    requires_approval: bool = False,
    required_permission: str = "canExecuteWorkflows"
):
    """
    Decorator for registering workflow functions

    Usage:
        @workflow(
            name="user_onboarding",
            description="Onboard new M365 user with license assignment",
            category="user_management",
            tags=["m365", "user"],
            execution_mode="sync",
            timeout_seconds=300,
            expose_in_forms=True
        )
        @param("first_name", type="string", label="First Name", required=True)
        @param("last_name", type="string", label="Last Name", required=True)
        async def onboard_user(context, first_name, last_name):
            # Implementation
            pass

    Args:
        name: Unique workflow identifier (snake_case)
        description: Human-readable description
        category: Category for organization (default: "General")
        tags: Optional list of tags for filtering
        execution_mode: "sync" | "async" | "scheduled" (default: "sync")
        timeout_seconds: Max execution time in seconds (default: 300)
        max_duration_seconds: Hard limit for execution (default: 300)
        retry_policy: Dict with retry config (e.g., {"max_attempts": 3, "backoff": 2})
        schedule: Cron expression for scheduled workflows (e.g., "0 9 * * *")
        requires_org: Whether workflow requires organization context (default: True)
        expose_in_forms: Can this be called from forms? (default: True)
        requires_approval: Requires approval before execution (default: False)
        required_permission: Permission required to execute (default: "canExecuteWorkflows")

    Returns:
        Decorated function (unchanged for normal Python execution)
    """
    if tags is None:
        tags = []

    def decorator(func: Callable) -> Callable:
        # Extract function signature
        sig = inspect.signature(func)
        func_params = list(sig.parameters.keys())

        # Collect parameters from @param decorators (if any)
        # Decorators are applied bottom-up, so parameters are in reverse order
        pending_params = []
        if hasattr(func, '_pending_parameters'):
            pending_params = list(reversed(func._pending_parameters))
            delattr(func, '_pending_parameters')  # Clean up

        # Initialize metadata
        metadata = WorkflowMetadata(
            name=name,
            description=description,
            category=category,
            tags=tags,
            execution_mode=execution_mode,
            timeout_seconds=timeout_seconds,
            max_duration_seconds=max_duration_seconds,
            retry_policy=retry_policy,
            schedule=schedule,
            requires_org=requires_org,
            expose_in_forms=expose_in_forms,
            requires_approval=requires_approval,
            required_permission=required_permission,
            parameters=pending_params,
            function=func
        )

        # Store metadata in function
        func._workflow_metadata = metadata

        # Register with registry
        registry = get_registry()
        registry.register_workflow(metadata)

        logger.debug(
            f"Workflow decorator applied: {name} "
            f"({len(pending_params)} params, requires_org={requires_org})"
        )

        # Return function unchanged (for normal Python execution)
        # No need for wrapper since we're not modifying behavior
        return func

    return decorator


def param(
    name: str,
    type: str,
    label: Optional[str] = None,
    required: bool = False,
    validation: Optional[Dict[str, Any]] = None,
    data_provider: Optional[str] = None,
    default_value: Optional[Any] = None,
    help_text: Optional[str] = None
):
    """
    Decorator for defining workflow parameters with metadata

    Must be used WITH @workflow decorator (decorators are applied bottom-up).
    Can be chained multiple times for multiple parameters.

    Usage:
        @workflow(name="my_workflow", description="...")
        @param("user_email", type="email", label="User Email", required=True,
               validation={"pattern": r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$"})
        @param("license", type="string", label="License Type",
               data_provider="get_available_licenses")
        async def my_workflow(context, user_email, license):
            pass

    Args:
        name: Parameter name (must match function parameter)
        type: Parameter type (string, int, bool, float, json, list, email)
        label: Display label for UI (defaults to title case of name)
        required: Whether parameter is required
        validation: Validation rules dict (e.g., {"min": 0, "max": 100, "pattern": "..."})
        data_provider: Name of data provider for dynamic options
        default_value: Default value if not provided
        help_text: Help text for UI

    Returns:
        Decorated function
    """
    # Validate parameter type
    if type not in VALID_PARAM_TYPES:
        raise ValueError(
            f"Invalid parameter type '{type}'. Must be one of: {', '.join(VALID_PARAM_TYPES)}"
        )

    def decorator(func: Callable) -> Callable:
        # Create parameter metadata
        param_meta = WorkflowParameter(
            name=name,
            type=type,
            label=label or name.replace('_', ' ').title(),
            required=required,
            validation=validation,
            data_provider=data_provider,
            default_value=default_value,
            help_text=help_text
        )

        # Store parameters on function temporarily (will be collected by @workflow)
        # Since decorators are applied bottom-up, we append in reverse order
        if not hasattr(func, '_pending_parameters'):
            func._pending_parameters = []

        func._pending_parameters.append(param_meta)

        logger.debug(
            f"Parameter '{name}' pending for function '{func.__name__}' "
            f"(type={type}, required={required})"
        )

        return func

    return decorator


def data_provider(
    name: str,
    description: str,
    category: str = "General",
    cache_ttl_seconds: int = 300
):
    """
    Decorator for registering data provider functions

    Data providers return dynamic options for form fields.

    Usage:
        @data_provider(
            name="get_available_licenses",
            description="Returns available M365 licenses for the organization",
            category="m365",
            cache_ttl_seconds=300
        )
        async def get_available_licenses(context):
            graph = context.get_integration('msgraph')
            skus = await graph.subscribed_skus.get()

            return [
                {
                    "label": sku.sku_part_number,
                    "value": sku.sku_id,
                    "metadata": {"available": sku.prepaid_units.enabled - sku.consumed_units}
                }
                for sku in skus.value
                if sku.prepaid_units.enabled > sku.consumed_units
            ]

    Args:
        name: Unique data provider identifier (snake_case)
        description: Human-readable description
        category: Category for organization (default: "General")
        cache_ttl_seconds: Cache TTL in seconds (default: 300 = 5 minutes)

    Returns:
        Decorated function (unchanged for normal Python execution)
    """
    def decorator(func: Callable) -> Callable:
        # Create metadata
        metadata = DataProviderMetadata(
            name=name,
            description=description,
            category=category,
            cache_ttl_seconds=cache_ttl_seconds,
            function=func
        )

        # Store metadata on function
        func._data_provider_metadata = metadata

        # Register with registry
        registry = get_registry()
        registry.register_data_provider(metadata)

        logger.debug(
            f"Data provider decorator applied: {name} "
            f"(cache_ttl={cache_ttl_seconds}s)"
        )

        # Return function unchanged
        return func

    return decorator
