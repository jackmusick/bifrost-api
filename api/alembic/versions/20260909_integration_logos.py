"""Add descriptions and uploaded logos for integrations.

Revision ID: 20260909_integration_logos
Revises: 20260908_home_collections
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260909_integration_logos"
down_revision = "20260908_home_collections"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("integrations", sa.Column("description", sa.Text(), nullable=True))
    op.add_column("integrations", sa.Column("logo_data", sa.LargeBinary(), nullable=True))
    op.add_column(
        "integrations",
        sa.Column("logo_content_type", sa.String(length=50), nullable=True),
    )
    op.add_column(
        "integrations",
        sa.Column("logo_thumbnail_data", sa.LargeBinary(), nullable=True),
    )
    op.add_column(
        "integrations",
        sa.Column("logo_thumbnail_content_type", sa.String(length=50), nullable=True),
    )
    op.add_column(
        "integrations",
        sa.Column("logo_thumbnail_version", sa.String(length=64), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("integrations", "logo_thumbnail_version")
    op.drop_column("integrations", "logo_thumbnail_content_type")
    op.drop_column("integrations", "logo_thumbnail_data")
    op.drop_column("integrations", "logo_content_type")
    op.drop_column("integrations", "logo_data")
    op.drop_column("integrations", "description")
