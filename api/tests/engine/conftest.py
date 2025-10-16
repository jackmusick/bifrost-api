"""
Pytest fixtures for Engine tests
Extends parent conftest and adds engine-specific fixtures
"""

import os
import sys

import pytest

# Ensure api directory is on path
api_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
if api_dir not in sys.path:
    sys.path.insert(0, api_dir)

# Now we can import from both shared and engine.shared
from shared.registry import get_registry
from shared.storage import TableStorageService as EngineTableStorage

# Re-export parent fixtures by importing
from tests.conftest import *  # noqa: F401, F403


# Engine-specific fixtures
@pytest.fixture
def engine_registry():
    """Get the engine registry for workflow tests"""
    return get_registry()


@pytest.fixture
def engine_table_service(azurite_tables):  # noqa: F405
    """Returns engine TableStorageService"""
    return EngineTableStorage("WorkflowExecutions")
