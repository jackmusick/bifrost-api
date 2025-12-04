"""simplify branding table

Revision ID: 009_simplify_branding
Revises: 008_branding
Create Date: 2024-12-04

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '009_simplify_branding'
down_revision = '008_branding'
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
