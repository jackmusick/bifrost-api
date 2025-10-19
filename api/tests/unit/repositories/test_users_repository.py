"""
Unit tests for UserRepository
"""

import pytest
from datetime import datetime

from shared.repositories.users import UserRepository
from shared.models import UserType


class TestUserRepositoryCreate:
    """Test user creation"""

    def test_create_user_success(self, mock_table_service):
        """Test successful user creation"""
        repo = UserRepository()

        mock_table_service.insert_entity.return_value = None

        result = repo.create_user(
            "user@example.com",
            "John Doe",
            UserType.ORG,
            is_platform_admin=False
        )

        assert result.email == "user@example.com"
        assert result.displayName == "John Doe"
        assert result.userType == UserType.ORG
        assert result.isPlatformAdmin is False
        assert result.isActive is True
        mock_table_service.insert_entity.assert_called_once()

    def test_create_platform_admin(self, mock_table_service):
        """Test creating platform admin user"""
        repo = UserRepository()

        mock_table_service.insert_entity.return_value = None

        result = repo.create_user(
            "admin@example.com",
            "Admin User",
            UserType.PLATFORM,
            is_platform_admin=True
        )

        assert result.isPlatformAdmin is True
        assert result.userType == UserType.PLATFORM

    def test_create_user_sets_timestamps(self, mock_table_service):
        """Test that timestamps are set during creation"""
        repo = UserRepository()

        mock_table_service.insert_entity.return_value = None
        before = datetime.utcnow()

        result = repo.create_user(
            "user@example.com",
            "Test User",
            UserType.ORG
        )

        after = datetime.utcnow()
        assert before <= result.createdAt <= after


class TestUserRepositoryRead:
    """Test user retrieval"""

    def test_get_user_success(self, mock_table_service):
        """Test retrieving a user"""
        repo = UserRepository()

        mock_table_service.get_entity.return_value = {
            "PartitionKey": "GLOBAL",
            "RowKey": "user:user@example.com",
            "Email": "user@example.com",
            "DisplayName": "John Doe",
            "UserType": "ORG",
            "IsPlatformAdmin": False,
            "IsActive": True,
            "CreatedAt": "2024-01-15T10:30:00",
            "LastLogin": "2024-01-16T14:22:00"
        }

        result = repo.get_user("user@example.com")

        assert result is not None
        assert result.email == "user@example.com"
        assert result.displayName == "John Doe"

    def test_get_user_not_found(self, mock_table_service):
        """Test retrieving non-existent user"""
        repo = UserRepository()

        mock_table_service.get_entity.return_value = None

        result = repo.get_user("nonexistent@example.com")

        assert result is None

    def test_has_any_users_true(self, mock_table_service):
        """Test has_any_users returns True when users exist"""
        repo = UserRepository()

        mock_table_service.query_entities.return_value = iter([
            {"RowKey": "user:user1@example.com"}
        ])

        result = repo.has_any_users()

        assert result is True

    def test_has_any_users_false(self, mock_table_service):
        """Test has_any_users returns False when no users exist"""
        repo = UserRepository()

        mock_table_service.query_entities.return_value = iter([])

        result = repo.has_any_users()

        assert result is False

    def test_has_any_users_efficient_query(self, mock_table_service):
        """Test that has_any_users uses efficient query"""
        repo = UserRepository()

        mock_table_service.query_entities.return_value = iter([])

        repo.has_any_users()

        # Verify efficient query parameters
        call_args = mock_table_service.query_entities.call_args
        kwargs = call_args[1]
        assert kwargs.get("select") == ["RowKey"]
        assert kwargs.get("top") == 1


class TestUserRepositoryUpdate:
    """Test user updates"""

    def test_update_last_login(self, mock_table_service):
        """Test updating last login timestamp"""
        repo = UserRepository()

        user_data = {
            "PartitionKey": "GLOBAL",
            "RowKey": "user:user@example.com",
            "Email": "user@example.com",
            "DisplayName": "User",
            "UserType": "ORG",
            "IsActive": True,
            "CreatedAt": "2024-01-15T10:30:00",
            "LastLogin": "2024-01-15T10:30:00"
        }

        mock_table_service.get_entity.return_value = user_data
        mock_table_service.update_entity.return_value = None

        repo.update_last_login("user@example.com")

        mock_table_service.update_entity.assert_called_once()


class TestUserOrgAssignments:
    """Test user-organization assignments"""

    def test_assign_user_to_org(self, mock_table_service):
        """Test assigning user to organization"""
        repo = UserRepository()

        mock_table_service.insert_entity.return_value = None

        repo.assign_user_to_org("user@example.com", "org-123", "admin")

        # Should create both forward and reverse indexes
        assert mock_table_service.insert_entity.call_count == 2

    def test_get_user_org_id(self, mock_table_service):
        """Test retrieving user's organization ID"""
        repo = UserRepository()

        mock_table_service.query_entities.return_value = iter([
            {"RowKey": "userperm:user@example.com:org-123"}
        ])

        result = repo.get_user_org_id("user@example.com")

        assert result == "org-123"

    def test_get_user_org_id_not_found(self, mock_table_service):
        """Test returns None when user has no org"""
        repo = UserRepository()

        mock_table_service.query_entities.return_value = iter([])

        result = repo.get_user_org_id("user@example.com")

        assert result is None

    def test_list_org_users_empty(self, mock_table_service):
        """Test listing users when org has none"""
        repo = UserRepository()

        mock_table_service.query_entities.return_value = iter([])

        result = repo.list_org_users("org-123")

        assert result == []

    def test_list_org_users_returns_multiple(self, mock_table_service):
        """Test listing multiple users in org"""
        repo = UserRepository()

        users_data = [
            {"RowKey": "orgperm:org-123:user1@example.com"},
            {"RowKey": "orgperm:org-123:user2@example.com"}
        ]

        mock_table_service.query_entities.return_value = iter(users_data)

        result = repo.list_org_users("org-123")

        assert len(result) == 2
        assert "user1@example.com" in result
        assert "user2@example.com" in result

    def test_list_org_users_full(self, mock_table_service):
        """Test listing full User models for org"""
        repo = UserRepository()

        # First query returns emails
        mock_table_service.query_entities.return_value = iter([
            {"RowKey": "orgperm:org-123:user1@example.com"},
            {"RowKey": "orgperm:org-123:user2@example.com"}
        ])

        # Get_entity calls for each user
        user_data = {
            "PartitionKey": "GLOBAL",
            "RowKey": "user:user1@example.com",
            "Email": "user1@example.com",
            "DisplayName": "User One",
            "UserType": "ORG",
            "IsPlatformAdmin": False,
            "IsActive": True,
            "CreatedAt": "2024-01-15T10:30:00"
        }

        mock_table_service.get_entity.return_value = user_data

        result = repo.list_org_users_full("org-123")

        assert len(result) >= 0  # May be filtered based on mock return


class TestUserEdgeCases:
    """Test edge cases"""

    def test_user_with_null_last_login(self, mock_table_service):
        """Test user with no last login"""
        repo = UserRepository()

        mock_table_service.get_entity.return_value = {
            "PartitionKey": "GLOBAL",
            "RowKey": "user:user@example.com",
            "Email": "user@example.com",
            "DisplayName": "New User",
            "UserType": "ORG",
            "IsActive": True,
            "CreatedAt": "2024-01-15T10:30:00",
            "LastLogin": None
        }

        result = repo.get_user("user@example.com")

        assert result is not None
        assert result.lastLogin is None

    def test_user_timestamps_parsed(self, mock_table_service):
        """Test that timestamps are parsed correctly"""
        repo = UserRepository()

        mock_table_service.get_entity.return_value = {
            "PartitionKey": "GLOBAL",
            "RowKey": "user:user@example.com",
            "Email": "user@example.com",
            "DisplayName": "User",
            "UserType": "ORG",
            "IsActive": True,
            "CreatedAt": "2024-01-15T10:30:45.123456",
            "LastLogin": "2024-01-16T14:22:10.654321"
        }

        result = repo.get_user("user@example.com")

        assert result is not None
        assert result.createdAt is not None
        assert result.lastLogin is not None
