"""Add execution variables column and remove blob flag

Revision ID: 003_exec_variables
Revises: 002_mfa_oauth
Create Date: 2024-11-30

This migration:
- Adds 'variables' JSONB column to executions table for runtime variables
- Removes 'result_in_blob' column (no longer using blob storage)
- Adds 'input_data' column alias for 'parameters' (API compatibility)
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '003_exec_variables'
down_revision: Union[str, None] = '002_mfa_oauth'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add variables JSONB column for storing runtime variables from execution scope
    op.add_column(
        'executions',
        sa.Column(
            'variables',
            postgresql.JSONB(),
            nullable=True,
            comment='Runtime variables captured from execution scope'
        )
    )

    # Remove result_in_blob column - we no longer use blob storage
    op.drop_column('executions', 'result_in_blob')


def downgrade() -> None:
    # Re-add result_in_blob column
    op.add_column(
        'executions',
        sa.Column(
            'result_in_blob',
            sa.Boolean(),
            nullable=False,
            server_default='false',
            comment='True if result is stored in blob storage'
        )
    )

    # Remove variables column
    op.drop_column('executions', 'variables')
