"""add_oauth_provider_missing_columns

Revision ID: a756d691f8a5
Revises: c297e89e018d
Create Date: 2025-12-05 03:45:19.013631+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a756d691f8a5'
down_revision: Union[str, None] = 'c297e89e018d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add missing columns to oauth_providers table
    # These are defined in the ORM but were missing from the initial migration
    op.add_column(
        'oauth_providers',
        sa.Column('status_message', sa.Text(), nullable=True)
    )
    op.add_column(
        'oauth_providers',
        sa.Column('last_token_refresh', sa.DateTime(timezone=True), nullable=True)
    )


def downgrade() -> None:
    op.drop_column('oauth_providers', 'last_token_refresh')
    op.drop_column('oauth_providers', 'status_message')
