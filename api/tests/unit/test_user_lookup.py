"""
Unit tests for user_lookup module (pure business logic)

Tests user existence checks and organization lookups with mocked repositories.
"""

import pytest
from unittest.mock import Mock, patch

from shared.models import User, UserType
from shared.user_lookup import ensure_user_exists_in_db, get_user_organization
import shared.user_lookup as user_lookup_module


@pytest.fixture(autouse=True)
def clear_user_caches():
    """Clear in-memory user and org caches before each test"""
    # Clear caches before test
    user_lookup_module._user_cache.clear()
    user_lookup_module._org_cache.clear()
    yield
    # Clear caches after test
    user_lookup_module._user_cache.clear()
    user_lookup_module._org_cache.clear()


class TestEnsureUserExistsInDb:
    """Test ensure_user_exists_in_db function with mocked UserRepository"""

    @pytest.fixture
    def mock_user_repo(self):
        """Mock UserRepository for testing"""
        with patch("shared.user_lookup.UserRepository") as mock:
            yield mock.return_value

    def test_existing_user_updates_last_login(self, mock_user_repo):
        """Existing user should have last login updated"""
        # Arrange
        existing_user = Mock(spec=User)
        existing_user.email = "user@example.com"
        mock_user_repo.get_user.return_value = existing_user

        # Act
        ensure_user_exists_in_db("user@example.com", is_platform_admin=False)

        # Assert
        mock_user_repo.get_user.assert_called_once_with("user@example.com")
        mock_user_repo.update_last_login.assert_called_once_with("user@example.com")
        mock_user_repo.create_user.assert_not_called()

    def test_creates_platform_admin_user(self, mock_user_repo):
        """Non-existent platform admin should be created"""
        # Arrange
        mock_user_repo.get_user.return_value = None

        # Act
        ensure_user_exists_in_db("admin@example.com", is_platform_admin=True)

        # Assert
        mock_user_repo.create_user.assert_called_once_with(
            email="admin@example.com",
            display_name="admin",
            user_type=UserType.PLATFORM,
            is_platform_admin=True
        )

    def test_creates_org_user(self, mock_user_repo):
        """Non-existent org user should be created"""
        # Arrange
        mock_user_repo.get_user.return_value = None

        # Act
        with patch("shared.user_provisioning._provision_org_relationship_by_domain") as mock_provision:
            mock_provision.return_value = "org-123"
            ensure_user_exists_in_db("user@example.com", is_platform_admin=False)

        # Assert
        mock_user_repo.create_user.assert_called_once_with(
            email="user@example.com",
            display_name="user",
            user_type=UserType.ORG,
            is_platform_admin=False
        )

    def test_org_user_auto_provisions_relationship(self, mock_user_repo):
        """New org user should attempt domain-based org relationship provisioning"""
        # Arrange
        mock_user_repo.get_user.return_value = None

        # Act
        with patch("shared.user_provisioning._provision_org_relationship_by_domain") as mock_provision:
            mock_provision.return_value = "org-123"
            ensure_user_exists_in_db("user@acme.com", is_platform_admin=False)

            # Assert
            mock_provision.assert_called_once_with("user@acme.com")

    def test_org_user_handles_provision_failure_gracefully(self, mock_user_repo):
        """If org relationship provisioning fails, should log but not raise"""
        # Arrange
        mock_user_repo.get_user.return_value = None

        # Act - should not raise
        with patch("shared.user_provisioning._provision_org_relationship_by_domain") as mock_provision:
            mock_provision.side_effect = ValueError("No matching domain")
            ensure_user_exists_in_db("user@nowhere.com", is_platform_admin=False)

        # Assert - user still created
        mock_user_repo.create_user.assert_called_once()


class TestGetUserOrganization:
    """Test get_user_organization function with mocked UserRepository"""

    @pytest.fixture
    def mock_user_repo(self):
        """Mock UserRepository for testing"""
        with patch("shared.user_lookup.UserRepository") as mock:
            yield mock.return_value

    def test_returns_org_id_for_user(self, mock_user_repo):
        """Should return org_id when user has assignment"""
        # Arrange
        mock_user_repo.get_user_org_id.return_value = "org-123"

        # Act
        result = get_user_organization("user@example.com")

        # Assert
        assert result == "org-123"
        mock_user_repo.get_user_org_id.assert_called_once_with("user@example.com")

    def test_returns_none_for_no_org(self, mock_user_repo):
        """Should return None when user has no org assignment"""
        # Arrange
        mock_user_repo.get_user_org_id.return_value = None

        # Act
        result = get_user_organization("user@example.com")

        # Assert
        assert result is None

    def test_handles_query_error(self, mock_user_repo):
        """Should return None and log error on query failure"""
        # Arrange
        mock_user_repo.get_user_org_id.side_effect = Exception("Database error")

        # Act
        result = get_user_organization("user@example.com")

        # Assert
        assert result is None
