"""Add workflow registry and data providers tables

Revision ID: 005_workflow_registry
Revises: 004_is_registered
Create Date: 2024-12-02

This migration:
- Creates 'workflows' table for workflow metadata registry
- Creates 'data_providers' table for data provider registry
- Adds discovery columns to 'forms' table (file_path, last_seen_at)
- Migrates data from 'workflow_keys' to 'workflows' table
- Note: workflow_keys table is kept for backward compatibility
  but new API keys should be created on workflows table
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '005_workflow_registry'
down_revision: Union[str, None] = '004_is_registered'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create workflows table
    op.create_table(
        'workflows',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('category', sa.String(100), nullable=False, server_default='General'),

        # File discovery metadata
        sa.Column('file_path', sa.String(1000), nullable=False),
        sa.Column('module_path', sa.String(500), nullable=True),
        sa.Column('schedule', sa.String(100), nullable=True),  # CRON expression
        sa.Column('parameters_schema', postgresql.JSONB(), nullable=False, server_default='[]'),
        sa.Column('tags', postgresql.JSONB(), nullable=False, server_default='[]'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('last_seen_at', sa.DateTime(timezone=True), nullable=True),

        # Endpoint configuration (from @workflow decorator)
        sa.Column('endpoint_enabled', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('allowed_methods', postgresql.JSONB(), nullable=False, server_default='["POST"]'),
        sa.Column('execution_mode', sa.String(20), nullable=False, server_default='sync'),

        # API key (merged from workflow_keys - one key per workflow)
        sa.Column('api_key_hash', sa.String(64), nullable=True),  # SHA-256 hash
        sa.Column('api_key_description', sa.Text(), nullable=True),
        sa.Column('api_key_enabled', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('api_key_created_by', sa.String(255), nullable=True),
        sa.Column('api_key_created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('api_key_last_used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('api_key_expires_at', sa.DateTime(timezone=True), nullable=True),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),

        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name', name='uq_workflows_name'),
    )
    op.create_index('ix_workflows_name', 'workflows', ['name'])
    op.create_index('ix_workflows_is_active', 'workflows', ['is_active'])
    op.create_index('ix_workflows_schedule', 'workflows', ['schedule'], postgresql_where=sa.text('schedule IS NOT NULL'))
    op.create_index('ix_workflows_api_key_hash', 'workflows', ['api_key_hash'], postgresql_where=sa.text('api_key_hash IS NOT NULL'))

    # Create data_providers table
    op.create_table(
        'data_providers',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('file_path', sa.String(1000), nullable=False),
        sa.Column('module_path', sa.String(500), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('last_seen_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),

        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name', name='uq_data_providers_name'),
    )
    op.create_index('ix_data_providers_name', 'data_providers', ['name'])
    op.create_index('ix_data_providers_is_active', 'data_providers', ['is_active'])

    # Add discovery columns to forms table
    op.add_column(
        'forms',
        sa.Column('file_path', sa.String(1000), nullable=True)
    )
    op.add_column(
        'forms',
        sa.Column('module_path', sa.String(500), nullable=True)
    )
    op.add_column(
        'forms',
        sa.Column('last_seen_at', sa.DateTime(timezone=True), nullable=True)
    )
    # Note: forms.is_active already exists, so we don't add it


def downgrade() -> None:
    # Remove columns from forms table
    op.drop_column('forms', 'last_seen_at')
    op.drop_column('forms', 'module_path')
    op.drop_column('forms', 'file_path')

    # Drop data_providers table
    op.drop_index('ix_data_providers_is_active', table_name='data_providers')
    op.drop_index('ix_data_providers_name', table_name='data_providers')
    op.drop_table('data_providers')

    # Drop workflows table
    op.drop_index('ix_workflows_api_key_hash', table_name='workflows')
    op.drop_index('ix_workflows_schedule', table_name='workflows')
    op.drop_index('ix_workflows_is_active', table_name='workflows')
    op.drop_index('ix_workflows_name', table_name='workflows')
    op.drop_table('workflows')
