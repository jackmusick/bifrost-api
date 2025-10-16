"""
End-to-end tests for Organizations API
Tests against running Azure Functions instance with real Azurite data
"""

import requests


class TestOrganizationsE2E:
    """Test Organizations API endpoints end-to-end"""

    def test_health_check(self, base_url):
        """Verify the API is running"""
        response = requests.get(f"{base_url}/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ["healthy", "degraded"]  # degraded is acceptable if Key Vault has limited permissions
        assert "checks" in data
        assert isinstance(data["checks"], list)

    def test_list_organizations_as_platform_admin(self, base_url, platform_admin_headers):
        """Platform admin should see all organizations"""
        response = requests.get(
            f"{base_url}/organizations",
            headers=platform_admin_headers
        )

        assert response.status_code == 200
        orgs = response.json()
        assert isinstance(orgs, list)
        assert len(orgs) >= 2  # At least Covi Development and Contoso Ltd from seed data

        # Verify structure
        org_names = [org["name"] for org in orgs]
        assert "Covi Development" in org_names
        assert "Contoso Ltd" in org_names

    def test_list_organizations_as_org_user_forbidden(self, base_url, org_user_headers):
        """Org users should not have access to organizations endpoint"""
        response = requests.get(
            f"{base_url}/organizations",
            headers=org_user_headers
        )

        # Should be 403 Forbidden - org users can't list all organizations
        assert response.status_code == 403

    def test_create_organization_as_platform_admin(self, base_url, platform_admin_headers):
        """Platform admin can create organizations"""
        response = requests.post(
            f"{base_url}/organizations",
            headers=platform_admin_headers,
            json={
                "name": "Test Organization E2E",
                "tenantId": "11111111-2222-3333-4444-555555555555"
            }
        )

        assert response.status_code == 201
        org = response.json()
        assert org["name"] == "Test Organization E2E"
        assert org["tenantId"] == "11111111-2222-3333-4444-555555555555"
        assert org["isActive"] is True
        assert org["createdBy"] == "jack@gocovi.com"
        assert "id" in org

        # Verify we can retrieve it
        org_id = org["id"]
        get_response = requests.get(
            f"{base_url}/organizations/{org_id}",
            headers=platform_admin_headers
        )
        assert get_response.status_code == 200
        retrieved_org = get_response.json()
        assert retrieved_org["id"] == org_id
        assert retrieved_org["name"] == "Test Organization E2E"

    def test_create_organization_as_org_user_forbidden(self, base_url, org_user_headers):
        """Org users cannot create organizations"""
        response = requests.post(
            f"{base_url}/organizations",
            headers=org_user_headers,
            json={
                "name": "Should Fail",
                "tenantId": "11111111-2222-3333-4444-555555555555"
            }
        )

        assert response.status_code == 403

    def test_update_organization_as_platform_admin(self, base_url, platform_admin_headers):
        """Platform admin can update organizations"""
        # First, create an org to update
        create_response = requests.post(
            f"{base_url}/organizations",
            headers=platform_admin_headers,
            json={
                "name": "Org to Update",
                "tenantId": "22222222-3333-4444-5555-666666666666"
            }
        )
        assert create_response.status_code == 201
        org_id = create_response.json()["id"]

        # Now update it
        update_response = requests.patch(
            f"{base_url}/organizations/{org_id}",
            headers=platform_admin_headers,
            json={
                "name": "Updated Organization Name"
            }
        )

        assert update_response.status_code == 200
        updated_org = update_response.json()
        assert updated_org["name"] == "Updated Organization Name"
        assert updated_org["id"] == org_id

    def test_delete_organization_as_platform_admin(self, base_url, platform_admin_headers):
        """Platform admin can soft-delete organizations"""
        # First, create an org to delete
        create_response = requests.post(
            f"{base_url}/organizations",
            headers=platform_admin_headers,
            json={
                "name": "Org to Delete",
                "tenantId": "33333333-4444-5555-6666-777777777777"
            }
        )
        assert create_response.status_code == 201
        org_id = create_response.json()["id"]

        # Now delete it
        delete_response = requests.delete(
            f"{base_url}/organizations/{org_id}",
            headers=platform_admin_headers
        )

        assert delete_response.status_code == 204

        # Verify it's soft-deleted (should return 404 or not appear in list)
        get_response = requests.get(
            f"{base_url}/organizations/{org_id}",
            headers=platform_admin_headers
        )
        # Either 404 (not found) or 200 with isActive=false
        if get_response.status_code == 200:
            org = get_response.json()
            assert org["isActive"] is False
        else:
            assert get_response.status_code == 404

    def test_get_organization_not_found(self, base_url, platform_admin_headers):
        """Getting non-existent organization returns 404"""
        response = requests.get(
            f"{base_url}/organizations/non-existent-org-id",
            headers=platform_admin_headers
        )

        assert response.status_code == 404
        error = response.json()
        assert error["error"] == "NotFound"

    def test_create_organization_validation_error(self, base_url, platform_admin_headers):
        """Creating organization without required fields returns 400"""
        response = requests.post(
            f"{base_url}/organizations",
            headers=platform_admin_headers,
            json={}  # Missing required 'name'
        )

        assert response.status_code == 400
        error = response.json()
        assert error["error"] == "ValidationError"
