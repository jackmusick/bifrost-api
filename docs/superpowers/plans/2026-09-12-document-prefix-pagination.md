# Document Prefix Pagination Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make document-prefix keyset pagination use bounded, selective PostgreSQL index scans under `en_US.UTF-8`, including prepared, empty, and final pages.

**Architecture:** Add a concurrent composite B-tree index on `(table_id, id COLLATE "C")`. Prefix queries will apply literal-prefix `LIKE` matching, cursor comparison, and ordering to the same C-collated expression; the prefix pattern is safely escaped and rendered as a post-compile SQL literal so PostgreSQL can derive its internal prefix bounds even when the remaining statement uses a generic prepared plan. No application string-successor is computed.

**Tech Stack:** Python 3.14, FastAPI, SQLAlchemy 2, Alembic, PostgreSQL 16, pytest.

---

### Task 1: Lock the query and migration contract with failing tests

**Files:**
- Modify: `api/tests/e2e/api-integration/test_tables.py`
- Modify: `api/tests/performance/test_table_document_id_pagination.py`
- Create: `api/tests/unit/test_document_prefix_index_migration.py`

- [ ] **Step 1: Extend document-query correctness coverage before production code**

Add literal-prefix cases for `%`, `_`, `/`, backslash, composed/decomposed Unicode, first/middle/deep/final/empty pages, a nonexistent prefix, a second logical table, policy-filter interaction, `skip_count`, and `document_ids` composition. Assert each complete traversal has exactly the expected IDs with no duplicate or missing rows.

- [ ] **Step 2: Add the failing SQL contract assertion**

Capture the prefix query and compile it with PostgreSQL `render_postcompile=True`. Assert that the escaped prefix appears as a quoted literal, `documents.id COLLATE "C"` is used for `LIKE`, cursor comparison, and `ORDER BY`, and other request/policy values remain bind parameters.

- [ ] **Step 3: Add the failing migration contract test**

Load the new migration module and assert that upgrade/downgrade use Alembic autocommit blocks with bounded lock/statement timeouts and `CREATE INDEX CONCURRENTLY` / `DROP INDEX CONCURRENTLY` for `ix_documents_table_id_id_c`.

- [ ] **Step 4: Run tests and verify RED**

Run:
```bash
./test.sh tests/e2e/api-integration/test_tables.py::TestDocumentRepositoryIntegration::test_document_prefix_literal_semantics tests/performance/test_table_document_id_pagination.py::test_document_prefix_statement_uses_c_collation_and_literal_pattern tests/unit/test_document_prefix_index_migration.py -v
```
Expected: failures because the query still uses database-default collation and a bound concatenated prefix, and the migration does not exist.

### Task 2: Implement the C-collated prefix index and query

**Files:**
- Modify: `api/src/routers/tables.py`
- Create: `api/alembic/versions/20260912_document_prefix_index.py`

- [ ] **Step 1: Add a dedicated prefix-pattern helper**

Implement a helper that escapes `/` as `//`, `%` as `/%`, and `_` as `/_`, then appends `%`. Keep Unicode and backslashes unchanged because `/` is the explicit SQL `LIKE` escape character.

- [ ] **Step 2: Build the prefix query against one collated expression**

Use `Document.id.collate("C")` for the prefix `LIKE`, cursor `>`, and document-ID pagination `ORDER BY`. Wrap the escaped pattern in `bindparam(..., type_=String(), literal_execute=True)` so the database planner sees the constant prefix without interpolating user text manually. Preserve the `document_ids`, JSON filters, policy `extra_where`, count, and non-document-ID branches unchanged.

- [ ] **Step 3: Add the concurrent index migration**

Create `ix_documents_table_id_id_c` on `(table_id, id COLLATE "C")`, based on migration head `20260909_form_logos`. Use an Alembic autocommit block, a short lock timeout, a bounded build timeout, and concurrent create/drop. Document invalid-index cleanup after an interrupted build.

- [ ] **Step 4: Run Task 1 tests and verify GREEN**

Run the exact Task 1 command. Expected: all pass.

- [ ] **Step 5: Run existing compatibility tests**

Run:
```bash
./test.sh tests/e2e/api-integration/test_tables.py::TestDocumentRepositoryIntegration::test_query_documents_by_actual_id_cursor_and_prefix tests/e2e/api-integration/test_tables.py::TestDocumentRepositoryIntegration::test_query_documents_by_actual_document_ids tests/e2e/platform/test_policies.py::TestPoliciesMatrix::test_own_row_policy_filters_document_id_keyset_query tests/performance/test_table_document_id_pagination.py::test_document_id_batch_query_uses_composite_index -v
```
Expected: all pass.

### Task 3: Prove scale, prepared-plan behavior, and operational safety

**Files:**
- Modify: `docker-compose.test.yml`
- Modify: `api/tests/performance/test_table_document_id_pagination.py`
- Create: `docs/performance/2026-09-12-document-prefix-pagination.md`
- Create: `docs/performance/2026-09-12-document-prefix-query-plans.json`

- [ ] **Step 1: Match production collation in the PostgreSQL test service**

Initialize the ephemeral test cluster with `POSTGRES_INITDB_ARGS=--locale=en_US.UTF-8` and assert the performance fixture reports `en_US.UTF-8`.

- [ ] **Step 2: Seed realistic scale efficiently**

Use set-based `generate_series` inserts for at least two million documents across multiple logical tables and tenant prefixes, with both 50-row and 20,000-row matching groups. `ANALYZE documents` after loading.

- [ ] **Step 3: Exercise all page positions with bounded plans**

Set a local 2.5-second statement timeout. Capture `EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)` for first, middle, deep, final, empty, nonexistent, wildcard-containing, and Unicode prefixes. Assert `ix_documents_table_id_id_c` is used, no relation-wide scan or relation-wide sort appears, and buffers remain bounded independently of unrelated rows. PostgreSQL may legitimately choose a bounded `Bitmap Index Scan` on `ix_documents_table_id_id_c` followed by a top-N/in-memory `Sort`; that is acceptable only when the sort is fed by bounded index output with PostgreSQL-generated lower/upper LIKE prefix bounds in `Index Cond`.

- [ ] **Step 4: Exercise a forced generic prepared plan**

Prepare a statement whose escaped prefix is literal while table ID, cursor, and limit remain parameters; set `plan_cache_mode=force_generic_plan`; execute first and final pages; assert the same index and internal lower/upper prefix bounds are present.

- [ ] **Step 5: Record reproducible before/after evidence**

Write the commands, dataset, collation, PostgreSQL version, latency, buffer counts, index sizes, plan summaries, rollout order, invalid-index recovery, downgrade behavior, mixed-version pagination caveat, and remaining limitations. Store machine-readable representative plans in the JSON artifact. Do not query or mutate production.

- [ ] **Step 6: Run scoped verification**

Run:
```bash
./test.sh stack down
./test.sh stack up
./test.sh tests/performance/test_table_document_id_pagination.py -v
./test.sh tests/e2e/api-integration/test_tables.py tests/e2e/platform/test_policies.py -v
./test.sh quality api
```
Expected: all selected tests and API quality checks pass.

### Task 4: Final candidate and PR

**Files:**
- Review all files changed above.

- [ ] **Step 1: Rebase safety check**

Fetch `origin/main`, verify the branch contains it, and resolve any migration-head drift before finalizing.

- [ ] **Step 2: Commit the exact candidate and run the broad gate**

Run:
```bash
./test.sh pre-pr
```
Expected: pass for a clean `HEAD`; record the SHA emitted by the gate.

- [ ] **Step 3: Open the PR**

Include `Fixes #731`, root cause, query/index semantics, prepared-plan evidence, migration size/load/locking behavior, deployment/rollback instructions, exact targeted checks, pre-PR SHA, and an explicit statement that the SharePoint campaign remains on hold.
