# Table Batch Write Consolidation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the unreleased specialized bulk-upsert route with one bounded canonical batch endpoint and one set-based engine while preserving released SDK behavior.

**Architecture:** Extend the existing `/documents/batch` request with explicit write and response modes while retaining `upsert` as its backward-compatible spelling. Move set-based preflight, policy evaluation, insert, merge-upsert, and replace-upsert behavior into `shared/table_batch_writes.py`; keep the router responsible for HTTP orchestration and existing notification publication. The unreleased `tables.bulk_upsert()` method becomes a convenience caller of `/documents/batch`, and the dedicated HTTP route and server DTOs are deleted.

**Tech Stack:** Python 3.11, FastAPI, Pydantic v2, SQLAlchemy 2, PostgreSQL 16, pytest, Alembic-free API change.

---

### Task 1: Lock the canonical wire contract

**Files:**
- Modify: `api/src/models/contracts/tables.py:208-285`
- Create: `api/tests/unit/test_table_batch_contract.py`

- [ ] **Step 1: Write failing contract tests**

Create tests that prove old requests normalize unchanged, new modes validate,
and the bound is enforced:

```python
import pytest
from pydantic import ValidationError

from src.models.contracts.tables import DocumentBatchCreate


def _documents(count: int, *, with_ids: bool = True) -> list[dict]:
    return [
        {"id": f"doc-{index}" if with_ids else None, "data": {"index": index}}
        for index in range(count)
    ]


@pytest.mark.parametrize(
    ("payload", "expected"),
    [
        ({"documents": [{"data": {"x": 1}}]}, "insert"),
        ({"upsert": True, "documents": _documents(1)}, "merge_upsert"),
        (
            {"write_mode": "replace_upsert", "documents": _documents(1)},
            "replace_upsert",
        ),
    ],
)
def test_batch_request_normalizes_write_mode(payload, expected):
    assert DocumentBatchCreate(**payload).effective_write_mode == expected


def test_batch_request_accepts_1000_documents():
    assert len(DocumentBatchCreate(documents=_documents(1000)).documents) == 1000


def test_batch_request_preserves_released_empty_insert_behavior():
    request = DocumentBatchCreate(documents=[])
    assert request.effective_write_mode == "insert"
    assert request.documents == []


def test_batch_request_rejects_1001_documents():
    with pytest.raises(ValidationError):
        DocumentBatchCreate(documents=_documents(1001))


def test_upsert_modes_require_explicit_ids():
    with pytest.raises(ValidationError, match="explicit id"):
        DocumentBatchCreate(
            write_mode="replace_upsert",
            documents=[{"data": {"x": 1}}],
        )


def test_old_upsert_flag_cannot_contradict_explicit_mode():
    with pytest.raises(ValidationError, match="contradictory"):
        DocumentBatchCreate(
            upsert=True,
            write_mode="replace_upsert",
            documents=_documents(1),
        )
```

- [ ] **Step 2: Run the tests and confirm the missing contract fails**

Run:

```bash
./test.sh tests/unit/test_table_batch_contract.py -v
```

Expected: failures for missing `write_mode`, `return_documents`, the 1,000-row
bound, and `effective_write_mode`.

- [ ] **Step 3: Extend `DocumentBatchCreate` and remove route-only bulk DTOs**

Implement the canonical model and delete `DocumentBulkUpsertItem`,
`DocumentBulkUpsertRequest`, and `DocumentBulkUpsertResponse`:

```python
class DocumentBatchCreate(BaseModel):
    """Input for one bounded batch insert or upsert."""

    documents: list[DocumentBatchItem] = Field(
        ...,
        max_length=1000,
        description="Documents to write. Maximum 1000 rows per request.",
    )
    upsert: bool = Field(
        default=False,
        description="Backward-compatible alias for write_mode='merge_upsert'.",
    )
    write_mode: Literal[
        "insert", "merge_upsert", "replace_upsert"
    ] | None = None
    return_documents: bool = True

    @model_validator(mode="after")
    def validate_write_mode(self) -> "DocumentBatchCreate":
        if self.write_mode is not None and self.upsert and self.write_mode != "merge_upsert":
            raise ValueError("upsert and write_mode are contradictory")
        if self.write_mode in {"merge_upsert", "replace_upsert"} and any(
            item.id is None for item in self.documents
        ):
            raise ValueError("upsert batch documents require an explicit id")
        return self

    @property
    def effective_write_mode(self) -> Literal[
        "insert", "merge_upsert", "replace_upsert"
    ]:
        if self.write_mode is not None:
            return self.write_mode
        return "merge_upsert" if self.upsert else "insert"
```

- [ ] **Step 4: Run the focused contract tests**

Run `./test.sh tests/unit/test_table_batch_contract.py -v`.

Expected: all tests pass.

- [ ] **Step 5: Commit the contract slice**

```bash
git add api/src/models/contracts/tables.py api/tests/unit/test_table_batch_contract.py
git commit -m "feat: define canonical table batch modes"
```

### Task 2: Build one set-based batch engine

**Files:**
- Create: `api/shared/table_batch_writes.py`
- Create: `api/tests/e2e/test_table_batch_write_engine.py`
- Modify: `api/src/routers/tables.py:327-478`

- [ ] **Step 1: Write failing engine tests against PostgreSQL**

Use the existing `db_session`, `Organization`, and `Table` fixtures to cover:

```python
from uuid import uuid4

import pytest
from sqlalchemy import event

from shared.policies.probe import make_seed_admin_bypass
from shared.table_batch_writes import BatchWriteRow, execute_document_batch
from src.core.principal import UserPrincipal
from src.models.contracts.policies import TablePolicies
from src.models.orm.tables import Table


@pytest.mark.asyncio
async def test_batch_engine_inserts_1000_rows_with_one_preflight_and_one_write(
    db_session,
):
    table = Table(
        id=uuid4(),
        name=f"batch_engine_{uuid4().hex[:8]}",
        organization_id=None,
        created_by="test@example.com",
        access=make_seed_admin_bypass(),
    )
    db_session.add(table)
    await db_session.flush()
    user = UserPrincipal(
        user_id=uuid4(),
        email="admin@example.com",
        organization_id=None,
        is_superuser=True,
        roles=["authenticated"],
    )
    statements: list[str] = []

    def capture(_conn, _cursor, statement, _params, _context, _many):
        if "documents" in statement:
            statements.append(statement)

    event.listen(db_session.sync_session.bind, "before_cursor_execute", capture)
    try:
        result = await execute_document_batch(
            db_session,
            table,
            rows=[
                BatchWriteRow(
                    index=index,
                    id=f"doc-{index:04d}",
                    data={"index": index},
                    created_by="test@example.com",
                    updated_by="test@example.com",
                )
                for index in range(1000)
            ],
            mode="insert",
            policies=TablePolicies.model_validate(make_seed_admin_bypass()),
            user=user,
        )
    finally:
        event.remove(db_session.sync_session.bind, "before_cursor_execute", capture)

    assert len(result.documents_by_id) == 1000
    assert sum("SELECT" in statement for statement in statements) == 1
    assert sum("INSERT" in statement for statement in statements) == 1
```

Add separate tests proving top-level merge, full replacement, insert conflict
errors, duplicate rejection, policy-denial atomicity, creator preservation,
updater changes, generated insert IDs, and a guarded concurrent-insert count
mismatch.

- [ ] **Step 2: Run the engine tests and confirm they fail before the module exists**

Run:

```bash
./test.sh tests/e2e/test_table_batch_write_engine.py -v
```

Expected: collection fails because `shared.table_batch_writes` is absent.

- [ ] **Step 3: Implement the engine data contract**

Create these focused types in `shared/table_batch_writes.py`:

```python
BatchWriteMode = Literal["insert", "merge_upsert", "replace_upsert"]


@dataclass(frozen=True)
class BatchWriteRow:
    index: int
    id: str
    data: dict[str, Any]
    created_by: str | None
    updated_by: str | None


@dataclass(frozen=True)
class BatchWriteError:
    index: int
    id: str
    error: str


@dataclass
class BatchWriteResult:
    documents_by_id: dict[str, Document]
    previous_by_id: dict[str, Document]
    errors: list[BatchWriteError]
```

Move the reusable row-flattening helper from the router into this module and
import it back into the router for single-document policy and event paths.

- [ ] **Step 4: Implement set-based preflight and policy evaluation**

Use one ordered, locked query for all explicit IDs:

```python
stmt = (
    select(Document)
    .where(Document.table_id == table.id, Document.id.in_(sorted(ids)))
    .order_by(Document.id)
    .with_for_update()
)
existing = {doc.id: doc for doc in (await session.execute(stmt)).scalars()}
```

Evaluate `update` against existing rows and `create` against candidates using
the already-resolved `TablePolicies` and caller. Raise an HTTP-independent
`BatchPolicyDenied(indices)` exception containing every denied submission
index. Reject duplicate request IDs with `DuplicateBatchIds(ids)` before SQL.

- [ ] **Step 5: Implement one PostgreSQL write per mode**

Build one `pg_insert(Document).values(values)` statement. For insert mode use
`on_conflict_do_nothing(index_elements=["table_id", "id"])`. For merge mode:

```python
statement = insert_stmt.on_conflict_do_update(
    index_elements=["table_id", "id"],
    set_={
        "data": Document.data.op("||")(insert_stmt.excluded.data),
        "updated_by": insert_stmt.excluded.updated_by,
        "updated_at": now,
    },
    where=Document.id.in_(existing_ids),
)
```

Replacement mode uses the same guarded statement with
`"data": insert_stmt.excluded.data`. Add `.returning(Document)` and map returned
documents by ID. In insert mode, convert non-returned explicit IDs into ordered
`BatchWriteError` entries. In upsert modes, a returned-row count mismatch raises
`ConcurrentBatchWrite` so the handler can roll back and return 409.

- [ ] **Step 6: Remove the duplicate repository bulk method**

Delete `DocumentRepository.bulk_upsert()`. Keep `get_many_for_update()` only if
another caller remains after router migration; otherwise delete it as dead code.

- [ ] **Step 7: Run the engine suite**

Run `./test.sh tests/e2e/test_table_batch_write_engine.py -v`.

Expected: every engine contract passes, including the two-statement assertion.

- [ ] **Step 8: Commit the engine slice**

```bash
git add api/shared/table_batch_writes.py api/src/routers/tables.py api/tests/e2e/test_table_batch_write_engine.py
git commit -m "refactor: unify set-based table batch writes"
```

### Task 3: Migrate the canonical handler and delete the emergency route

**Files:**
- Modify: `api/src/routers/tables.py:1246-1332,1525-1640`
- Modify: `api/tests/unit/test_table_bulk_upsert_route.py`
- Modify: `api/tests/e2e/api/test_tables_batch.py`
- Delete: `api/tests/e2e/test_table_bulk_upsert.py`

- [ ] **Step 1: Rewrite route tests to target `/documents/batch`**

Move the unique replacement-mode cases into the canonical batch suite. Each
request uses:

```python
{
    "write_mode": "replace_upsert",
    "return_documents": False,
    "documents": [
        {"id": "alpha", "data": {"replacement": True}},
        {"id": "beta", "data": {"nullable": None}},
    ],
}
```

Assert the response is:

```python
{"inserted": 2, "errors": [], "documents": []}
```

Add an OpenAPI assertion that no path ends in `/documents/bulk-upsert`. Convert
the race unit test to patch `execute_document_batch` and assert that
`ConcurrentBatchWrite` becomes HTTP 409 after rollback.

- [ ] **Step 2: Run the migrated route tests and confirm failures**

Run:

```bash
./test.sh tests/unit/test_table_bulk_upsert_route.py -v
./test.sh tests/e2e/api/test_tables_batch.py -v
```

Expected: replacement requests use old merge behavior and the removed route
still appears in OpenAPI.

- [ ] **Step 3: Replace both route implementations with one handler**

Delete `bulk_upsert_documents`. In `batch_documents`:

1. resolve the table and Solution ownership;
2. resolve policies and claims once;
3. normalize IDs and attribution into `BatchWriteRow` values;
4. call `execute_document_batch` with `body.effective_write_mode`;
5. translate `DuplicateBatchIds` to 422, `BatchPolicyDenied` to 403, and
   `ConcurrentBatchWrite` to rollback plus 409;
6. publish existing-format insert/update events for successful rows;
7. commit and return successful documents in submission order unless
   `return_documents` is false.

Construct the response without a second fetch:

```python
ordered_documents = [
    result.documents_by_id[row.id]
    for row in rows
    if row.id in result.documents_by_id
]
return DocumentBatchCreateResponse(
    inserted=len(ordered_documents),
    errors=[
        {"id": error.id, "error": error.error}
        for error in result.errors
    ],
    documents=(
        [DocumentPublic.model_validate(doc) for doc in ordered_documents]
        if body.return_documents
        else []
    ),
)
```

- [ ] **Step 4: Prove authorization, semantics, and notifications**

Extend the focused tests to cover ordinary policy-authorized replacement,
denied create/update rows, attribution, table/Solution isolation, and one
insert/update notification per successful document. Keep the existing released
merge and generated-ID assertions unchanged.

- [ ] **Step 5: Run all canonical batch route tests**

Run:

```bash
./test.sh tests/unit/test_table_bulk_upsert_route.py -v
./test.sh tests/e2e/api/test_tables_batch.py -v
./test.sh tests/e2e/platform/test_policies.py -k batch -v
```

Expected: all selected tests pass and the removed URL is absent.

- [ ] **Step 6: Commit the route consolidation**

```bash
git add api/src/routers/tables.py api/tests/unit/test_table_bulk_upsert_route.py api/tests/e2e/api/test_tables_batch.py api/tests/e2e/test_table_bulk_upsert.py
git commit -m "refactor: consolidate table batch endpoint"
```

### Task 4: Preserve the SDK while changing its transport

**Files:**
- Modify: `api/bifrost/tables.py:440-625`
- Modify: `api/tests/unit/sdk/test_sdk_tables.py:150-225`

- [ ] **Step 1: Write failing SDK transport and size tests**

Update the existing bulk test to require:

```python
client.post.assert_awaited_once_with(
    "/api/tables/customers/documents/batch?scope=global",
    json={
        "write_mode": "replace_upsert",
        "return_documents": False,
        "documents": expected_documents,
    },
)
assert result.count == 2
```

Add parameterized 1,001-row tests for `insert_batch`, `upsert_batch`, and
`bulk_upsert` which assert `ValueError("table batch writes accept at most 1000 documents")`
and verify the HTTP client was never called.

- [ ] **Step 2: Run the SDK tests and observe the old URL and missing bounds**

Run `./test.sh tests/unit/sdk/test_sdk_tables.py -v`.

Expected: the updated assertions fail.

- [ ] **Step 3: Add one SDK validation helper and migrate bulk transport**

Add and use:

```python
def _validate_batch_size(documents: list[dict[str, Any]]) -> None:
    if len(documents) > 1000:
        raise ValueError("table batch writes accept at most 1000 documents")
```

Keep released method signatures unchanged. `insert_batch()` and
`upsert_batch()` retain their current request bodies after validation.
`bulk_upsert()` sends replacement/count-only fields to `/documents/batch`,
parses `body["inserted"]`, and returns `BulkUpsertResult(count=...)`. Preserve
its one-time table auto-create and bounded 409 retry loop.

- [ ] **Step 4: Run SDK and Solution-scope contract tests**

Run:

```bash
./test.sh tests/unit/sdk/test_sdk_tables.py tests/unit/test_tables_sdk_solution_scope.py -v
```

Expected: all tests pass with no call to `/documents/bulk-upsert`.

- [ ] **Step 5: Commit the SDK migration**

```bash
git add api/bifrost/tables.py api/tests/unit/sdk/test_sdk_tables.py
git commit -m "feat: route bulk table writes through batch"
```

### Task 5: Refresh contracts and documentation

**Files:**
- Modify: `client/src/lib/v1.d.ts`
- Modify: `.claude/skills/bifrost-build/generated/openapi-digest.md`
- Modify: `.claude/skills/bifrost-build/generated/python-sdk-signatures.md`
- Modify: `plugins/bifrost/skills/bifrost-build/generated/openapi-digest.md`
- Modify: `plugins/bifrost/skills/bifrost-build/generated/python-sdk-signatures.md`
- Modify: `api/tests/unit/test_contract_version.py`
- Modify: `docs/audits/2026-09-10-large-table-memory-and-ninja-state.md`

- [ ] **Step 1: Remove documentation claims about the specialized route**

Update the September 10 audit to record that the pre-release specialized route
was superseded by canonical batch modes. Preserve the historical measurement,
but point current readers to `tables.bulk_upsert()` over `/documents/batch`.

- [ ] **Step 2: Regenerate SDK skill truth**

Run:

```bash
python api/scripts/skill-truth/generate.py
```

Expected: generated Python signatures remain stable for public methods and the
OpenAPI digest drops the specialized route.

- [ ] **Step 3: Regenerate client OpenAPI types from the worktree stack**

Run:

```bash
./debug.sh status | grep -q "Status:   UP" || ./debug.sh up
(cd client && npm run generate:types)
```

Expected: `client/src/lib/v1.d.ts` is generated from this worktree's running
API. Do not hand-edit the generated file.

- [ ] **Step 4: Resolve the contract fingerprint deliberately**

Run:

```bash
./test.sh tests/unit/test_contract_version.py tests/unit/test_skill_appendix_fresh.py tests/unit/test_codex_mirror_sync.py -v
```

The removed unreleased route and additive canonical fields do not require a
minimum released CLI bump. Refresh only `EXPECTED_CONTRACT_FINGERPRINT` using
the failure's generated value, then rerun until the three tripwires pass.

- [ ] **Step 5: Commit generated and documentation changes**

```bash
git add client/src/lib/v1.d.ts .claude/skills/bifrost-build/generated plugins/bifrost/skills/bifrost-build/generated api/tests/unit/test_contract_version.py docs/audits/2026-09-10-large-table-memory-and-ninja-state.md
git commit -m "docs: refresh canonical table batch contracts"
```

### Task 6: Verify and prepare the PR

**Files:**
- Verify all files changed by Tasks 1-5

- [ ] **Step 1: Run focused behavioral coverage**

```bash
./test.sh tests/unit/test_table_batch_contract.py tests/unit/test_table_bulk_upsert_route.py tests/unit/sdk/test_sdk_tables.py tests/unit/test_tables_sdk_solution_scope.py -v
./test.sh tests/e2e/test_table_batch_write_engine.py tests/e2e/api/test_tables_batch.py -v
./test.sh tests/e2e/platform/test_policies.py -k batch -v
```

Expected: all selected tests pass with no skip, xfail, or retry.

- [ ] **Step 2: Run API quality checks**

Run `./test.sh quality api`.

Expected: pyright reports zero errors and ruff reports all checks passed.

- [ ] **Step 3: Verify removed and retained surfaces**

```bash
rg -n "documents/bulk-upsert|DocumentBulkUpsert(Request|Response|Item)|def bulk_upsert_documents" api client .claude plugins
rg -n "async def bulk_upsert|write_mode.*replace_upsert" api/bifrost api/tests
```

Expected: the first command finds no live contract or implementation reference;
the second finds the SDK convenience method and canonical request tests.

- [ ] **Step 4: Rebase the candidate on current main if necessary**

```bash
git fetch origin main
git log --oneline HEAD..origin/main
git status --short
```

Expected: no commits are missing from `origin/main` and the worktree is clean.
If main advanced, merge `origin/main`, resolve conflicts, regenerate derived
files, commit, and rerun all focused checks.

- [ ] **Step 5: Run the exact-candidate local PR gate**

```bash
./test.sh pre-pr
```

Expected: the command prints `Local PR gate passed for <HEAD SHA>`.

- [ ] **Step 6: Open the linked PR without merging**

Push `734-batch-write-consolidation`, open a PR containing `Fixes #734`, explain
the pre-release route removal and the intentional 1,000-row bound, and include
the exact focused commands plus pre-PR candidate SHA. Watch CI and review
comments. Do not merge or deploy without explicit user authorization.
