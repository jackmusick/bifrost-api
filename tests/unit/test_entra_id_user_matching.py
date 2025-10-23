"""
Unit tests for Entra ID user matching and profile updates
Tests the dual lookup strategy: Entra ID first, then email
"""

from datetime import datetime
from unittest.mock import Mock, patch


from shared.models import User, UserType
from shared.user_provisioning import ensure_user_provisioned


class TestEntraIdLookupStrategy:
    """Test Entra ID lookup takes precedence over email"""

    @patch("shared.user_provisioning.UserRepository")
    def test_lookup_by_entra_id_finds_user(self, mock_repo_class):
        """When Entra ID provided, lookup by Entra ID first"""
        mock_repo = Mock()
        mock_repo_class.return_value = mock_repo

        mock_user = User(
            id="user@example.com",
            email="user@example.com",
            displayName="Test User",
            userType=UserType.ORG,
            isPlatformAdmin=False,
            isActive=True,
            createdAt=datetime.utcnow(),
            entraUserId="entra-123"
        )
        mock_repo.get_user_by_entra_id.return_value = mock_user
        mock_repo.get_user_org_id.return_value = "org-123"

        result = ensure_user_provisioned(
            user_email="user@example.com",
            entra_user_id="entra-123"
        )

        # Should call get_user_by_entra_id, NOT get_user
        mock_repo.get_user_by_entra_id.assert_called_once_with("entra-123")
        mock_repo.get_user.assert_not_called()
        assert result.was_created is False

    @patch("shared.user_provisioning.UserRepository")
    def test_fallback_to_email_when_entra_not_found(self, mock_repo_class):
        """If Entra ID lookup fails, fall back to email lookup"""
        mock_repo = Mock()
        mock_repo_class.return_value = mock_repo

        mock_user = User(
            id="user@example.com",
            email="user@example.com",
            displayName="Test User",
            userType=UserType.ORG,
            isPlatformAdmin=False,
            isActive=True,
            createdAt=datetime.utcnow(),
            entraUserId=None
        )
        mock_repo.get_user_by_entra_id.return_value = None
        mock_repo.get_user.return_value = mock_user
        mock_repo.get_user_org_id.return_value = "org-123"

        result = ensure_user_provisioned(
            user_email="user@example.com",
            entra_user_id="entra-123"
        )

        # Should try Entra ID first, then email
        mock_repo.get_user_by_entra_id.assert_called_once_with("entra-123")
        mock_repo.get_user.assert_called_once_with("user@example.com")
        assert result.was_created is False


class TestEntraIdBackfill:
    """Test backfilling Entra ID when user found by email"""

    @patch("shared.user_provisioning.UserRepository")
    def test_backfill_entra_id_when_missing(self, mock_repo_class):
        """When user found by email but no Entra ID, backfill it"""
        mock_repo = Mock()
        mock_repo_class.return_value = mock_repo

        mock_user = User(
            id="user@example.com",
            email="user@example.com",
            displayName="Test User",
            userType=UserType.PLATFORM,
            isPlatformAdmin=True,
            isActive=True,
            createdAt=datetime.utcnow(),
            entraUserId=None  # No Entra ID stored
        )
        mock_repo.get_user_by_entra_id.return_value = None
        mock_repo.get_user.return_value = mock_user

        ensure_user_provisioned(
            user_email="user@example.com",
            entra_user_id="entra-new-123"
        )

        # Should backfill the Entra ID
        mock_repo.update_user_entra_id.assert_called_once_with(
            "user@example.com",
            "entra-new-123"
        )

    @patch("shared.user_provisioning.UserRepository")
    def test_no_backfill_when_entra_id_exists(self, mock_repo_class):
        """When user has Entra ID, don't backfill"""
        mock_repo = Mock()
        mock_repo_class.return_value = mock_repo

        mock_user = User(
            id="user@example.com",
            email="user@example.com",
            displayName="Test User",
            userType=UserType.PLATFORM,
            isPlatformAdmin=True,
            isActive=True,
            createdAt=datetime.utcnow(),
            entraUserId="entra-existing"
        )
        mock_repo.get_user_by_entra_id.return_value = None
        mock_repo.get_user.return_value = mock_user

        ensure_user_provisioned(
            user_email="user@example.com",
            entra_user_id="entra-new-123"
        )

        # Should NOT backfill
        mock_repo.update_user_entra_id.assert_not_called()


class TestProfileUpdates:
    """Test profile updates when matched by Entra ID"""

    @patch("shared.user_provisioning.UserRepository")
    def test_update_email_when_changed(self, mock_repo_class):
        """When email changes, update user profile"""
        mock_repo = Mock()
        mock_repo_class.return_value = mock_repo

        old_user = User(
            id="old@example.com",
            email="old@example.com",
            displayName="Test User",
            userType=UserType.ORG,
            isPlatformAdmin=False,
            isActive=True,
            createdAt=datetime.utcnow(),
            entraUserId="entra-123"
        )
        updated_user = User(
            id="new@example.com",
            email="new@example.com",
            displayName="Test User",
            userType=UserType.ORG,
            isPlatformAdmin=False,
            isActive=True,
            createdAt=datetime.utcnow(),
            entraUserId="entra-123"
        )
        mock_repo.get_user_by_entra_id.return_value = old_user
        mock_repo.update_user_profile.return_value = updated_user
        mock_repo.get_user_org_id.return_value = "org-123"

        ensure_user_provisioned(
            user_email="new@example.com",
            entra_user_id="entra-123",
            display_name="Test User"
        )

        # Should update profile
        mock_repo.update_user_profile.assert_called_once_with(
            old_email="old@example.com",
            new_email="new@example.com",
            display_name="Test User"
        )

    @patch("shared.user_provisioning.UserRepository")
    def test_update_display_name_when_changed(self, mock_repo_class):
        """When display name changes, update user profile"""
        mock_repo = Mock()
        mock_repo_class.return_value = mock_repo

        old_user = User(
            id="user@example.com",
            email="user@example.com",
            displayName="Old Name",
            userType=UserType.ORG,
            isPlatformAdmin=False,
            isActive=True,
            createdAt=datetime.utcnow(),
            entraUserId="entra-123"
        )
        updated_user = User(
            id="user@example.com",
            email="user@example.com",
            displayName="New Name",
            userType=UserType.ORG,
            isPlatformAdmin=False,
            isActive=True,
            createdAt=datetime.utcnow(),
            entraUserId="entra-123"
        )
        mock_repo.get_user_by_entra_id.return_value = old_user
        mock_repo.update_user_profile.return_value = updated_user
        mock_repo.get_user_org_id.return_value = "org-123"

        ensure_user_provisioned(
            user_email="user@example.com",
            entra_user_id="entra-123",
            display_name="New Name"
        )

        # Should update profile
        mock_repo.update_user_profile.assert_called_once_with(
            old_email="user@example.com",
            new_email="user@example.com",
            display_name="New Name"
        )

    @patch("shared.user_provisioning.UserRepository")
    def test_no_update_when_profile_unchanged(self, mock_repo_class):
        """When profile unchanged, don't update"""
        mock_repo = Mock()
        mock_repo_class.return_value = mock_repo

        mock_user = User(
            id="user@example.com",
            email="user@example.com",
            displayName="Test User",
            userType=UserType.ORG,
            isPlatformAdmin=False,
            isActive=True,
            createdAt=datetime.utcnow(),
            entraUserId="entra-123"
        )
        mock_repo.get_user_by_entra_id.return_value = mock_user
        mock_repo.get_user_org_id.return_value = "org-123"

        ensure_user_provisioned(
            user_email="user@example.com",
            entra_user_id="entra-123",
            display_name="Test User"
        )

        # Should NOT update profile
        mock_repo.update_user_profile.assert_not_called()


class TestNewUserCreationWithEntraId:
    """Test creating new users with Entra ID"""

    @patch("shared.user_provisioning.OrganizationRepository")
    @patch("shared.user_provisioning.UserRepository")
    def test_create_first_user_with_entra_id(self, mock_user_repo_class, mock_org_repo_class):
        """First user created with Entra ID stored"""
        mock_user_repo = Mock()
        mock_user_repo_class.return_value = mock_user_repo

        mock_user_repo.get_user_by_entra_id.return_value = None
        mock_user_repo.get_user.return_value = None
        mock_user_repo.has_any_users.return_value = False

        result = ensure_user_provisioned(
            user_email="first@example.com",
            entra_user_id="entra-first",
            display_name="First User"
        )

        # Should create user with Entra ID
        mock_user_repo.create_user.assert_called_once_with(
            email="first@example.com",
            display_name="First User",
            user_type=UserType.PLATFORM,
            is_platform_admin=True,
            entra_user_id="entra-first"
        )
        assert result.was_created is True
        assert result.is_platform_admin is True

    @patch("shared.user_provisioning.OrganizationRepository")
    @patch("shared.user_provisioning.UserRepository")
    def test_create_org_user_with_entra_id(self, mock_user_repo_class, mock_org_repo_class):
        """New org user created with Entra ID"""
        from shared.models import Organization

        mock_user_repo = Mock()
        mock_org_repo = Mock()
        mock_user_repo_class.return_value = mock_user_repo
        mock_org_repo_class.return_value = mock_org_repo

        mock_org = Organization(
            id="org-123",
            name="Example Org",
            domain="example.com",
            isActive=True,
            createdAt=datetime.utcnow(),
            createdBy="system",
            updatedAt=datetime.utcnow()
        )

        mock_user_repo.get_user_by_entra_id.return_value = None
        mock_user_repo.get_user.return_value = None
        mock_user_repo.has_any_users.return_value = True
        mock_org_repo.get_organization_by_domain.return_value = mock_org

        result = ensure_user_provisioned(
            user_email="new@example.com",
            entra_user_id="entra-new",
            display_name="New User"
        )

        # Should create user with Entra ID
        mock_user_repo.create_user.assert_called_once_with(
            email="new@example.com",
            display_name="New User",
            user_type=UserType.ORG,
            is_platform_admin=False,
            entra_user_id="entra-new"
        )
        assert result.was_created is True
        assert result.org_id == "org-123"
