"""
Unit tests for user auto-provisioning logic (shared/user_provisioning.py)
Tests first user detection, domain-based auto-join, and edge cases
"""

from datetime import datetime
from unittest.mock import Mock, patch

import pytest

from shared.user_provisioning import (
    UserProvisioningResult,
    _create_first_platform_admin,
    _get_user_org_id,
    _provision_user_by_domain,
    ensure_user_provisioned,
)


class TestEnsureUserProvisioned:
    """Test main ensure_user_provisioned function"""

    @patch("shared.user_provisioning.UserRepository")
    def test_existing_platform_admin_user(self, mock_user_repo_class):
        """Existing PlatformAdmin user returns correct status"""
        from shared.models import User, UserType

        mock_user_repo = Mock()
        mock_user_repo_class.return_value = mock_user_repo

        # Mock existing platform admin
        mock_user = User(
            id="admin@example.com",
            email="admin@example.com",
            displayName="admin",
            userType=UserType.PLATFORM,
            isPlatformAdmin=True,
            isActive=True,
            lastLogin=datetime.utcnow(),
            createdAt=datetime.utcnow()
        )
        mock_user_repo.get_user.return_value = mock_user

        result = ensure_user_provisioned("admin@example.com")

        assert result.user_type == "PLATFORM"
        assert result.is_platform_admin is True
        assert result.org_id is None
        assert result.was_created is False
        assert "PlatformAdmin" in result.roles
        assert "authenticated" in result.roles

        # Verify last login was updated
        mock_user_repo.update_last_login.assert_called_once_with("admin@example.com")

    @patch("shared.user_provisioning.UserRepository")
    def test_existing_org_user(self, mock_user_repo_class):
        """Existing ORG user returns correct status with org_id"""
        from shared.models import User, UserType

        mock_user_repo = Mock()
        mock_user_repo_class.return_value = mock_user_repo

        # Mock existing org user
        mock_user = User(
            id="user@company.com",
            email="user@company.com",
            displayName="user",
            userType=UserType.ORG,
            isPlatformAdmin=False,
            isActive=True,
            lastLogin=None,
            createdAt=datetime.utcnow()
        )
        mock_user_repo.get_user.return_value = mock_user
        mock_user_repo.get_user_org_id.return_value = "org-123"

        result = ensure_user_provisioned("user@company.com")

        assert result.user_type == "ORG"
        assert result.is_platform_admin is False
        assert result.org_id == "org-123"
        assert result.was_created is False
        assert "OrgUser" in result.roles
        assert "PlatformAdmin" not in result.roles

    @patch("shared.user_provisioning._create_first_platform_admin")
    @patch("shared.user_provisioning.UserRepository")
    def test_first_user_creation(self, mock_user_repo_class, mock_create_first):
        """First user in system is created as PlatformAdmin"""
        mock_user_repo = Mock()
        mock_user_repo_class.return_value = mock_user_repo

        # Mock user doesn't exist
        mock_user_repo.get_user.return_value = None

        # Mock has_any_users returns False (no users exist)
        mock_user_repo.has_any_users.return_value = False

        # Mock creation result
        mock_create_first.return_value = UserProvisioningResult(
            user_type="PLATFORM",
            is_platform_admin=True,
            org_id=None,
            was_created=True,
        )

        result = ensure_user_provisioned("first@example.com")

        assert result.user_type == "PLATFORM"
        assert result.is_platform_admin is True
        assert result.was_created is True
        mock_create_first.assert_called_once_with("first@example.com")

    @patch("shared.user_provisioning._provision_user_by_domain")
    @patch("shared.user_provisioning.UserRepository")
    def test_domain_based_provisioning(self, mock_user_repo_class, mock_provision):
        """Non-first user triggers domain-based provisioning"""
        mock_user_repo = Mock()
        mock_user_repo_class.return_value = mock_user_repo

        # Mock user doesn't exist
        mock_user_repo.get_user.return_value = None

        # Mock has_any_users returns True (users exist)
        mock_user_repo.has_any_users.return_value = True

        # Mock successful domain provisioning
        mock_provision.return_value = UserProvisioningResult(
            user_type="ORG", is_platform_admin=False, org_id="org-456", was_created=True
        )

        result = ensure_user_provisioned("newuser@company.com")

        assert result.user_type == "ORG"
        assert result.org_id == "org-456"
        assert result.was_created is True
        mock_provision.assert_called_once_with("newuser@company.com")

    def test_invalid_email_format(self):
        """Invalid email raises ValueError"""
        with pytest.raises(ValueError, match="Invalid email format"):
            ensure_user_provisioned("not-an-email")

        with pytest.raises(ValueError, match="Invalid email format"):
            ensure_user_provisioned("")

    @patch("shared.user_provisioning._provision_org_relationship_by_domain")
    @patch("shared.user_provisioning.UserRepository")
    def test_existing_org_user_without_relationship(
        self, mock_user_repo_class, mock_provision_relationship
    ):
        """Existing ORG user without org relationship gets auto-provisioned"""
        from shared.models import User, UserType

        mock_user_repo = Mock()
        mock_user_repo_class.return_value = mock_user_repo

        # Mock existing ORG user
        mock_user = User(
            id="orphan@company.com",
            email="orphan@company.com",
            displayName="orphan",
            userType=UserType.ORG,
            isPlatformAdmin=False,
            isActive=True,
            lastLogin=None,
            createdAt=datetime.utcnow()
        )
        mock_user_repo.get_user.return_value = mock_user

        # Mock no org assignment initially
        mock_user_repo.get_user_org_id.return_value = None

        # Mock successful relationship provisioning
        mock_provision_relationship.return_value = "org-999"

        result = ensure_user_provisioned("orphan@company.com")

        assert result.user_type == "ORG"
        assert result.is_platform_admin is False
        assert result.org_id == "org-999"
        assert result.was_created is False

        # Verify relationship provisioning was called
        mock_provision_relationship.assert_called_once_with("orphan@company.com")


class TestCreateFirstPlatformAdmin:
    """Test first user creation logic"""

    @patch("shared.user_provisioning.UserRepository")
    def test_creates_platform_admin_user(self, mock_user_repo_class):
        """First user is created with PlatformAdmin privileges"""
        from shared.models import User, UserType

        mock_user_repo = Mock()
        mock_user_repo_class.return_value = mock_user_repo

        # Mock the created user
        mock_user = User(
            id="first@example.com",
            email="first@example.com",
            displayName="first",
            userType=UserType.PLATFORM,
            isPlatformAdmin=True,
            isActive=True,
            lastLogin=None,
            createdAt=datetime.utcnow()
        )
        mock_user_repo.create_user.return_value = mock_user

        result = _create_first_platform_admin("first@example.com")

        assert result.user_type == "PLATFORM"
        assert result.is_platform_admin is True
        assert result.org_id is None
        assert result.was_created is True

        # Verify create_user was called with correct data
        mock_user_repo.create_user.assert_called_once_with(
            email="first@example.com",
            display_name="first",
            user_type=UserType.PLATFORM,
            is_platform_admin=True
        )


class TestProvisionUserByDomain:
    """Test domain-based auto-provisioning"""

    @patch("shared.user_provisioning.OrganizationRepository")
    @patch("shared.user_provisioning.UserRepository")
    def test_successful_domain_match(self, mock_user_repo_class, mock_org_repo_class):
        """User with matching domain is auto-provisioned to org"""
        from shared.models import User, Organization, UserType

        # Mock OrganizationRepository
        mock_org_repo = Mock()
        mock_org_repo_class.return_value = mock_org_repo

        # Mock matched organization
        mock_org = Organization(
            id="org-789",
            name="Company Inc",
            domain="company.com",
            isActive=True,
            createdAt=datetime.utcnow(),
            createdBy="system",
            updatedAt=datetime.utcnow()
        )
        mock_org_repo.get_organization_by_domain.return_value = mock_org

        # Mock UserRepository
        mock_user_repo = Mock()
        mock_user_repo_class.return_value = mock_user_repo

        # Mock created user
        mock_user = User(
            id="newuser@company.com",
            email="newuser@company.com",
            displayName="newuser",
            userType=UserType.ORG,
            isPlatformAdmin=False,
            isActive=True,
            lastLogin=None,
            createdAt=datetime.utcnow()
        )
        mock_user_repo.create_user.return_value = mock_user

        # Run the function
        result = _provision_user_by_domain("newuser@company.com")

        # Verify the assertions
        assert result.user_type == "ORG"
        assert result.is_platform_admin is False
        assert result.org_id == "org-789"
        assert result.was_created is True

        # Verify organization lookup was called with lowercase domain
        mock_org_repo.get_organization_by_domain.assert_called_once_with("company.com")

        # Verify user was created with correct details
        mock_user_repo.create_user.assert_called_once_with(
            email="newuser@company.com",
            display_name="newuser",
            user_type=UserType.ORG,
            is_platform_admin=False
        )

        # Verify relationship was created
        mock_user_repo.assign_user_to_org.assert_called_once_with(
            email="newuser@company.com",
            org_id="org-789",
            assigned_by="system"
        )

    @patch("shared.user_provisioning.OrganizationRepository")
    def test_no_matching_domain(self, mock_org_repo_class):
        """User with no matching domain raises ValueError"""
        mock_org_repo = Mock()
        mock_org_repo_class.return_value = mock_org_repo

        # Mock no matching organization
        mock_org_repo.get_organization_by_domain.return_value = None

        with pytest.raises(ValueError, match="No organization configured for domain"):
            _provision_user_by_domain("user@nomatch.com")

    @patch("shared.user_provisioning.OrganizationRepository")
    @patch("shared.user_provisioning.UserRepository")
    def test_case_insensitive_domain_matching(self, mock_user_repo_class, mock_org_repo_class):
        """Domain matching is case-insensitive"""
        from shared.models import User, Organization, UserType

        # Mock OrganizationRepository
        mock_org_repo = Mock()
        mock_org_repo_class.return_value = mock_org_repo

        # Mock matched organization with uppercase domain
        mock_org = Organization(
            id="org-999",
            name="Company",
            domain="COMPANY.COM",
            isActive=True,
            createdAt=datetime.utcnow(),
            createdBy="system",
            updatedAt=datetime.utcnow()
        )
        mock_org_repo.get_organization_by_domain.return_value = mock_org

        # Mock UserRepository
        mock_user_repo = Mock()
        mock_user_repo_class.return_value = mock_user_repo

        # Mock created user
        mock_user = User(
            id="user@company.com",
            email="user@company.com",
            displayName="user",
            userType=UserType.ORG,
            isPlatformAdmin=False,
            isActive=True,
            lastLogin=None,
            createdAt=datetime.utcnow()
        )
        mock_user_repo.create_user.return_value = mock_user

        # Run the function
        result = _provision_user_by_domain("user@company.com")

        # Verify the assertions
        assert result.org_id == "org-999"
        assert result.was_created is True

        # Verify organization lookup was called with lowercase domain
        mock_org_repo.get_organization_by_domain.assert_called_once_with("company.com")

        # Verify user was created with correct details
        mock_user_repo.create_user.assert_called_once_with(
            email="user@company.com",
            display_name="user",
            user_type=UserType.ORG,
            is_platform_admin=False
        )


class TestGetUserOrgId:
    """Test user org lookup helper"""

    @patch("shared.user_provisioning.UserRepository")
    def test_returns_org_id_for_user(self, mock_user_repo_class):
        """Returns org_id from UserRepository"""
        mock_user_repo = Mock()
        mock_user_repo_class.return_value = mock_user_repo

        mock_user_repo.get_user_org_id.return_value = "org-abc"

        org_id = _get_user_org_id("user@company.com")

        assert org_id == "org-abc"
        mock_user_repo.get_user_org_id.assert_called_once_with("user@company.com")

    @patch("shared.user_provisioning.UserRepository")
    def test_returns_none_for_no_org(self, mock_user_repo_class):
        """Returns None if user has no org assignments"""
        mock_user_repo = Mock()
        mock_user_repo_class.return_value = mock_user_repo

        mock_user_repo.get_user_org_id.return_value = None

        org_id = _get_user_org_id("orphan@example.com")

        assert org_id is None

    @patch("shared.user_provisioning.UserRepository")
    def test_handles_query_error(self, mock_user_repo_class):
        """Returns None on query error"""
        mock_user_repo = Mock()
        mock_user_repo_class.return_value = mock_user_repo

        mock_user_repo.get_user_org_id.side_effect = Exception("Database error")

        org_id = _get_user_org_id("user@example.com")

        assert org_id is None


class TestUserProvisioningResult:
    """Test UserProvisioningResult helper class"""

    def test_platform_admin_roles(self):
        """PlatformAdmin gets correct roles"""
        result = UserProvisioningResult(
            user_type="PLATFORM", is_platform_admin=True, org_id=None, was_created=False
        )

        assert result.roles == ["authenticated", "PlatformAdmin"]

    def test_org_user_roles(self):
        """OrgUser gets correct roles"""
        result = UserProvisioningResult(
            user_type="ORG", is_platform_admin=False, org_id="org-123", was_created=True
        )

        assert result.roles == ["authenticated", "OrgUser"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
