"""Add a C-collated index for document ID prefix scans.

Revision ID: 20260912_document_prefix_index
Revises: 20260909_form_logos

Document-ID prefix pages intentionally use two predicates: a C-collated lower
bound to seek into the target table/prefix region and a literal LIKE check to
keep the result at the exact prefix boundary. This index must be deployed
before the query code that depends on it so PostgreSQL can satisfy both the
prefix bounds and cursor seek selectively. PostgreSQL may scan it in order or
choose a bounded bitmap scan followed by a small sort.

The index is created concurrently so normal DML remains available while
PostgreSQL performs its two table scans. Lock acquisition is bounded to 5s and
the build itself is bounded to 30min; if a failed concurrent build leaves an
invalid index behind, clean it up with:

    DROP INDEX CONCURRENTLY IF EXISTS ix_documents_table_id_id_c;
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260912_document_prefix_index"
down_revision: str | None = "20260909_form_logos"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.get_context().autocommit_block():
        try:
            op.execute("SET lock_timeout = '5s'")
            op.execute("SET statement_timeout = '30min'")
            op.execute(
                'CREATE INDEX CONCURRENTLY ix_documents_table_id_id_c '
                'ON documents (table_id, (id COLLATE "C"))'
            )
        finally:
            op.execute("RESET statement_timeout")
            op.execute("RESET lock_timeout")


def downgrade() -> None:
    with op.get_context().autocommit_block():
        try:
            op.execute("SET lock_timeout = '5s'")
            op.execute("SET statement_timeout = '30min'")
            op.execute(
                "DROP INDEX CONCURRENTLY IF EXISTS ix_documents_table_id_id_c"
            )
        finally:
            op.execute("RESET statement_timeout")
            op.execute("RESET lock_timeout")
