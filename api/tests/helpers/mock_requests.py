"""
Mock Request Helpers for Testing

Provides reusable helpers to create mock FastAPI HTTP requests with proper authentication.
These helpers simulate the actual HTTP requests that endpoints receive in production.
"""

import json
from typing import Any
from unittest.mock import MagicMock

import azure.functions as func

from .mock_auth import TestUsers, create_function_key_headers, create_org_user_headers, create_platform_admin_headers


class MockRequestHelper:
    """Helper class for creating mock FastAPI HTTP requests"""

    @staticmethod
    def create_mock_request(
        method: str,
        url: str,
        body: dict[str, Any] | str | None = None,
        headers: dict[str, str] | None = None,
        params: dict[str, str] | None = None,
        user_type: str = "admin",
        org_id: str | None = None
    ) -> func.HttpRequest:
        """
        Create a mock FastAPI HTTP request with authentication.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE, etc.)
            url: Request URL
            body: Request body (dict or string)
            headers: Additional headers (merged with auth headers)
            params: Query parameters
            user_type: Type of user ("admin", "org_user", "function_key", "anonymous")
            org_id: Organization ID for scoping (for admin and function_key)

        Returns:
            Mock func.HttpRequest object
        """
        # Start with base headers
        request_headers = {"Content-Type": "application/json"}

        # Add authentication headers based on user type
        if user_type == "admin":
            auth_headers = create_platform_admin_headers(org_id)
            request_headers.update(auth_headers)
        elif user_type == "org_user":
            auth_headers = create_org_user_headers(org_id)
            request_headers.update(auth_headers)
        elif user_type == "function_key":
            auth_headers = create_function_key_headers(org_id)
            request_headers.update(auth_headers)
        elif user_type == "anonymous":
            auth_headers = {"Content-Type": "application/json"}
            request_headers.update(auth_headers)

        # Add additional headers
        if headers:
            request_headers.update(headers)

        # Prepare body
        if body is not None:
            if isinstance(body, dict):
                body_str = json.dumps(body)
            else:
                body_str = str(body)
        else:
            body_str = ""

        # Create mock request
        mock_req = MagicMock(spec=func.HttpRequest)
        mock_req.method = method
        mock_req.url = url
        mock_req.headers = request_headers
        mock_req.params = params or {}

        # Mock get_json method for POST/PUT requests
        if method.upper() in ["POST", "PUT", "PATCH"] and body:
            mock_req.get_json = MagicMock(return_value=body if isinstance(body, dict) else json.loads(body_str))
        else:
            mock_req.get_json = MagicMock(return_value={})

        # Mock get_body method
        mock_req.get_body = MagicMock(return_value=body_str.encode('utf-8'))

        return mock_req

    @staticmethod
    def create_platform_admin_request(
        method: str,
        url: str,
        body: dict[str, Any] | None = None,
        org_id: str | None = None,
        headers: dict[str, str] | None = None
    ) -> func.HttpRequest:
        """
        Create a mock request from a platform admin.

        Args:
            method: HTTP method
            url: Request URL
            body: Request body (dict)
            org_id: Organization ID for scoping (None = GLOBAL scope)
            headers: Additional headers

        Returns:
            Mock func.HttpRequest for platform admin
        """
        return MockRequestHelper.create_mock_request(
            method=method,
            url=url,
            body=body,
            headers=headers,
            user_type="admin",
            org_id=org_id
        )

    @staticmethod
    def create_org_user_request(
        method: str,
        url: str,
        body: dict[str, Any] | None = None,
        org_id: str | None = None,
        headers: dict[str, str] | None = None
    ) -> func.HttpRequest:
        """
        Create a mock request from an organization user.

        Args:
            method: HTTP method
            url: Request URL
            body: Request body (dict)
            org_id: Organization ID (defaults to test org)
            headers: Additional headers

        Returns:
            Mock func.HttpRequest for org user
        """
        if org_id is None:
            org_id = TestUsers.ORG_USER["org_id"]

        return MockRequestHelper.create_mock_request(
            method=method,
            url=url,
            body=body,
            headers=headers,
            user_type="org_user",
            org_id=org_id
        )

    @staticmethod
    def create_function_key_request(
        method: str,
        url: str,
        body: dict[str, Any] | None = None,
        org_id: str | None = None,
        headers: dict[str, str] | None = None
    ) -> func.HttpRequest:
        """
        Create a mock request with function key authentication.

        Args:
            method: HTTP method
            url: Request URL
            body: Request body (dict)
            org_id: Organization ID for scoping (None = GLOBAL scope)
            headers: Additional headers

        Returns:
            Mock func.HttpRequest with function key auth
        """
        return MockRequestHelper.create_mock_request(
            method=method,
            url=url,
            body=body,
            headers=headers,
            user_type="function_key",
            org_id=org_id
        )

    @staticmethod
    def create_anonymous_request(
        method: str,
        url: str,
        body: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None
    ) -> func.HttpRequest:
        """
        Create a mock anonymous request (no authentication).

        Args:
            method: HTTP method
            url: Request URL
            body: Request body (dict)
            headers: Additional headers

        Returns:
            Mock func.HttpRequest without authentication
        """
        return MockRequestHelper.create_mock_request(
            method=method,
            url=url,
            body=body,
            headers=headers,
            user_type="anonymous"
        )


# Convenience functions for common request patterns
def create_get_request(url: str, user_type: str = "admin", org_id: str | None = None) -> func.HttpRequest:
    """Create a GET request with specified user type"""
    return MockRequestHelper.create_mock_request(
        method="GET",
        url=url,
        user_type=user_type,
        org_id=org_id
    )


def create_post_request(url: str, body: dict[str, Any], user_type: str = "admin", org_id: str | None = None) -> func.HttpRequest:
    """Create a POST request with body and specified user type"""
    return MockRequestHelper.create_mock_request(
        method="POST",
        url=url,
        body=body,
        user_type=user_type,
        org_id=org_id
    )


def create_put_request(url: str, body: dict[str, Any], user_type: str = "admin", org_id: str | None = None) -> func.HttpRequest:
    """Create a PUT request with body and specified user type"""
    return MockRequestHelper.create_mock_request(
        method="PUT",
        url=url,
        body=body,
        user_type=user_type,
        org_id=org_id
    )


def create_delete_request(url: str, user_type: str = "admin", org_id: str | None = None) -> func.HttpRequest:
    """Create a DELETE request with specified user type"""
    return MockRequestHelper.create_mock_request(
        method="DELETE",
        url=url,
        user_type=user_type,
        org_id=org_id
    )


# Test data helpers
class TestDataHelper:
    """Helper class for creating test data for requests"""

    @staticmethod
    def create_organization_request_data(
        name: str = "Test Organization",
        domain: str | None = None
    ) -> dict[str, Any]:
        """Create organization creation request data"""
        data = {"name": name}
        if domain is not None:
            data["domain"] = domain
        return data

    @staticmethod
    def create_form_request_data(
        name: str = "Test Form",
        description: str = "Test form description",
        linked_workflow: str = "test_workflow",
        is_global: bool = False,
        is_public: bool = False
    ) -> dict[str, Any]:
        """Create form creation request data"""
        return {
            "name": name,
            "description": description,
            "linkedWorkflow": linked_workflow,
            "formSchema": {
                "fields": [
                    {
                        "name": "test_field",
                        "label": "Test Field",
                        "type": "text",
                        "required": True
                    }
                ]
            },
            "isGlobal": is_global,
            "isPublic": is_public
        }

    @staticmethod
    def create_oauth_connection_request_data(
        connection_name: str = "Test Connection",
        oauth_flow_type: str = "authorization_code",
        client_id: str = "test-client-id",
        authorization_url: str = "https://test.com/authorize",
        token_url: str = "https://test.com/token",
        scopes: str = "User.Read",
        redirect_uri: str = "/oauth/callback/TestConnection"
    ) -> dict[str, Any]:
        """Create OAuth connection creation request data"""
        return {
            "connection_name": connection_name,
            "oauth_flow_type": oauth_flow_type,
            "client_id": client_id,
            "authorization_url": authorization_url,
            "token_url": token_url,
            "scopes": scopes,
            "redirect_uri": redirect_uri
        }

    @staticmethod
    def create_config_request_data(
        key: str = "test_config",
        value: str = "test_value",
        config_type: str = "string",
        scope: str = "GLOBAL",
        description: str = "Test configuration"
    ) -> dict[str, Any]:
        """Create config setting request data"""
        return {
            "key": key,
            "value": value,
            "type": config_type,
            "scope": scope,
            "description": description
        }

    @staticmethod
    def create_role_request_data(
        name: str = "Test Role",
        description: str = "Test role description"
    ) -> dict[str, Any]:
        """Create role creation request data"""
        return {
            "name": name,
            "description": description
        }

    @staticmethod
    def create_workflow_execution_request_data(
        workflow_name: str = "test_workflow",
        form_id: str | None = None,
        input_data: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Create workflow execution request data"""
        if input_data is None:
            input_data = {"test_param": "test_value"}

        return {
            "workflowName": workflow_name,
            "formId": form_id,
            "inputData": input_data
        }
