"""
Unit tests for OrganizationRepository
"""

import pytest
from datetime import datetime
from unittest.mock import MagicMock

from shared.repositories.organizations import OrganizationRepository
from shared.models import CreateOrganizationRequest, UpdateOrganizationRequest


class TestOrganizationRepositoryCreate:
    """Test organization creation"""

    def test_create_organization_success(self, mock_table_service):
        """Test successful organization creation"""
        repo = OrganizationRepository()

        org_request = CreateOrganizationRequest(
            name="ACME Corp",
            domain="acme.com"
        )

        mock_table_service.insert_entity.return_value = None

        result = repo.create_organization(org_request, "creator-user")

        assert result.name == "ACME Corp"
        assert result.domain == "acme.com"
        assert result.id is not None
        assert result.isActive is True
        mock_table_service.insert_entity.assert_called_once()

    def test_create_organization_sets_defaults(self, mock_table_service):
        """Test default values are set"""
        repo = OrganizationRepository()

        org_request = CreateOrganizationRequest(
            name="Test Org",
            domain="test.org"
        )

        mock_table_service.insert_entity.return_value = None

        result = repo.create_organization(org_request, "admin")

        assert result.isActive is True
        assert result.createdAt is not None
        assert result.createdBy == "admin"


class TestOrganizationRepositoryRead:
    """Test organization retrieval"""

    def test_get_organization_success(self, mock_table_service):
        """Test retrieving organization"""
        repo = OrganizationRepository()

        mock_table_service.get_entity.return_value = {
            "PartitionKey": "GLOBAL",
            "RowKey": "org:org-uuid",
            "Name": "ACME Corp",
            "Domain": "acme.com",
            "IsActive": True,
            "CreatedBy": "admin",
            "CreatedAt": "2024-01-15T10:30:00",
            "UpdatedAt": "2024-01-15T10:30:00"
        }

        result = repo.get_organization("org-uuid")

        assert result is not None
        assert result.name == "ACME Corp"
        assert result.domain == "acme.com"
        assert result.id == "org-uuid"

    def test_get_organization_not_found(self, mock_table_service):
        """Test retrieving non-existent organization"""
        repo = OrganizationRepository()

        mock_table_service.get_entity.return_value = None

        result = repo.get_organization("nonexistent")

        assert result is None

    def test_get_organization_by_domain(self, mock_table_service):
        """Test retrieving organization by domain"""
        repo = OrganizationRepository()

        org_data = {
            "PartitionKey": "GLOBAL",
            "RowKey": "org:org-uuid",
            "Name": "ACME Corp",
            "Domain": "acme.com",
            "IsActive": True,
            "CreatedBy": "admin",
            "CreatedAt": "2024-01-15T10:30:00",
            "UpdatedAt": "2024-01-15T10:30:00"
        }

        mock_table_service.query_entities.return_value = iter([org_data])

        result = repo.get_organization_by_domain("acme.com")

        assert result is not None
        assert result.domain == "acme.com"

    def test_list_organizations_empty(self, mock_table_service):
        """Test listing when no organizations exist"""
        repo = OrganizationRepository()

        mock_table_service.query_entities.return_value = iter([])

        result = repo.list_organizations()

        assert result == []

    def test_list_organizations_returns_multiple(self, mock_table_service):
        """Test listing multiple organizations"""
        repo = OrganizationRepository()

        orgs_data = [
            {
                "PartitionKey": "GLOBAL",
                "RowKey": "org:org-1",
                "Name": "Org 1",
                "Domain": "org1.com",
                "IsActive": True,
                "CreatedBy": "admin",
                "CreatedAt": "2024-01-15T10:30:00",
                "UpdatedAt": "2024-01-15T10:30:00"
            },
            {
                "PartitionKey": "GLOBAL",
                "RowKey": "org:org-2",
                "Name": "Org 2",
                "Domain": "org2.com",
                "IsActive": True,
                "CreatedBy": "admin",
                "CreatedAt": "2024-01-15T10:30:00",
                "UpdatedAt": "2024-01-15T10:30:00"
            }
        ]

        mock_table_service.query_entities.return_value = iter(orgs_data)

        result = repo.list_organizations()

        assert len(result) == 2
        assert result[0].name == "Org 1"
        assert result[1].name == "Org 2"

    def test_list_organizations_excludes_inactive(self, mock_table_service):
        """Test that inactive organizations are excluded"""
        repo = OrganizationRepository()

        mock_table_service.query_entities.return_value = iter([])

        repo.list_organizations(active_only=True)

        call_args = mock_table_service.query_entities.call_args
        # query_entities is called with keyword arguments: filter=...
        filter_query = call_args[1].get("filter", call_args[0][0] if call_args[0] else "")
        assert "IsActive eq true" in filter_query


class TestOrganizationRepositoryUpdate:
    """Test organization update operations"""

    def test_update_organization_success(self, mock_table_service):
        """Test successful organization update"""
        repo = OrganizationRepository()

        existing_org = {
            "PartitionKey": "GLOBAL",
            "RowKey": "org:org-123",
            "Name": "Original Name",
            "Domain": "original.com",
            "IsActive": True,
            "CreatedBy": "admin",
            "CreatedAt": "2024-01-15T10:30:00",
            "UpdatedAt": "2024-01-15T10:30:00"
        }

        mock_table_service.get_entity.return_value = existing_org
        mock_table_service.update_entity.return_value = None

        updates = UpdateOrganizationRequest(
            name="Updated Name",
            domain="updated.com",
            isActive=None
        )

        result = repo.update_organization("org-123", updates)

        assert result.name == "Updated Name"
        assert result.domain == "updated.com"

    def test_update_organization_not_found(self, mock_table_service):
        """Test update raises error when org not found"""
        repo = OrganizationRepository()

        mock_table_service.get_entity.return_value = None

        updates = UpdateOrganizationRequest(name="Updated")

        with pytest.raises(ValueError, match="not found"):
            repo.update_organization("nonexistent", updates)

    def test_update_organization_partial_fields(self, mock_table_service):
        """Test partial field updates"""
        repo = OrganizationRepository()

        existing_org = {
            "PartitionKey": "GLOBAL",
            "RowKey": "org:org-123",
            "Name": "Original Name",
            "Domain": "original.com",
            "IsActive": True,
            "CreatedBy": "admin",
            "CreatedAt": "2024-01-15T10:30:00",
            "UpdatedAt": "2024-01-15T10:30:00"
        }

        mock_table_service.get_entity.return_value = existing_org
        mock_table_service.update_entity.return_value = None

        updates = UpdateOrganizationRequest(name="New Name", domain=None, isActive=None)

        result = repo.update_organization("org-123", updates)

        assert result.name == "New Name"
        assert result.domain == "original.com"


class TestOrganizationRepositoryDelete:
    """Test organization deletion"""

    def test_soft_delete_organization(self, mock_table_service):
        """Test soft delete sets IsActive to False"""
        repo = OrganizationRepository()

        existing_org = {
            "PartitionKey": "GLOBAL",
            "RowKey": "org:org-123",
            "Name": "To Delete",
            "IsActive": True,
            "CreatedBy": "admin",
            "CreatedAt": "2024-01-15T10:30:00",
            "UpdatedAt": "2024-01-15T10:30:00"
        }

        mock_table_service.get_entity.return_value = existing_org
        mock_table_service.update_entity.return_value = None

        result = repo.soft_delete_organization("org-123")

        assert result is True
        mock_table_service.update_entity.assert_called_once()

    def test_soft_delete_organization_not_found(self, mock_table_service):
        """Test soft delete returns False when not found"""
        repo = OrganizationRepository()

        mock_table_service.get_entity.return_value = None

        result = repo.soft_delete_organization("nonexistent")

        assert result is False

    def test_delete_organization_success(self, mock_table_service):
        """Test hard delete"""
        repo = OrganizationRepository()

        existing_org = {
            "PartitionKey": "GLOBAL",
            "RowKey": "org:org-123",
            "Name": "To Delete"
        }

        mock_table_service.get_entity.return_value = existing_org
        mock_table_service.delete_entity.return_value = True

        result = repo.delete_organization("org-123")

        assert result is True
        mock_table_service.delete_entity.assert_called_once()

    def test_delete_organization_not_found(self, mock_table_service):
        """Test hard delete returns False when not found"""
        repo = OrganizationRepository()

        mock_table_service.get_entity.return_value = None

        result = repo.delete_organization("nonexistent")

        assert result is False
