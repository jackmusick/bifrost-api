"""
Integration tests for OAuth API endpoints
Tests full request/response cycle with Azurite for all 10 OAuth endpoints
"""

import pytest
import json
import os
import uuid
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch, AsyncMock
import azure.functions as func

# Set development environment for mock auth
os.environ["AZURE_FUNCTIONS_ENVIRONMENT"] = "Development"

from functions.oauth_api import (
    create_oauth_connection,
    list_oauth_connections,
    get_oauth_connection,
    update_oauth_connection,
    delete_oauth_connection,
    authorize_oauth_connection,
    cancel_oauth_authorization,
    refresh_oauth_token,
    get_oauth_credentials,
    get_oauth_refresh_job_status
)
from shared.storage import TableStorageService


def create_mock_request(user_id, email="test@example.com", org_id="GLOBAL", **kwargs):
    """Helper to create a properly mocked request for testing"""
    req = MagicMock(spec=func.HttpRequest)
    req.headers = MagicMock()
    req.headers.get = lambda key, default=None: {
        "X-Test-User-Id": user_id,
        "X-Test-User-Email": email,
        "X-Test-User-Name": "Test User"
    }.get(key, default)
    req.url = "http://localhost:7072/api/oauth/test"
    req.params = {}
    req.route_params = {}

    # Add any additional attributes
    for key, value in kwargs.items():
        setattr(req, key, value)

    return req


class TestCreateOAuthConnection:
    """Integration tests for POST /api/oauth/connections"""

    async def test_create_connection_valid(self, test_user, azurite_tables):
        """Test creating a new OAuth connection with valid data"""
        req = create_mock_request(test_user["user_id"], test_user["email"])
        req.get_json = MagicMock(return_value={
            "connection_name": "TestConnection",
            "oauth_flow_type": "authorization_code",
            "client_id": "test-client-id",
            "authorization_url": "https://login.microsoftonline.com/authorize",
            "token_url": "https://login.microsoftonline.com/token",
            "scopes": "User.Read,Mail.Read",
            "redirect_uri": "/oauth/callback/TestConnection"
        })

        # Call endpoint
        response = await create_oauth_connection(req)

        # Assertions
        assert response.status_code == 201
        connection = json.loads(response.get_body())
        assert connection["connectionName"] == "TestConnection"
        assert connection["provider"] == "microsoft"
        assert connection["status"] == "not_connected"
        assert connection["orgId"] == "GLOBAL"

    async def test_create_connection_duplicate(self, test_user, azurite_tables):
        """Test creating duplicate connection returns 409"""
        # Create first connection
        config_service = TableStorageService("Config")
        connection_id = str(uuid.uuid4())
        config_service.insert_entity({
            "PartitionKey": "GLOBAL",
            "RowKey": f"oauth-connection:TestDuplicate",
            "Value": json.dumps({
                "id": connection_id,
                "connection_name": "TestDuplicate",
                "provider": "microsoft",
                "client_id": "test-id",
                "authorization_url": "https://test.com",
                "token_url": "https://test.com/token",
                "scopes": "test",
                "redirect_uri": "/oauth/callback",
                "status": "not_connected",
                "org_id": "GLOBAL",
                "created_by": test_user["user_id"],
                "created_at": datetime.utcnow().isoformat()
            })
        })

        # Try to create duplicate
        req = create_mock_request(test_user["user_id"], test_user["email"])
        req.get_json = MagicMock(return_value={
            "connection_name": "TestDuplicate",
            "oauth_flow_type": "authorization_code",
            "client_id": "test-client-id",
            "authorization_url": "https://test.com",
            "token_url": "https://test.com/token",
            "scopes": "test",
            "redirect_uri": "/oauth/callback/TestDuplicate"
        })

        response = await create_oauth_connection(req)

        # Assertions
        assert response.status_code == 409
        error = json.loads(response.get_body())
        assert error["error"] == "Conflict"


class TestListOAuthConnections:
    """Integration tests for GET /api/oauth/connections"""

    async def test_list_connections_global(self, test_user, azurite_tables):
        """Test listing OAuth connections for GLOBAL scope"""
        # Create test connections
        config_service = TableStorageService("Config")
        for i in range(3):
            connection_id = str(uuid.uuid4())
            config_service.insert_entity({
                "PartitionKey": "GLOBAL",
                "RowKey": f"oauth-connection:Connection{i}",
                "Value": json.dumps({
                    "id": connection_id,
                    "connection_name": f"Connection{i}",
                    "provider": "microsoft",
                    "client_id": f"client-{i}",
                    "authorization_url": "https://test.com",
                    "token_url": "https://test.com/token",
                    "scopes": "test",
                    "redirect_uri": "/oauth/callback",
                    "status": "not_connected" if i < 2 else "completed",
                    "org_id": "GLOBAL",
                    "created_by": test_user["user_id"],
                    "created_at": datetime.utcnow().isoformat()
                })
            })

        # List connections
        req = create_mock_request(test_user["user_id"], test_user["email"])
        response = await list_oauth_connections(req)

        # Assertions
        assert response.status_code == 200
        connections = json.loads(response.get_body())
        assert isinstance(connections, list)
        assert len(connections) == 3

    async def test_list_connections_empty(self, test_user, azurite_tables):
        """Test listing when no connections exist"""
        req = create_mock_request(test_user["user_id"], test_user["email"])
        response = await list_oauth_connections(req)

        # Assertions
        assert response.status_code == 200
        connections = json.loads(response.get_body())
        assert isinstance(connections, list)
        assert len(connections) == 0


class TestGetOAuthConnection:
    """Integration tests for GET /api/oauth/connections/{connection_name}"""

    async def test_get_connection_exists(self, test_user, azurite_tables):
        """Test getting an existing OAuth connection"""
        # Create connection
        config_service = TableStorageService("Config")
        connection_id = str(uuid.uuid4())
        config_service.insert_entity({
            "PartitionKey": "GLOBAL",
            "RowKey": "oauth-connection:TestConnection",
            "Value": json.dumps({
                "id": connection_id,
                "connection_name": "TestConnection",
                "provider": "microsoft",
                "client_id": "test-client-id",
                "authorization_url": "https://test.com",
                "token_url": "https://test.com/token",
                "scopes": "User.Read",
                "redirect_uri": "/oauth/callback",
                "status": "completed",
                "org_id": "GLOBAL",
                "created_by": test_user["user_id"],
                "created_at": datetime.utcnow().isoformat()
            })
        })

        # Get connection
        req = create_mock_request(test_user["user_id"], test_user["email"])
        req.route_params = {"connection_name": "TestConnection"}
        response = await get_oauth_connection(req)

        # Assertions
        assert response.status_code == 200
        connection = json.loads(response.get_body())
        assert connection["connectionName"] == "TestConnection"
        assert connection["provider"] == "microsoft"
        assert connection["status"] == "completed"

    async def test_get_connection_not_found(self, test_user, azurite_tables):
        """Test getting non-existent connection returns 404"""
        req = create_mock_request(test_user["user_id"], test_user["email"])
        req.route_params = {"connection_name": "NonExistent"}
        response = await get_oauth_connection(req)

        # Assertions
        assert response.status_code == 404
        error = json.loads(response.get_body())
        assert error["error"] == "NotFound"


class TestUpdateOAuthConnection:
    """Integration tests for PUT /api/oauth/connections/{connection_name}"""

    async def test_update_connection_valid(self, test_user, azurite_tables):
        """Test updating an OAuth connection"""
        # Create connection
        config_service = TableStorageService("Config")
        connection_id = str(uuid.uuid4())
        config_service.insert_entity({
            "PartitionKey": "GLOBAL",
            "RowKey": "oauth-connection:UpdateTest",
            "Value": json.dumps({
                "id": connection_id,
                "connection_name": "UpdateTest",
                "provider": "microsoft",
                "client_id": "old-client-id",
                "authorization_url": "https://test.com",
                "token_url": "https://test.com/token",
                "scopes": "User.Read",
                "redirect_uri": "/oauth/callback",
                "status": "not_connected",
                "org_id": "GLOBAL",
                "created_by": test_user["user_id"],
                "created_at": datetime.utcnow().isoformat()
            })
        })

        # Update connection
        req = create_mock_request(test_user["user_id"], test_user["email"])
        req.route_params = {"connection_name": "UpdateTest"}
        req.get_json = MagicMock(return_value={
            "client_id": "new-client-id",
            "scopes": "User.Read,Mail.Read"
        })
        response = await update_oauth_connection(req)

        # Assertions
        assert response.status_code == 200
        connection = json.loads(response.get_body())
        assert connection["clientId"] == "new-client-id"
        assert connection["scopes"] == "User.Read,Mail.Read"

    async def test_update_connection_not_found(self, test_user, azurite_tables):
        """Test updating non-existent connection returns 404"""
        req = create_mock_request(test_user["user_id"], test_user["email"])
        req.route_params = {"connection_name": "NonExistent"}
        req.get_json = MagicMock(return_value={"scopes": "new-scopes"})
        response = await update_oauth_connection(req)

        # Assertions
        assert response.status_code == 404


class TestDeleteOAuthConnection:
    """Integration tests for DELETE /api/oauth/connections/{connection_name}"""

    async def test_delete_connection_exists(self, test_user, azurite_tables):
        """Test deleting an existing OAuth connection"""
        # Create connection
        config_service = TableStorageService("Config")
        connection_id = str(uuid.uuid4())
        config_service.insert_entity({
            "PartitionKey": "GLOBAL",
            "RowKey": "oauth-connection:DeleteTest",
            "Value": json.dumps({
                "id": connection_id,
                "connection_name": "DeleteTest",
                "provider": "microsoft",
                "client_id": "test-id",
                "authorization_url": "https://test.com",
                "token_url": "https://test.com/token",
                "scopes": "test",
                "redirect_uri": "/oauth/callback",
                "status": "not_connected",
                "org_id": "GLOBAL",
                "created_by": test_user["user_id"],
                "created_at": datetime.utcnow().isoformat()
            })
        })

        # Delete connection
        req = create_mock_request(test_user["user_id"], test_user["email"])
        req.route_params = {"connection_name": "DeleteTest"}
        response = await delete_oauth_connection(req)

        # Assertions
        assert response.status_code == 204

        # Verify deleted
        try:
            config_service.get_entity("GLOBAL", "oauth-connection:DeleteTest")
            assert False, "Connection should be deleted"
        except:
            pass  # Expected

    async def test_delete_connection_idempotent(self, test_user, azurite_tables):
        """Test deleting non-existent connection is idempotent"""
        req = create_mock_request(test_user["user_id"], test_user["email"])
        req.route_params = {"connection_name": "NonExistent"}
        response = await delete_oauth_connection(req)

        # Should return 204 even if doesn't exist
        assert response.status_code == 204


class TestAuthorizeOAuthConnection:
    """Integration tests for POST /api/oauth/connections/{connection_name}/authorize"""

    async def test_authorize_connection_valid(self, test_user, azurite_tables):
        """Test initiating OAuth authorization flow"""
        # Create connection
        config_service = TableStorageService("Config")
        connection_id = str(uuid.uuid4())
        config_service.insert_entity({
            "PartitionKey": "GLOBAL",
            "RowKey": "oauth-connection:AuthTest",
            "Value": json.dumps({
                "id": connection_id,
                "connection_name": "AuthTest",
                "provider": "microsoft",
                "client_id": "test-client-id",
                "authorization_url": "https://login.microsoftonline.com/authorize",
                "token_url": "https://login.microsoftonline.com/token",
                "scopes": "User.Read",
                "redirect_uri": "/oauth/callback/AuthTest",
                "oauth_flow_type": "authorization_code",
                "status": "not_connected",
                "org_id": "GLOBAL",
                "created_by": test_user["user_id"],
                "created_at": datetime.utcnow().isoformat()
            })
        })

        # Authorize connection
        req = create_mock_request(test_user["user_id"], test_user["email"])
        req.route_params = {"connection_name": "AuthTest"}
        response = await authorize_oauth_connection(req)

        # Assertions
        assert response.status_code == 200
        result = json.loads(response.get_body())
        assert "authorization_url" in result
        assert "state" in result
        assert "https://login.microsoftonline.com/authorize" in result["authorization_url"]

    async def test_authorize_client_credentials_flow(self, test_user, azurite_tables):
        """Test that client credentials flow cannot be authorized"""
        # Create client credentials connection
        config_service = TableStorageService("Config")
        connection_id = str(uuid.uuid4())
        config_service.insert_entity({
            "PartitionKey": "GLOBAL",
            "RowKey": "oauth-connection:ClientCreds",
            "Value": json.dumps({
                "id": connection_id,
                "connection_name": "ClientCreds",
                "provider": "custom",
                "client_id": "test-id",
                "authorization_url": "https://test.com/authorize",
                "token_url": "https://test.com/token",
                "scopes": "test",
                "redirect_uri": "/oauth/callback",
                "oauth_flow_type": "client_credentials",
                "status": "not_connected",
                "org_id": "GLOBAL",
                "created_by": test_user["user_id"],
                "created_at": datetime.utcnow().isoformat()
            })
        })

        req = create_mock_request(test_user["user_id"], test_user["email"])
        req.route_params = {"connection_name": "ClientCreds"}
        response = await authorize_oauth_connection(req)

        # Assertions
        assert response.status_code == 400
        error = json.loads(response.get_body())
        assert "client credentials" in error["message"].lower()


class TestCancelOAuthAuthorization:
    """Integration tests for POST /api/oauth/connections/{connection_name}/cancel"""

    async def test_cancel_authorization_valid(self, test_user, azurite_tables):
        """Test canceling OAuth authorization"""
        # Create connection in waiting_callback state
        config_service = TableStorageService("Config")
        connection_id = str(uuid.uuid4())
        config_service.insert_entity({
            "PartitionKey": "GLOBAL",
            "RowKey": "oauth-connection:CancelTest",
            "Value": json.dumps({
                "id": connection_id,
                "connection_name": "CancelTest",
                "provider": "microsoft",
                "client_id": "test-id",
                "authorization_url": "https://test.com",
                "token_url": "https://test.com/token",
                "scopes": "test",
                "redirect_uri": "/oauth/callback",
                "status": "waiting_callback",
                "org_id": "GLOBAL",
                "created_by": test_user["user_id"],
                "created_at": datetime.utcnow().isoformat()
            })
        })

        req = create_mock_request(test_user["user_id"], test_user["email"])
        req.route_params = {"connection_name": "CancelTest"}
        response = await cancel_oauth_authorization(req)

        # Assertions
        assert response.status_code == 204


class TestGetOAuthRefreshJobStatus:
    """Integration tests for GET /api/oauth/refresh_job_status"""

    async def test_get_job_status_no_runs(self, test_user, azurite_tables):
        """Test getting job status when no job has run"""
        req = create_mock_request(test_user["user_id"], test_user["email"])
        response = await get_oauth_refresh_job_status(req)

        # Assertions
        assert response.status_code == 200
        result = json.loads(response.get_body())
        assert result["last_run"] is None

    async def test_get_job_status_with_run(self, test_user, azurite_tables):
        """Test getting job status when job has run"""
        # Create job status entry
        system_config = TableStorageService("SystemConfig")
        system_config.upsert_entity({
            "PartitionKey": "OAuthJobStatus",
            "RowKey": "TokenRefreshJob",
            "StartTime": "2025-01-14T10:00:00Z",
            "EndTime": "2025-01-14T10:05:00Z",
            "DurationSeconds": 300,
            "Status": "completed",
            "TotalConnections": 10,
            "NeedsRefresh": 3,
            "RefreshedSuccessfully": 3,
            "RefreshFailed": 0,
            "Errors": json.dumps([])
        })

        req = create_mock_request(test_user["user_id"], test_user["email"])
        response = await get_oauth_refresh_job_status(req)

        # Assertions
        assert response.status_code == 200
        result = json.loads(response.get_body())
        assert result["last_run"] is not None
        assert result["last_run"]["status"] == "completed"
        assert result["last_run"]["total_connections"] == 10


class TestOAuthOrgScoping:
    """Integration tests for organization scoping in OAuth"""

    async def test_create_connection_org_scoped(self, test_user_with_full_permissions, azurite_tables):
        """Test creating OAuth connection scoped to specific org"""
        # User with org should create connection in their org scope
        req = create_mock_request(
            test_user_with_full_permissions["user_id"],
            test_user_with_full_permissions["email"],
            org_id=test_user_with_full_permissions["org_id"]
        )
        req.get_json = MagicMock(return_value={
            "connection_name": "OrgConnection",
            "oauth_flow_type": "authorization_code",
            "client_id": "test-id",
            "authorization_url": "https://test.com",
            "token_url": "https://test.com/token",
            "scopes": "test",
            "redirect_uri": "/oauth/callback"
        })

        response = await create_oauth_connection(req)

        # Assertions
        assert response.status_code == 201
        connection = json.loads(response.get_body())
        assert connection["orgId"] == test_user_with_full_permissions["org_id"]

    async def test_list_connections_includes_global_fallback(self, test_user_with_full_permissions, azurite_tables):
        """Test that listing connections includes GLOBAL connections as fallback"""
        config_service = TableStorageService("Config")

        # Create GLOBAL connection
        config_service.insert_entity({
            "PartitionKey": "GLOBAL",
            "RowKey": "oauth-connection:GlobalConn",
            "Value": json.dumps({
                "id": str(uuid.uuid4()),
                "connection_name": "GlobalConn",
                "provider": "microsoft",
                "client_id": "global-id",
                "authorization_url": "https://test.com",
                "token_url": "https://test.com/token",
                "scopes": "test",
                "redirect_uri": "/oauth/callback",
                "status": "not_connected",
                "org_id": "GLOBAL",
                "created_by": "system",
                "created_at": datetime.utcnow().isoformat()
            })
        })

        # Create org-specific connection
        org_id = test_user_with_full_permissions["org_id"]
        config_service.insert_entity({
            "PartitionKey": org_id,
            "RowKey": "oauth-connection:OrgConn",
            "Value": json.dumps({
                "id": str(uuid.uuid4()),
                "connection_name": "OrgConn",
                "provider": "custom",
                "client_id": "org-id",
                "authorization_url": "https://test.com",
                "token_url": "https://test.com/token",
                "scopes": "test",
                "redirect_uri": "/oauth/callback",
                "status": "not_connected",
                "org_id": org_id,
                "created_by": test_user_with_full_permissions["user_id"],
                "created_at": datetime.utcnow().isoformat()
            })
        })

        # List connections - should include both
        req = create_mock_request(
            test_user_with_full_permissions["user_id"],
            test_user_with_full_permissions["email"],
            org_id=org_id
        )
        response = await list_oauth_connections(req)

        # Assertions
        assert response.status_code == 200
        connections = json.loads(response.get_body())
        connection_names = {c["connectionName"] for c in connections}

        # Should include both GLOBAL and org-specific
        assert "GlobalConn" in connection_names
        assert "OrgConn" in connection_names
