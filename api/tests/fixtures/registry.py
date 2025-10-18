"""
Registry isolation fixture for unit tests.

Provides completely isolated WorkflowRegistry for each test,
preventing global state pollution between tests.
"""

import pytest


@pytest.fixture
def isolated_registry(monkeypatch):
    """
    Provides completely isolated WorkflowRegistry for each test.
    No shared state between tests.

    This fixture:
    1. Creates a new registry instance (bypassing singleton)
    2. Patches all get_registry() calls to return this instance
    3. Automatically cleans up via monkeypatch

    Args:
        monkeypatch: pytest monkeypatch fixture

    Returns:
        WorkflowRegistry: Fresh registry instance for test

    Example:
        >>> def test_registry_isolation(isolated_registry):
        ...     registry = isolated_registry
        ...     registry.register_workflow("test", lambda: None)
        ...     assert "test" in registry._workflows
    """
    from shared.registry import WorkflowRegistry

    # Create new instance bypassing singleton
    reg = object.__new__(WorkflowRegistry)
    reg._workflows = {}
    reg._data_providers = {}
    reg._initialized = True

    # Patch all get_registry() calls to return our isolated instance
    monkeypatch.setattr("shared.registry.get_registry", lambda: reg)
    monkeypatch.setattr("shared.decorators.get_registry", lambda: reg)

    # Cleanup automatic via monkeypatch
    yield reg
