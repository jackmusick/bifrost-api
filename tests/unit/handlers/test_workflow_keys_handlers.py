"""
Unit tests for workflow_keys_handlers
Tests workflow key generation, listing, and revocation
"""

import json
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

import azure.functions as func

from shared.handlers.workflow_keys_handlers import (
    create_workflow_key_handler,
    list_workflow_keys_handler,
    revoke_workflow_key_handler,
    _mask_key,
)


class TestMaskKey:
    """Test key masking utility"""

    def test_mask_key_normal(self):
        """Test masking normal length keys"""
        result = _mask_key("abcd1234efgh5678")
        assert result == "****5678"

    def test_mask_key_short(self):
        """Test masking short keys"""
        result = _mask_key("ab")
        assert result == "****"


class TestCreateWorkflowKeyHandler:
    """Test create_workflow_key_handler"""

    @pytest.mark.asyncio
    async def test_create_workflow_key_success(self):
        """Test successful workflow key creation"""
        mock_req = Mock(spec=func.HttpRequest)
        mock_req.get_json.return_value = {
            "workflowId": "workflows.test",
            "expiresInDays": 90,
            "description": "Test key"
        }
        mock_req.org_context = Mock(caller=Mock(email="user@example.com"))

        with patch('shared.handlers.workflow_keys_handlers.generate_workflow_key') as mock_gen:
            mock_gen.return_value = ("raw_key_abc123", Mock(
                id="key-123",
                hashedKey="hashed_abc123",
                workflowId="workflows.test",
                createdBy="user@example.com",
                createdAt=datetime.utcnow(),
                lastUsedAt=None,
                revoked=False,
                revokedAt=None,
                revokedBy=None,
                expiresAt=None,
                description="Test key",
                disableGlobalKey=False
            ))

            with patch('shared.handlers.workflow_keys_handlers.get_global_config_repository') as mock_table:
                mock_client = mock_table.return_value
                mock_client.create_workflow_key = Mock()

                response = await create_workflow_key_handler(mock_req)

                assert response.status_code == 201
                data = json.loads(response.get_body())
                assert data["rawKey"] == "raw_key_abc123"
                assert data["id"] == "key-123"
                mock_client.create_workflow_key.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_workflow_key_global(self):
        """Test creating global (workflow-agnostic) key"""
        mock_req = Mock(spec=func.HttpRequest)
        mock_req.get_json.return_value = {
            "workflowId": None,  # Global key
            "expiresInDays": None,
            "description": "Global key"
        }
        mock_req.org_context = Mock(caller=Mock(email="user@example.com"))

        with patch('shared.handlers.workflow_keys_handlers.generate_workflow_key') as mock_gen:
            mock_gen.return_value = ("raw_key_global", Mock(
                id="key-global",
                hashedKey="hashed_global",
                workflowId=None,
                createdBy="user@example.com",
                createdAt=datetime.utcnow(),
                lastUsedAt=None,
                revoked=False,
                revokedAt=None,
                revokedBy=None,
                expiresAt=None,
                description="Global key",
                disableGlobalKey=False
            ))

            with patch('shared.handlers.workflow_keys_handlers.get_global_config_repository') as mock_table:
                mock_client = mock_table.return_value
                mock_client.create_workflow_key = Mock()

                response = await create_workflow_key_handler(mock_req)

                assert response.status_code == 201
                # Verify global key uses correct prefix
                call_args = mock_client.create_workflow_key.call_args
                entity = call_args[0][0]
                assert entity["RowKey"].startswith("systemconfig:globalkey:")

    @pytest.mark.asyncio
    async def test_create_workflow_key_with_expiration(self):
        """Test creating key with expiration"""
        mock_req = Mock(spec=func.HttpRequest)
        mock_req.get_json.return_value = {
            "workflowId": "workflows.test",
            "expiresInDays": 30,
        }
        mock_req.org_context = Mock(caller=Mock(email="user@example.com"))

        with patch('shared.handlers.workflow_keys_handlers.generate_workflow_key') as mock_gen:
            mock_gen.return_value = ("raw_key_exp", Mock(
                id="key-exp",
                hashedKey="hashed_exp",
                workflowId="workflows.test",
                createdBy="user@example.com",
                createdAt=datetime.utcnow(),
                lastUsedAt=None,
                revoked=False,
                revokedAt=None,
                revokedBy=None,
                expiresAt=datetime.utcnow() + timedelta(days=30),
                description=None,
                disableGlobalKey=False
            ))

            with patch('shared.handlers.workflow_keys_handlers.get_global_config_repository') as mock_table:
                mock_client = mock_table.return_value
                mock_client.create_workflow_key = Mock()

                response = await create_workflow_key_handler(mock_req)

                assert response.status_code == 201

    @pytest.mark.asyncio
    async def test_create_workflow_key_validation_error(self):
        """Test validation error in key creation"""
        mock_req = Mock(spec=func.HttpRequest)
        mock_req.get_json.return_value = {}
        mock_req.org_context = Mock(caller=Mock(email="user@example.com"))

        with patch('shared.handlers.workflow_keys_handlers.WorkflowKeyCreateRequest') as MockRequest:
            MockRequest.side_effect = ValueError("Invalid input")

            response = await create_workflow_key_handler(mock_req)

            assert response.status_code == 400
            data = json.loads(response.get_body())
            assert data["error"] == "ValidationError"

    @pytest.mark.asyncio
    async def test_create_workflow_key_server_error(self):
        """Test server error during key creation"""
        mock_req = Mock(spec=func.HttpRequest)
        mock_req.get_json.return_value = {
            "workflowId": "workflows.test"
        }
        mock_req.org_context = Mock(caller=Mock(email="user@example.com"))

        with patch('shared.handlers.workflow_keys_handlers.generate_workflow_key') as mock_gen:
            mock_gen.side_effect = Exception("Key generation failed")

            response = await create_workflow_key_handler(mock_req)

            assert response.status_code == 500
            data = json.loads(response.get_body())
            assert data["error"] == "InternalError"


class TestListWorkflowKeysHandler:
    """Test list_workflow_keys_handler"""


    @pytest.mark.asyncio
    async def test_list_workflow_keys_empty(self):
        """Test listing when no keys exist"""
        mock_req = Mock(spec=func.HttpRequest)
        mock_req.org_context = Mock(caller=Mock(email="user@example.com"))
        mock_req.params = {}

        with patch('shared.handlers.workflow_keys_handlers.get_global_config_repository') as mock_table:
            mock_client = mock_table.return_value
            mock_client.list_workflow_keys.return_value = []

            response = await list_workflow_keys_handler(mock_req)

            assert response.status_code == 200
            data = json.loads(response.get_body())
            assert data == []

    @pytest.mark.asyncio
    async def test_list_workflow_keys_filter_by_workflow(self):
        """Test listing keys filtered by workflow"""
        mock_req = Mock(spec=func.HttpRequest)
        mock_req.org_context = Mock(caller=Mock(email="user@example.com"))
        mock_req.params = {"workflowId": "workflows.specific"}

        with patch('shared.handlers.workflow_keys_handlers.get_global_config_repository') as mock_table:
            mock_client = mock_table.return_value
            mock_client.list_workflow_keys.return_value = []

            response = await list_workflow_keys_handler(mock_req)

            assert response.status_code == 200
            # Verify query filters by workflow
            call_args = mock_client.list_workflow_keys.call_args
            # Args are: (user_email, workflow_id_filter, include_revoked)
            workflow_id_filter = call_args[0][1]
            assert workflow_id_filter == "workflows.specific"

    @pytest.mark.asyncio
    async def test_list_workflow_keys_include_revoked(self):
        """Test listing with revoked keys included"""
        mock_req = Mock(spec=func.HttpRequest)
        mock_req.org_context = Mock(caller=Mock(email="user@example.com"))
        mock_req.params = {"includeRevoked": "true"}

        with patch('shared.handlers.workflow_keys_handlers.get_global_config_repository') as mock_table:
            mock_client = mock_table.return_value
            mock_client.list_workflow_keys.return_value = []

            response = await list_workflow_keys_handler(mock_req)

            assert response.status_code == 200
            # Verify include_revoked parameter is True
            call_args = mock_client.list_workflow_keys.call_args
            # Args are: (user_email, workflow_id_filter, include_revoked)
            include_revoked = call_args[0][2]
            assert include_revoked is True

    @pytest.mark.asyncio
    async def test_list_workflow_keys_exclude_revoked(self):
        """Test listing excluding revoked keys (default)"""
        mock_req = Mock(spec=func.HttpRequest)
        mock_req.org_context = Mock(caller=Mock(email="user@example.com"))
        mock_req.params = {}

        with patch('shared.handlers.workflow_keys_handlers.get_global_config_repository') as mock_table:
            mock_client = mock_table.return_value
            mock_client.list_workflow_keys.return_value = []

            response = await list_workflow_keys_handler(mock_req)

            assert response.status_code == 200
            # Verify include_revoked parameter is False (default)
            call_args = mock_client.list_workflow_keys.call_args
            # Args are: (user_email, workflow_id_filter, include_revoked)
            include_revoked = call_args[0][2]
            assert include_revoked is False

    @pytest.mark.asyncio
    async def test_list_workflow_keys_error(self):
        """Test error handling in listing"""
        mock_req = Mock(spec=func.HttpRequest)
        mock_req.org_context = Mock(caller=Mock(email="user@example.com"))
        mock_req.params = {}

        with patch('shared.handlers.workflow_keys_handlers.get_global_config_repository') as mock_table:
            mock_client = mock_table.return_value
            mock_client.list_workflow_keys.side_effect = Exception("Database error")

            response = await list_workflow_keys_handler(mock_req)

            assert response.status_code == 500


class TestRevokeWorkflowKeyHandler:
    """Test revoke_workflow_key_handler"""

    @pytest.mark.asyncio
    async def test_revoke_workflow_key_success(self):
        """Test successful key revocation"""
        mock_req = Mock(spec=func.HttpRequest)
        mock_req.route_params = {"keyId": "key-123"}
        mock_req.org_context = Mock(caller=Mock(email="user@example.com"))

        entity = {
            "PartitionKey": "GLOBAL",
            "RowKey": "workflowkey:key-123",
            "KeyId": "key-123",
            "CreatedBy": "user@example.com",
            "HashedKey": "hashed123",
            "Revoked": False,
        }

        with patch('shared.handlers.workflow_keys_handlers.get_global_config_repository') as mock_table:
            mock_client = mock_table.return_value
            mock_client.get_workflow_key_by_id.return_value = entity
            mock_client.revoke_workflow_key.return_value = True  # Success

            response = await revoke_workflow_key_handler(mock_req)

            assert response.status_code == 204
            mock_client.revoke_workflow_key.assert_called_once()
            # Verify revoke_workflow_key called with correct parameters
            call_args = mock_client.revoke_workflow_key.call_args
            # Args are: (key_id, user_email)
            key_id = call_args[0][0]
            user_email = call_args[0][1]
            assert key_id == "key-123"
            assert user_email == "user@example.com"

    @pytest.mark.asyncio
    async def test_revoke_workflow_key_not_found(self):
        """Test revoking non-existent key"""
        mock_req = Mock(spec=func.HttpRequest)
        mock_req.route_params = {"keyId": "key-nonexistent"}
        mock_req.org_context = Mock(caller=Mock(email="user@example.com"))

        with patch('shared.handlers.workflow_keys_handlers.get_global_config_repository') as mock_table:
            mock_client = mock_table.return_value
            mock_client.get_workflow_key_by_id.return_value = None  # Not found

            response = await revoke_workflow_key_handler(mock_req)

            assert response.status_code == 404
            data = json.loads(response.get_body())
            assert data["error"] == "NotFound"

    @pytest.mark.asyncio
    async def test_revoke_workflow_key_forbidden(self):
        """Test revoking key owned by another user"""
        mock_req = Mock(spec=func.HttpRequest)
        mock_req.route_params = {"keyId": "key-123"}
        mock_req.org_context = Mock(caller=Mock(email="user@example.com"))

        entity = {
            "PartitionKey": "GLOBAL",
            "RowKey": "workflowkey:key-123",
            "CreatedBy": "other@example.com",  # Different user
            "HashedKey": "hashed123",
        }

        with patch('shared.handlers.workflow_keys_handlers.get_global_config_repository') as mock_table:
            mock_client = mock_table.return_value
            mock_client.get_workflow_key_by_id.return_value = entity

            response = await revoke_workflow_key_handler(mock_req)

            assert response.status_code == 403
            data = json.loads(response.get_body())
            assert data["error"] == "Forbidden"

    @pytest.mark.asyncio
    async def test_revoke_workflow_key_missing_keyid(self):
        """Test revoking without keyId"""
        mock_req = Mock(spec=func.HttpRequest)
        mock_req.route_params = {}  # No keyId
        mock_req.org_context = Mock(caller=Mock(email="user@example.com"))

        response = await revoke_workflow_key_handler(mock_req)

        assert response.status_code == 400
        data = json.loads(response.get_body())
        assert data["error"] == "BadRequest"

    @pytest.mark.asyncio
    async def test_revoke_global_key(self):
        """Test revoking global (non-workflow-specific) key"""
        mock_req = Mock(spec=func.HttpRequest)
        mock_req.route_params = {"keyId": "key-global"}
        mock_req.org_context = Mock(caller=Mock(email="user@example.com"))

        # First call fails (workflow key), second succeeds (global key)
        entity = {
            "PartitionKey": "GLOBAL",
            "RowKey": "systemconfig:globalkey:key-global",
            "CreatedBy": "user@example.com",
            "HashedKey": "hashed_global",
            "Revoked": False,
        }

        with patch('shared.handlers.workflow_keys_handlers.get_global_config_repository') as mock_table:
            mock_client = mock_table.return_value
            mock_client.get_workflow_key_by_id.return_value = entity
            mock_client.revoke_workflow_key.return_value = True

            response = await revoke_workflow_key_handler(mock_req)

            assert response.status_code == 204
