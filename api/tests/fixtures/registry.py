"""
Discovery isolation fixture for unit tests.

Provides isolated mocks for the discovery module in each test,
preventing global state pollution between tests.
"""

import pytest
from unittest.mock import MagicMock


@pytest.fixture
def isolated_registry(monkeypatch):
    """
    DEPRECATED: Use mock_discovery fixture instead.

    This fixture is kept for backward compatibility but now mocks
    the discovery module instead of the old registry.

    Args:
        monkeypatch: pytest monkeypatch fixture

    Returns:
        MagicMock: Mock discovery module
    """
    mock = MagicMock()
    mock.scan_all_workflows = MagicMock(return_value=[])
    mock.scan_all_data_providers = MagicMock(return_value=[])
    mock.scan_all_forms = MagicMock(return_value=[])
    mock.load_workflow = MagicMock(return_value=None)
    mock.load_data_provider = MagicMock(return_value=None)
    mock.load_form = MagicMock(return_value=None)

    # Patch discovery functions
    monkeypatch.setattr("shared.discovery.scan_all_workflows", mock.scan_all_workflows)
    monkeypatch.setattr("shared.discovery.scan_all_data_providers", mock.scan_all_data_providers)
    monkeypatch.setattr("shared.discovery.scan_all_forms", mock.scan_all_forms)
    monkeypatch.setattr("shared.discovery.load_workflow", mock.load_workflow)
    monkeypatch.setattr("shared.discovery.load_data_provider", mock.load_data_provider)
    monkeypatch.setattr("shared.discovery.load_form", mock.load_form)

    yield mock


@pytest.fixture
def mock_discovery(monkeypatch):
    """
    Provides isolated mocks for the discovery module.

    This fixture:
    1. Creates mock functions for all discovery operations
    2. Patches all discovery module functions
    3. Automatically cleans up via monkeypatch

    Args:
        monkeypatch: pytest monkeypatch fixture

    Returns:
        MagicMock: Mock object with all discovery functions

    Example:
        >>> def test_with_mock_discovery(mock_discovery):
        ...     from shared.discovery import WorkflowMetadata
        ...     mock_workflow = WorkflowMetadata(name="test", ...)
        ...     mock_discovery.scan_all_workflows.return_value = [mock_workflow]
        ...     mock_discovery.load_workflow.return_value = (lambda: None, mock_workflow)
    """
    mock = MagicMock()
    mock.scan_all_workflows = MagicMock(return_value=[])
    mock.scan_all_data_providers = MagicMock(return_value=[])
    mock.scan_all_forms = MagicMock(return_value=[])
    mock.load_workflow = MagicMock(return_value=None)
    mock.load_data_provider = MagicMock(return_value=None)
    mock.load_form = MagicMock(return_value=None)
    mock.get_form_metadata = MagicMock(return_value=None)
    mock.get_forms_by_workflow = MagicMock(return_value=[])

    # Patch discovery functions
    monkeypatch.setattr("shared.discovery.scan_all_workflows", mock.scan_all_workflows)
    monkeypatch.setattr("shared.discovery.scan_all_data_providers", mock.scan_all_data_providers)
    monkeypatch.setattr("shared.discovery.scan_all_forms", mock.scan_all_forms)
    monkeypatch.setattr("shared.discovery.load_workflow", mock.load_workflow)
    monkeypatch.setattr("shared.discovery.load_data_provider", mock.load_data_provider)
    monkeypatch.setattr("shared.discovery.load_form", mock.load_form)
    monkeypatch.setattr("shared.discovery.get_form_metadata", mock.get_form_metadata)
    monkeypatch.setattr("shared.discovery.get_forms_by_workflow", mock.get_forms_by_workflow)

    yield mock
