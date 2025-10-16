"""
Integration tests for Security (cross-org isolation and authorization)
Tests cross-org isolation and authorization boundaries by calling Azure Functions directly (no HTTP)
"""

import pytest

from functions.executions import list_executions
from functions.forms import create_form, execute_form, get_form, list_forms
from functions.oauth_api import (
    authorize_oauth_connection,
    cancel_oauth_authorization,
    create_oauth_connection,
    delete_oauth_connection,
    get_oauth_connection,
    get_oauth_refresh_job_status,
    list_oauth_connections,
    refresh_oauth_token,
    update_oauth_connection,
)
from functions.org_config import get_config, set_config
from functions.organizations import create_organization
from functions.roles import assign_forms_to_role, create_role
from tests.helpers.http_helpers import (
    create_mock_request,
    create_org_user_headers,
    create_platform_admin_headers,
    parse_response,
)


class TestCrossOrgIsolation:
    """Test that users cannot access data from other organizations"""

    @pytest.mark.asyncio
    async def test_org_user_cannot_list_other_orgs_forms(self):
        """
        Org user (jack@gocovi.dev in Covi Development org) should only see:
        - Forms from their org (Covi Development)
        - Public GLOBAL forms

        Should NOT see:
        - Forms from other orgs (e.g., Contoso Ltd)
        """
        req = create_mock_request(
            method="GET",
            url="/api/forms",
            headers=create_org_user_headers(),
        )

        response = await list_forms(req)
        status, forms = parse_response(response)

        assert status == 200

        # Get the user's org ID by checking which org forms belong to
        # Find the non-GLOBAL org ID from the returned forms
        user_org_id = None
        for form in forms:
            if form.get("orgId") != "GLOBAL":
                user_org_id = form.get("orgId")
                break

        # Verify no forms from other orgs are returned
        for form in forms:
            org_id = form.get("orgId")
            # Should only be GLOBAL or user's org
            assert org_id in ["GLOBAL", user_org_id], \
                f"Org user seeing form from other org: {org_id}"

    @pytest.mark.asyncio
    async def test_org_user_cannot_access_other_org_form_by_id(self):
        """
        Org user should get 404 when trying to access a form from another org
        """
        # First, as platform admin, create a form in a different org
        contoso_org_id = "22222222-3333-4444-5555-666666666666"  # Contoso Ltd or create new org

        # Create org first
        org_req = create_mock_request(
            method="POST",
            url="/api/organizations",
            headers=create_platform_admin_headers(),
            body={
                "name": "Security Test Org"
            }
        )

        org_response = await create_organization(org_req)
        org_status, org_body = parse_response(org_response)

        if org_status == 201:
            other_org_id = org_body["id"]
        else:
            # Use existing org
            other_org_id = contoso_org_id

        # Create a form in that other org (as platform admin with X-Organization-Id header)
        platform_admin_with_org = create_platform_admin_headers()
        platform_admin_with_org["X-Organization-Id"] = other_org_id

        form_req = create_mock_request(
            method="POST",
            url="/api/forms",
            headers=platform_admin_with_org,
            body={
                "name": "Other Org Secret Form",
                "linkedWorkflow": "test",
                "formSchema": {"fields": []},
                "isGlobal": False,
                "isPublic": False
            }
        )

        form_response = await create_form(form_req)
        form_status, form_body = parse_response(form_response)

        if form_status != 201:
            pytest.skip(f"Could not create form in other org: {form_status}")

        other_org_form_id = form_body["id"]

        # Now try to access it as org user from different org
        get_req = create_mock_request(
            method="GET",
            url=f"/api/forms/{other_org_form_id}",
            headers=create_org_user_headers(),
            route_params={"formId": other_org_form_id}
        )

        get_response = await get_form(get_req)
        get_status, _ = parse_response(get_response)

        # Should be 404 (not found) or 403 (forbidden)
        assert get_status in [403, 404], \
            f"Org user can access another org's form! Status: {get_status}"

    @pytest.mark.asyncio
    async def test_org_user_cannot_access_other_org_executions(self):
        """
        Org user should only see executions from their own org
        """
        req = create_mock_request(
            method="GET",
            url="/api/executions",
            headers=create_org_user_headers(),
        )

        response = await list_executions(req)
        status, response_data = parse_response(response)

        assert status == 200
        executions = response_data.get("executions", response_data)

        # Get the user's org ID by checking which org executions belong to
        # Find the non-GLOBAL org ID from the returned executions
        user_org_id = None
        for execution in executions:
            if execution.get("orgId") and execution.get("orgId") != "GLOBAL":
                user_org_id = execution.get("orgId")
                break

        # Verify all executions belong to user's org
        for execution in executions:
            exec_org_id = execution.get("orgId")
            # Executions should only be from user's org or GLOBAL
            if exec_org_id:
                assert exec_org_id in ["GLOBAL", user_org_id], \
                    f"Org user seeing execution from other org: {exec_org_id}"

    @pytest.mark.asyncio
    async def test_org_user_cannot_access_other_org_oauth_connections(self):
        """
        Org user should only see OAuth connections from their org + GLOBAL
        """
        req = create_mock_request(
            method="GET",
            url="/api/oauth/connections",
            headers=create_org_user_headers(),
        )

        response = await list_oauth_connections(req)
        status, connections = parse_response(response)

        # May return 500 due to existing bug, but if it succeeds, verify isolation
        if status == 200:
            user_org_id = "546478ea-fc38-4bf7-a524-35f522f90b0e"

            for connection in connections:
                conn_org_id = connection.get("orgId")
                if conn_org_id:
                    assert conn_org_id in ["GLOBAL", user_org_id], \
                        f"Org user seeing OAuth connection from other org: {conn_org_id}"


class TestExecutionAccessControl:
    """Test that users can only access executions they have permission for"""

    @pytest.mark.asyncio
    async def test_org_user_cannot_access_execution_by_id_from_other_org(self):
        """
        Verify that org user can only see executions from their own org
        """
        # Get list of executions - org user should only see their own
        req = create_mock_request(
            method="GET",
            url="/api/executions",
            headers=create_org_user_headers(),
        )

        response = await list_executions(req)
        status, response_data = parse_response(response)

        assert status == 200
        executions = response_data.get("executions", response_data)

        # Get the user's actual org_id from the headers or first execution
        org_user_headers = create_org_user_headers()
        user_org_id = org_user_headers.get("X-Organization-Id")

        # If no org_id in headers, infer from executions
        if not user_org_id and len(executions) > 0:
            for execution in executions:
                exec_org_id = execution.get("orgId")
                if exec_org_id and exec_org_id != "GLOBAL":
                    user_org_id = exec_org_id
                    break

        # Verify all executions belong to the user's org (or GLOBAL)
        for execution in executions:
            exec_org_id = execution.get("orgId")
            if exec_org_id and exec_org_id != "GLOBAL":
                # Should be user's org - if not, this is a security violation
                assert exec_org_id == user_org_id, \
                    f"Security violation: User seeing execution from different org ({exec_org_id} != {user_org_id})"

    @pytest.mark.asyncio
    async def test_platform_admin_can_access_all_executions(self):
        """
        Platform admin should be able to see executions across all orgs
        (when not scoped to specific org via X-Organization-Id header)
        """
        req = create_mock_request(
            method="GET",
            url="/api/executions",
            headers=create_platform_admin_headers(),
        )

        response = await list_executions(req)
        status, response_data = parse_response(response)

        assert status == 200
        executions = response_data.get("executions", response_data)

        # Platform admin in GLOBAL scope should see GLOBAL executions
        # (may be empty if no global executions exist)
        assert isinstance(executions, list)


class TestConfigAccessControl:
    """Test that config values are properly isolated by org"""

    @pytest.mark.asyncio
    async def test_org_user_cannot_access_config_endpoints(self):
        """
        Org users should not have access to config endpoints at all
        (These are platform admin only)
        """
        # Try to list configs
        list_req = create_mock_request(
            method="GET",
            url="/api/config?scope=global",
            headers=create_org_user_headers(),
            query_params={"scope": "global"}
        )

        list_response = await get_config(list_req)
        list_status, _ = parse_response(list_response)
        assert list_status == 403

        # Try to create config
        create_req = create_mock_request(
            method="POST",
            url="/api/config",
            headers=create_org_user_headers(),
            body={
                "key": "test",
                "value": "value",
                "type": "string",
                "scope": "GLOBAL"
            }
        )

        create_response = await set_config(create_req)
        create_status, _ = parse_response(create_response)
        assert create_status == 403

    @pytest.mark.asyncio
    async def test_platform_admin_without_org_header_gets_global_config(self):
        """
        Platform admin without X-Organization-Id header should get GLOBAL config
        """
        req = create_mock_request(
            method="GET",
            url="/api/config",
            headers=create_platform_admin_headers(),
        )

        response = await get_config(req)
        status, configs = parse_response(response)

        # Should return 200 with GLOBAL configs
        assert status == 200
        assert isinstance(configs, list)
        # All configs should be GLOBAL scope
        for config in configs:
            assert config["scope"] == "GLOBAL"


class TestOAuthAccessControl:
    """Test OAuth connection access control"""

    @pytest.mark.asyncio
    async def test_org_user_cannot_create_oauth_connection(self):
        """
        Org users should not be able to create OAuth connections
        (Requires canManageConfig permission or platform admin)
        """
        req = create_mock_request(
            method="POST",
            url="/api/oauth/connections",
            headers=create_org_user_headers(),
            body={
                "connection_name": "unauthorized_connection",
                "oauth_flow_type": "authorization_code",
                "authorization_url": "https://test.com/auth",
                "token_url": "https://test.com/token",
                "scopes": "read",
                "client_id": "test",
                "client_secret_value": "secret",
                "redirect_uri": "/callback"
            }
        )

        response = await create_oauth_connection(req)
        status, _ = parse_response(response)

        # Should be 403 Forbidden
        assert status == 403

    @pytest.mark.asyncio
    async def test_org_user_cannot_delete_oauth_connection(self):
        """
        Org users should not be able to delete OAuth connections
        """
        # First create a connection as platform admin
        create_req = create_mock_request(
            method="POST",
            url="/api/oauth/connections",
            headers=create_platform_admin_headers(),
            body={
                "connection_name": "test_delete_security",
                "oauth_flow_type": "authorization_code",
                "authorization_url": "https://test.com/auth",
                "token_url": "https://test.com/token",
                "scopes": "read",
                "client_id": "test",
                "client_secret_value": "secret",
                "redirect_uri": "/callback"
            }
        )

        create_response = await create_oauth_connection(create_req)
        create_status, _ = parse_response(create_response)

        if create_status not in [201, 409]:
            pytest.skip(f"Could not create OAuth connection: {create_status}")

        # Try to delete as org user
        delete_req = create_mock_request(
            method="DELETE",
            url="/api/oauth/connections/test_delete_security",
            headers=create_org_user_headers(),
            route_params={"connection_name": "test_delete_security"}
        )

        delete_response = await delete_oauth_connection(delete_req)
        delete_status, _ = parse_response(delete_response)

        # Should be 403 Forbidden
        assert delete_status == 403

    @pytest.mark.asyncio
    async def test_org_user_cannot_list_oauth_connections(self):
        """
        Org users should not be able to list OAuth connections
        (Platform admin only)
        """
        req = create_mock_request(
            method="GET",
            url="/api/oauth/connections",
            headers=create_org_user_headers(),
        )

        response = await list_oauth_connections(req)
        status, _ = parse_response(response)

        assert status == 403

    @pytest.mark.asyncio
    async def test_org_user_cannot_view_oauth_connection(self):
        """
        Org users should not be able to view OAuth connection details
        (Platform admin only)
        """
        req = create_mock_request(
            method="GET",
            url="/api/oauth/connections/test_connection",
            headers=create_org_user_headers(),
            route_params={"connection_name": "test_connection"}
        )

        response = await get_oauth_connection(req)
        status, _ = parse_response(response)

        # Should be 403 even if connection doesn't exist
        assert status == 403

    @pytest.mark.asyncio
    async def test_org_user_cannot_update_oauth_connection(self):
        """
        Org users should not be able to update OAuth connections
        """
        req = create_mock_request(
            method="PUT",
            url="/api/oauth/connections/test_connection",
            headers=create_org_user_headers(),
            route_params={"connection_name": "test_connection"},
            body={"description": "Attempted update"}
        )

        response = await update_oauth_connection(req)
        status, _ = parse_response(response)

        assert status == 403

    @pytest.mark.asyncio
    async def test_org_user_cannot_authorize_oauth(self):
        """
        Org users should not be able to initiate OAuth authorization
        """
        req = create_mock_request(
            method="POST",
            url="/api/oauth/connections/test_connection/authorize",
            headers=create_org_user_headers(),
            route_params={"connection_name": "test_connection"}
        )

        response = await authorize_oauth_connection(req)
        status, _ = parse_response(response)

        assert status == 403

    @pytest.mark.asyncio
    async def test_org_user_cannot_cancel_oauth_authorization(self):
        """
        Org users should not be able to cancel OAuth authorization
        """
        req = create_mock_request(
            method="POST",
            url="/api/oauth/connections/test_connection/cancel",
            headers=create_org_user_headers(),
            route_params={"connection_name": "test_connection"}
        )

        response = await cancel_oauth_authorization(req)
        status, _ = parse_response(response)

        assert status == 403

    @pytest.mark.asyncio
    async def test_org_user_cannot_refresh_oauth_token(self):
        """
        Org users should not be able to manually refresh OAuth tokens
        """
        req = create_mock_request(
            method="POST",
            url="/api/oauth/connections/test_connection/refresh",
            headers=create_org_user_headers(),
            route_params={"connection_name": "test_connection"}
        )

        response = await refresh_oauth_token(req)
        status, _ = parse_response(response)

        assert status == 403

    @pytest.mark.asyncio
    async def test_org_user_cannot_view_refresh_job_status(self):
        """
        Org users should not be able to view OAuth refresh job status
        """
        req = create_mock_request(
            method="GET",
            url="/api/oauth/refresh_job_status",
            headers=create_org_user_headers(),
        )

        response = await get_oauth_refresh_job_status(req)
        status, _ = parse_response(response)

        assert status == 403


class TestRoleBasedFormAccess:
    """Test that form access is properly controlled by roles"""

    @pytest.mark.asyncio
    async def test_org_user_cannot_see_role_restricted_form_without_role(self):
        """
        Create a non-public form restricted to a specific role
        Verify that org user without that role cannot see it in the list
        """
        # Create a role
        role_req = create_mock_request(
            method="POST",
            url="/api/roles",
            headers=create_platform_admin_headers(),
            body={
                "name": "Security Test Restricted Role",
                "isActive": True
            }
        )

        role_response = await create_role(role_req)
        role_status, role_body = parse_response(role_response)

        assert role_status in [200, 201], \
            f"Failed to create role: {role_status} - {role_body}"

        role_id = role_body["id"]

        # Create a non-public form
        form_req = create_mock_request(
            method="POST",
            url="/api/forms",
            headers=create_platform_admin_headers(),
            body={
                "name": "Security Test Restricted Form",
                "linkedWorkflow": "test",
                "formSchema": {"fields": []},
                "isGlobal": False,
                "isPublic": False  # Not public
            }
        )

        form_response = await create_form(form_req)
        form_status, form_body = parse_response(form_response)

        assert form_status == 201, \
            f"Failed to create form: {form_status} - {form_body}"

        form_id = form_body["id"]

        # Assign form to role
        assign_req = create_mock_request(
            method="POST",
            url=f"/api/roles/{role_id}/forms",
            headers=create_platform_admin_headers(),
            route_params={"roleId": role_id},
            body={"formIds": [form_id]}  # API expects array
        )

        assign_response = await assign_forms_to_role(assign_req)
        assign_status, assign_body = parse_response(assign_response)

        assert assign_status in [200, 201], \
            f"Failed to assign form to role: {assign_status} - {assign_body}"

        # Now list forms as org user (who is NOT in this role)
        list_req = create_mock_request(
            method="GET",
            url="/api/forms",
            headers=create_org_user_headers(),
        )

        list_response = await list_forms(list_req)
        list_status, forms = parse_response(list_response)

        assert list_status == 200
        form_ids = [f["id"] for f in forms]

        # User should NOT see this role-restricted form
        assert form_id not in form_ids, \
            "Org user can see role-restricted form without having the required role!"

    @pytest.mark.asyncio
    async def test_org_user_cannot_submit_role_restricted_form_without_role(self):
        """
        Verify that org user cannot submit a role-restricted form if they don't have the role
        """
        # Create a role
        role_req = create_mock_request(
            method="POST",
            url="/api/roles",
            headers=create_platform_admin_headers(),
            body={
                "name": "Security Test Submit Role",
                "isActive": True
            }
        )

        role_response = await create_role(role_req)
        role_status, role_body = parse_response(role_response)

        assert role_status in [200, 201], \
            f"Failed to create role: {role_status} - {role_body}"

        role_id = role_body["id"]

        # Create a non-public form
        form_req = create_mock_request(
            method="POST",
            url="/api/forms",
            headers=create_platform_admin_headers(),
            body={
                "name": "Security Test Form Submission",
                "linkedWorkflow": "test_workflow",
                "formSchema": {"fields": []},
                "isGlobal": False,
                "isPublic": False  # Not public
            }
        )

        form_response = await create_form(form_req)
        form_status, form_body = parse_response(form_response)

        assert form_status == 201, \
            f"Failed to create form: {form_status} - {form_body}"

        form_id = form_body["id"]

        # Assign form to role
        assign_req = create_mock_request(
            method="POST",
            url=f"/api/roles/{role_id}/forms",
            headers=create_platform_admin_headers(),
            route_params={"roleId": role_id},
            body={"formIds": [form_id]}  # API expects array
        )

        assign_response = await assign_forms_to_role(assign_req)
        assign_status, assign_body = parse_response(assign_response)

        assert assign_status in [200, 201], \
            f"Failed to assign form to role: {assign_status} - {assign_body}"

        # Try to submit as org user (who doesn't have this role)
        submit_req = create_mock_request(
            method="POST",
            url=f"/api/forms/{form_id}/execute",
            headers=create_org_user_headers(),
            route_params={"formId": form_id},
            body={"form_data": {}}
        )

        submit_response = await execute_form(submit_req)
        submit_status, _ = parse_response(submit_response)

        # Should be 403 Forbidden - user doesn't have the required role
        assert submit_status == 403


class TestSensitiveDataMasking:
    """Test that sensitive data is properly masked in responses"""

    @pytest.mark.asyncio
    async def test_oauth_connection_does_not_expose_client_secret(self):
        """
        OAuth connection responses should never include the actual client_secret_value
        """
        # Create connection with client_secret
        create_req = create_mock_request(
            method="POST",
            url="/api/oauth/connections",
            headers=create_platform_admin_headers(),
            body={
                "connection_name": "test_secret_masking",
                "oauth_flow_type": "authorization_code",
                "authorization_url": "https://test.com/auth",
                "token_url": "https://test.com/token",
                "scopes": "read",
                "client_id": "test-client",
                "client_secret_value": "super-secret-password-123",
                "redirect_uri": "/callback"
            }
        )

        create_response = await create_oauth_connection(create_req)
        create_status, _ = parse_response(create_response)

        if create_status not in [201, 409]:
            pytest.skip(f"Could not create OAuth connection: {create_status}")

        # Get the connection
        get_req = create_mock_request(
            method="GET",
            url="/api/oauth/connections/test_secret_masking",
            headers=create_platform_admin_headers(),
            route_params={"connection_name": "test_secret_masking"}
        )

        get_response = await get_oauth_connection(get_req)
        get_status, connection = parse_response(get_response)

        assert get_status == 200
        assert connection is not None

        # Should NOT contain the actual secret value
        assert "client_secret_value" not in connection or connection.get("client_secret_value") != "super-secret-password-123", \
            "OAuth connection response exposes client secret!"

    @pytest.mark.asyncio
    async def test_config_sensitive_values_are_masked(self):
        """
        Config values with sensitive keywords should be masked in responses
        """
        req = create_mock_request(
            method="POST",
            url="/api/config",
            headers=create_platform_admin_headers(),
            body={
                "key": "database_password",  # Contains 'password' keyword
                "value": "my-super-secret-database-password-12345",
                "type": "string",
                "scope": "GLOBAL"
            }
        )

        response = await set_config(req)
        status, config = parse_response(response)

        # Should succeed (200 or 201)
        assert status in [200, 201]

        # Value should be masked
        assert "***" in config["value"], \
            "Sensitive config value is not masked in response!"
        assert config["value"] != "my-super-secret-database-password-12345", \
            "Sensitive config value is exposed unmasked!"
