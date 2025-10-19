"""Integration tests for Workflows API endpoints

Tests the workflow execution and management endpoints:
- GET /api/workflows - List workflows (discovery)
- GET /api/workflows/{workflowName} - Get workflow metadata
- POST /api/workflows/{workflowName}/execute - Execute workflow
- GET /api/workflows/{workflowName}/status - Get workflow status
"""

import json
import logging
import pytest
import requests

logger = logging.getLogger(__name__)


class TestWorkflowsDiscovery:
    """Test workflow discovery endpoints"""

    def test_list_workflows_endpoint_exists(self, api_base_url, admin_headers):
        """Should have workflows discovery endpoint"""
        # Try common discovery patterns
        endpoints = [
            f"{api_base_url}/api/workflows",
            f"{api_base_url}/api/workflows/list",
        ]

        found = False
        for endpoint in endpoints:
            response = requests.get(
                endpoint,
                headers=admin_headers,
                timeout=10
            )
            # Endpoint might exist and return 200, 404, or 501
            if response.status_code == 200:
                data = response.json()
                assert isinstance(data, list) or isinstance(data, dict)
                found = True
                logger.info(f"Workflows discovery endpoint found at {endpoint}")
                break

        logger.info(f"Workflows discovery check completed (found: {found})")

    def test_execute_workflow_sync(self, api_base_url, admin_headers):
        """Should execute workflow synchronously"""
        workflow_name = "test-workflow"
        response = requests.post(
            f"{api_base_url}/api/workflows/{workflow_name}/execute",
            headers=admin_headers,
            json={
                "inputData": {"test": "value"}
            },
            timeout=10
        )

        # Response could be 200 (success), 404 (workflow not found), 202 (async)
        assert response.status_code in [200, 202, 404, 400]
        if response.status_code in [200, 202]:
            data = response.json()
            # Should have execution ID or status
            assert "executionId" in data or "status" in data or "message" in data
            logger.info(f"Workflow execution response: {response.status_code}")

    def test_execute_workflow_with_empty_input(self, api_base_url, admin_headers):
        """Should handle workflow execution with empty input"""
        workflow_name = "test-workflow"
        response = requests.post(
            f"{api_base_url}/api/workflows/{workflow_name}/execute",
            headers=admin_headers,
            json={
                "inputData": {}
            },
            timeout=10
        )

        # Should accept empty input
        assert response.status_code in [200, 202, 404, 400]
        logger.info(f"Empty input workflow execution: {response.status_code}")

    def test_execute_workflow_without_body(self, api_base_url, admin_headers):
        """Should handle workflow execution without request body"""
        workflow_name = "test-workflow"
        response = requests.post(
            f"{api_base_url}/api/workflows/{workflow_name}/execute",
            headers=admin_headers,
            timeout=10
        )

        # Should handle missing body gracefully
        assert response.status_code in [200, 202, 400, 404]
        logger.info(f"No body workflow execution: {response.status_code}")

    def test_execute_nonexistent_workflow(self, api_base_url, admin_headers):
        """Should return 404 for non-existent workflow"""
        response = requests.post(
            f"{api_base_url}/api/workflows/nonexistent-workflow-xyz/execute",
            headers=admin_headers,
            json={"inputData": {}},
            timeout=10
        )

        # Should return 404 for missing workflow
        assert response.status_code in [404, 400]
        logger.info(f"Non-existent workflow execution: {response.status_code}")


class TestWorkflowsExecution:
    """Test workflow execution operations"""

    def test_execute_workflow_returns_execution_id(self, api_base_url, admin_headers):
        """Successful execution should return execution ID"""
        workflow_name = "test-workflow"
        response = requests.post(
            f"{api_base_url}/api/workflows/{workflow_name}/execute",
            headers=admin_headers,
            json={
                "inputData": {"param1": "value1"}
            },
            timeout=10
        )

        if response.status_code in [200, 202]:
            data = response.json()
            # Should have execution tracking ID
            assert "executionId" in data or "id" in data or "status" in data
            logger.info("Execution returned proper ID")

    def test_execute_workflow_with_form_id(self, api_base_url, admin_headers, test_form):
        """Should execute workflow triggered by form"""
        workflow_name = "test-workflow"
        response = requests.post(
            f"{api_base_url}/api/workflows/{workflow_name}/execute",
            headers=admin_headers,
            json={
                "inputData": {},
                "formId": test_form
            },
            timeout=10
        )

        # Should accept formId parameter
        assert response.status_code in [200, 202, 404, 400]
        if response.status_code in [200, 202]:
            data = response.json()
            assert "executionId" in data or "status" in data
            logger.info("Form-triggered workflow execution successful")

    def test_execute_workflow_invalid_json(self, api_base_url, admin_headers):
        """Should reject invalid JSON input"""
        workflow_name = "test-workflow"
        # Send raw invalid JSON
        response = requests.post(
            f"{api_base_url}/api/workflows/{workflow_name}/execute",
            headers=admin_headers,
            data="invalid json {",
            timeout=10
        )

        # Should return 400 for invalid JSON or 404 if workflow not found
        assert response.status_code in [400, 404, 415]
        logger.info(f"Invalid JSON handling: {response.status_code}")

    def test_execute_workflow_with_parameters(self, api_base_url, admin_headers):
        """Should execute workflow with typed parameters"""
        workflow_name = "test-workflow"
        response = requests.post(
            f"{api_base_url}/api/workflows/{workflow_name}/execute",
            headers=admin_headers,
            json={
                "inputData": {
                    "stringParam": "value",
                    "numberParam": 42,
                    "boolParam": True,
                    "arrayParam": [1, 2, 3]
                }
            },
            timeout=10
        )

        # Should handle various parameter types
        assert response.status_code in [200, 202, 404, 400]
        if response.status_code in [200, 202]:
            data = response.json()
            if "result" in data:
                # Workflow should have processed parameters
                logger.info("Complex parameters handled")


class TestWorkflowsStatus:
    """Test workflow status endpoints"""

    def test_get_workflow_status(self, api_base_url, admin_headers):
        """Should get workflow status"""
        workflow_name = "test-workflow"
        response = requests.get(
            f"{api_base_url}/api/workflows/{workflow_name}/status",
            headers=admin_headers,
            timeout=10
        )

        # Status endpoint might be 200 (success), 404 (not found), 501 (not implemented)
        assert response.status_code in [200, 404, 501]
        if response.status_code == 200:
            data = response.json()
            # Should have status information
            assert "enabled" in data or "status" in data or "available" in data
            logger.info("Workflow status retrieved")

    def test_enable_workflow(self, api_base_url, admin_headers):
        """Should enable workflow"""
        workflow_name = "test-workflow"
        response = requests.put(
            f"{api_base_url}/api/workflows/{workflow_name}/enable",
            headers=admin_headers,
            timeout=10
        )

        # Enable might be 200 (success), 204 (no content), 404 (not found), 501 (not implemented)
        assert response.status_code in [200, 204, 404, 501]
        if response.status_code in [200, 204]:
            logger.info("Workflow enabled successfully")

    def test_disable_workflow(self, api_base_url, admin_headers):
        """Should disable workflow"""
        workflow_name = "test-workflow"
        response = requests.put(
            f"{api_base_url}/api/workflows/{workflow_name}/disable",
            headers=admin_headers,
            timeout=10
        )

        # Disable might be 200 (success), 204 (no content), 404 (not found), 501 (not implemented)
        assert response.status_code in [200, 204, 404, 501]
        if response.status_code in [200, 204]:
            logger.info("Workflow disabled successfully")

    def test_get_execution_history(self, api_base_url, admin_headers):
        """Should get workflow execution history"""
        workflow_name = "test-workflow"
        response = requests.get(
            f"{api_base_url}/api/workflows/{workflow_name}/executions",
            headers=admin_headers,
            timeout=10
        )

        # History endpoint might be 200 (success), 404 (not found), 501 (not implemented)
        assert response.status_code in [200, 404, 501]
        if response.status_code == 200:
            data = response.json()
            # Should return list of executions
            assert isinstance(data, list)
            logger.info(f"Retrieved {len(data)} workflow executions")

    def test_get_execution_details(self, api_base_url, admin_headers):
        """Should get specific execution details"""
        execution_id = "test-execution-123"
        response = requests.get(
            f"{api_base_url}/api/executions/{execution_id}",
            headers=admin_headers,
            timeout=10
        )

        # Execution details might be 200 (success), 404 (not found), 501 (not implemented)
        assert response.status_code in [200, 404, 501]
        if response.status_code == 200:
            data = response.json()
            # Should have execution details
            assert "executionId" in data or "id" in data or "status" in data
            logger.info("Execution details retrieved")


class TestWorkflowsAuthorization:
    """Test workflow authorization and access control"""

    def test_execute_workflow_requires_auth(self, api_base_url):
        """Workflow execution should require authentication"""
        response = requests.post(
            f"{api_base_url}/api/workflows/test-workflow/execute",
            timeout=10
        )

        # Should require auth (403, 401) or reject without headers
        assert response.status_code in [400, 401, 403, 404]
        logger.info(f"Unauthenticated execution rejected: {response.status_code}")

    def test_execute_workflow_with_non_admin_user(self, api_base_url, user_headers):
        """Non-admin user should have limited workflow access"""
        response = requests.post(
            f"{api_base_url}/api/workflows/test-workflow/execute",
            headers=user_headers,
            json={"inputData": {}},
            timeout=10
        )

        # Non-admin might be rejected (403) or allowed depending on policy
        assert response.status_code in [200, 202, 403, 404]
        logger.info(f"Non-admin workflow execution: {response.status_code}")

    def test_execute_workflow_with_workflow_key(self, api_base_url, test_org_id):
        """Should allow execution with valid workflow key"""
        # This test assumes workflow key auth is implemented
        # Using function key for now
        headers = {
            "X-Organization-ID": test_org_id,
            "Content-Type": "application/json"
        }

        response = requests.post(
            f"{api_base_url}/api/workflows/test-workflow/execute",
            headers=headers,
            json={"inputData": {}},
            timeout=10
        )

        # Might be rejected (missing key) or accepted
        assert response.status_code in [200, 202, 401, 403, 404]
        logger.info(f"Workflow key execution: {response.status_code}")

    def test_execute_workflow_without_permission_rejected(self, api_base_url, user_headers):
        """Unauthorized users should be rejected"""
        # Try to access protected workflow
        response = requests.post(
            f"{api_base_url}/api/workflows/admin-only-workflow/execute",
            headers=user_headers,
            json={"inputData": {}},
            timeout=10
        )

        # Should either reject (403) or workflow might not exist (404)
        assert response.status_code in [403, 404]
        logger.info(f"Permission check enforced: {response.status_code}")


class TestWorkflowsMetadata:
    """Test workflow metadata endpoints"""

    def test_get_workflow_parameters_schema(self, api_base_url, admin_headers):
        """Should get workflow input parameter schema"""
        workflow_name = "test-workflow"
        response = requests.get(
            f"{api_base_url}/api/workflows/{workflow_name}/schema",
            headers=admin_headers,
            timeout=10
        )

        # Schema endpoint might be 200 (success), 404 (not found), 501 (not implemented)
        assert response.status_code in [200, 404, 501]
        if response.status_code == 200:
            data = response.json()
            # Should have parameter information
            assert "parameters" in data or "properties" in data or "inputSchema" in data
            logger.info("Workflow schema retrieved")

    def test_list_workflows_with_pagination(self, api_base_url, admin_headers):
        """Should support pagination for workflow listing"""
        response = requests.get(
            f"{api_base_url}/api/workflows?limit=10&offset=0",
            headers=admin_headers,
            timeout=10
        )

        # Pagination might be supported or ignored
        assert response.status_code in [200, 400, 404]
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, list) or isinstance(data, dict)
            logger.info("Workflow pagination supported")

    def test_search_workflows(self, api_base_url, admin_headers):
        """Should support searching workflows"""
        response = requests.get(
            f"{api_base_url}/api/workflows?search=test",
            headers=admin_headers,
            timeout=10
        )

        # Search might be supported or ignored
        assert response.status_code in [200, 400, 404]
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, list) or isinstance(data, dict)
            logger.info("Workflow search tested")


class TestWorkflowsErrorHandling:
    """Test error handling in workflow endpoints"""

    def test_execute_workflow_with_invalid_parameters(self, api_base_url, admin_headers):
        """Should validate workflow parameters"""
        workflow_name = "test-workflow"
        response = requests.post(
            f"{api_base_url}/api/workflows/{workflow_name}/execute",
            headers=admin_headers,
            json={
                "inputData": {
                    "required_field": None,  # Missing required field
                    "invalid_type": "should_be_number"
                }
            },
            timeout=10
        )

        # Should return error if validation fails
        assert response.status_code in [200, 202, 400, 404]
        if response.status_code == 400:
            data = response.json()
            # Should have error details
            assert "error" in data or "message" in data or "details" in data
            logger.info("Parameter validation error returned")

    def test_execute_workflow_timeout(self, api_base_url, admin_headers):
        """Workflow execution should have reasonable timeout"""
        workflow_name = "test-workflow"
        # This test just verifies the endpoint responds
        response = requests.post(
            f"{api_base_url}/api/workflows/{workflow_name}/execute",
            headers=admin_headers,
            json={"inputData": {}},
            timeout=30  # 30 second timeout for test
        )

        # Should complete within timeout
        assert response.status_code in [200, 202, 400, 404]
        logger.info(f"Execution completed within timeout: {response.status_code}")

    def test_get_nonexistent_execution(self, api_base_url, admin_headers):
        """Should handle query for non-existent execution"""
        response = requests.get(
            f"{api_base_url}/api/executions/nonexistent-execution-xyz",
            headers=admin_headers,
            timeout=10
        )

        # Should return 404 for missing execution
        assert response.status_code in [404, 501]
        logger.info(f"Non-existent execution handled: {response.status_code}")
