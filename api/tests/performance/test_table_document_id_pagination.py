"""Query-plan regressions for physical document-ID filtering."""

from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy import event, insert, text
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.contracts.tables import DocumentQuery
from src.models.orm.organizations import Organization
from src.models.orm.tables import Document, Table
from src.routers.tables import DocumentRepository


def _plan_nodes(plan: dict):
    yield plan
    for child in plan.get("Plans", []):
        yield from _plan_nodes(child)


@pytest.mark.asyncio
@pytest.mark.slow
@pytest.mark.timeout(120)
async def test_document_id_keyset_query_uses_composite_index_without_sort(
    db_session: AsyncSession,
) -> None:
    """A production-shaped tenant page seeks through ``documents_pkey``."""
    org = Organization(
        id=uuid4(),
        name=f"Document ID plan {uuid4().hex[:8]}",
        domain=f"document-id-plan-{uuid4().hex[:8]}.example.com",
        created_by="test@example.com",
    )
    table = Table(
        id=uuid4(),
        name=f"document_id_plan_{uuid4().hex[:8]}",
        organization_id=org.id,
        created_by="test@example.com",
    )
    db_session.add_all([org, table])
    await db_session.flush()

    rows = []
    for tenant in range(5):
        prefix = f"tenant-{tenant:02d}|"
        rows.extend(
            {
                "table_id": table.id,
                "id": f"{prefix}drive|item-{item:05d}",
                "data": {"tenant": tenant, "item": item},
                "created_by": "test@example.com",
                "updated_by": "test@example.com",
            }
            for item in range(4_000)
        )
    await db_session.execute(insert(Document), rows)
    await db_session.commit()
    await db_session.execute(text("ANALYZE documents"))

    captured = []

    def capture_statement(orm_execute_state):
        if orm_execute_state.is_select:
            captured.append(orm_execute_state.statement)

    event.listen(db_session.sync_session, "do_orm_execute", capture_statement)
    try:
        documents, total = await DocumentRepository(db_session, table).query(
            DocumentQuery(
                document_id_prefix="tenant-03|",
                after_document_id="tenant-03|drive|item-01999",
                skip_count=True,
                limit=500,
            )
        )
    finally:
        event.remove(db_session.sync_session, "do_orm_execute", capture_statement)

    assert total == -1
    assert len(documents) == 500
    statement = captured[-1]
    sql = str(
        statement.compile(
            dialect=postgresql.dialect(),
            compile_kwargs={"literal_binds": True},
        )
    )
    result = await db_session.execute(text(f"EXPLAIN (FORMAT JSON) {sql}"))
    plan = result.scalar_one()[0]["Plan"]
    nodes = list(_plan_nodes(plan))

    assert all(node["Node Type"] != "Sort" for node in nodes)
    assert any(
        node["Node Type"] in {"Index Scan", "Index Only Scan"}
        and node.get("Index Name") == "documents_pkey"
        for node in nodes
    )


@pytest.mark.asyncio
@pytest.mark.slow
@pytest.mark.timeout(120)
async def test_document_id_batch_query_uses_composite_index(
    db_session: AsyncSession,
) -> None:
    """A large exact-ID batch is resolved through ``documents_pkey``."""
    org = Organization(
        id=uuid4(),
        name=f"Document ID batch plan {uuid4().hex[:8]}",
        domain=f"document-id-batch-plan-{uuid4().hex[:8]}.example.com",
        created_by="test@example.com",
    )
    table = Table(
        id=uuid4(),
        name=f"document_id_batch_plan_{uuid4().hex[:8]}",
        organization_id=org.id,
        created_by="test@example.com",
    )
    db_session.add_all([org, table])
    await db_session.flush()

    await db_session.execute(
        text(
            """
            INSERT INTO documents (
                table_id, id, data, created_by, updated_by
            )
            SELECT
                CAST(:table_id AS uuid),
                'tenant|drive|item-' || lpad(item::text, 6, '0'),
                jsonb_build_object('tenant_id', 'tenant', 'item', item),
                'test@example.com',
                'test@example.com'
            FROM generate_series(0, 199999) AS item
            """
        ),
        {"table_id": str(table.id)},
    )
    await db_session.commit()
    await db_session.execute(text("ANALYZE documents"))

    requested_ids = [
        f"tenant|drive|item-{item:06d}" for item in range(0, 200_000, 400)
    ]
    captured = []

    def capture_statement(orm_execute_state):
        if orm_execute_state.is_select:
            captured.append(orm_execute_state.statement)

    event.listen(db_session.sync_session, "do_orm_execute", capture_statement)
    try:
        documents, total = await DocumentRepository(db_session, table).query(
            DocumentQuery(
                document_ids=requested_ids,
                where={"tenant_id": "tenant"},
                skip_count=True,
                limit=500,
            )
        )
    finally:
        event.remove(db_session.sync_session, "do_orm_execute", capture_statement)

    assert total == -1
    assert len(documents) == 500
    assert len(captured) == 1
    sql = str(
        captured[0].compile(
            dialect=postgresql.dialect(),
            compile_kwargs={"literal_binds": True},
        )
    )
    result = await db_session.execute(text(f"EXPLAIN (FORMAT JSON) {sql}"))
    nodes = list(_plan_nodes(result.scalar_one()[0]["Plan"]))

    assert any(
        node["Node Type"] in {"Index Scan", "Index Only Scan", "Bitmap Index Scan"}
        and node.get("Index Name") == "documents_pkey"
        for node in nodes
    ), nodes
