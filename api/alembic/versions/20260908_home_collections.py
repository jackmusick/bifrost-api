"""Persist personal launcher preferences and shared collections.

Revision ID: 20260908_home_collections
Revises: 20260902_chat_run_agentless
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260908_home_collections"
down_revision = "20260902_chat_run_agentless"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "home_collections",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("owner_id", sa.UUID(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("organization_id", sa.UUID(), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True),
        sa.Column("shared", sa.Boolean(), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("icon", sa.String(50), nullable=False),
        sa.Column("resource_keys", postgresql.JSONB(), nullable=False),
    )
    op.create_index("ix_home_collections_owner_id", "home_collections", ["owner_id"])
    op.create_index("ix_home_collections_organization_id", "home_collections", ["organization_id"])
    op.create_table(
        "home_resource_preferences",
        sa.Column("user_id", sa.UUID(), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("resource_key", sa.String(50), primary_key=True),
        sa.Column("pinned", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("last_opened_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("home_resource_preferences")
    op.drop_table("home_collections")
