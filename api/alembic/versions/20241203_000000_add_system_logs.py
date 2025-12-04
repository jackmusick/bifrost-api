"""add system_logs table

Revision ID: 006_system_logs
Revises: 005_workflow_registry
Create Date: 2024-12-03

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '006_system_logs'
down_revision = '005_workflow_registry'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create system_logs table
    op.create_table(
        'system_logs',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('category', sa.String(length=50), nullable=False),
        sa.Column('level', sa.String(length=20), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('executed_by', sa.UUID(), nullable=True),
        sa.Column('executed_by_name', sa.String(length=255), nullable=False),
        sa.Column('details', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.ForeignKeyConstraint(['executed_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes for efficient querying
    op.create_index('ix_system_logs_category', 'system_logs', ['category'], unique=False)
    op.create_index('ix_system_logs_level', 'system_logs', ['level'], unique=False)
    op.create_index('ix_system_logs_timestamp', 'system_logs', ['timestamp'], unique=False)
    op.create_index('ix_system_logs_executed_by', 'system_logs', ['executed_by'], unique=False)
    op.create_index('ix_system_logs_category_timestamp', 'system_logs', ['category', 'timestamp'], unique=False)


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_system_logs_category_timestamp', table_name='system_logs')
    op.drop_index('ix_system_logs_executed_by', table_name='system_logs')
    op.drop_index('ix_system_logs_timestamp', table_name='system_logs')
    op.drop_index('ix_system_logs_level', table_name='system_logs')
    op.drop_index('ix_system_logs_category', table_name='system_logs')

    # Drop table
    op.drop_table('system_logs')
