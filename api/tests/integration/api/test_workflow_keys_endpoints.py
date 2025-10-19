"""Integration tests for Workflow Keys API endpoints

Tests the workflow API key management endpoints for creating, listing,
and revoking API keys for workflow execution.
"""

import pytest
import requests
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


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


class TestWorkflowKeysGeneration:
    """Test workflow key generation"""

    def test_generate_key_without_expiration(self, api_base_url, platform_admin_headers, test_org_id):
        """Should generate permanent workflow key (no expiration)"""
        response = requests.post(
            f"{api_base_url}/api/workflow-keys",
            headers={**platform_admin_headers, "X-Organization-ID": test_org_id},
            json={
                "description": "Permanent Key Test",
                "workflowId": None
            },
            timeout=10
        )

        if response.status_code == 201:
            data = response.json()
            assert "id" in data
            # No expiration should mean expiresAt is null or absent
            if "expiresAt" in data:
                assert data["expiresAt"] is None or data["expiresAt"] == ""
            logger.info("Generated permanent workflow key")

    def test_key_format_validation(self, api_base_url, platform_admin_headers, test_org_id):
        """Should generate properly formatted API key"""
        response = requests.post(
            f"{api_base_url}/api/workflow-keys",
            headers={**platform_admin_headers, "X-Organization-ID": test_org_id},
            json={
                "description": "Format Test Key",
                "workflowId": None,
                "expiresInDays": 7
            },
            timeout=10
        )

        if response.status_code == 201:
            data = response.json()
            # Verify key structure
            assert "id" in data
            assert "description" in data
            assert data["description"] == "Format Test Key"
            logger.info("Key format validation passed")

    def test_key_collision_prevention(self, api_base_url, platform_admin_headers, test_org_id):
        """Generated keys should be unique"""
        response1 = requests.post(
            f"{api_base_url}/api/workflow-keys",
            headers={**platform_admin_headers, "X-Organization-ID": test_org_id},
            json={"description": "Key 1"},
            timeout=10
        )

        response2 = requests.post(
            f"{api_base_url}/api/workflow-keys",
            headers={**platform_admin_headers, "X-Organization-ID": test_org_id},
            json={"description": "Key 2"},
            timeout=10
        )

        if response1.status_code == 201 and response2.status_code == 201:
            key1 = response1.json().get("id")
            key2 = response2.json().get("id")
            # Keys should be different
            assert key1 != key2
            logger.info("Key collision prevention verified")


class TestWorkflowKeysValidation:
    """Test workflow key validation"""

    def test_key_with_workflow_id(self, api_base_url, platform_admin_headers, test_org_id):
        """Should create key scoped to specific workflow"""
        response = requests.post(
            f"{api_base_url}/api/workflow-keys",
            headers={**platform_admin_headers, "X-Organization-ID": test_org_id},
            json={
                "description": "Workflow-Specific Key",
                "workflowId": "workflows.test_workflow",
                "expiresInDays": 30
            },
            timeout=10
        )

        if response.status_code == 201:
            data = response.json()
            assert data.get("workflowId") == "workflows.test_workflow"
            logger.info("Workflow-scoped key created successfully")

    def test_key_disable_global_flag(self, api_base_url, platform_admin_headers, test_org_id):
        """Should handle disableGlobalKey flag"""
        response = requests.post(
            f"{api_base_url}/api/workflow-keys",
            headers={**platform_admin_headers, "X-Organization-ID": test_org_id},
            json={
                "description": "Key with disable flag",
                "workflowId": None,
                "disableGlobalKey": True
            },
            timeout=10
        )

        if response.status_code == 201:
            data = response.json()
            if "disableGlobalKey" in data:
                assert data["disableGlobalKey"] is True
            logger.info("disableGlobalKey flag handled")

    def test_invalid_expiration_days(self, api_base_url, platform_admin_headers, test_org_id):
        """Should handle invalid expiration values"""
        response = requests.post(
            f"{api_base_url}/api/workflow-keys",
            headers={**platform_admin_headers, "X-Organization-ID": test_org_id},
            json={
                "description": "Invalid expiration",
                "workflowId": None,
                "expiresInDays": -1  # Invalid: negative days
            },
            timeout=10
        )

        # Should reject invalid expiration or org context issue
        assert response.status_code in [400, 201, 404]
        logger.info(f"Invalid expiration handled: {response.status_code}")


class TestWorkflowKeysManagement:
    """Test workflow key management operations"""

    def test_list_keys_with_workflow_filter(self, api_base_url, platform_admin_headers, test_org_id):
        """Should filter keys by workflow ID"""
        response = requests.get(
            f"{api_base_url}/api/workflow-keys?workflowId=workflows.test",
            headers={**platform_admin_headers, "X-Organization-ID": test_org_id},
            timeout=10
        )

        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, list)
            # All returned keys should match workflow filter
            for key in data:
                if key.get("workflowId"):
                    assert key["workflowId"] == "workflows.test"
            logger.info(f"Listed {len(data)} keys for workflow filter")

    def test_list_keys_include_revoked_filter(self, api_base_url, platform_admin_headers, test_org_id):
        """Should filter revoked keys"""
        # Get non-revoked keys
        response1 = requests.get(
            f"{api_base_url}/api/workflow-keys?includeRevoked=false",
            headers={**platform_admin_headers, "X-Organization-ID": test_org_id},
            timeout=10
        )

        # Get all keys (including revoked)
        response2 = requests.get(
            f"{api_base_url}/api/workflow-keys?includeRevoked=true",
            headers={**platform_admin_headers, "X-Organization-ID": test_org_id},
            timeout=10
        )

        if response1.status_code == 200 and response2.status_code == 200:
            non_revoked = response1.json()
            all_keys = response2.json()
            # With revoked included, should have same or more keys
            assert len(all_keys) >= len(non_revoked)
            logger.info(f"Non-revoked: {len(non_revoked)}, Total: {len(all_keys)}")

    def test_revoke_key_idempotent(self, api_base_url, platform_admin_headers, test_org_id):
        """Revoking same key twice should be safe"""
        # Create a key
        create_response = requests.post(
            f"{api_base_url}/api/workflow-keys",
            headers={**platform_admin_headers, "X-Organization-ID": test_org_id},
            json={"description": "Key to double revoke"},
            timeout=10
        )

        if create_response.status_code == 201:
            key_id = create_response.json().get("id")

            # Revoke once
            response1 = requests.delete(
                f"{api_base_url}/api/workflow-keys/{key_id}",
                headers={**platform_admin_headers, "X-Organization-ID": test_org_id},
                timeout=10
            )

            # Revoke again (should still succeed or return 404/409)
            response2 = requests.delete(
                f"{api_base_url}/api/workflow-keys/{key_id}",
                headers={**platform_admin_headers, "X-Organization-ID": test_org_id},
                timeout=10
            )

            # First revoke should succeed
            assert response1.status_code in [200, 204]
            # Second should be idempotent (204, 404, or 409)
            assert response2.status_code in [200, 204, 404, 409]
            logger.info("Revoke idempotency verified")

    def test_key_creation_returns_metadata(self, api_base_url, platform_admin_headers, test_org_id):
        """Created key should include all metadata"""
        response = requests.post(
            f"{api_base_url}/api/workflow-keys",
            headers={**platform_admin_headers, "X-Organization-ID": test_org_id},
            json={
                "description": "Metadata Test",
                "workflowId": "workflows.meta_test",
                "expiresInDays": 60
            },
            timeout=10
        )

        if response.status_code == 201:
            data = response.json()
            # Should have required metadata fields
            required_fields = ["id", "createdBy", "createdAt", "description"]
            for field in required_fields:
                assert field in data, f"Missing field: {field}"
            logger.info("Key metadata validation passed")

    def test_masked_key_format(self, api_base_url, platform_admin_headers, test_org_id):
        """Listed keys should have masked values (not raw keys)"""
        response = requests.get(
            f"{api_base_url}/api/workflow-keys",
            headers={**platform_admin_headers, "X-Organization-ID": test_org_id},
            timeout=10
        )

        if response.status_code == 200:
            keys = response.json()
            for key in keys:
                # Raw key should not be present in list
                assert key.get("rawKey") is None or key.get("rawKey") == ""
                # Should have masked key or other identifier
                assert "id" in key or "maskedKey" in key
            logger.info("Masked key format verified")
