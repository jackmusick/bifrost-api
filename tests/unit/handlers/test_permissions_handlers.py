"""
Unit tests for permissions_handlers
Tests user sorting and deprecated endpoint handling
"""

import json
import pytest
from unittest.mock import Mock, patch

from shared.handlers.permissions_handlers import (
    list_users_handler,
    get_user_permissions_handler,
    get_org_permissions_handler,
    grant_permissions_handler,
    revoke_permissions_handler,
)


class TestListUsersSorting:
    """Test list_users_handler sorting functionality"""

    @pytest.mark.asyncio
    async def test_list_users_sorts_by_last_login(self):
        """Test that users are sorted by lastLogin descending"""
        mock_context = Mock(user_id="admin-123", scope="GLOBAL")

        user_entity1 = {
            "RowKey": "user:old@example.com",
            "Email": "old@example.com",
            "DisplayName": "Old",
            "UserType": "PLATFORM",
            "IsPlatformAdmin": False,
            "IsActive": True,
            "LastLogin": "2024-01-01T00:00:00",
            "CreatedAt": "2024-01-01T00:00:00",
            "EntraUserId": None,
            "LastEntraIdSync": None
        }
        user_entity2 = {
            "RowKey": "user:recent@example.com",
            "Email": "recent@example.com",
            "DisplayName": "Recent",
            "UserType": "PLATFORM",
            "IsPlatformAdmin": False,
            "IsActive": True,
            "LastLogin": "2024-10-19T12:00:00",
            "CreatedAt": "2024-02-01T00:00:00",
            "EntraUserId": None,
            "LastEntraIdSync": None
        }
        user_entity3 = {
            "RowKey": "user:never@example.com",
            "Email": "never@example.com",
            "DisplayName": "Never",
            "UserType": "PLATFORM",
            "IsPlatformAdmin": False,
            "IsActive": True,
            "LastLogin": None,
            "CreatedAt": "2024-03-01T00:00:00",
            "EntraUserId": None,
            "LastEntraIdSync": None
        }

        with patch('shared.handlers.permissions_handlers.get_async_table_service') as mock_get_service:
            # Mock service should return user entities for Entities table
            mock_entities_service = Mock()
            async def mock_query_entities(filter=None):
                return [user_entity1, user_entity3, user_entity2]
            mock_entities_service.query_entities = mock_query_entities

            # Only return the entities service (no Relationships service call for global scope)
            mock_get_service.return_value = mock_entities_service

            response = await list_users_handler(mock_context)

            assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.get_body()}"
            data = json.loads(response.get_body())
            assert len(data) == 3, f"Expected 3 users, got {len(data)}: {data}"
            # Most recent first
            assert data[0]["email"] == "recent@example.com"
            # Oldest second
            assert data[1]["email"] == "old@example.com"
            # Never logged in last
            assert data[2]["email"] == "never@example.com"


class TestDeprecatedPermissionsEndpoints:
    """Test get_user_permissions_handler"""

    @pytest.mark.asyncio
    async def test_get_user_permissions_returns_empty(self):
        """Test that deprecated endpoint returns empty list"""
        mock_context = Mock(user_id="admin-123")
        user_id = "user@example.com"

        response = await get_user_permissions_handler(mock_context, user_id)

        assert response.status_code == 200
        data = json.loads(response.get_body())
        assert data == []


class TestGetOrgPermissionsHandler:
    """Test get_org_permissions_handler"""

    @pytest.mark.asyncio
    async def test_get_org_permissions_returns_empty(self):
        """Test that deprecated endpoint returns empty list"""
        mock_context = Mock(user_id="admin-123")
        org_id = "org-123"

        response = await get_org_permissions_handler(mock_context, org_id)

        assert response.status_code == 200
        data = json.loads(response.get_body())
        assert data == []


class TestGrantPermissionsHandler:
    """Test grant_permissions_handler"""

    @pytest.mark.asyncio
    async def test_grant_permissions_returns_not_implemented(self):
        """Test that deprecated endpoint returns 501"""
        mock_context = Mock(user_id="admin-123")

        response = await grant_permissions_handler(mock_context)

        assert response.status_code == 501
        data = json.loads(response.get_body())
        assert data["error"] == "NotImplemented"
        assert "deprecated" in data["message"].lower()

    @pytest.mark.asyncio
    async def test_revoke_permissions_returns_not_implemented(self):
        """Test that deprecated endpoint returns 501"""
        mock_context = Mock(user_id="admin-123")

        response = await revoke_permissions_handler(
            mock_context,
            user_id="user@example.com",
            org_id="org-123"
        )

        assert response.status_code == 501
        data = json.loads(response.get_body())
        assert data["error"] == "NotImplemented"
        assert "deprecated" in data["message"].lower()

