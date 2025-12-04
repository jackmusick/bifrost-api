"""simplify branding table

Revision ID: 010_simplify_branding
Revises: 009_execution_log_sequence
Create Date: 2024-12-04

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '010_simplify_branding'
down_revision = '009_execution_log_sequence'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop unnecessary columns from branding table
    op.drop_column('branding', 'secondary_color')
    op.drop_column('branding', 'custom_css')
    op.drop_column('branding', 'font_family')


def downgrade() -> None:
    # Re-add columns if needed to rollback
    op.add_column('branding', sa.Column('secondary_color', sa.String(length=7), nullable=True))
    op.add_column('branding', sa.Column('custom_css', sa.Text(), nullable=True))
    op.add_column('branding', sa.Column('font_family', sa.String(length=255), nullable=True))
