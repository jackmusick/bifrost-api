"""
Unit tests for executions handlers

Tests business logic for execution queries and filtering.
Uses AsyncMock for async functions and mocks repositories.
"""

import uuid
from datetime import datetime
from unittest.mock import MagicMock, Mock, patch

import pytest

from shared.handlers.executions_handlers import (
    apply_limit,
    determine_result_type,
    filter_executions_by_status,
    filter_executions_by_workflow,
    map_frontend_status_to_backend,
    map_status_to_frontend,
)
from shared.models import WorkflowExecution
from shared.request_context import RequestContext


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_context():
    """Create a mock RequestContext"""
    context = Mock(spec=RequestContext)
    context.user_id = "user-123"
    context.is_platform_admin = False
    context.scope = "org-456"
    return context


@pytest.fixture
def mock_context_admin():
    """Create a mock RequestContext for platform admin"""
    context = Mock(spec=RequestContext)
    context.user_id = "admin-user"
    context.is_platform_admin = True
    context.scope = "GLOBAL"
    return context


@pytest.fixture
def sample_execution_dict():
    """Create a sample execution dict"""
    return {
        'executionId': str(uuid.uuid4()),
        'workflowName': 'test-workflow',
        'orgId': 'org-456',
        'status': 'Success',
        'errorMessage': None,
        'executedBy': 'user-123',
        'executedByName': 'Test User',
        'startedAt': datetime.now().isoformat(),
        'completedAt': datetime.now().isoformat(),
        'formId': None,
        'durationMs': 1500
    }


@pytest.fixture
def sample_workflow_execution():
    """Create a sample WorkflowExecution model"""
    from shared.models import ExecutionStatus

    execution_id = str(uuid.uuid4())
    return WorkflowExecution(
        executionId=execution_id,
        workflowName='test-workflow',
        orgId='org-456',
        status=ExecutionStatus.SUCCESS,
        errorMessage=None,
        executedBy='user-123',
        executedByName='Test User',
        startedAt=datetime.now(),
        completedAt=datetime.now(),
        formId=None,
        durationMs=1500,
        inputData={'param1': 'value1'},
        result={'key': 'value'},
        logs=[]
    )


# ============================================================================
# Status Mapping Tests
# ============================================================================


class TestStatusMapping:
    """Tests for status mapping functions"""

    def test_map_frontend_status_to_backend_pending(self):
        """Test mapping pending status"""
        assert map_frontend_status_to_backend('pending') == 'Pending'

    def test_map_frontend_status_to_backend_running(self):
        """Test mapping running status"""
        assert map_frontend_status_to_backend('running') == 'Running'

    def test_map_frontend_status_to_backend_completed(self):
        """Test mapping completed status to Success"""
        assert map_frontend_status_to_backend('completed') == 'Success'

    def test_map_frontend_status_to_backend_failed(self):
        """Test mapping failed status"""
        assert map_frontend_status_to_backend('failed') == 'Failed'

    def test_map_frontend_status_to_backend_completed_with_errors(self):
        """Test mapping completed with errors status"""
        assert map_frontend_status_to_backend('completedwitherrors') == 'CompletedWithErrors'

    def test_map_frontend_status_to_backend_case_insensitive(self):
        """Test that mapping is case insensitive"""
        assert map_frontend_status_to_backend('PENDING') == 'Pending'
        assert map_frontend_status_to_backend('Running') == 'Running'

    def test_map_frontend_status_to_backend_unknown(self):
        """Test that unknown status is returned as-is"""
        assert map_frontend_status_to_backend('unknown') == 'unknown'

    def test_map_status_to_frontend(self):
        """Test mapping backend status to frontend (identity function)"""
        assert map_status_to_frontend('Success') == 'Success'
        assert map_status_to_frontend('Pending') == 'Pending'
        assert map_status_to_frontend('CompletedWithErrors') == 'CompletedWithErrors'


# ============================================================================
# Result Type Determination Tests
# ============================================================================


class TestDetermineResultType:
    """Tests for result type determination"""

    def test_determine_result_type_none(self):
        """Test that None returns None"""
        assert determine_result_type(None) is None

    def test_determine_result_type_dict(self):
        """Test that dict returns json"""
        assert determine_result_type({'key': 'value'}) == 'json'
        assert determine_result_type({}) == 'json'

    def test_determine_result_type_html_string(self):
        """Test that HTML string returns html"""
        assert determine_result_type('<html><body>test</body></html>') == 'html'
        assert determine_result_type('  <div>content</div>  ') == 'html'
        assert determine_result_type('<p>paragraph</p>') == 'html'

    def test_determine_result_type_text_string(self):
        """Test that plain text string returns text"""
        assert determine_result_type('plain text') == 'text'
        assert determine_result_type('this is not html') == 'text'
        assert determine_result_type('no tags here') == 'text'

    def test_determine_result_type_json_like_string(self):
        """Test that JSON-like string returns text (not parsed)"""
        # Note: We only check if it starts with < and contains >, not JSON parsing
        assert determine_result_type('{"key": "value"}') == 'text'

    def test_determine_result_type_other_types(self):
        """Test that other types default to json"""
        assert determine_result_type([1, 2, 3]) == 'json'
        assert determine_result_type(123) == 'json'
        assert determine_result_type(True) == 'json'


# ============================================================================
# Filter Functions Tests
# ============================================================================


class TestFilterFunctions:
    """Tests for execution filtering functions"""

    def test_filter_executions_by_workflow_no_filter(self):
        """Test filtering with no workflow name filter"""
        executions = [
            {'workflowName': 'workflow-a'},
            {'workflowName': 'workflow-b'},
            {'workflowName': 'workflow-a'},
        ]
        result = filter_executions_by_workflow(executions, None)
        assert len(result) == 3
        assert result == executions

    def test_filter_executions_by_workflow_single_match(self):
        """Test filtering executions by workflow name"""
        executions = [
            {'workflowName': 'workflow-a'},
            {'workflowName': 'workflow-b'},
            {'workflowName': 'workflow-a'},
        ]
        result = filter_executions_by_workflow(executions, 'workflow-a')
        assert len(result) == 2
        assert all(e['workflowName'] == 'workflow-a' for e in result)

    def test_filter_executions_by_workflow_no_match(self):
        """Test filtering when no executions match"""
        executions = [
            {'workflowName': 'workflow-a'},
            {'workflowName': 'workflow-b'},
        ]
        result = filter_executions_by_workflow(executions, 'workflow-c')
        assert len(result) == 0

    def test_filter_executions_by_status_no_filter(self):
        """Test filtering with no status filter"""
        executions = [
            {'status': 'Success'},
            {'status': 'Failed'},
            {'status': 'Running'},
        ]
        result = filter_executions_by_status(executions, None)
        assert len(result) == 3
        assert result == executions

    def test_filter_executions_by_status_single_match(self):
        """Test filtering executions by status"""
        executions = [
            {'status': 'Success'},
            {'status': 'Failed'},
            {'status': 'Success'},
        ]
        result = filter_executions_by_status(executions, 'completed')
        assert len(result) == 2
        assert all(e['status'] == 'Success' for e in result)

    def test_filter_executions_by_status_completed_with_errors(self):
        """Test filtering by completed with errors status"""
        executions = [
            {'status': 'CompletedWithErrors'},
            {'status': 'Failed'},
            {'status': 'CompletedWithErrors'},
        ]
        result = filter_executions_by_status(executions, 'completedwitherrors')
        assert len(result) == 2
        assert all(e['status'] == 'CompletedWithErrors' for e in result)

    def test_apply_limit(self):
        """Test applying limit to executions list"""
        executions = [{'id': i} for i in range(100)]
        result = apply_limit(executions, 10)
        assert len(result) == 10
        assert result == executions[:10]

    def test_apply_limit_larger_than_list(self):
        """Test applying limit larger than list size"""
        executions = [{'id': i} for i in range(5)]
        result = apply_limit(executions, 10)
        assert len(result) == 5
        assert result == executions

    def test_apply_limit_zero(self):
        """Test applying zero limit"""
        executions = [{'id': i} for i in range(5)]
        result = apply_limit(executions, 0)
        assert len(result) == 0
