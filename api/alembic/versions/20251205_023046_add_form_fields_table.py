"""add_form_fields_table

Revision ID: c297e89e018d
Revises: 0e1572bff775
Create Date: 2025-12-05 02:30:46.904200+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID, ARRAY


# revision identifiers, used by Alembic.
revision: str = 'c297e89e018d'
down_revision: Union[str, None] = '0e1572bff775'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create form_fields table
    op.create_table(
        'form_fields',
        sa.Column('id', UUID, primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('form_id', UUID, sa.ForeignKey('forms.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('label', sa.String(200), nullable=True),
        sa.Column('type', sa.String(50), nullable=False),
        sa.Column('required', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('position', sa.Integer, nullable=False),

        # Optional field properties
        sa.Column('placeholder', sa.String(500), nullable=True),
        sa.Column('help_text', sa.Text, nullable=True),
        sa.Column('default_value', JSONB, nullable=True),

        # For select/radio fields
        sa.Column('options', JSONB, nullable=True),

        # For data provider integration
        sa.Column('data_provider', sa.String(100), nullable=True),
        sa.Column('data_provider_inputs', JSONB, nullable=True),

        # Advanced features
        sa.Column('visibility_expression', sa.Text, nullable=True),
        sa.Column('validation', JSONB, nullable=True),

        # For file fields
        sa.Column('allowed_types', ARRAY(sa.Text), nullable=True),
        sa.Column('multiple', sa.Boolean, nullable=True),
        sa.Column('max_size_mb', sa.Integer, nullable=True),

        # For markdown/html fields
        sa.Column('content', sa.Text, nullable=True),

        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.text('NOW()')),

        sa.UniqueConstraint('form_id', 'name', name='form_fields_form_id_name_key')
    )

    # Create indexes
    op.create_index('idx_form_fields_form_id', 'form_fields', ['form_id'])
    op.create_index('idx_form_fields_position', 'form_fields', ['form_id', 'position'])

    # Drop the old form_schema JSONB column - we're going full relational
    op.drop_column('forms', 'form_schema')


def downgrade() -> None:
    # Recreate form_schema column
    op.add_column('forms', sa.Column('form_schema', JSONB, nullable=True))

    # Drop form_fields table and indexes
    op.drop_index('idx_form_fields_position', 'form_fields')
    op.drop_index('idx_form_fields_form_id', 'form_fields')
    op.drop_table('form_fields')
