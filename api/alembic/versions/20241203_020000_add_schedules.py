"""add schedules table

Revision ID: 007_schedules
Revises: 006_system_logs
Create Date: 2024-12-03

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '007_schedules'
down_revision = '006_system_logs'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create schedules table
    op.create_table(
        'schedules',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('organization_id', sa.UUID(), nullable=True),
        sa.Column('workflow_name', sa.String(length=255), nullable=False),
        sa.Column('cron_expression', sa.String(length=100), nullable=False),
        sa.Column('parameters', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('created_by', sa.UUID(), nullable=True),
        sa.Column('last_run_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes for efficient querying
    op.create_index('ix_schedules_organization_id', 'schedules', ['organization_id'], unique=False)
    op.create_index('ix_schedules_workflow_name', 'schedules', ['workflow_name'], unique=False)
    op.create_index('ix_schedules_enabled', 'schedules', ['enabled'], unique=False)
    op.create_index('ix_schedules_enabled_org', 'schedules', ['enabled', 'organization_id'], unique=False)


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_schedules_enabled_org', table_name='schedules')
    op.drop_index('ix_schedules_enabled', table_name='schedules')
    op.drop_index('ix_schedules_workflow_name', table_name='schedules')
    op.drop_index('ix_schedules_organization_id', table_name='schedules')

    # Drop table
    op.drop_table('schedules')
