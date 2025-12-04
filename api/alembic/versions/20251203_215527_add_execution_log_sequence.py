"""add execution log sequence

Revision ID: 009_execution_log_sequence
Revises: 008_branding
Create Date: 2025-12-04 02:45:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '009_execution_log_sequence'
down_revision = '008_branding'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add sequence column to execution_logs
    op.add_column('execution_logs', sa.Column('sequence', sa.Integer(), nullable=False, server_default='0'))
    
    # Create index for efficient ordering
    op.create_index('ix_execution_logs_exec_seq', 'execution_logs', ['execution_id', 'sequence'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_execution_logs_exec_seq', table_name='execution_logs')
    op.drop_column('execution_logs', 'sequence')
