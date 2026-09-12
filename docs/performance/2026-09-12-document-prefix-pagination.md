# Document Prefix Pagination Performance Evidence

Date: 2026-09-12

This captures local evidence for document ID prefix pagination after adding the
`ix_documents_table_id_id_c` expression index on `(table_id, id COLLATE "C")`.
The goal is selective indexed work bounded by the requested logical table and
document ID prefix, independent of unrelated documents.

## Dataset And Environment

- Test stack project: `bifrost-test-93ff02f4`
- PostgreSQL: `16.13 (Debian 16.13-1.pgdg12+1)`
- Locale: `lc_collate=en_US.UTF-8`, `lc_ctype=en_US.UTF-8`
- Unrelated documents: `2,000,000`
- Unrelated logical tables: `8` at `250,000` documents each
- Large target group: `20,024` documents, including `20,000` under `tenant-03|drive|`
- Small target group: `50` documents
- Escaped/Unicode target rows: literal `%`, `_`, `/`, backslash, composed
  `U+00E9`, and decomposed `e + U+0301`
- Index sizes after load: `documents_pkey=266 MB`, `ix_documents_table_id_id_c=266 MB`

The representative machine-readable plan artifact is
`docs/performance/2026-09-12-document-prefix-pagination-plans.json`.

## Measured Plans

Each representative query used the actual app shape: `table_id = ?`,
`id COLLATE "C" >= prefix`, literal escaped `LIKE ... ESCAPE '/'`, optional
`id COLLATE "C" > cursor`, `ORDER BY id COLLATE "C"`, and `LIMIT`.
`SET LOCAL statement_timeout = '2500ms'` bounded every `EXPLAIN ANALYZE`.

| Page | Rows | Time | Shared blocks | Plan |
| --- | ---: | ---: | ---: | --- |
| First 20k prefix page | 500 | 10.328 ms | 599 | Bitmap Index Scan on `ix_documents_table_id_id_c` -> Bitmap Heap Scan -> top-N Sort |
| Deep page after `item-19499` | 500 | 0.430 ms | 22 | Bitmap Index Scan on `ix_documents_table_id_id_c` -> Bitmap Heap Scan -> Sort |
| Final empty page after `item-19999` | 0 | 0.075 ms | 7 | Bitmap Index Scan on `ix_documents_table_id_id_c` -> Bitmap Heap Scan -> Sort |

The first page locally chose a bounded bitmap scan plus top-N sort. Earlier
cold-cache runs observed the same shape around 11-19 ms and about 726 root
shared blocks. This is a legitimate PostgreSQL cost choice, not a regression:
the index condition still contains the app lower bound and PostgreSQL's
internally generated LIKE range bounds, for example
`id >= 'tenant-03|drive|'` and `id < 'tenant-03|drive}'`.

As a research-only diagnostic, `SET enable_bitmapscan=off` on the deep-page
query produced an ordered `Index Scan` on `ix_documents_table_id_id_c` at
0.216 ms and 19 shared blocks. That setting is not shipped and is not required
for correctness; it only confirms that the C-collated index can provide ordered
access when the planner chooses that path.

## Assertions In The Performance Test

The performance test verifies:

- the ephemeral test database was initialized with the `en_US` UTF-8 locale;
- a complete traversal of the 20k group returns exactly the expected IDs, with
  no duplicates or missing rows;
- a 50-row target group also paginates completely and correctly;
- first, middle, deep, final-empty, nonexistent, escaped wildcard, backslash,
  and composed/decomposed Unicode prefix cases return correct page sizes;
- representative plans use `ix_documents_table_id_id_c`;
- no `Seq Scan` or `Gather Merge` appears;
- if `Sort` appears, it must be fed by a bounded `Bitmap Index Scan` on
  `ix_documents_table_id_id_c`;
- shared blocks and index rows remain bounded by the target prefix, not by the
  2,000,000 unrelated rows.

## PostgreSQL Rationale

PostgreSQL documents that a constant, beginning-anchored `LIKE` pattern can use
a B-tree index, and that B-tree indexes can return data in sorted order, though
that is not always cheaper than a scan plus sort:
https://www.postgresql.org/docs/current/indexes-types.html

PostgreSQL also documents why bitmap plans can require a separate sort: bitmap
heap scans visit table rows in physical order, so original index ordering is
lost when the query has `ORDER BY`:
https://www.postgresql.org/docs/current/indexes-bitmap-scans.html

For deployment, PostgreSQL's `CREATE INDEX CONCURRENTLY` documentation is the
operational reference. Concurrent builds avoid locks that block inserts,
updates, and deletes, but they perform two table scans, wait around those scans,
cannot run inside a transaction block, and can leave an invalid index after
failure. The documented recovery is to drop the invalid index and retry:
https://www.postgresql.org/docs/current/sql-createindex.html

## Deployment Notes

- Deploy the index migration before deploying app code that depends on it.
- Use the migration's bounded timeouts; the build statement timeout is 30
  minutes.
- If a concurrent index build is interrupted, check for an invalid
  `ix_documents_table_id_id_c` and drop it before retrying.
- Roll back app code before rolling back the index. The old app code can run
  with the extra index; new app code without the index can regress to expensive
  prefix scans.
- Mixed-version in-flight pagination may observe different physical query plans
  across page requests. Cursor semantics remain based on document ID order, but
  deploy during a low-traffic window if users are running very long table scans.
- Do not change planner GUCs in production for this feature. The
  `enable_bitmapscan=off` measurement was diagnostic only.

## Limitations

- Local measurements use the Dockerized test stack, not production hardware or
  production cache state.
- The dataset intentionally stresses unrelated rows and target-prefix selectivity
  but does not model every tenant's document ID distribution.
- PostgreSQL may choose either ordered index scan or bounded bitmap-plus-sort as
  costs change. The invariant is bounded indexed work, not "no Sort" in every
  valid plan.

## SharePoint Campaign Hold

No SharePoint production system or SharePoint repository was touched. Keep any
SharePoint campaign or production rollout on hold until the index migration has
landed, the app deployment is sequenced after it, and the relevant production
tenant data distribution has been reviewed.
