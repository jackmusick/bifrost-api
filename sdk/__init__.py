"""
Bifrost SDK - Python SDK for workflow and script development

The SDK provides a modern, context-aware API for:
- Configuration management (config module)
- Secret management (secrets module)
- OAuth connection management (oauth module)
- File operations (files module)
- Execution management (executions module)
- And more...

All SDK modules use context variables to automatically access the current execution context.
"""

__all__ = [
    "config",
    "secrets",
    "oauth",
]
