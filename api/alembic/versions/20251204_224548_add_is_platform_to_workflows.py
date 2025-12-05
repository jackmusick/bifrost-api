"""add_is_platform_to_workflows

Revision ID: de187ff08713
Revises: 010_drop_workflow_keys
Create Date: 2025-12-04 22:45:48.867920+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'de187ff08713'
down_revision: Union[str, None] = '010_drop_workflow_keys'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add is_platform column (default False for user workspace workflows)
    op.add_column(
        'workflows',
        sa.Column('is_platform', sa.Boolean(), nullable=False, server_default='false')
    )

    # Create index for faster filtering
    op.create_index(
        'ix_workflows_is_platform',
        'workflows',
        ['is_platform']
    )


def downgrade() -> None:
    # Drop index first
    op.drop_index('ix_workflows_is_platform', table_name='workflows')

    # Drop column
    op.drop_column('workflows', 'is_platform')
