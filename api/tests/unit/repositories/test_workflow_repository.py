"""
Unit tests for WorkflowRepository.

Tests the database operations for workflow registry.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from src.repositories.workflows import WorkflowRepository


class TestWorkflowRepository:
    """Tests for WorkflowRepository methods."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock database session."""
        session = AsyncMock()
        session.execute = AsyncMock()
        session.flush = AsyncMock()
        return session

    @pytest.fixture
    def repository(self, mock_session):
        """Create repository with mock session."""
        return WorkflowRepository(mock_session)

    @pytest.fixture
    def mock_workflow(self):
        """Create a mock workflow object."""
        workflow = MagicMock()
        workflow.id = uuid4()
        workflow.name = "test-workflow"
        workflow.description = "Test workflow"
        workflow.category = "Testing"
        workflow.file_path = "/workspace/test.py"
        workflow.schedule = "*/5 * * * *"
        workflow.is_active = True
        workflow.endpoint_enabled = True
        workflow.api_key_hash = "abc123"
        workflow.api_key_enabled = True
        workflow.api_key_expires_at = None
        return workflow

    async def test_get_by_name_found(self, repository, mock_session, mock_workflow):
        """Test getting workflow by name when found."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_workflow
        mock_session.execute.return_value = mock_result

        result = await repository.get_by_name("test-workflow")

        assert result == mock_workflow
        mock_session.execute.assert_called_once()

    async def test_get_by_name_not_found(self, repository, mock_session):
        """Test getting workflow by name when not found."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await repository.get_by_name("nonexistent")

        assert result is None

    async def test_get_all_active(self, repository, mock_session, mock_workflow):
        """Test getting all active workflows."""
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [mock_workflow]
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        result = await repository.get_all_active()

        assert len(result) == 1
        assert result[0] == mock_workflow

    async def test_get_scheduled(self, repository, mock_session, mock_workflow):
        """Test getting workflows with schedules."""
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [mock_workflow]
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        result = await repository.get_scheduled()

        assert len(result) == 1
        assert result[0].schedule is not None

    async def test_get_endpoint_enabled(self, repository, mock_session, mock_workflow):
        """Test getting workflows with endpoint enabled."""
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [mock_workflow]
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        result = await repository.get_endpoint_enabled()

        assert len(result) == 1
        assert result[0].endpoint_enabled is True

    async def test_count_active(self, repository, mock_session):
        """Test counting active workflows."""
        mock_result = MagicMock()
        mock_result.scalar.return_value = 5
        mock_session.execute.return_value = mock_result

        result = await repository.count_active()

        assert result == 5

    async def test_count_active_returns_zero_on_none(self, repository, mock_session):
        """Test count returns 0 when result is None."""
        mock_result = MagicMock()
        mock_result.scalar.return_value = None
        mock_session.execute.return_value = mock_result

        result = await repository.count_active()

        assert result == 0

    async def test_search_with_query(self, repository, mock_session, mock_workflow):
        """Test search with text query."""
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [mock_workflow]
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        result = await repository.search(query="test")

        assert len(result) == 1

    async def test_search_with_category(self, repository, mock_session, mock_workflow):
        """Test search with category filter."""
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [mock_workflow]
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        result = await repository.search(category="Testing")

        assert len(result) == 1

    async def test_get_by_api_key_hash(self, repository, mock_session, mock_workflow):
        """Test getting workflow by API key hash."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_workflow
        mock_session.execute.return_value = mock_result

        result = await repository.get_by_api_key_hash("abc123")

        assert result == mock_workflow

    async def test_validate_api_key_valid(self, repository, mock_session, mock_workflow):
        """Test validating a valid API key."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_workflow
        mock_session.execute.return_value = mock_result

        is_valid, workflow_id = await repository.validate_api_key("abc123")

        assert is_valid is True
        assert workflow_id == mock_workflow.id

    async def test_validate_api_key_expired(self, repository, mock_session, mock_workflow):
        """Test validating an expired API key."""
        mock_workflow.api_key_expires_at = datetime.utcnow() - timedelta(days=1)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_workflow
        mock_session.execute.return_value = mock_result

        is_valid, workflow_id = await repository.validate_api_key("abc123")

        assert is_valid is False
        assert workflow_id is None

    async def test_validate_api_key_wrong_workflow(self, repository, mock_session, mock_workflow):
        """Test validating API key for wrong workflow."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_workflow
        mock_session.execute.return_value = mock_result

        is_valid, workflow_id = await repository.validate_api_key(
            "abc123", workflow_name="other-workflow"
        )

        assert is_valid is False
        assert workflow_id is None

    async def test_validate_api_key_not_found(self, repository, mock_session):
        """Test validating API key that doesn't exist."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        is_valid, workflow_id = await repository.validate_api_key("nonexistent")

        assert is_valid is False
        assert workflow_id is None

    async def test_set_api_key(self, repository, mock_session, mock_workflow):
        """Test setting API key for a workflow."""
        # Mock get_by_id
        with patch.object(repository, 'get_by_id', return_value=mock_workflow):
            result = await repository.set_api_key(
                workflow_id=mock_workflow.id,
                key_hash="new_hash",
                description="Test key",
                created_by="admin",
            )

        assert result == mock_workflow
        assert mock_workflow.api_key_hash == "new_hash"
        assert mock_workflow.api_key_enabled is True
        mock_session.flush.assert_called_once()

    async def test_revoke_api_key(self, repository, mock_session, mock_workflow):
        """Test revoking API key."""
        with patch.object(repository, 'get_by_id', return_value=mock_workflow):
            result = await repository.revoke_api_key(mock_workflow.id)

        assert result == mock_workflow
        assert mock_workflow.api_key_enabled is False
        mock_session.flush.assert_called_once()
