from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException

from src.core.principal import UserPrincipal
from src.models.contracts.policies import TablePolicies
from src.models.contracts.tables import DocumentBulkUpsertRequest


class _FakeDb:
    def __init__(self) -> None:
        self.committed = False
        self.rolled_back = False

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        self.rolled_back = True


class _RaceRepo:
    async def get_many_for_update(self, doc_ids):
        return {}

    async def bulk_upsert(self, rows, *, update_ids):
        assert update_ids == set()
        return 0


@pytest.mark.asyncio
async def test_bulk_upsert_rolls_back_and_409s_on_guarded_count_mismatch(monkeypatch):
    import src.routers.tables as router

    table = SimpleNamespace(
        id=uuid4(),
        name="bulk_race",
        organization_id=None,
        solution_id=None,
    )
    db = _FakeDb()
    user = UserPrincipal(
        user_id=uuid4(),
        email="admin@example.com",
        organization_id=None,
        is_superuser=True,
        roles=["authenticated"],
    )
    ctx = SimpleNamespace(
        db=db,
        user=user,
        org_id=None,
        solution_id=None,
        app_id=None,
    )

    async def fake_get_table_or_404(*args, **kwargs):
        return table

    async def fake_solution_gate(*args, **kwargs):
        return None

    async def fake_load_policies(*args, **kwargs):
        return TablePolicies()

    async def fake_preresolve(*args, **kwargs):
        return None

    monkeypatch.setattr(router, "get_table_or_404", fake_get_table_or_404)
    monkeypatch.setattr(router, "_assert_solution_write_targets_owned_table", fake_solution_gate)
    monkeypatch.setattr(router, "DocumentRepository", lambda db, table: _RaceRepo())
    monkeypatch.setattr(router, "load_resolved_table_policies", fake_load_policies)
    monkeypatch.setattr(router, "preresolve_for_policies", fake_preresolve)
    monkeypatch.setattr(router, "evaluate_action", lambda *args, **kwargs: True)

    body = DocumentBulkUpsertRequest(
        documents=[{"id": "new-row", "data": {"value": 1}}]
    )
    with pytest.raises(HTTPException) as exc_info:
        await router.bulk_upsert_documents(
            "bulk_race",
            body,
            ctx,
            user,
        )

    assert exc_info.value.status_code == 409
    assert db.rolled_back is True
    assert db.committed is False
