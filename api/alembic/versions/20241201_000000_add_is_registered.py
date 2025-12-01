"""Add is_registered column to users table

Revision ID: 004_is_registered
Revises: 003_exec_variables
Create Date: 2024-12-01

This migration:
- Adds 'is_registered' boolean column to users table
- Used to track admin-created users who haven't completed registration
- Default is True (existing users are considered registered)
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '004_is_registered'
down_revision: Union[str, None] = '003_exec_variables'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add is_registered column with default True (existing users are registered)
    op.add_column(
        'users',
        sa.Column(
            'is_registered',
            sa.Boolean(),
            nullable=False,
            server_default='true',
            comment='False for admin-created users who haven\'t completed registration'
        )
    )


def downgrade() -> None:
    op.drop_column('users', 'is_registered')
