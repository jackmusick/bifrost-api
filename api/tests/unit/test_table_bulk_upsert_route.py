from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException

from src.core.principal import UserPrincipal
from src.models.contracts.policies import TablePolicies
from src.models.contracts.tables import DocumentBatchCreate
from src.models.orm.tables import Document
from shared.table_batch_writes import BatchWriteResult, ConcurrentBatchWrite


class _FakeDb:
    def __init__(self) -> None:
        self.committed = False
        self.rolled_back = False
        self.calls: list[str] = []

    async def commit(self) -> None:
        self.calls.append("commit")
        self.committed = True

    async def rollback(self) -> None:
        self.calls.append("rollback")
        self.rolled_back = True


@pytest.mark.asyncio
async def test_batch_upsert_rolls_back_and_409s_on_guarded_count_mismatch(monkeypatch):
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

    async def fake_write_table_batch(*args, **kwargs):
        raise ConcurrentBatchWrite("lost race")

    monkeypatch.setattr(router, "get_table_or_404", fake_get_table_or_404)
    monkeypatch.setattr(router, "_assert_solution_write_targets_owned_table", fake_solution_gate)
    monkeypatch.setattr(router, "load_resolved_table_policies", fake_load_policies)
    monkeypatch.setattr(router, "preresolve_for_policies", fake_preresolve)
    monkeypatch.setattr(router, "write_table_batch", fake_write_table_batch)

    body = DocumentBatchCreate(
        write_mode="replace_upsert",
        return_documents=False,
        documents=[{"id": "new-row", "data": {"value": 1}}]
    )
    with pytest.raises(HTTPException) as exc_info:
        await router.batch_documents(
            "bulk_race",
            body,
            ctx=ctx,
            scope=None,
        )

    assert exc_info.value.status_code == 409
    assert db.rolled_back is True
    assert db.committed is False


@pytest.mark.asyncio
async def test_batch_documents_publishes_successes_in_submission_order(monkeypatch):
    import src.routers.tables as router

    table = SimpleNamespace(
        id=uuid4(),
        name="batch_events",
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
    now = datetime.now(timezone.utc)
    alpha = Document(
        id="alpha",
        table_id=table.id,
        data={"value": "alpha"},
        created_by=str(user.user_id),
        updated_by=str(user.user_id),
        created_at=now,
        updated_at=now,
    )
    beta = Document(
        id="beta",
        table_id=table.id,
        data={"value": "beta"},
        created_by=str(user.user_id),
        updated_by=str(user.user_id),
        created_at=now,
        updated_at=now,
    )
    published: list[dict] = []

    async def fake_get_table_or_404(*args, **kwargs):
        return table

    async def fake_solution_gate(*args, **kwargs):
        return None

    async def fake_load_policies(*args, **kwargs):
        return TablePolicies()

    async def fake_preresolve(*args, **kwargs):
        return None

    async def fake_write_table_batch(*args, **kwargs):
        return BatchWriteResult(
            documents_by_index={0: alpha, 1: beta},
            previous_rows_by_index={1: {"id": "beta", "value": "old"}},
            insert_conflicts=[],
        )

    async def fake_publish_document_change(**kwargs):
        db.calls.append(f"publish:{kwargs['action']}")
        published.append(kwargs)

    monkeypatch.setattr(router, "get_table_or_404", fake_get_table_or_404)
    monkeypatch.setattr(router, "_assert_solution_write_targets_owned_table", fake_solution_gate)
    monkeypatch.setattr(router, "load_resolved_table_policies", fake_load_policies)
    monkeypatch.setattr(router, "preresolve_for_policies", fake_preresolve)
    monkeypatch.setattr(router, "write_table_batch", fake_write_table_batch)
    monkeypatch.setattr(router, "publish_document_change", fake_publish_document_change)

    body = DocumentBatchCreate(
        documents=[
            {"id": "alpha", "data": {"value": "alpha"}},
            {"id": "beta", "data": {"value": "beta"}},
        ]
    )

    response = await router.batch_documents("batch_events", body, ctx=ctx, scope=None)

    assert [doc.id for doc in response.documents] == ["alpha", "beta"]
    assert [event["action"] for event in published] == ["insert", "update"]
    assert published[0]["old_row"] is None
    assert published[1]["old_row"] == {"id": "beta", "value": "old"}
    assert db.calls == ["commit", "publish:insert", "publish:update"]
    assert db.committed is True
