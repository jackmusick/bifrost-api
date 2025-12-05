"""Drop workflow_keys table

Revision ID: 010_drop_workflow_keys
Revises: 009_simplify_branding
Create Date: 2024-12-04

Consolidates workflow API keys into the workflows table.
The workflow_keys table is no longer needed as each workflow now has
api_key_* columns directly on the workflows table.
"""
from alembic import op


# revision identifiers
revision = '010_drop_workflow_keys'
down_revision = '009_simplify_branding'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Drop the workflow_keys table."""
    # Drop the table and its indexes
    op.drop_table('workflow_keys')


def downgrade() -> None:
    """
    Recreate workflow_keys table (data will be lost).

    Note: This is provided for rollback capability but does not restore data.
    """
    # Import required types
    import sqlalchemy as sa
    from sqlalchemy.dialects import postgresql

    # Recreate the table structure
    op.create_table(
        'workflow_keys',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('workflow_name', sa.String(length=255), nullable=True),
        sa.Column('hashed_key', sa.String(length=64), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_by', sa.String(length=255), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('last_used_at', sa.DateTime(), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('revoked', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('revoked_at', sa.DateTime(), nullable=True),
        sa.Column('revoked_by', sa.String(length=255), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    # Recreate indexes
    op.create_index('ix_workflow_keys_hashed', 'workflow_keys', ['hashed_key'])
    op.create_index('ix_workflow_keys_workflow', 'workflow_keys', ['workflow_name'])
