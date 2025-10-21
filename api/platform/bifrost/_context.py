"""
Execution context management for Bifrost SDK.

Provides ContextVar-based context propagation from workflow engine to SDK calls.
"""

from contextvars import ContextVar
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from shared.request_context import RequestContext

# Context variable for current execution context
# Set by workflow engine before executing user code
_execution_context: ContextVar['RequestContext | None'] = ContextVar(
    'bifrost_execution_context',
    default=None
)


def set_execution_context(context: 'RequestContext') -> None:
    """
    Set the execution context for the current workflow execution.

    Called by the workflow engine before executing user code.

    Args:
        context: RequestContext with user, org, and permission info
    """
    _execution_context.set(context)


def get_execution_context() -> 'RequestContext':
    """
    Get the current execution context.

    Returns:
        RequestContext for the current execution

    Raises:
        RuntimeError: If called outside of a workflow execution context
    """
    context = _execution_context.get()
    if context is None:
        raise RuntimeError(
            "No execution context found. "
            "The bifrost SDK can only be used within workflow executions."
        )
    return context


def clear_execution_context() -> None:
    """
    Clear the execution context.

    Called by the workflow engine after user code execution completes.
    """
    _execution_context.set(None)
