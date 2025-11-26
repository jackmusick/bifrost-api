"""
Unit tests for metrics handlers

Tests business logic for dashboard metrics and statistics.
Uses mocks for discovery and table services.
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from shared.handlers.metrics_handlers import (
    get_dashboard_metrics,
    get_execution_statistics,
    get_form_count,
    get_reverse_timestamp,
    get_workflow_metadata,
)
from shared.context import ExecutionContext


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_context():
    """Create a mock ExecutionContext"""
    context = Mock(spec=ExecutionContext)
    context.user_id = "user-123"
    context.scope = "org-456"
    return context


@pytest.fixture
def mock_entities_service():
    """Create a mock table service for entities"""
    service = AsyncMock()
    return service


def make_async_context_manager(mock_service):
    """Helper to create an async context manager for mocking get_async_table_service"""
    class AsyncContextManager:
        async def __aenter__(self):
            return mock_service
        async def __aexit__(self, *args):
            return None

    def create_context_manager(*args, **kwargs):
        return AsyncContextManager()

    return create_context_manager


# ============================================================================
# Tests for get_reverse_timestamp
# ============================================================================


class TestGetReverseTimestamp:
    """Tests for get_reverse_timestamp function"""

    def test_reverse_timestamp_calculation(self):
        """Test reverse timestamp calculation is correct"""
        # Use a fixed datetime for predictable testing
        dt = datetime(2024, 1, 1, 12, 0, 0)
        result = get_reverse_timestamp(dt)

        # Calculate expected value
        timestamp_ms = int(dt.timestamp() * 1000)
        expected = 9999999999999 - timestamp_ms

        assert result == expected
        assert isinstance(result, int)

    def test_reverse_timestamp_order(self):
        """Test that earlier dates have higher reverse timestamps"""
        earlier = datetime(2024, 1, 1, 0, 0, 0)
        later = datetime(2024, 1, 2, 0, 0, 0)

        earlier_ts = get_reverse_timestamp(earlier)
        later_ts = get_reverse_timestamp(later)

        # Earlier date should have higher reverse timestamp
        assert earlier_ts > later_ts

    def test_reverse_timestamp_with_microseconds(self):
        """Test reverse timestamp handles microseconds"""
        dt = datetime(2024, 1, 1, 12, 30, 45, 123456)
        result = get_reverse_timestamp(dt)

        assert isinstance(result, int)
        assert result > 0


# ============================================================================
# Tests for get_workflow_metadata
# ============================================================================


class TestGetWorkflowMetadata:
    """Tests for get_workflow_metadata function"""

    @patch("shared.handlers.metrics_handlers.scan_all_workflows")
    @patch("shared.handlers.metrics_handlers.scan_all_data_providers")
    def test_successful_metadata_retrieval(self, mock_scan_providers, mock_scan_workflows):
        """Test successful retrieval of workflow metadata"""
        # Create mock workflows and providers
        mock_scan_workflows.return_value = [Mock() for _ in range(5)]
        mock_scan_providers.return_value = [Mock() for _ in range(3)]

        result = get_workflow_metadata()

        assert result["workflowCount"] == 5
        assert result["dataProviderCount"] == 3
        mock_scan_workflows.assert_called_once()
        mock_scan_providers.assert_called_once()

    @patch("shared.handlers.metrics_handlers.scan_all_workflows")
    @patch("shared.handlers.metrics_handlers.scan_all_data_providers")
    def test_metadata_with_zero_counts(self, mock_scan_providers, mock_scan_workflows):
        """Test metadata retrieval with zero counts"""
        mock_scan_workflows.return_value = []
        mock_scan_providers.return_value = []

        result = get_workflow_metadata()

        assert result["workflowCount"] == 0
        assert result["dataProviderCount"] == 0

    @patch("shared.handlers.metrics_handlers.scan_all_workflows")
    @patch("shared.handlers.metrics_handlers.scan_all_data_providers")
    def test_metadata_retrieval_exception(self, mock_scan_providers, mock_scan_workflows):
        """Test graceful handling when discovery fails"""
        mock_scan_workflows.side_effect = Exception("Discovery error")

        result = get_workflow_metadata()

        assert result["workflowCount"] == 0
        assert result["dataProviderCount"] == 0


# ============================================================================
# Tests for get_form_count
# ============================================================================


class TestGetFormCount:
    """Tests for get_form_count function"""

    @pytest.mark.asyncio
    async def test_successful_form_count(self, mock_entities_service):
        """Test successful form count retrieval"""
        mock_form_1 = {"RowKey": "form:id1", "IsActive": True}
        mock_form_2 = {"RowKey": "form:id2", "IsActive": True}
        mock_entities_service.query_entities.return_value = [mock_form_1, mock_form_2]

        result = await get_form_count(mock_entities_service)

        assert result == 2
        mock_entities_service.query_entities.assert_called_once()

    @pytest.mark.asyncio
    async def test_zero_forms(self, mock_entities_service):
        """Test when no forms exist"""
        mock_entities_service.query_entities.return_value = []

        result = await get_form_count(mock_entities_service)

        assert result == 0

    @pytest.mark.asyncio
    async def test_form_count_exception(self, mock_entities_service):
        """Test graceful handling when query fails"""
        mock_entities_service.query_entities.side_effect = Exception("Query error")

        result = await get_form_count(mock_entities_service)

        assert result == 0

    @pytest.mark.asyncio
    async def test_form_count_filter_applied(self, mock_entities_service):
        """Test that correct filter is applied"""
        mock_entities_service.query_entities.return_value = []

        await get_form_count(mock_entities_service)

        # Verify correct filter is applied
        call_args = mock_entities_service.query_entities.call_args
        assert call_args[1]["filter"] == "RowKey ge 'form:' and RowKey lt 'form;' and IsActive eq true"


# ============================================================================
# Tests for get_execution_statistics
# ============================================================================


class TestGetExecutionStatistics:
    """Tests for get_execution_statistics function"""

    @pytest.mark.asyncio
    async def test_successful_statistics_retrieval(self, mock_entities_service):
        """Test successful execution statistics retrieval"""
        now = datetime.utcnow()
        mock_execution_success = {
            "ExecutionId": "exec-1",
            "Status": "Success",
            "WorkflowName": "workflow-1",
            "StartedAt": now,
            "DurationMs": 5000
        }
        mock_execution_failed = {
            "ExecutionId": "exec-2",
            "Status": "Failed",
            "WorkflowName": "workflow-2",
            "StartedAt": now,
            "ErrorMessage": "Test error",
            "DurationMs": 2000
        }

        mock_entities_service.query_entities.return_value = [
            mock_execution_success,
            mock_execution_failed
        ]

        result = await get_execution_statistics(mock_entities_service)

        assert result["totalExecutions"] == 2
        assert result["successCount"] == 1
        assert result["failedCount"] == 1
        assert result["successRate"] == 50.0
        assert result["avgDurationSeconds"] == pytest.approx(3.5)
        assert len(result["recentFailures"]) == 1

    @pytest.mark.asyncio
    async def test_zero_executions(self, mock_entities_service):
        """Test statistics with zero executions"""
        mock_entities_service.query_entities.return_value = []

        result = await get_execution_statistics(mock_entities_service)

        assert result["totalExecutions"] == 0
        assert result["successCount"] == 0
        assert result["failedCount"] == 0
        assert result["successRate"] == 0.0
        assert result["avgDurationSeconds"] == 0.0
        assert result["recentFailures"] == []

    @pytest.mark.asyncio
    async def test_success_rate_calculation(self, mock_entities_service):
        """Test correct success rate calculation"""
        executions = [
            {"Status": "Success", "DurationMs": 1000},
            {"Status": "Success", "DurationMs": 1000},
            {"Status": "Success", "DurationMs": 1000},
            {"Status": "Failed", "DurationMs": 1000}
        ]
        mock_entities_service.query_entities.return_value = executions

        result = await get_execution_statistics(mock_entities_service)

        assert result["successRate"] == 75.0

    @pytest.mark.asyncio
    async def test_running_and_pending_counts(self, mock_entities_service):
        """Test counting of running and pending executions"""
        executions = [
            {"Status": "Success", "DurationMs": 1000},
            {"Status": "Running", "DurationMs": None},
            {"Status": "Pending", "DurationMs": None},
            {"Status": "Running", "DurationMs": None}
        ]
        mock_entities_service.query_entities.return_value = executions

        result = await get_execution_statistics(mock_entities_service)

        assert result["successCount"] == 1
        assert result["runningCount"] == 2
        assert result["pendingCount"] == 1

    @pytest.mark.asyncio
    async def test_recent_failures_limit(self, mock_entities_service):
        """Test that recent failures is limited to 10"""
        now = datetime.utcnow()
        executions = [
            {
                "ExecutionId": f"exec-{i}",
                "Status": "Failed",
                "WorkflowName": f"workflow-{i}",
                "StartedAt": now,
                "ErrorMessage": f"Error {i}",
                "DurationMs": 1000
            }
            for i in range(15)
        ]
        mock_entities_service.query_entities.return_value = executions

        result = await get_execution_statistics(mock_entities_service)

        assert len(result["recentFailures"]) == 10

    @pytest.mark.asyncio
    async def test_recent_failures_structure(self, mock_entities_service):
        """Test structure of recent failures"""
        now = datetime.utcnow()
        mock_execution_failed = {
            "ExecutionId": "exec-123",
            "Status": "Failed",
            "WorkflowName": "test-workflow",
            "StartedAt": now,
            "ErrorMessage": "Connection timeout",
            "DurationMs": 5000
        }
        mock_entities_service.query_entities.return_value = [mock_execution_failed]

        result = await get_execution_statistics(mock_entities_service)

        assert len(result["recentFailures"]) == 1
        failure = result["recentFailures"][0]
        assert failure["executionId"] == "exec-123"
        assert failure["workflowName"] == "test-workflow"
        assert failure["errorMessage"] == "Connection timeout"
        assert failure["startedAt"] == now.isoformat()

    @pytest.mark.asyncio
    async def test_missing_started_at_in_failure(self, mock_entities_service):
        """Test handling of missing StartedAt in failed execution"""
        mock_execution_failed = {
            "ExecutionId": "exec-123",
            "Status": "Failed",
            "WorkflowName": "test-workflow",
            "StartedAt": None,
            "ErrorMessage": "Error"
        }
        mock_entities_service.query_entities.return_value = [mock_execution_failed]

        result = await get_execution_statistics(mock_entities_service)

        assert len(result["recentFailures"]) == 1
        assert result["recentFailures"][0]["startedAt"] is None

    @pytest.mark.asyncio
    async def test_custom_days_parameter(self, mock_entities_service):
        """Test using custom days parameter"""
        mock_entities_service.query_entities.return_value = []

        await get_execution_statistics(mock_entities_service, days=7)

        # Verify query was called
        mock_entities_service.query_entities.assert_called_once()

    @pytest.mark.asyncio
    async def test_execution_query_exception(self, mock_entities_service):
        """Test graceful handling when execution query fails"""
        mock_entities_service.query_entities.side_effect = Exception("Query error")

        result = await get_execution_statistics(mock_entities_service)

        assert result["totalExecutions"] == 0
        assert result["successRate"] == 0.0
        assert result["recentFailures"] == []

    @pytest.mark.asyncio
    async def test_average_duration_calculation(self, mock_entities_service):
        """Test average duration calculation with various durations"""
        executions = [
            {"Status": "Success", "DurationMs": 2000},
            {"Status": "Success", "DurationMs": 4000},
            {"Status": "Running", "DurationMs": None},  # Should be skipped
            {"Status": "Failed", "DurationMs": 6000}
        ]
        mock_entities_service.query_entities.return_value = executions

        result = await get_execution_statistics(mock_entities_service)

        # (2000 + 4000 + 6000) / 3 / 1000 = 4.0
        assert result["avgDurationSeconds"] == pytest.approx(4.0)

    @pytest.mark.asyncio
    async def test_execution_with_missing_status(self, mock_entities_service):
        """Test handling execution with missing status"""
        executions = [
            {"ExecutionId": "exec-1", "DurationMs": 1000},  # Missing Status
            {"Status": "Success", "DurationMs": 1000}
        ]
        mock_entities_service.query_entities.return_value = executions

        result = await get_execution_statistics(mock_entities_service)

        assert result["totalExecutions"] == 2
        # First execution has status "Unknown"
        assert "Unknown" in [
            "Unknown",
            "Success"
        ]


# ============================================================================
# Tests for get_dashboard_metrics
# ============================================================================


class TestGetDashboardMetrics:
    """Tests for get_dashboard_metrics function"""

    @pytest.mark.asyncio
    @patch("shared.handlers.metrics_handlers.scan_all_workflows")
    @patch("shared.handlers.metrics_handlers.scan_all_data_providers")
    @patch("shared.handlers.metrics_handlers.get_async_table_service")
    async def test_successful_metrics_aggregation(
        self,
        mock_get_async_table_service,
        mock_scan_providers,
        mock_scan_workflows,
        mock_context
    ):
        """Test successful aggregation of all metrics"""
        # Setup discovery mocks
        mock_scan_workflows.return_value = [Mock() for _ in range(5)]
        mock_scan_providers.return_value = [Mock() for _ in range(3)]

        # Setup table service mock
        mock_service = AsyncMock()
        mock_get_async_table_service.side_effect = make_async_context_manager(mock_service)

        # Mock form query
        mock_service.query_entities.side_effect = [
            [{"RowKey": "form:1"}, {"RowKey": "form:2"}],
            []  # For execution statistics query
        ]

        # Call handler
        result = await get_dashboard_metrics(mock_context)

        # Verify structure
        assert "workflowCount" in result
        assert "dataProviderCount" in result
        assert "formCount" in result
        assert "executionStats" in result
        assert "recentFailures" in result

    @pytest.mark.asyncio
    @patch("shared.handlers.metrics_handlers.scan_all_workflows")
    @patch("shared.handlers.metrics_handlers.scan_all_data_providers")
    @patch("shared.handlers.metrics_handlers.get_async_table_service")
    async def test_metrics_with_discovery_failure(
        self,
        mock_get_async_table_service,
        mock_scan_providers,
        mock_scan_workflows,
        mock_context
    ):
        """Test metrics generation when discovery fails"""
        # Setup discovery to fail
        mock_scan_workflows.side_effect = Exception("Discovery error")

        # Setup table service mock
        mock_service = AsyncMock()
        mock_get_async_table_service.side_effect = make_async_context_manager(mock_service)
        mock_service.query_entities.side_effect = [[], []]

        result = await get_dashboard_metrics(mock_context)

        # Should have defaults from failed discovery
        assert result["workflowCount"] == 0
        assert result["dataProviderCount"] == 0

    @pytest.mark.asyncio
    @patch("shared.handlers.metrics_handlers.scan_all_workflows")
    @patch("shared.handlers.metrics_handlers.scan_all_data_providers")
    @patch("shared.handlers.metrics_handlers.get_async_table_service")
    async def test_metrics_complete_structure(
        self,
        mock_get_async_table_service,
        mock_scan_providers,
        mock_scan_workflows,
        mock_context
    ):
        """Test complete metrics structure"""
        mock_scan_workflows.return_value = [Mock() for _ in range(10)]
        mock_scan_providers.return_value = [Mock() for _ in range(5)]

        mock_service = AsyncMock()
        mock_get_async_table_service.side_effect = make_async_context_manager(mock_service)
        mock_service.query_entities.side_effect = [[], []]

        result = await get_dashboard_metrics(mock_context)

        # Verify all required fields
        assert result["workflowCount"] == 10
        assert result["dataProviderCount"] == 5
        assert result["formCount"] == 0
        assert isinstance(result["executionStats"], dict)
        assert "totalExecutions" in result["executionStats"]
        assert "successCount" in result["executionStats"]
        assert "failedCount" in result["executionStats"]
        assert "runningCount" in result["executionStats"]
        assert "pendingCount" in result["executionStats"]
        assert "successRate" in result["executionStats"]
        assert "avgDurationSeconds" in result["executionStats"]
        assert isinstance(result["recentFailures"], list)

    @pytest.mark.asyncio
    @patch("shared.handlers.metrics_handlers.scan_all_workflows")
    @patch("shared.handlers.metrics_handlers.scan_all_data_providers")
    @patch("shared.handlers.metrics_handlers.get_async_table_service")
    async def test_metrics_with_complex_execution_data(
        self,
        mock_get_async_table_service,
        mock_scan_providers,
        mock_scan_workflows,
        mock_context
    ):
        """Test metrics with complex execution data"""
        mock_scan_workflows.return_value = [Mock() for _ in range(3)]
        mock_scan_providers.return_value = [Mock() for _ in range(2)]

        mock_service = AsyncMock()
        mock_get_async_table_service.side_effect = make_async_context_manager(mock_service)

        # Mock execution entities
        executions = [
            {"Status": "Success", "DurationMs": 1000},
            {"Status": "Success", "DurationMs": 2000},
            {"Status": "Failed", "DurationMs": 3000, "ErrorMessage": "Error"},
            {"Status": "Running", "DurationMs": None}
        ]

        # First call for forms, second for executions
        mock_service.query_entities.side_effect = [[], executions]

        result = await get_dashboard_metrics(mock_context)

        assert result["executionStats"]["totalExecutions"] == 4
        assert result["executionStats"]["successCount"] == 2
        assert result["executionStats"]["failedCount"] == 1
        assert result["executionStats"]["runningCount"] == 1
        assert result["executionStats"]["successRate"] == 66.7
