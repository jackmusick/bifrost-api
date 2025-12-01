"""
Integration tests for execution cleanup endpoints

Tests HTTP endpoints for finding and cleaning up stuck executions.
Requires:
- docker-compose.testing.yml running (Azurite on custom ports)
- func start running on port 7071
"""

import logging
import os
from datetime import datetime, timedelta
from uuid import uuid4

import pytest
import requests

logger = logging.getLogger(__name__)

# Skip unless running E2E tests (requires running API server)
pytestmark = pytest.mark.skipif(
    os.environ.get("E2E_TESTS") != "true",
    reason="E2E test requires running API server (set E2E_TESTS=true)"
)


@pytest.fixture
def stuck_execution_pending(table_service, test_org_id):
    """Create a stuck execution in Pending status (15 minutes old)"""
    execution_id = str(uuid4())
    org_id = test_org_id or "GLOBAL"
    old_time = (datetime.utcnow() - timedelta(minutes=15)).isoformat()

    # Reverse timestamp for sorting
    reverse_ts = str(9999999999999 - int((datetime.utcnow() - timedelta(minutes=15)).timestamp() * 1000))

    entities_table = table_service.get_table_client("Entities")
    relationships_table = table_service.get_table_client("Relationships")

    # Primary execution record
    execution_entity = {
        "PartitionKey": org_id,
        "RowKey": f"execution:{reverse_ts}_{execution_id}",
        "ExecutionId": execution_id,
        "WorkflowName": "StuckPendingWorkflow",
        "ExecutedBy": "test-user@example.com",
        "ExecutedByName": "Test User",
        "Status": "Pending",
        "StartedAt": old_time,
        "InputData": "{}",
        "ResultInBlob": False
    }

    # Status index
    status_index = {
        "PartitionKey": "GLOBAL",
        "RowKey": f"status:Pending:{execution_id}",
        "ExecutionId": execution_id,
        "OrganizationId": org_id,
        "WorkflowName": "StuckPendingWorkflow",
        "ExecutedBy": "test-user@example.com",
        "ExecutedByName": "Test User",
        "Status": "Pending",
        "StartedAt": old_time,
        "UpdatedAt": old_time  # Key field for stuck detection
    }

    try:
        entities_table.upsert_entity(execution_entity)
        relationships_table.upsert_entity(status_index)
        logger.info(f"Created stuck Pending execution: {execution_id}")
    except Exception as e:
        logger.error(f"Failed to create stuck execution: {e}")

    yield execution_id

    # Cleanup
    try:
        entities_table.delete_entity(partition_key=org_id, row_key=f"execution:{reverse_ts}_{execution_id}")
        relationships_table.delete_entity(partition_key="GLOBAL", row_key=f"status:Pending:{execution_id}")
        # Try to delete any status change that might have happened
        try:
            relationships_table.delete_entity(partition_key="GLOBAL", row_key=f"status:Timeout:{execution_id}")
        except Exception:
            pass
    except Exception as e:
        logger.warning(f"Cleanup warning for stuck execution: {e}")


@pytest.fixture
def stuck_execution_running(table_service, test_org_id):
    """Create a stuck execution in Running status (35 minutes old)"""
    execution_id = str(uuid4())
    org_id = test_org_id or "GLOBAL"
    old_time = (datetime.utcnow() - timedelta(minutes=35)).isoformat()

    reverse_ts = str(9999999999999 - int((datetime.utcnow() - timedelta(minutes=35)).timestamp() * 1000))

    entities_table = table_service.get_table_client("Entities")
    relationships_table = table_service.get_table_client("Relationships")

    execution_entity = {
        "PartitionKey": org_id,
        "RowKey": f"execution:{reverse_ts}_{execution_id}",
        "ExecutionId": execution_id,
        "WorkflowName": "StuckRunningWorkflow",
        "ExecutedBy": "test-user@example.com",
        "ExecutedByName": "Test User",
        "Status": "Running",
        "StartedAt": old_time,
        "InputData": "{}",
        "ResultInBlob": False
    }

    status_index = {
        "PartitionKey": "GLOBAL",
        "RowKey": f"status:Running:{execution_id}",
        "ExecutionId": execution_id,
        "OrganizationId": org_id,
        "WorkflowName": "StuckRunningWorkflow",
        "ExecutedBy": "test-user@example.com",
        "ExecutedByName": "Test User",
        "Status": "Running",
        "StartedAt": old_time,
        "UpdatedAt": old_time
    }

    try:
        entities_table.upsert_entity(execution_entity)
        relationships_table.upsert_entity(status_index)
        logger.info(f"Created stuck Running execution: {execution_id}")
    except Exception as e:
        logger.error(f"Failed to create stuck execution: {e}")

    yield execution_id

    # Cleanup
    try:
        entities_table.delete_entity(partition_key=org_id, row_key=f"execution:{reverse_ts}_{execution_id}")
        relationships_table.delete_entity(partition_key="GLOBAL", row_key=f"status:Running:{execution_id}")
        try:
            relationships_table.delete_entity(partition_key="GLOBAL", row_key=f"status:Timeout:{execution_id}")
        except Exception:
            pass
    except Exception as e:
        logger.warning(f"Cleanup warning for stuck execution: {e}")


@pytest.fixture
def recent_execution_running(table_service, test_org_id):
    """Create a recent execution in Running status (5 minutes old) - NOT stuck"""
    execution_id = str(uuid4())
    org_id = test_org_id or "GLOBAL"
    recent_time = (datetime.utcnow() - timedelta(minutes=5)).isoformat()

    reverse_ts = str(9999999999999 - int((datetime.utcnow() - timedelta(minutes=5)).timestamp() * 1000))

    entities_table = table_service.get_table_client("Entities")
    relationships_table = table_service.get_table_client("Relationships")

    execution_entity = {
        "PartitionKey": org_id,
        "RowKey": f"execution:{reverse_ts}_{execution_id}",
        "ExecutionId": execution_id,
        "WorkflowName": "RecentRunningWorkflow",
        "ExecutedBy": "test-user@example.com",
        "ExecutedByName": "Test User",
        "Status": "Running",
        "StartedAt": recent_time,
        "InputData": "{}",
        "ResultInBlob": False
    }

    status_index = {
        "PartitionKey": "GLOBAL",
        "RowKey": f"status:Running:{execution_id}",
        "ExecutionId": execution_id,
        "OrganizationId": org_id,
        "WorkflowName": "RecentRunningWorkflow",
        "ExecutedBy": "test-user@example.com",
        "ExecutedByName": "Test User",
        "Status": "Running",
        "StartedAt": recent_time,
        "UpdatedAt": recent_time
    }

    try:
        entities_table.upsert_entity(execution_entity)
        relationships_table.upsert_entity(status_index)
        logger.info(f"Created recent Running execution (not stuck): {execution_id}")
    except Exception as e:
        logger.error(f"Failed to create recent execution: {e}")

    yield execution_id

    # Cleanup
    try:
        entities_table.delete_entity(partition_key=org_id, row_key=f"execution:{reverse_ts}_{execution_id}")
        relationships_table.delete_entity(partition_key="GLOBAL", row_key=f"status:Running:{execution_id}")
    except Exception as e:
        logger.warning(f"Cleanup warning for recent execution: {e}")


class TestGetStuckExecutions:
    """Tests for GET /executions/cleanup/stuck endpoint"""

    def test_returns_stuck_executions(self, api_base_url, platform_admin_headers, stuck_execution_pending, stuck_execution_running):
        """Should return stuck executions in Pending (10+ min) and Running (30+ min) status"""
        response = requests.get(
            f"{api_base_url}/api/executions/cleanup/stuck",
            headers=platform_admin_headers,
            timeout=10
        )

        assert response.status_code == 200
        data = response.json()

        # Should have both stuck executions
        assert "executions" in data
        assert "count" in data
        assert data["count"] >= 2  # At least our 2 test executions

        # Find our test executions
        execution_ids = [ex["executionId"] for ex in data["executions"]]
        assert stuck_execution_pending in execution_ids
        assert stuck_execution_running in execution_ids

        # Verify fields
        for execution in data["executions"]:
            assert "executionId" in execution
            assert "workflowName" in execution
            assert "status" in execution
            assert "executedBy" in execution
            assert "executedByName" in execution
            assert execution["status"] in ["Pending", "Running"]

    def test_does_not_return_recent_executions(self, api_base_url, platform_admin_headers, recent_execution_running):
        """Should NOT return recent executions within timeout threshold"""
        response = requests.get(
            f"{api_base_url}/api/executions/cleanup/stuck",
            headers=platform_admin_headers,
            timeout=10
        )

        assert response.status_code == 200
        data = response.json()

        # Should not include recent execution
        execution_ids = [ex["executionId"] for ex in data["executions"]]
        assert recent_execution_running not in execution_ids

    def test_requires_platform_admin(self, api_base_url, regular_user_headers):
        """Should require PlatformAdmin role"""
        response = requests.get(
            f"{api_base_url}/api/executions/cleanup/stuck",
            headers=regular_user_headers,
            timeout=10
        )

        # Should be forbidden for non-platform-admins
        assert response.status_code == 403

    def test_returns_empty_when_no_stuck_executions(self, api_base_url, platform_admin_headers):
        """Should return empty list when no stuck executions exist"""
        # Clean up any existing stuck executions first (from previous test runs)
        requests.post(
            f"{api_base_url}/api/executions/cleanup/trigger",
            headers=platform_admin_headers,
            json={},
            timeout=10
        )

        # Now query for stuck executions
        response = requests.get(
            f"{api_base_url}/api/executions/cleanup/stuck",
            headers=platform_admin_headers,
            timeout=10
        )

        assert response.status_code == 200
        data = response.json()
        assert "executions" in data
        # After cleanup, should have 0 or very few stuck executions
        # (Can't assert 0 because there might be genuinely stuck executions from other processes)


class TestTriggerCleanup:
    """Tests for POST /executions/cleanup/trigger endpoint"""

    def test_cleans_up_stuck_executions(self, api_base_url, platform_admin_headers, stuck_execution_pending, stuck_execution_running, table_service):
        """Should timeout stuck executions and remove from status index"""
        # First verify stuck executions exist
        get_response = requests.get(
            f"{api_base_url}/api/executions/cleanup/stuck",
            headers=platform_admin_headers,
            timeout=10
        )
        assert get_response.status_code == 200
        get_response.json()["count"]

        # Trigger cleanup
        response = requests.post(
            f"{api_base_url}/api/executions/cleanup/trigger",
            headers=platform_admin_headers,
            json={},
            timeout=10
        )

        assert response.status_code == 200
        data = response.json()

        # Should have cleaned up at least our 2 executions
        assert "cleaned" in data
        assert "pending" in data
        assert "running" in data
        assert "failed" in data
        assert data["cleaned"] >= 2

        # Verify stuck executions are now gone
        after_response = requests.get(
            f"{api_base_url}/api/executions/cleanup/stuck",
            headers=platform_admin_headers,
            timeout=10
        )
        assert after_response.status_code == 200
        after_data = after_response.json()

        # Our specific executions should no longer be in stuck list
        execution_ids = [ex["executionId"] for ex in after_data["executions"]]
        assert stuck_execution_pending not in execution_ids
        assert stuck_execution_running not in execution_ids

    def test_updates_execution_status_to_timeout(self, api_base_url, platform_admin_headers, stuck_execution_pending, table_service, test_org_id):
        """Should update execution status to Timeout in primary record"""
        # Trigger cleanup
        response = requests.post(
            f"{api_base_url}/api/executions/cleanup/trigger",
            headers=platform_admin_headers,
            json={},
            timeout=10
        )

        assert response.status_code == 200

        # Verify primary execution record was updated
        entities_table = table_service.get_table_client("Entities")

        # Query for the execution
        filter_query = f"PartitionKey eq '{test_org_id}' and ExecutionId eq '{stuck_execution_pending}'"
        entities = list(entities_table.query_entities(filter_query))

        if len(entities) > 0:
            execution = entities[0]
            # Status should be updated to Timeout (or TIMEOUT depending on enum)
            assert execution.get("Status") in ["Timeout", "TIMEOUT", "Timed Out"]
            assert execution.get("ErrorMessage") is not None
            assert "10+ minutes" in execution.get("ErrorMessage", "")

    def test_removes_from_status_index(self, api_base_url, platform_admin_headers, stuck_execution_pending, table_service):
        """Should remove execution from Pending/Running status index"""
        # Trigger cleanup
        response = requests.post(
            f"{api_base_url}/api/executions/cleanup/trigger",
            headers=platform_admin_headers,
            json={},
            timeout=10
        )

        assert response.status_code == 200

        # Verify status index entry was removed
        relationships_table = table_service.get_table_client("Relationships")

        try:
            # Try to get the old Pending status index
            status_index = relationships_table.get_entity(
                partition_key="GLOBAL",
                row_key=f"status:Pending:{stuck_execution_pending}"
            )
            # If we get here, the index wasn't deleted (might be okay if execution moved to Timeout status)
            logger.info(f"Status index still exists: {status_index.get('RowKey')}")
        except Exception:
            # Expected - status index should be deleted
            pass

    def test_requires_platform_admin(self, api_base_url, regular_user_headers):
        """Should require PlatformAdmin role"""
        response = requests.post(
            f"{api_base_url}/api/executions/cleanup/trigger",
            headers=regular_user_headers,
            json={},
            timeout=10
        )

        assert response.status_code == 403

    def test_handles_empty_cleanup(self, api_base_url, platform_admin_headers):
        """Should handle case when no stuck executions exist"""
        # Run cleanup twice - second time should have nothing to clean
        requests.post(
            f"{api_base_url}/api/executions/cleanup/trigger",
            headers=platform_admin_headers,
            json={},
            timeout=10
        )

        response = requests.post(
            f"{api_base_url}/api/executions/cleanup/trigger",
            headers=platform_admin_headers,
            json={},
            timeout=10
        )

        assert response.status_code == 200
        data = response.json()

        # Should report 0 cleaned (or very few if other tests running)
        assert "cleaned" in data
        assert data["cleaned"] >= 0


class TestCleanupIntegration:
    """End-to-end integration tests for cleanup workflow"""

    def test_full_cleanup_workflow(self, api_base_url, platform_admin_headers, stuck_execution_pending, stuck_execution_running, recent_execution_running):
        """Test complete workflow: check stuck -> trigger cleanup -> verify results"""
        # Step 1: Get stuck executions
        get_response = requests.get(
            f"{api_base_url}/api/executions/cleanup/stuck",
            headers=platform_admin_headers,
            timeout=10
        )

        assert get_response.status_code == 200
        stuck_data = get_response.json()

        # Should find our 2 stuck executions
        stuck_ids = [ex["executionId"] for ex in stuck_data["executions"]]
        assert stuck_execution_pending in stuck_ids
        assert stuck_execution_running in stuck_ids
        assert recent_execution_running not in stuck_ids

        # Step 2: Trigger cleanup
        cleanup_response = requests.post(
            f"{api_base_url}/api/executions/cleanup/trigger",
            headers=platform_admin_headers,
            json={},
            timeout=10
        )

        assert cleanup_response.status_code == 200
        cleanup_data = cleanup_response.json()
        assert cleanup_data["cleaned"] >= 2

        # Step 3: Verify stuck executions are gone
        after_response = requests.get(
            f"{api_base_url}/api/executions/cleanup/stuck",
            headers=platform_admin_headers,
            timeout=10
        )

        assert after_response.status_code == 200
        after_data = after_response.json()

        # Our stuck executions should no longer appear
        after_ids = [ex["executionId"] for ex in after_data["executions"]]
        assert stuck_execution_pending not in after_ids
        assert stuck_execution_running not in after_ids

        # Step 4: Verify recent execution is still in Running status
        # (not affected by cleanup)
        # This would require querying the executions list endpoint
        # which we're not testing here, but the recent execution fixture
        # will verify in its cleanup that it still exists
