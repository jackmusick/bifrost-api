"""
Internal module for accessing the current execution context.

This module provides the _get_context() function that SDK modules use
to access the current ExecutionContext via context variables.
"""

from contextvars import ContextVar
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from shared.context import ExecutionContext

# Context variable to store the current execution context
_execution_context: ContextVar['ExecutionContext | None'] = ContextVar('execution_context', default=None)


def _get_context() -> 'ExecutionContext':
    """
    Get the current execution context.
    
    Returns:
        ExecutionContext: The current execution context
        
    Raises:
        RuntimeError: If no execution context is available
    """
    context = _execution_context.get()
    if context is None:
        raise RuntimeError(
            "No execution context available. "
            "SDK modules can only be used within workflow/provider execution."
        )
    return context


def _set_context(context: 'ExecutionContext') -> None:
    """
    Set the current execution context (internal use only).
    
    Args:
        context: The execution context to set
    """
    _execution_context.set(context)


def _clear_context() -> None:
    """Clear the current execution context (internal use only)."""
    _execution_context.set(None)
