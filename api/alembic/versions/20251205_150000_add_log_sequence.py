"""Add sequence column to execution_logs

Revision ID: add_log_sequence
Revises: add_platform_metrics
Create Date: 2025-12-05

Adds a sequence column to execution_logs for guaranteed ordering.
Timestamps alone don't guarantee order when multiple logs have the same timestamp.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "add_log_sequence"
down_revision = "add_platform_metrics"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add sequence column with default 0
    op.add_column(
        "execution_logs",
        sa.Column("sequence", sa.Integer(), server_default="0", nullable=False),
    )

    # Create index for efficient ordered queries
    op.create_index(
        "ix_execution_logs_exec_seq",
        "execution_logs",
        ["execution_id", "sequence"],
    )

    # Drop old timestamp-based index (optional, but we're replacing it)
    op.drop_index("ix_execution_logs_exec_time", table_name="execution_logs")


def downgrade() -> None:
    # Recreate old index
    op.create_index(
        "ix_execution_logs_exec_time",
        "execution_logs",
        ["execution_id", "timestamp"],
    )

    # Drop new index
    op.drop_index("ix_execution_logs_exec_seq", table_name="execution_logs")

    # Drop sequence column
    op.drop_column("execution_logs", "sequence")
