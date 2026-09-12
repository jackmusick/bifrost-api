"""Add uploaded logos for forms.

Revision ID: 20260909_form_logos
Revises: 20260909_integration_logos
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260909_form_logos"
down_revision = "20260909_integration_logos"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("forms", sa.Column("logo_data", sa.LargeBinary(), nullable=True))
    op.add_column("forms", sa.Column("logo_content_type", sa.String(length=50), nullable=True))
    op.add_column("forms", sa.Column("logo_thumbnail_data", sa.LargeBinary(), nullable=True))
    op.add_column(
        "forms",
        sa.Column("logo_thumbnail_content_type", sa.String(length=50), nullable=True),
    )
    op.add_column("forms", sa.Column("logo_thumbnail_version", sa.String(length=64), nullable=True))


def downgrade() -> None:
    op.drop_column("forms", "logo_thumbnail_version")
    op.drop_column("forms", "logo_thumbnail_content_type")
    op.drop_column("forms", "logo_thumbnail_data")
    op.drop_column("forms", "logo_content_type")
    op.drop_column("forms", "logo_data")
