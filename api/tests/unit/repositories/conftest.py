"""Shared fixtures for repository unit tests"""

import pytest
from unittest.mock import MagicMock, patch, call
from azure.core.exceptions import ResourceNotFoundError


@pytest.fixture
def mock_table_service():
    """Mock TableStorageService for all repository tests

    This fixture patches TableStorageService in all modules where it's imported:
    - shared.repositories.base (imported in BaseRepository)
    - shared.repositories.forms (imported in FormRepository)
    - shared.repositories.users (imported in UserRepository)
    - shared.repositories.config (imported in ConfigRepository)
    - etc.

    The mock simulates the real TableStorageService behavior:
    - get_entity returns None when entity not found (doesn't raise)
    - query_entities returns an empty iterator when no results
    - Other methods can raise exceptions as configured in tests
    """
    # Create mock instance with default behaviors
    instance = MagicMock()
    instance.get_entity.return_value = None
    instance.query_entities.return_value = iter([])
    instance.insert_entity.return_value = None
    instance.update_entity.return_value = None
    instance.upsert_entity.return_value = None
    instance.delete_entity.return_value = True

    # Patch all modules that directly import TableStorageService
    patches = [
        patch("shared.repositories.base.TableStorageService"),
        patch("shared.repositories.forms.TableStorageService"),
        patch("shared.repositories.users.TableStorageService"),
        patch("shared.repositories.roles.TableStorageService"),
        patch("shared.repositories.executions.TableStorageService"),
    ]

    with patches[0] as mock1, \
         patches[1] as mock2, \
         patches[2] as mock3, \
         patches[3] as mock4, \
         patches[4] as mock5:

        # Configure all mocks to return the same instance
        for mock in [mock1, mock2, mock3, mock4, mock5]:
            mock.return_value = instance

        yield instance


@pytest.fixture
def mock_context():
    """Mock RequestContext for scoped repositories"""
    context = MagicMock()
    context.org_id = "test-org-123"
    context.user_id = "test-user-456"
    context.scope = "test-org-123"
    context.caller = MagicMock()
    context.caller.email = "test@example.com"
    return context


@pytest.fixture
def sample_form_data():
    """Sample form data for testing"""
    return {
        "name": "User Onboarding",
        "description": "Onboard new users",
        "fields": [
            {
                "type": "text",
                "name": "email",
                "label": "Email Address",
                "required": True,
            },
            {"type": "text", "name": "name", "label": "Full Name", "required": True},
        ],
    }


@pytest.fixture
def sample_organization_data():
    """Sample organization data for testing"""
    return {
        "name": "Test Organization",
        "config": {
            "default_license": "O365_E3",
            "welcome_email_template": "welcome_v1",
        },
    }


@pytest.fixture
def sample_user_data():
    """Sample user data for testing"""
    return {
        "email": "test@example.com",
        "first_name": "Test",
        "last_name": "User",
        "password": "SecurePassword123!",
    }


@pytest.fixture
def sample_execution_data():
    """Sample execution data for testing"""
    return {
        "workflow_id": "workflow-123",
        "org_id": "test-org-123",
        "user_id": "test-user-456",
        "input_data": {"key": "value"},
        "status": "PENDING",
    }
