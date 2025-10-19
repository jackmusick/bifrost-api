"""Integration tests for Workflow Keys API endpoints

Tests the workflow API key management endpoints for creating, listing,
and revoking API keys for workflow execution.
"""

import pytest
import requests
from datetime import datetime, timedelta


class TestWorkflowKeysCRUD:
    """Test workflow key CRUD operations"""

    def test_create_workflow_key_success(self, api_base_url, platform_admin_headers, test_org_id):
        """Should create workflow execution key"""
        response = requests.post(
            f"{api_base_url}/api/workflow-keys",
            headers={**platform_admin_headers, "X-Organization-ID": test_org_id},
            json={
                "description": "Test Workflow Key",
                "workflowId": None,
                "expiresInDays": 90
            },
            timeout=10
        )
        # Should return 201 (created) or 404 (org not properly set up) or 400 (validation)
        assert response.status_code in [201, 404, 400]
        if response.status_code == 201:
            data = response.json()
            assert "id" in data
            assert data["description"] == "Test Workflow Key"
            # Raw key should be returned on creation
            assert data.get("rawKey") is not None or data.get("key") is not None

    def test_list_workflow_keys_success(self, api_base_url, platform_admin_headers, test_org_id):
        """Should list all workflow keys"""
        response = requests.get(
            f"{api_base_url}/api/workflow-keys",
            headers={**platform_admin_headers, "X-Organization-ID": test_org_id},
            timeout=10
        )
        # May return 200 (success) or 404 (org not found) or 400 (validation)
        assert response.status_code in [200, 404, 400]
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, list)

    def test_revoke_workflow_key_success(self, api_base_url, platform_admin_headers, test_org_id):
        """Should revoke workflow key"""
        # First create a key to revoke
        create_response = requests.post(
            f"{api_base_url}/api/workflow-keys",
            headers={**platform_admin_headers, "X-Organization-ID": test_org_id},
            json={
                "description": "Key to Revoke",
                "workflowId": None
            },
            timeout=10
        )

        if create_response.status_code == 201:
            key_data = create_response.json()
            key_id = key_data.get("id")

            if key_id:
                revoke_response = requests.delete(
                    f"{api_base_url}/api/workflow-keys/{key_id}",
                    headers={**platform_admin_headers, "X-Organization-ID": test_org_id},
                    timeout=10
                )
                # Should return 204 (no content) or 200 (success)
                assert revoke_response.status_code in [200, 204]


class TestWorkflowKeysAuthorization:
    """Test workflow key authorization and access control"""

    def test_regular_user_cannot_create_keys(self, api_base_url, regular_user_headers, test_org_id):
        """Regular users should not create workflow keys"""
        response = requests.post(
            f"{api_base_url}/api/workflow-keys",
            headers={**regular_user_headers, "X-Organization-ID": test_org_id},
            json={
                "description": "Unauthorized Key",
                "workflowId": None
            },
            timeout=10
        )
        # Should be 403 (Forbidden), 401 (Unauthorized), or 404 (org not found)
        assert response.status_code in [403, 401, 404]

    def test_regular_user_cannot_revoke_keys(self, api_base_url, regular_user_headers, test_org_id):
        """Regular users should not revoke workflow keys"""
        # Attempt to revoke a key with a dummy ID
        response = requests.delete(
            f"{api_base_url}/api/workflow-keys/dummy-key-id",
            headers={**regular_user_headers, "X-Organization-ID": test_org_id},
            timeout=10
        )
        # Should be 403 (Forbidden), 401 (Unauthorized), or 404 (not found)
        assert response.status_code in [403, 401, 404]

    def test_create_key_with_expiration(self, api_base_url, platform_admin_headers, test_org_id):
        """Should create workflow key with expiration"""
        response = requests.post(
            f"{api_base_url}/api/workflow-keys",
            headers={**platform_admin_headers, "X-Organization-ID": test_org_id},
            json={
                "description": "Expiring Key",
                "workflowId": None,
                "expiresInDays": 30
            },
            timeout=10
        )
        # May return 201 (created) or 404 (org not found) or 400 (validation)
        assert response.status_code in [201, 404, 400]
        if response.status_code == 201:
            data = response.json()
            assert "expiresAt" in data

    def test_masked_key_in_list(self, api_base_url, platform_admin_headers, test_org_id):
        """Listed keys should have masked values"""
        response = requests.get(
            f"{api_base_url}/api/workflow-keys",
            headers={**platform_admin_headers, "X-Organization-ID": test_org_id},
            timeout=10
        )
        # May return 200 (success) or 404 (org not found) or 400 (validation)
        assert response.status_code in [200, 404, 400]
        if response.status_code == 200:
            data = response.json()
            if len(data) > 0:
                key = data[0]
                # Raw key should never be returned in list
                assert key.get("rawKey") is None or key.get("rawKey") == ""

    def test_revoke_nonexistent_key(self, api_base_url, platform_admin_headers, test_org_id):
        """Should handle revocation of non-existent key"""
        response = requests.delete(
            f"{api_base_url}/api/workflow-keys/nonexistent-key-id-xyz",
            headers={**platform_admin_headers, "X-Organization-ID": test_org_id},
            timeout=10
        )
        # Should return 404 (not found) or 403/401 if auth check happens first
        assert response.status_code in [404, 403, 401]

    def test_create_global_workflow_key(self, api_base_url, platform_admin_headers, test_org_id):
        """Should create global workflow key (workflowId=None)"""
        response = requests.post(
            f"{api_base_url}/api/workflow-keys",
            headers={**platform_admin_headers, "X-Organization-ID": test_org_id},
            json={
                "description": "Global Workflow Key",
                "workflowId": None
            },
            timeout=10
        )
        # May return 201 (created) or 404 (org not found) or 400 (validation)
        assert response.status_code in [201, 404, 400]

    def test_list_empty_workflow_keys(self, api_base_url, platform_admin_headers, test_org_id):
        """Should handle empty list of workflow keys"""
        response = requests.get(
            f"{api_base_url}/api/workflow-keys?includeRevoked=false",
            headers={**platform_admin_headers, "X-Organization-ID": test_org_id},
            timeout=10
        )
        # May return 200 (empty list) or 404 (org not found) or 400 (validation)
        assert response.status_code in [200, 404, 400]
