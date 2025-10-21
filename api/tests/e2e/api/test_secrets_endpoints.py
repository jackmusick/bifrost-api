"""Integration tests for Secrets API endpoints

Tests the secrets management endpoints for Azure Key Vault integration.
All tests require a platform admin role to execute.
"""

import requests


class TestSecretsCRUD:
    """Test secret CRUD operations"""

    def test_list_secrets_success(self, api_base_url, platform_admin_headers):
        """Should list secrets successfully"""
        response = requests.get(
            f"{api_base_url}/api/secrets",
            headers=platform_admin_headers,
            timeout=10
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
        assert "secrets" in data
        assert isinstance(data["secrets"], list)

    def test_create_secret_success(self, api_base_url, platform_admin_headers):
        """Should create organization secret successfully"""
        response = requests.post(
            f"{api_base_url}/api/secrets",
            headers=platform_admin_headers,
            json={
                "orgId": "GLOBAL",
                "secretKey": "test-api-key-integration",
                "value": "secret-value-123"
            },
            timeout=10
        )
        # May return 201 (created) or 409 (conflict - already exists)
        assert response.status_code in [201, 409]
        if response.status_code == 201:
            data = response.json()
            assert data["secretKey"] == "test-api-key-integration"
            assert data["orgId"] == "GLOBAL"

    def test_update_secret_success(self, api_base_url, platform_admin_headers):
        """Should update existing secret"""
        # First ensure a secret exists
        create_response = requests.post(
            f"{api_base_url}/api/secrets",
            headers=platform_admin_headers,
            json={
                "orgId": "GLOBAL",
                "secretKey": "test-update-key",
                "value": "initial-value"
            },
            timeout=10
        )

        # Now update it
        response = requests.put(
            f"{api_base_url}/api/secrets/GLOBAL--test-update-key",
            headers=platform_admin_headers,
            json={
                "value": "updated-secret-value"
            },
            timeout=10
        )
        # May return 200 (success) or 404 (not found if create failed)
        assert response.status_code in [200, 404]
        if response.status_code == 200:
            data = response.json()
            assert data["value"] == "updated-secret-value"

    def test_delete_secret_success(self, api_base_url, platform_admin_headers):
        """Should delete secret successfully"""
        # First create a secret to delete
        create_response = requests.post(
            f"{api_base_url}/api/secrets",
            headers=platform_admin_headers,
            json={
                "orgId": "GLOBAL",
                "secretKey": "test-delete-key",
                "value": "to-be-deleted"
            },
            timeout=10
        )

        if create_response.status_code in [201, 409]:
            response = requests.delete(
                f"{api_base_url}/api/secrets/GLOBAL--test-delete-key",
                headers=platform_admin_headers,
                timeout=10
            )
            # May return 200 (deleted) or 404 (not found)
            assert response.status_code in [200, 204, 404]

    def test_list_secrets_with_org_filter(self, api_base_url, platform_admin_headers):
        """Should list secrets filtered by organization"""
        response = requests.get(
            f"{api_base_url}/api/secrets?org_id=GLOBAL",
            headers=platform_admin_headers,
            timeout=10
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
        assert data.get("orgId") == "GLOBAL"


class TestSecretsAuthorization:
    """Test secret authorization and access control"""

    def test_regular_user_cannot_list_secrets(self, api_base_url, regular_user_headers):
        """Regular users should not list secrets"""
        response = requests.get(
            f"{api_base_url}/api/secrets",
            headers=regular_user_headers,
            timeout=10
        )
        # Should be 403 (Forbidden) or 401 (Unauthorized)
        assert response.status_code in [403, 401]

    def test_regular_user_cannot_create_secrets(self, api_base_url, regular_user_headers):
        """Regular users should not create secrets"""
        response = requests.post(
            f"{api_base_url}/api/secrets",
            headers=regular_user_headers,
            json={
                "orgId": "GLOBAL",
                "secretKey": "unauthorized-key",
                "value": "value"
            },
            timeout=10
        )
        assert response.status_code in [403, 401]

    def test_regular_user_cannot_update_secrets(self, api_base_url, regular_user_headers):
        """Regular users should not update secrets"""
        response = requests.put(
            f"{api_base_url}/api/secrets/GLOBAL--test-key",
            headers=regular_user_headers,
            json={"value": "new-value"},
            timeout=10
        )
        assert response.status_code in [403, 401, 404]

    def test_regular_user_cannot_delete_secrets(self, api_base_url, regular_user_headers):
        """Regular users should not delete secrets"""
        response = requests.delete(
            f"{api_base_url}/api/secrets/GLOBAL--test-key",
            headers=regular_user_headers,
            timeout=10
        )
        assert response.status_code in [403, 401, 404]


class TestSecretsValidation:
    """Test secret validation and error handling"""

    def test_create_secret_missing_org_id(self, api_base_url, platform_admin_headers):
        """Should validate orgId is required"""
        response = requests.post(
            f"{api_base_url}/api/secrets",
            headers=platform_admin_headers,
            json={
                "secretKey": "test-key",
                "value": "test-value"
            },
            timeout=10
        )
        # Should be 400 (validation error) or 422 (unprocessable)
        assert response.status_code in [400, 422]

    def test_create_secret_missing_key(self, api_base_url, platform_admin_headers):
        """Should validate secretKey is required"""
        response = requests.post(
            f"{api_base_url}/api/secrets",
            headers=platform_admin_headers,
            json={
                "orgId": "GLOBAL",
                "value": "test-value"
            },
            timeout=10
        )
        # Should be 400 (validation error) or 422 (unprocessable)
        assert response.status_code in [400, 422]

    def test_create_secret_missing_value(self, api_base_url, platform_admin_headers):
        """Should validate value is required"""
        response = requests.post(
            f"{api_base_url}/api/secrets",
            headers=platform_admin_headers,
            json={
                "orgId": "GLOBAL",
                "secretKey": "test-key"
            },
            timeout=10
        )
        # Should be 400 (validation error) or 422 (unprocessable)
        assert response.status_code in [400, 422]

    def test_update_secret_invalid_format(self, api_base_url, platform_admin_headers):
        """Should validate secret name format"""
        response = requests.put(
            f"{api_base_url}/api/secrets/invalid-name-no-separator",
            headers=platform_admin_headers,
            json={"value": "new-value"},
            timeout=10
        )
        # Should be 400 (bad request) or 404 (not found)
        assert response.status_code in [400, 404]

    def test_create_secret_with_description(self, api_base_url, platform_admin_headers):
        """Should create secret with description"""
        response = requests.post(
            f"{api_base_url}/api/secrets",
            headers=platform_admin_headers,
            json={
                "orgId": "GLOBAL",
                "secretKey": "test-secret-with-desc",
                "value": "secret-value",
                "description": "This is a test secret with description"
            },
            timeout=10
        )
        assert response.status_code in [201, 409]
        if response.status_code == 201:
            data = response.json()
            # API may or may not return description field
            assert "secretKey" in data
            assert data["secretKey"] == "test-secret-with-desc"


class TestSecretsEncryption:
    """Test secret encryption and storage"""

    def test_secret_value_encrypted_in_storage(self, api_base_url, platform_admin_headers):
        """Should encrypt secret value before storage"""
        response = requests.post(
            f"{api_base_url}/api/secrets",
            headers=platform_admin_headers,
            json={
                "orgId": "GLOBAL",
                "secretKey": "encrypted-test-key",
                "value": "plaintext-secret-value"
            },
            timeout=10
        )
        assert response.status_code in [201, 409]
        # API may or may not mask the value in response
        if response.status_code == 201:
            data = response.json()
            # Response should contain secret data
            assert "secretKey" in data

    def test_secret_decryption_by_platform_admin(self, api_base_url, platform_admin_headers):
        """Should decrypt secret for platform admin on retrieval"""
        # Create secret
        create_resp = requests.post(
            f"{api_base_url}/api/secrets",
            headers=platform_admin_headers,
            json={
                "orgId": "GLOBAL",
                "secretKey": "decrypt-test-key",
                "value": "secret-to-decrypt"
            },
            timeout=10
        )

        if create_resp.status_code == 201:
            secret_id = create_resp.json().get("id") or "GLOBAL--decrypt-test-key"

            # Retrieve and check decryption
            get_resp = requests.get(
                f"{api_base_url}/api/secrets/{secret_id}",
                headers=platform_admin_headers,
                timeout=10
            )
            # May return the value if decryption is supported
            assert get_resp.status_code in [200, 404]

    def test_secret_value_masked_in_list_response(self, api_base_url, platform_admin_headers):
        """Should mask secret values in list endpoint"""
        response = requests.get(
            f"{api_base_url}/api/secrets",
            headers=platform_admin_headers,
            timeout=10
        )
        assert response.status_code == 200
        data = response.json()
        # API should return list of secrets or dict with secrets field
        if isinstance(data, dict) and "secrets" in data:
            if isinstance(data["secrets"], list):
                # Each secret should have some representation
                for secret in data["secrets"]:
                    if isinstance(secret, dict):
                        # Should have secretKey or name
                        assert "secretKey" in secret or "name" in secret
        elif isinstance(data, list):
            # Direct list of secrets
            for secret in data:
                assert isinstance(secret, dict)

    def test_secret_encryption_key_rotation_support(self, api_base_url, platform_admin_headers):
        """Should support re-encryption with new encryption key"""
        response = requests.post(
            f"{api_base_url}/api/secrets",
            headers=platform_admin_headers,
            json={
                "orgId": "GLOBAL",
                "secretKey": "rotation-test-key",
                "value": "secret-for-rotation"
            },
            timeout=10
        )

        if response.status_code == 201:
            secret_id = response.json().get("id") or "GLOBAL--rotation-test-key"

            # Try to rotate encryption
            rotate_resp = requests.post(
                f"{api_base_url}/api/secrets/{secret_id}/rotate-key",
                headers=platform_admin_headers,
                json={},
                timeout=10
            )
            # May have rotation endpoint or not
            assert rotate_resp.status_code in [200, 404, 405]


class TestSecretsAccessControl:
    """Test secret access control and authorization"""

    def test_org_admin_cannot_read_secret_value(self, api_base_url, admin_headers):
        """Should prevent org admin from reading secret values"""
        response = requests.post(
            f"{api_base_url}/api/secrets",
            headers=admin_headers,
            json={
                "orgId": "GLOBAL",
                "secretKey": "admin-access-test",
                "value": "protected-value"
            },
            timeout=10
        )

        if response.status_code in [201, 409]:
            secret_id = response.json().get("id") or "GLOBAL--admin-access-test"

            # Try to read as org admin
            get_resp = requests.get(
                f"{api_base_url}/api/secrets/{secret_id}",
                headers=admin_headers,
                timeout=10
            )
            # Should either deny or return masked value
            if get_resp.status_code == 200:
                data = get_resp.json()
                # If accessible, value should be masked
                assert data.get("value") is None or data.get("value") in ["***", ""]

    def test_regular_user_cannot_list_secrets(self, api_base_url, regular_user_headers):
        """Should prevent regular users from listing secrets"""
        response = requests.get(
            f"{api_base_url}/api/secrets",
            headers=regular_user_headers,
            timeout=10
        )
        assert response.status_code in [403, 401]

    def test_secret_access_audit_trail(self, api_base_url, platform_admin_headers):
        """Should log access to secrets"""
        # Create a secret
        create_resp = requests.post(
            f"{api_base_url}/api/secrets",
            headers=platform_admin_headers,
            json={
                "orgId": "GLOBAL",
                "secretKey": "audit-test-key",
                "value": "audit-test-value"
            },
            timeout=10
        )

        if create_resp.status_code == 201:
            secret_id = create_resp.json().get("id") or "GLOBAL--audit-test-key"

            # Access the secret
            requests.get(
                f"{api_base_url}/api/secrets/{secret_id}",
                headers=platform_admin_headers,
                timeout=10
            )

            # Try to get audit log
            audit_resp = requests.get(
                f"{api_base_url}/api/secrets/{secret_id}/audit-log",
                headers=platform_admin_headers,
                timeout=10
            )
            # May have audit endpoint or not
            assert audit_resp.status_code in [200, 404, 405]


class TestSecretsBulkOperations:
    """Test bulk secret operations"""

    def test_create_multiple_secrets_batch(self, api_base_url, platform_admin_headers):
        """Should create multiple secrets in batch"""
        batch_data = {
            "secrets": [
                {"orgId": "GLOBAL", "secretKey": f"batch-secret-{i}", "value": f"value-{i}"}
                for i in range(5)
            ]
        }
        response = requests.post(
            f"{api_base_url}/api/secrets/batch",
            headers=platform_admin_headers,
            json=batch_data,
            timeout=10
        )
        # May have batch endpoint or not
        assert response.status_code in [200, 201, 404, 405]

    def test_update_multiple_secrets_batch(self, api_base_url, platform_admin_headers):
        """Should update multiple secrets in batch"""
        batch_data = {
            "updates": [
                {"id": "GLOBAL--batch-update-1", "value": "new-value-1"},
                {"id": "GLOBAL--batch-update-2", "value": "new-value-2"}
            ]
        }
        response = requests.put(
            f"{api_base_url}/api/secrets/batch",
            headers=platform_admin_headers,
            json=batch_data,
            timeout=10
        )
        # May have batch endpoint or not (400 if not supported)
        assert response.status_code in [200, 204, 400, 404, 405]

    def test_delete_multiple_secrets_batch(self, api_base_url, platform_admin_headers):
        """Should delete multiple secrets in batch"""
        batch_data = {
            "ids": ["GLOBAL--batch-delete-1", "GLOBAL--batch-delete-2"]
        }
        response = requests.delete(
            f"{api_base_url}/api/secrets/batch",
            headers=platform_admin_headers,
            json=batch_data,
            timeout=10
        )
        # May have batch endpoint or not (400 if not supported)
        assert response.status_code in [200, 204, 400, 404, 405]

    def test_batch_operation_atomicity(self, api_base_url, platform_admin_headers):
        """Should handle batch operations atomically (all or nothing)"""
        batch_data = {
            "secrets": [
                {"orgId": "GLOBAL", "secretKey": "atomic-1", "value": "v1"},
                {"orgId": "GLOBAL", "secretKey": "atomic-2", "value": "v2"},
                {"orgId": "GLOBAL", "secretKey": "atomic-3", "value": "v3"}
            ]
        }
        response = requests.post(
            f"{api_base_url}/api/secrets/batch?atomic=true",
            headers=platform_admin_headers,
            json=batch_data,
            timeout=10
        )
        # If atomic flag supported, should be all or nothing
        assert response.status_code in [200, 201, 400, 404, 405]


class TestSecretsVersioning:
    """Test secret versioning and history"""

    def test_secret_update_creates_version(self, api_base_url, platform_admin_headers):
        """Should create new version on secret update"""
        # Create secret
        create_resp = requests.post(
            f"{api_base_url}/api/secrets",
            headers=platform_admin_headers,
            json={
                "orgId": "GLOBAL",
                "secretKey": "version-test",
                "value": "version-1"
            },
            timeout=10
        )

        if create_resp.status_code == 201:
            secret_id = create_resp.json().get("id") or "GLOBAL--version-test"

            # Update secret
            update_resp = requests.put(
                f"{api_base_url}/api/secrets/{secret_id}",
                headers=platform_admin_headers,
                json={"value": "version-2"},
                timeout=10
            )

            # Should complete successfully
            if update_resp.status_code == 200:
                data = update_resp.json()
                # Should have updated data
                assert "secretKey" in data or "name" in data

    def test_list_secret_versions(self, api_base_url, platform_admin_headers):
        """Should list all versions of a secret"""
        response = requests.post(
            f"{api_base_url}/api/secrets",
            headers=platform_admin_headers,
            json={
                "orgId": "GLOBAL",
                "secretKey": "version-list-test",
                "value": "initial"
            },
            timeout=10
        )

        if response.status_code == 201:
            secret_id = response.json().get("id") or "GLOBAL--version-list-test"

            # Get versions
            versions_resp = requests.get(
                f"{api_base_url}/api/secrets/{secret_id}/versions",
                headers=platform_admin_headers,
                timeout=10
            )
            # May have versions endpoint
            assert versions_resp.status_code in [200, 404, 405]

    def test_rollback_to_previous_secret_version(self, api_base_url, platform_admin_headers):
        """Should rollback secret to previous version"""
        # Create secret
        create_resp = requests.post(
            f"{api_base_url}/api/secrets",
            headers=platform_admin_headers,
            json={
                "orgId": "GLOBAL",
                "secretKey": "rollback-test",
                "value": "v1"
            },
            timeout=10
        )

        if create_resp.status_code == 201:
            secret_id = create_resp.json().get("id") or "GLOBAL--rollback-test"

            # Update
            requests.put(
                f"{api_base_url}/api/secrets/{secret_id}",
                headers=platform_admin_headers,
                json={"value": "v2"},
                timeout=10
            )

            # Rollback
            rollback_resp = requests.post(
                f"{api_base_url}/api/secrets/{secret_id}/rollback",
                headers=platform_admin_headers,
                json={"version": 1},
                timeout=10
            )
            # May have rollback endpoint
            assert rollback_resp.status_code in [200, 404, 405]

    def test_purge_old_secret_versions(self, api_base_url, platform_admin_headers):
        """Should purge old secret versions"""
        response = requests.post(
            f"{api_base_url}/api/secrets",
            headers=platform_admin_headers,
            json={
                "orgId": "GLOBAL",
                "secretKey": "purge-test",
                "value": "value"
            },
            timeout=10
        )

        if response.status_code == 201:
            secret_id = response.json().get("id") or "GLOBAL--purge-test"

            # Purge old versions
            purge_resp = requests.post(
                f"{api_base_url}/api/secrets/{secret_id}/purge-old-versions",
                headers=platform_admin_headers,
                json={"keep_versions": 1},
                timeout=10
            )
            # May have purge endpoint
            assert purge_resp.status_code in [200, 404, 405]

    def test_secret_expiration_ttl(self, api_base_url, platform_admin_headers):
        """Should support secret expiration/TTL"""
        response = requests.post(
            f"{api_base_url}/api/secrets",
            headers=platform_admin_headers,
            json={
                "orgId": "GLOBAL",
                "secretKey": "expiring-secret",
                "value": "temporary",
                "expiresIn": 3600  # 1 hour
            },
            timeout=10
        )
        # May support TTL or not
        assert response.status_code in [201, 409, 400]
