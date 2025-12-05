"""Add execution metrics columns

Revision ID: 20251205_130000
Revises: 20251205_034519
Create Date: 2025-12-05

Adds resource metrics columns to executions table:
- peak_memory_bytes: Peak RSS memory usage in bytes
- cpu_user_seconds: User-mode CPU time
- cpu_system_seconds: Kernel-mode CPU time
- cpu_total_seconds: Total CPU time (user + system)

These metrics are captured from worker processes during execution
and can be used for:
- Performance analysis
- Resource usage dashboards
- Billing based on compute usage
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "add_execution_metrics"
down_revision = "a756d691f8a5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add resource metrics columns to executions table
    op.add_column(
        "executions",
        sa.Column("peak_memory_bytes", sa.BigInteger(), nullable=True),
    )
    op.add_column(
        "executions",
        sa.Column("cpu_user_seconds", sa.Float(), nullable=True),
    )
    op.add_column(
        "executions",
        sa.Column("cpu_system_seconds", sa.Float(), nullable=True),
    )
    op.add_column(
        "executions",
        sa.Column("cpu_total_seconds", sa.Float(), nullable=True),
    )

    # Create index for querying by resource usage (useful for dashboards)
    op.create_index(
        "ix_executions_peak_memory",
        "executions",
        ["peak_memory_bytes"],
        postgresql_where=sa.text("peak_memory_bytes IS NOT NULL"),
    )
    op.create_index(
        "ix_executions_cpu_total",
        "executions",
        ["cpu_total_seconds"],
        postgresql_where=sa.text("cpu_total_seconds IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("ix_executions_cpu_total", table_name="executions")
    op.drop_index("ix_executions_peak_memory", table_name="executions")
    op.drop_column("executions", "cpu_total_seconds")
    op.drop_column("executions", "cpu_system_seconds")
    op.drop_column("executions", "cpu_user_seconds")
    op.drop_column("executions", "peak_memory_bytes")
