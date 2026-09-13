"""Add SDK provenance columns to applications.

Revision ID: 20260912_app_sdk_provenance
Revises: 20260912_document_prefix_index
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260912_app_sdk_provenance"
down_revision: str | None = "20260912_document_prefix_index"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "applications",
        sa.Column("sdk_package_version", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "applications",
        sa.Column("sdk_fingerprint", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "applications",
        sa.Column("sdk_contract_version", sa.Integer(), nullable=True),
    )
    op.add_column(
        "applications",
        sa.Column("sdk_built_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("applications", "sdk_built_at")
    op.drop_column("applications", "sdk_contract_version")
    op.drop_column("applications", "sdk_fingerprint")
    op.drop_column("applications", "sdk_package_version")
