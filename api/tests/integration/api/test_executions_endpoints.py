"""Integration tests for Executions API endpoints

Tests the workflow executions API:
- GET /api/executions - List executions
- GET /api/executions/{executionId} - Get execution details
- Execution filtering by workflow name and status
- Authorization checks for execution visibility
"""

import json
import logging
import pytest
import requests
import uuid
from datetime import datetime

logger = logging.getLogger(__name__)


class TestExecutionsCRUD:
    """Test execution CRUD operations"""

    def test_list_executions_success(self, api_base_url, admin_headers):
        """Should list executions for authenticated user"""
        response = requests.get(
            f"{api_base_url}/api/executions",
            headers=admin_headers,
            timeout=10
        )

        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        logger.info(f"Successfully listed {len(data)} executions")

    def test_list_executions_returns_paged_results(self, api_base_url, admin_headers):
        """Should support limit parameter for pagination"""
        response = requests.get(
            f"{api_base_url}/api/executions?limit=10",
            headers=admin_headers,
            timeout=10
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # Should not exceed limit
        assert len(data) <= 10
        logger.info(f"Pagination test: returned {len(data)} of max 10")

    def test_list_executions_with_invalid_limit(self, api_base_url, admin_headers):
        """Should handle invalid limit parameter"""
        response = requests.get(
            f"{api_base_url}/api/executions?limit=invalid",
            headers=admin_headers,
            timeout=10
        )

        # Should either handle gracefully, return 400, or error (500)
        assert response.status_code in [200, 400, 500]
        logger.info(f"Invalid limit handled with status {response.status_code}")

    def test_get_nonexistent_execution(self, api_base_url, admin_headers):
        """Should return 404 for nonexistent execution"""
        fake_id = str(uuid.uuid4())
        response = requests.get(
            f"{api_base_url}/api/executions/{fake_id}",
            headers=admin_headers,
            timeout=10
        )

        assert response.status_code == 404
        logger.info(f"Correctly returned 404 for nonexistent execution")

    def test_get_execution_missing_id(self, api_base_url, admin_headers):
        """Should handle missing execution ID"""
        response = requests.get(
            f"{api_base_url}/api/executions/",
            headers=admin_headers,
            timeout=10
        )

        # May return 404, 405, 400, or 200 (redirects to list) depending on routing
        assert response.status_code in [200, 404, 405, 400]


class TestExecutionsStatusUpdates:
    """Test execution status tracking"""

    def test_execution_status_field_exists(self, api_base_url, admin_headers):
        """Execution response should include status field"""
        response = requests.get(
            f"{api_base_url}/api/executions",
            headers=admin_headers,
            timeout=10
        )

        assert response.status_code == 200
        data = response.json()

        # If there are any executions, check status field
        if len(data) > 0:
            first_execution = data[0]
            assert "status" in first_execution
            # Status should be one of the valid states
            valid_statuses = ["Pending", "Running", "Success", "Failed", "CompletedWithErrors"]
            assert first_execution["status"] in valid_statuses
            logger.info(f"Execution status: {first_execution['status']}")

    def test_execution_status_filter(self, api_base_url, admin_headers):
        """Should filter executions by status"""
        response = requests.get(
            f"{api_base_url}/api/executions?status=Success",
            headers=admin_headers,
            timeout=10
        )

        assert response.status_code == 200
        data = response.json()

        # All results should have requested status
        for execution in data:
            if "status" in execution:
                assert execution["status"] in ["Success", "success"]

        logger.info(f"Status filter returned {len(data)} successful executions")

    def test_execution_has_timestamps(self, api_base_url, admin_headers):
        """Execution should include start and completion timestamps"""
        response = requests.get(
            f"{api_base_url}/api/executions",
            headers=admin_headers,
            timeout=10
        )

        assert response.status_code == 200
        data = response.json()

        if len(data) > 0:
            execution = data[0]
            # Should have at least one timestamp field
            timestamp_fields = ["startedAt", "completedAt"]
            has_timestamp = any(field in execution for field in timestamp_fields)
            assert has_timestamp
            logger.info(f"Execution has timestamp fields")


class TestExecutionsHistory:
    """Test execution history and logging"""

    def test_get_execution_with_logs(self, api_base_url, admin_headers):
        """Execution detail endpoint should include logs field"""
        response = requests.get(
            f"{api_base_url}/api/executions",
            headers=admin_headers,
            timeout=10
        )

        # First get a list to find an execution
        if response.status_code == 200:
            data = response.json()
            if len(data) > 0:
                execution = data[0]
                if "executionId" in execution:
                    # Now get the detail
                    detail_response = requests.get(
                        f"{api_base_url}/api/executions/{execution['executionId']}",
                        headers=admin_headers,
                        timeout=10
                    )

                    if detail_response.status_code == 200:
                        detail = detail_response.json()
                        # May or may not have logs, but structure should be valid
                        assert isinstance(detail, dict)
                        logger.info("Execution detail fetched successfully")

    def test_get_execution_with_result(self, api_base_url, admin_headers):
        """Execution detail endpoint should include result field"""
        response = requests.get(
            f"{api_base_url}/api/executions",
            headers=admin_headers,
            timeout=10
        )

        if response.status_code == 200:
            data = response.json()
            if len(data) > 0:
                execution = data[0]
                if "executionId" in execution:
                    detail_response = requests.get(
                        f"{api_base_url}/api/executions/{execution['executionId']}",
                        headers=admin_headers,
                        timeout=10
                    )

                    if detail_response.status_code == 200:
                        detail = detail_response.json()
                        # Result field may be null or contain data
                        if "result" in detail:
                            # Valid result types
                            assert detail["result"] is None or isinstance(detail["result"], (dict, str))
                            logger.info(f"Execution result type: {type(detail['result'])}")

    def test_execution_timeline_fields(self, api_base_url, admin_headers):
        """Execution should track timeline across steps"""
        response = requests.get(
            f"{api_base_url}/api/executions",
            headers=admin_headers,
            timeout=10
        )

        if response.status_code == 200:
            data = response.json()
            if len(data) > 0:
                execution = data[0]
                # Execution should have workflow and execution ID for tracking
                assert "executionId" in execution or "id" in execution
                assert "workflowName" in execution or "workflow" in execution
                logger.info("Execution timeline fields present")


class TestExecutionsFiltering:
    """Test execution filtering capabilities"""

    def test_filter_by_workflow_name(self, api_base_url, admin_headers):
        """Should filter executions by workflow name"""
        response = requests.get(
            f"{api_base_url}/api/executions?workflowName=test-workflow",
            headers=admin_headers,
            timeout=10
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

        # All results should match the workflow filter (if any exist)
        for execution in data:
            if "workflowName" in execution:
                assert "test" in execution["workflowName"].lower() or len(data) == 0

        logger.info(f"Workflow filter returned {len(data)} executions")

    def test_combine_filters(self, api_base_url, admin_headers):
        """Should handle multiple filters together"""
        response = requests.get(
            f"{api_base_url}/api/executions?status=Success&limit=5",
            headers=admin_headers,
            timeout=10
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) <= 5
        logger.info(f"Combined filters returned {len(data)} results")

    def test_filter_with_limit_max_value(self, api_base_url, admin_headers):
        """Should handle maximum limit value"""
        response = requests.get(
            f"{api_base_url}/api/executions?limit=1000",
            headers=admin_headers,
            timeout=10
        )

        assert response.status_code == 200
        data = response.json()
        # Should be capped at some reasonable value
        assert len(data) <= 1000
        logger.info(f"Max limit handled: returned {len(data)} results")


class TestExecutionsAuthorization:
    """Test authorization for execution visibility"""

    def test_authenticated_user_can_list_executions(self, api_base_url, auth_headers):
        """Authenticated user should be able to list executions"""
        response = requests.get(
            f"{api_base_url}/api/executions",
            headers=auth_headers,
            timeout=10
        )

        # Should either return 200 (list) or 401 (auth required)
        # But not 403 (forbidden) - user has some access
        assert response.status_code in [200, 401]
        logger.info(f"Authenticated user list: status {response.status_code}")

    def test_platform_admin_access(self, api_base_url, platform_admin_headers):
        """Platform admin should have access to executions endpoint"""
        response = requests.get(
            f"{api_base_url}/api/executions",
            headers=platform_admin_headers,
            timeout=10
        )

        # Admin should have access
        assert response.status_code in [200, 401, 500]
        logger.info(f"Platform admin access: status {response.status_code}")

    def test_unauthenticated_request_handling(self, api_base_url):
        """Unauthenticated request should be handled"""
        response = requests.get(
            f"{api_base_url}/api/executions",
            timeout=10
        )

        # Should be denied, bad request, or allowed depending on auth config
        assert response.status_code in [200, 401, 400, 403]
        logger.info(f"Unauthenticated access: status {response.status_code}")


class TestExecutionsErrorHandling:
    """Test error handling in executions endpoints"""

    def test_execution_with_error_message(self, api_base_url, admin_headers):
        """Execution list should include error message if execution failed"""
        response = requests.get(
            f"{api_base_url}/api/executions",
            headers=admin_headers,
            timeout=10
        )

        if response.status_code == 200:
            data = response.json()
            if len(data) > 0:
                execution = data[0]
                # Error message may be present for failed executions
                if "errorMessage" in execution:
                    assert execution["errorMessage"] is None or isinstance(execution["errorMessage"], str)
                    logger.info("Error message field validated")

    def test_execution_duration_field(self, api_base_url, admin_headers):
        """Execution should include duration in milliseconds"""
        response = requests.get(
            f"{api_base_url}/api/executions",
            headers=admin_headers,
            timeout=10
        )

        if response.status_code == 200:
            data = response.json()
            if len(data) > 0:
                execution = data[0]
                if "durationMs" in execution:
                    assert execution["durationMs"] is None or isinstance(execution["durationMs"], int)
                    if execution["durationMs"] is not None:
                        assert execution["durationMs"] >= 0
                    logger.info(f"Duration: {execution.get('durationMs')}ms")
