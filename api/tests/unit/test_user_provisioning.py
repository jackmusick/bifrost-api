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

    @patch("shared.user_provisioning.TableStorageService")
    def test_existing_platform_admin_user(self, mock_table_service):
        """Existing PlatformAdmin user returns correct status"""
        mock_users = Mock()
        mock_table_service.return_value = mock_users

        # Mock existing platform admin
        mock_users.get_entity.return_value = {
            "PartitionKey": "admin@example.com",
            "RowKey": "user",
            "Email": "admin@example.com",
            "UserType": "PLATFORM",
            "IsPlatformAdmin": True,
            "LastLogin": datetime.utcnow().isoformat(),
        }

        result = ensure_user_provisioned("admin@example.com")

        assert result.user_type == "PLATFORM"
        assert result.is_platform_admin is True
        assert result.org_id is None
        assert result.was_created is False
        assert "PlatformAdmin" in result.roles
        assert "authenticated" in result.roles

        # Verify last login was updated
        mock_users.update_entity.assert_called_once()

    @patch("shared.user_provisioning.TableStorageService")
    @patch("shared.user_provisioning._get_user_org_id")
    def test_existing_org_user(self, mock_get_org_id, mock_table_service):
        """Existing ORG user returns correct status with org_id"""
        mock_users = Mock()
        mock_table_service.return_value = mock_users
        mock_get_org_id.return_value = "org-123"

        # Mock existing org user
        mock_users.get_entity.return_value = {
            "PartitionKey": "user@company.com",
            "RowKey": "user",
            "Email": "user@company.com",
            "UserType": "ORG",
            "IsPlatformAdmin": False,
        }

        result = ensure_user_provisioned("user@company.com")

        assert result.user_type == "ORG"
        assert result.is_platform_admin is False
        assert result.org_id == "org-123"
        assert result.was_created is False
        assert "OrgUser" in result.roles
        assert "PlatformAdmin" not in result.roles

    @patch("shared.user_provisioning._create_first_platform_admin")
    @patch("shared.user_provisioning.TableStorageService")
    def test_first_user_creation(self, mock_table_service, mock_create_first):
        """First user in system is created as PlatformAdmin"""
        mock_users = Mock()
        mock_table_service.return_value = mock_users

        # Mock user doesn't exist
        mock_users.get_entity.return_value = None

        # Mock no existing users (first user)
        mock_users.query_entities.return_value = iter([])

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
    @patch("shared.user_provisioning.TableStorageService")
    def test_domain_based_provisioning(self, mock_table_service, mock_provision):
        """Non-first user triggers domain-based provisioning"""
        mock_users = Mock()
        mock_table_service.return_value = mock_users

        # Mock user doesn't exist
        mock_users.get_entity.return_value = None

        # Mock existing users in system (not first user)
        mock_users.query_entities.return_value = iter([{"PartitionKey": "admin@example.com"}])

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
    @patch("shared.user_provisioning._get_user_org_id")
    @patch("shared.user_provisioning.TableStorageService")
    def test_existing_org_user_without_relationship(
        self, mock_table_service, mock_get_org_id, mock_provision_relationship
    ):
        """Existing ORG user without org relationship gets auto-provisioned"""
        mock_users = Mock()
        mock_table_service.return_value = mock_users

        # Mock existing ORG user
        mock_users.get_entity.return_value = {
            "PartitionKey": "orphan@company.com",
            "RowKey": "user",
            "Email": "orphan@company.com",
            "UserType": "ORG",
            "IsPlatformAdmin": False,
        }

        # Mock no org assignment initially
        mock_get_org_id.return_value = None

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

    @patch("shared.user_provisioning.TableStorageService")
    def test_creates_platform_admin_user(self, mock_table_service):
        """First user is created with PlatformAdmin privileges"""
        mock_users = Mock()
        mock_table_service.return_value = mock_users

        result = _create_first_platform_admin("first@example.com")

        assert result.user_type == "PLATFORM"
        assert result.is_platform_admin is True
        assert result.org_id is None
        assert result.was_created is True

        # Verify insert was called with correct data
        mock_users.insert_entity.assert_called_once()
        created_user = mock_users.insert_entity.call_args[0][0]
        assert created_user["Email"] == "first@example.com"
        assert created_user["UserType"] == "PLATFORM"
        assert created_user["IsPlatformAdmin"] is True
        assert created_user["IsActive"] is True


class TestProvisionUserByDomain:
    """Test domain-based auto-provisioning"""

    @patch("shared.user_provisioning.TableStorageService")
    def test_successful_domain_match(self, mock_table_service):
        """User with matching domain is auto-provisioned to org"""
        mock_entities = Mock()
        mock_users = Mock()
        mock_relationships = Mock()

        def get_table(table_name):
            if table_name == "Entities":
                return mock_entities
            elif table_name == "Users":
                return mock_users
            elif table_name == "Relationships":
                return mock_relationships
            return Mock()

        mock_table_service.side_effect = get_table

        # Mock organization with matching domain
        mock_entities.query_entities.return_value = [
            {
                "PartitionKey": "GLOBAL",
                "RowKey": "org:org-789",
                "Name": "Company Inc",
                "Domain": "company.com",
                "IsActive": True,
            }
        ]

        result = _provision_user_by_domain("newuser@company.com")

        assert result.user_type == "ORG"
        assert result.is_platform_admin is False
        assert result.org_id == "org-789"
        assert result.was_created is True

        # Verify user was created
        mock_users.insert_entity.assert_called_once()
        created_user = mock_users.insert_entity.call_args[0][0]
        assert created_user["Email"] == "newuser@company.com"
        assert created_user["UserType"] == "ORG"
        assert created_user["IsPlatformAdmin"] is False

        # Verify relationship was created
        mock_relationships.insert_entity.assert_called_once()
        relationship = mock_relationships.insert_entity.call_args[0][0]
        assert relationship["RowKey"] == "userperm:newuser@company.com:org-789"
        assert relationship["UserId"] == "newuser@company.com"
        assert relationship["OrganizationId"] == "org-789"

    @patch("shared.user_provisioning.TableStorageService")
    def test_no_matching_domain(self, mock_table_service):
        """User with no matching domain raises ValueError"""
        mock_entities = Mock()
        mock_table_service.return_value = mock_entities

        # Mock organizations with different domains
        mock_entities.query_entities.return_value = [
            {
                "RowKey": "org:org-123",
                "Name": "Other Company",
                "Domain": "other.com",
                "IsActive": True,
            }
        ]

        with pytest.raises(ValueError, match="No organization configured for domain"):
            _provision_user_by_domain("user@nomatch.com")

    @patch("shared.user_provisioning.TableStorageService")
    def test_case_insensitive_domain_matching(self, mock_table_service):
        """Domain matching is case-insensitive"""
        mock_entities = Mock()
        mock_users = Mock()
        mock_relationships = Mock()

        def get_table(table_name):
            if table_name == "Entities":
                return mock_entities
            elif table_name == "Users":
                return mock_users
            elif table_name == "Relationships":
                return mock_relationships

        mock_table_service.side_effect = get_table

        # Mock org with uppercase domain
        mock_entities.query_entities.return_value = [
            {
                "RowKey": "org:org-999",
                "Name": "Company",
                "Domain": "COMPANY.COM",
                "IsActive": True,
            }
        ]

        result = _provision_user_by_domain("user@company.com")

        assert result.org_id == "org-999"
        assert result.was_created is True


class TestGetUserOrgId:
    """Test user org lookup helper"""

    @patch("shared.user_provisioning.TableStorageService")
    def test_returns_org_id_for_user(self, mock_table_service):
        """Returns org_id from Relationships table"""
        mock_relationships = Mock()
        mock_table_service.return_value = mock_relationships

        mock_relationships.query_entities.return_value = [
            {
                "PartitionKey": "GLOBAL",
                "RowKey": "userperm:user@company.com:org-abc",
                "UserId": "user@company.com",
                "OrganizationId": "org-abc",
            }
        ]

        org_id = _get_user_org_id("user@company.com")

        assert org_id == "org-abc"

    @patch("shared.user_provisioning.TableStorageService")
    def test_returns_none_for_no_org(self, mock_table_service):
        """Returns None if user has no org assignments"""
        mock_relationships = Mock()
        mock_table_service.return_value = mock_relationships

        mock_relationships.query_entities.return_value = []

        org_id = _get_user_org_id("orphan@example.com")

        assert org_id is None

    @patch("shared.user_provisioning.TableStorageService")
    def test_handles_query_error(self, mock_table_service):
        """Returns None on query error"""
        mock_relationships = Mock()
        mock_table_service.return_value = mock_relationships

        mock_relationships.query_entities.side_effect = Exception("Database error")

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
