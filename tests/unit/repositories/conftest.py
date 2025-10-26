"""Shared fixtures for repository unit tests"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture
def mock_table_service():
    """Mock AsyncTableStorageService for all repository tests

    This fixture patches AsyncTableStorageService in all modules where it's imported:
    - shared.repositories.base (imported in BaseRepository)
    - shared.repositories.forms (imported in FormRepository)
    - shared.repositories.users (imported in UserRepository)
    - shared.repositories.config (imported in ConfigRepository)
    - etc.

    The mock simulates the real AsyncTableStorageService behavior:
    - get_entity returns None when entity not found (doesn't raise)
    - query_entities returns an empty iterator when no results
    - Other methods can raise exceptions as configured in tests
    """
    # Create mock instance with default behaviors
    instance = AsyncMock()
    instance.get_entity.return_value = None
    instance.query_entities.return_value = iter([])
    instance.insert_entity.return_value = None
    instance.update_entity.return_value = None
    instance.upsert_entity.return_value = None
    instance.delete_entity.return_value = True

    # Patch AsyncTableStorageService at the module level
    with patch("shared.async_storage.AsyncTableStorageService") as mock_class:
        # Configure the mock to return the same instance
        mock_class.return_value = instance
        yield instance


@pytest.fixture
def mock_context():
    """Mock ExecutionContext for scoped repositories"""
    context = MagicMock()
    context.org_id = "test-org-123"
    context.user_id = "test-user-456"
    context.scope = "test-org-123"
    context.email = "test@example.com"
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
