"""add global branding table

Revision ID: 008_branding
Revises: 007_schedules
Create Date: 2024-12-03

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '008_branding'
down_revision = '007_schedules'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create branding table (global, no org_id)
    op.create_table(
        'branding',
        sa.Column('id', sa.UUID(), nullable=False),
        # Square logo (favicon, profile pics, etc.)
        sa.Column('square_logo_data', sa.LargeBinary(), nullable=True),
        sa.Column('square_logo_content_type', sa.String(length=50), nullable=True),
        # Rectangle logo (headers, main branding, etc.)
        sa.Column('rectangle_logo_data', sa.LargeBinary(), nullable=True),
        sa.Column('rectangle_logo_content_type', sa.String(length=50), nullable=True),
        sa.Column('primary_color', sa.String(length=7), nullable=True),
        sa.Column('secondary_color', sa.String(length=7), nullable=True),
        sa.Column('custom_css', sa.Text(), nullable=True),
        sa.Column('font_family', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    # Drop table
    op.drop_table('branding')
