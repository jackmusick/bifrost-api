"""create_system_configs_table

Revision ID: 0e1572bff775
Revises: de187ff08713
Create Date: 2025-12-05 00:47:01.486884+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0e1572bff775'
down_revision: Union[str, None] = 'de187ff08713'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create system_configs table
    op.create_table(
        'system_configs',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('category', sa.String(length=50), nullable=False),
        sa.Column('key', sa.String(length=100), nullable=False),
        sa.Column('value_json', sa.JSON(), nullable=True),
        sa.Column('value_bytes', sa.LargeBinary(), nullable=True),
        sa.Column('organization_id', sa.UUID(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('created_by', sa.String(length=255), nullable=True),
        sa.Column('updated_by', sa.String(length=255), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('category', 'key', 'organization_id', name='uq_system_config_category_key_org')
    )

    # Create indexes for common queries
    op.create_index('ix_system_configs_category', 'system_configs', ['category'])
    op.create_index('ix_system_configs_category_key', 'system_configs', ['category', 'key'])
    op.create_index('ix_system_configs_org_id', 'system_configs', ['organization_id'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_system_configs_org_id', table_name='system_configs')
    op.drop_index('ix_system_configs_category_key', table_name='system_configs')
    op.drop_index('ix_system_configs_category', table_name='system_configs')

    # Drop table
    op.drop_table('system_configs')
