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
- Same-table unrelated documents: `1,600,000` under UUID-shaped non-target prefixes
- Other-table unrelated documents: `400,000` across `8` logical tables at `50,000` documents each
- Large table total: `1,620,024` documents, including `20,000` under `11111111-1111-4111-8111-111111111111|drive|`
- Small target group: `50` documents
- Escaped/Unicode target rows: literal `%`, `_`, `/`, backslash, composed
  `U+00E9`, and decomposed `e + U+0301`
- Index sizes after load: `documents_pkey=320 MB`, `ix_documents_table_id_id_c=320 MB`

The representative machine-readable plan artifact is
`docs/performance/2026-09-12-document-prefix-query-plans.json`.

## Measured Plans

Each representative query used the actual app shape: `table_id = ?`,
`id COLLATE "C" >= prefix`, literal escaped `LIKE ... ESCAPE '/'`, optional
`id COLLATE "C" > cursor`, `ORDER BY id COLLATE "C"`, and `LIMIT`.
`SET LOCAL statement_timeout = '2500ms'` bounded every `EXPLAIN ANALYZE`.

| Page | Rows | Time | Shared blocks | Plan |
| --- | ---: | ---: | ---: | --- |
| First 20k prefix page | 500 | 10.901 ms | 735 | Bitmap Index Scan on `ix_documents_table_id_id_c` -> Bitmap Heap Scan -> top-N Sort |
| Deep page after `item-19499` | 500 | 0.540 ms | 26 | Bitmap Index Scan on `ix_documents_table_id_id_c` -> Bitmap Heap Scan -> Sort |
| Final empty page after `item-19999` | 0 | 0.055 ms | 7 | Bitmap Index Scan on `ix_documents_table_id_id_c` -> Bitmap Heap Scan -> Sort |

The first page locally chose a bounded bitmap scan plus top-N sort. Earlier
cold-cache runs observed the same shape around 11-19 ms and about 726 root
shared blocks. This is a legitimate PostgreSQL cost choice, not a regression:
the index condition still contains the app lower bound and PostgreSQL's
internally generated LIKE range bounds, for example
`id >= '11111111-1111-4111-8111-111111111111|drive|'` and
`id < '11111111-1111-4111-8111-111111111111|drive}'`.

## Local Old-Shape Comparison

On the same `en_US.UTF-8` dataset, bounded `EXPLAIN ANALYZE` was also captured
for the old query shape: database-default `id >= ...`, escaped `LIKE`, optional
database-default cursor, and database-default `ORDER BY id`, without the
C-collated expression contract in the app query.

| Page | Old time / blocks | Fixed time / blocks | Local plan difference |
| --- | ---: | ---: | --- |
| First 20k prefix page | 40.879 ms / 735 | 10.901 ms / 735 | both bounded bitmap paths; fixed avoids default-collation comparison work |
| Deep page after `item-19499` | 28.165 ms / 735 | 0.540 ms / 26 | old cursor remained a filter over 20k rows; fixed cursor is in the C index condition |
| Final empty page after `item-19999` | 33.291 ms / 735 | 0.055 ms / 7 | old cursor filtered all 20k rows; fixed proves empty through the index range |

The old-plan ratio is local. These old-shape measurements run after the new
index exists, so PostgreSQL can still use `ix_documents_table_id_id_c` for
compatible prefix bounds. The production original was EXPLAIN-only evidence,
not an `EXPLAIN ANALYZE` run against production.

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
- no relation-wide scan or relation-wide sort appears;
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
- Avoid mixed-version page sequences. Old app pods order and compare using the
  database-default `en_US` collation, while new app pods use `COLLATE "C"` for
  prefix, cursor, and ordering. Switching versions mid-traversal can miss or
  repeat rows across cursor pages. Drain/pause long scans during rollout or
  route a traversal consistently to one app version.
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
