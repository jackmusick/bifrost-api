from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from sqlalchemy import event, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.table_batch_writes import (
    BatchPolicyDenied,
    BatchWriteRow,
    ConcurrentBatchWrite,
    DuplicateBatchIds,
    write_table_batch,
)
from src.core.principal import UserPrincipal
from src.models.contracts.policies import TablePolicies
from src.models.contracts.tables import TableCreate
from src.models.orm.organizations import Organization
from src.models.orm.tables import Document, Table
from src.repositories.tables import TableRepository


@pytest_asyncio.fixture
async def org(db_session: AsyncSession) -> Organization:
    org = Organization(
        id=uuid4(),
        name=f"Batch Engine {uuid4().hex[:8]}",
        domain=f"batch-{uuid4().hex[:8]}.example.com",
        created_by="tests@example.com",
    )
    db_session.add(org)
    await db_session.commit()
    return org


@pytest_asyncio.fixture
async def table(db_session: AsyncSession, org: Organization) -> Table:
    table = await TableRepository(db_session, org.id).create_table(
        TableCreate(name=f"batch_engine_{uuid4().hex[:8]}"),
        created_by="tests@example.com",
    )
    await db_session.commit()
    return table


@pytest.fixture
def principal(org: Organization) -> UserPrincipal:
    return UserPrincipal(
        user_id=uuid4(),
        email="writer@example.com",
        organization_id=org.id,
        is_superuser=False,
    )


@pytest.fixture
def allow_all_policies() -> TablePolicies:
    return TablePolicies.model_validate(
        {
            "policies": [
                {
                    "name": "allow_all_writes",
                    "actions": ["create", "update"],
                    "when": None,
                }
            ]
        }
    )


@contextmanager
def count_sql(session: AsyncSession) -> Iterator[list[str]]:
    statements: list[str] = []
    engine = session.bind.sync_engine

    def before_cursor_execute(_conn, _cursor, statement, _params, _context, _executemany):
        statements.append(statement)

    event.listen(engine, "before_cursor_execute", before_cursor_execute)
    try:
        yield statements
    finally:
        event.remove(engine, "before_cursor_execute", before_cursor_execute)


def row(index: int, doc_id: str, data: dict, actor: str = "writer") -> BatchWriteRow:
    return BatchWriteRow(
        submission_index=index,
        id=doc_id,
        data=data,
        created_by=f"{actor}-created",
        updated_by=f"{actor}-updated",
    )


def generated_row(index: int, data: dict, actor: str = "writer") -> BatchWriteRow:
    return BatchWriteRow(
        submission_index=index,
        id=None,
        data=data,
        created_by=f"{actor}-created",
        updated_by=f"{actor}-updated",
    )


async def fetch_docs(db_session: AsyncSession, table: Table) -> dict[str, Document]:
    result = await db_session.execute(
        select(Document).where(Document.table_id == table.id).order_by(Document.id)
    )
    return {doc.id: doc for doc in result.scalars().all()}


@pytest.mark.asyncio
async def test_insert_1000_rows_uses_bounded_statements_and_returns_documents(
    db_session: AsyncSession,
    table: Table,
    principal: UserPrincipal,
    allow_all_policies: TablePolicies,
):
    rows = [row(i, f"doc-{i:04d}", {"position": i}) for i in range(1000)]

    with count_sql(db_session) as statements:
        result = await write_table_batch(
            db_session,
            table,
            rows,
            mode="insert",
            policies=allow_all_policies,
            user=principal,
        )

    assert result.insert_conflicts == []
    assert set(result.documents_by_index) == set(range(1000))
    assert result.documents_by_index[7].data == {"position": 7}
    assert result.previous_rows_by_index == {}

    normalized = [" ".join(statement.lower().split()) for statement in statements]
    document_selects = [
        statement
        for statement in normalized
        if statement.startswith("select") and " from documents " in statement
    ]
    document_writes = [
        statement
        for statement in normalized
        if statement.startswith("insert into documents")
    ]
    assert len(document_selects) == 1
    assert " for update" in document_selects[0]
    assert len(document_writes) == 1


@pytest.mark.asyncio
async def test_insert_generates_uuid_ids_and_persists_rows(
    db_session: AsyncSession,
    table: Table,
    principal: UserPrincipal,
    allow_all_policies: TablePolicies,
):
    result = await write_table_batch(
        db_session,
        table,
        [
            generated_row(0, {"value": "first"}),
            generated_row(1, {"value": "second"}),
        ],
        mode="insert",
        policies=allow_all_policies,
        user=principal,
    )

    generated_ids = [result.documents_by_index[index].id for index in (0, 1)]
    assert len(set(generated_ids)) == 2
    assert [str(UUID(doc_id)) for doc_id in generated_ids] == generated_ids

    docs = await fetch_docs(db_session, table)
    assert set(docs) == set(generated_ids)
    assert docs[generated_ids[0]].data == {"value": "first"}
    assert docs[generated_ids[1]].created_by == "writer-created"


@pytest.mark.asyncio
async def test_legacy_merge_upsert_idless_rows_are_inserted_with_generated_ids(
    db_session: AsyncSession,
    table: Table,
    principal: UserPrincipal,
    allow_all_policies: TablePolicies,
):
    result = await write_table_batch(
        db_session,
        table,
        [generated_row(0, {"value": "legacy"})],
        mode="merge_upsert",
        policies=allow_all_policies,
        user=principal,
    )

    generated_id = result.documents_by_index[0].id
    assert str(UUID(generated_id)) == generated_id
    assert result.previous_rows_by_index == {}
    assert result.insert_conflicts == []
    docs = await fetch_docs(db_session, table)
    assert docs[generated_id].data == {"value": "legacy"}


@pytest.mark.asyncio
async def test_insert_reports_generated_ids_and_ordered_conflicts(
    db_session: AsyncSession,
    table: Table,
    principal: UserPrincipal,
    allow_all_policies: TablePolicies,
):
    db_session.add(
        Document(
            table_id=table.id,
            id="existing",
            data={"value": "old"},
            created_by="original",
            updated_by="original",
        )
    )
    await db_session.commit()

    db_session.add(
        Document(
            table_id=table.id,
            id="other-existing",
            data={"value": "old"},
            created_by="original",
            updated_by="original",
        )
    )
    await db_session.commit()

    rows = [
        row(0, str(uuid4()), {"value": "generated"}),
        row(1, "existing", {"value": "conflict-1"}),
        row(2, "new", {"value": "inserted"}),
        row(3, "other-existing", {"value": "conflict-2"}),
    ]
    result = await write_table_batch(
        db_session,
        table,
        rows,
        mode="insert",
        policies=allow_all_policies,
        user=principal,
    )

    assert [error.submission_index for error in result.insert_conflicts] == [1, 3]
    assert [error.id for error in result.insert_conflicts] == ["existing", "other-existing"]
    assert set(result.documents_by_index) == {0, 2}
    assert result.documents_by_index[0].id == rows[0].id
    assert result.documents_by_index[2].id == "new"


@pytest.mark.asyncio
async def test_merge_and_replace_upsert_semantics_preserve_insert_attribution(
    db_session: AsyncSession,
    table: Table,
    principal: UserPrincipal,
    allow_all_policies: TablePolicies,
):
    db_session.add_all(
        [
            Document(
                table_id=table.id,
                id="merge",
                data={"keep": True, "replace": "old"},
                created_by="creator",
                updated_by="old-updater",
            ),
            Document(
                table_id=table.id,
                id="replace",
                data={"keep": True, "replace": "old"},
                created_by="creator",
                updated_by="old-updater",
            ),
        ]
    )
    await db_session.commit()

    merged = await write_table_batch(
        db_session,
        table,
        [row(0, "merge", {"replace": "new", "added": 1}, actor="merge")],
        mode="merge_upsert",
        policies=allow_all_policies,
        user=principal,
    )
    replaced = await write_table_batch(
        db_session,
        table,
        [row(0, "replace", {"replace": "new"}, actor="replace")],
        mode="replace_upsert",
        policies=allow_all_policies,
        user=principal,
    )

    assert merged.previous_rows_by_index[0]["keep"] is True
    assert merged.previous_rows_by_index[0]["replace"] == "old"
    assert merged.documents_by_index[0].data == {"keep": True, "replace": "new", "added": 1}
    assert replaced.documents_by_index[0].data == {"replace": "new"}

    docs = await fetch_docs(db_session, table)
    assert docs["merge"].created_by == "creator"
    assert docs["merge"].updated_by == "merge-updated"
    assert docs["replace"].created_by == "creator"
    assert docs["replace"].updated_by == "replace-updated"


@pytest.mark.asyncio
async def test_duplicate_ids_are_rejected_before_writes(
    db_session: AsyncSession,
    table: Table,
    principal: UserPrincipal,
    allow_all_policies: TablePolicies,
):
    rows = [row(0, "same", {"value": 1}), row(1, "same", {"value": 2})]

    with pytest.raises(DuplicateBatchIds) as exc_info:
        await write_table_batch(
            db_session,
            table,
            rows,
            mode="replace_upsert",
            policies=allow_all_policies,
            user=principal,
        )

    assert exc_info.value.ids == ["same"]
    assert await fetch_docs(db_session, table) == {}


@pytest.mark.asyncio
async def test_policy_denial_is_atomic_and_reports_submission_indices(
    db_session: AsyncSession,
    table: Table,
    principal: UserPrincipal,
):
    policies = TablePolicies.model_validate(
        {
            "policies": [
                {
                    "name": "only_allowed_rows",
                    "actions": ["create", "update"],
                    "when": {"eq": [{"row": "allowed"}, True]},
                }
            ]
        }
    )
    rows = [
        row(0, "allowed", {"allowed": True}),
        row(1, "denied", {"allowed": False}),
    ]

    with pytest.raises(BatchPolicyDenied) as exc_info:
        await write_table_batch(
            db_session,
            table,
            rows,
            mode="insert",
            policies=policies,
            user=principal,
        )

    assert exc_info.value.indices == [1]
    assert await fetch_docs(db_session, table) == {}


@pytest.mark.asyncio
async def test_upsert_guard_detects_concurrent_insert_after_preflight(
    db_session: AsyncSession,
    table: Table,
    principal: UserPrincipal,
    allow_all_policies: TablePolicies,
):
    async def insert_racing_row() -> None:
        db_session.add(
            Document(
                table_id=table.id,
                id="raced",
                data={"value": "other"},
                created_by="other",
                updated_by="other",
            )
        )
        await db_session.flush()

    with pytest.raises(ConcurrentBatchWrite):
        await write_table_batch(
            db_session,
            table,
            [row(0, "raced", {"value": "ours"})],
            mode="replace_upsert",
            policies=allow_all_policies,
            user=principal,
            _after_preflight=insert_racing_row,
        )
