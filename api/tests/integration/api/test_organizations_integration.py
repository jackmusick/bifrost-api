"""
Integration tests for Organizations API
Tests Organizations CRUD operations by calling Azure Functions directly (no HTTP)
"""

import pytest

from functions.health import general_health
from functions.organizations import (
    create_organization,
    delete_organization,
    get_organization,
    list_organizations,
    update_organization,
)
from tests.helpers.http_helpers import (
    create_mock_request,
    create_org_user_headers,
    create_platform_admin_headers,
    parse_response,
)


class TestOrganizationsIntegration:
    """Test Organizations API endpoints"""

    @pytest.mark.asyncio
    async def test_health_check(self):
        """Verify the API is running"""
        req = create_mock_request(
            method="GET",
            url="/api/health",
        )

        response = await general_health(req)
        status, body = parse_response(response)

        assert status == 200
        assert body["status"] in ["healthy", "degraded"]  # degraded is acceptable if Key Vault has limited permissions
        assert "checks" in body
        assert isinstance(body["checks"], list)

    @pytest.mark.asyncio
    async def test_list_organizations_as_platform_admin(self, test_platform_admin_user, test_org, test_org_2):
        """Platform admin should see all organizations"""
        req = create_mock_request(
            method="GET",
            url="/api/organizations",
            headers=create_platform_admin_headers(user_email=test_platform_admin_user["email"]),
        )

        response = await list_organizations(req)
        status, body = parse_response(response)

        assert status == 200
        organizations = body
        assert isinstance(organizations, list)
        assert len(organizations) >= 2  # At least two test organizations

        # Verify structure using test_org fixtures
        assert any(org["name"] == test_org["name"] for org in organizations)
        assert any(org["name"] == test_org_2["name"] for org in organizations)

    @pytest.mark.asyncio
    async def test_list_organizations_as_org_user_forbidden(self, test_org_with_user):
        """Org users should not have access to organizations endpoint"""
        req = create_mock_request(
            method="GET",
            url="/api/organizations",
            headers=create_org_user_headers(user_email=test_org_with_user["email"]),
        )

        response = await list_organizations(req)
        status, body = parse_response(response)

        # Should be 403 Forbidden - org users can't list all organizations
        assert status == 403

    @pytest.mark.asyncio
    async def test_create_organization_as_platform_admin(self):
        """Platform admin can create organizations"""
        req = create_mock_request(
            method="POST",
            url="/api/organizations",
            headers=create_platform_admin_headers(),
            body={
                "name": "Test Organization Integration",
                "domain": "test-integration.com"
            },
        )

        response = await create_organization(req)
        status, body = parse_response(response)

        assert status == 201
        assert body["name"] == "Test Organization Integration"
        assert body["domain"] == "test-integration.com"
        assert body["isActive"] is True
        assert body["createdBy"] == "jack@gocovi.com"
        assert "id" in body

        # Verify we can retrieve it
        org_id = body["id"]
        get_req = create_mock_request(
            method="GET",
            url=f"/api/organizations/{org_id}",
            headers=create_platform_admin_headers(),
            route_params={"orgId": org_id},
        )

        get_response = await get_organization(get_req)
        get_status, retrieved_org = parse_response(get_response)

        assert get_status == 200
        assert retrieved_org["id"] == org_id
        assert retrieved_org["name"] == "Test Organization Integration"

    @pytest.mark.asyncio
    async def test_create_organization_as_org_user_forbidden(self, test_org_with_user):
        """Org users cannot create organizations"""
        req = create_mock_request(
            method="POST",
            url="/api/organizations",
            headers=create_org_user_headers(user_email=test_org_with_user["email"]),
            body={
                "name": "Should Fail"
            },
        )

        response = await create_organization(req)
        status, body = parse_response(response)

        assert status == 403

    @pytest.mark.asyncio
    async def test_update_organization_as_platform_admin(self):
        """Platform admin can update organizations"""
        # First, create an org to update
        create_req = create_mock_request(
            method="POST",
            url="/api/organizations",
            headers=create_platform_admin_headers(),
            body={
                "name": "Org to Update Integration"
            },
        )

        create_response = await create_organization(create_req)
        create_status, created_org = parse_response(create_response)

        assert create_status == 201
        org_id = created_org["id"]

        # Now update it
        update_req = create_mock_request(
            method="PATCH",
            url=f"/api/organizations/{org_id}",
            headers=create_platform_admin_headers(),
            route_params={"orgId": org_id},
            body={
                "name": "Updated Organization Name Integration"
            },
        )

        update_response = await update_organization(update_req)
        update_status, updated_org = parse_response(update_response)

        assert update_status == 200
        assert updated_org["name"] == "Updated Organization Name Integration"
        assert updated_org["id"] == org_id

    @pytest.mark.asyncio
    async def test_delete_organization_as_platform_admin(self):
        """Platform admin can soft-delete organizations"""
        # First, create an org to delete
        create_req = create_mock_request(
            method="POST",
            url="/api/organizations",
            headers=create_platform_admin_headers(),
            body={
                "name": "Org to Delete Integration"
            },
        )

        create_response = await create_organization(create_req)
        create_status, created_org = parse_response(create_response)

        assert create_status == 201
        org_id = created_org["id"]

        # Now delete it
        delete_req = create_mock_request(
            method="DELETE",
            url=f"/api/organizations/{org_id}",
            headers=create_platform_admin_headers(),
            route_params={"orgId": org_id},
        )

        delete_response = await delete_organization(delete_req)
        delete_status, _ = parse_response(delete_response)

        assert delete_status == 204

        # Verify it's soft-deleted (should return 404 or isActive=false)
        get_req = create_mock_request(
            method="GET",
            url=f"/api/organizations/{org_id}",
            headers=create_platform_admin_headers(),
            route_params={"orgId": org_id},
        )

        get_response = await get_organization(get_req)
        get_status, org = parse_response(get_response)

        # Either 404 (not found) or 200 with isActive=false
        if get_status == 200:
            assert org["isActive"] is False
        else:
            assert get_status == 404

    @pytest.mark.asyncio
    async def test_get_organization_not_found(self):
        """Getting non-existent organization returns 404"""
        req = create_mock_request(
            method="GET",
            url="/api/organizations/non-existent-org-id",
            headers=create_platform_admin_headers(),
            route_params={"orgId": "non-existent-org-id"},
        )

        response = await get_organization(req)
        status, body = parse_response(response)

        assert status == 404
        assert body["error"] == "NotFound"

    @pytest.mark.asyncio
    async def test_create_organization_validation_error(self):
        """Creating organization without required fields returns 400"""
        req = create_mock_request(
            method="POST",
            url="/api/organizations",
            headers=create_platform_admin_headers(),
            body={},  # Missing required 'name'
        )

        response = await create_organization(req)
        status, body = parse_response(response)

        assert status == 400
        assert body["error"] == "ValidationError"
