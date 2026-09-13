from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

from src.core.auth import UserPrincipal
from src.routers import websocket as ws_mod


def _websocket_with_subscriptions(*table_ids: str) -> SimpleNamespace:
    return SimpleNamespace(
        state=SimpleNamespace(
            table_subscriptions={table_id: {"filter": None} for table_id in table_ids},
        ),
        send_json=AsyncMock(),
    )


def _user() -> UserPrincipal:
    return UserPrincipal(
        user_id=uuid.uuid4(),
        email="user@example.com",
        organization_id=uuid.uuid4(),
        is_superuser=False,
    )


async def test_table_invalidated_for_active_subscription_forwards_canonical_payload(monkeypatch):
    table_id = str(uuid.uuid4())
    websocket = _websocket_with_subscriptions(table_id)
    load_policies = AsyncMock()
    monkeypatch.setattr(ws_mod, "_load_policies_for_table", load_policies)

    await ws_mod._handle_table_message(
        websocket,
        _user(),
        f"table:{table_id}",
        {"type": "table_invalidated", "table_id": "ignored", "extra": "ignored"},
    )

    websocket.send_json.assert_awaited_once_with({
        "type": "table_invalidated",
        "table_id": table_id,
    })
    load_policies.assert_not_awaited()


async def test_table_invalidated_without_active_subscription_does_not_send(monkeypatch):
    table_id = str(uuid.uuid4())
    websocket = _websocket_with_subscriptions()
    load_policies = AsyncMock()
    monkeypatch.setattr(ws_mod, "_load_policies_for_table", load_policies)

    await ws_mod._handle_table_message(
        websocket,
        _user(),
        f"table:{table_id}",
        {"type": "table_invalidated", "table_id": table_id},
    )

    websocket.send_json.assert_not_awaited()
    load_policies.assert_not_awaited()
