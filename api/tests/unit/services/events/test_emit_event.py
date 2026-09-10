"""Transaction-order tests for the public topic-event emitter."""

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest


@pytest.mark.asyncio
async def test_emit_event_commits_deliveries_before_queueing():
    """AgentRun's separate transaction must be able to resolve its delivery FK."""
    db = AsyncMock()
    processor = AsyncMock()
    event_id = uuid4()
    processor.emit_topic.return_value = (event_id, 1)

    async def assert_delivery_is_committed(_event_id):
        assert db.commit.await_count == 1

    processor.queue_event_deliveries.side_effect = assert_delivery_is_committed

    @asynccontextmanager
    async def session_context():
        yield db

    with (
        patch("src.core.database.get_session_factory", return_value=session_context),
        patch("src.services.events.EventProcessor", return_value=processor),
    ):
        from src.services.events import emit_event

        result = await emit_event("test.topic", {"value": 1})

    assert result == (event_id, 1)
    processor.queue_event_deliveries.assert_awaited_once_with(event_id)
    assert db.commit.await_count == 2
