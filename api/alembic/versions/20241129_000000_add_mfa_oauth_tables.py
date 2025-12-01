"""Add MFA and OAuth tables

Revision ID: 002_mfa_oauth
Revises: 001_initial
Create Date: 2024-11-29

This migration adds:
- MFA fields to users table
- user_mfa_methods table for TOTP enrollment
- mfa_recovery_codes table for backup codes
- trusted_devices table for MFA bypass
- user_oauth_accounts table for SSO linking
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '002_mfa_oauth'
down_revision: Union[str, None] = '001_initial'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create MFA enum types (PostgreSQL doesn't support IF NOT EXISTS for CREATE TYPE)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE mfa_method_type AS ENUM ('totp', 'sms', 'email', 'webauthn');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE mfa_method_status AS ENUM ('pending', 'active', 'disabled');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)

    # Add MFA columns to users table
    op.add_column(
        'users',
        sa.Column('mfa_enabled', sa.Boolean(), nullable=False, server_default='false')
    )
    op.add_column(
        'users',
        sa.Column(
            'mfa_enforced_at',
            sa.DateTime(timezone=True),
            nullable=True,
            comment='When MFA was enforced by admin (NULL = not enforced)'
        )
    )

    # Create user_mfa_methods table
    op.create_table(
        'user_mfa_methods',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            'method_type',
            postgresql.ENUM('totp', 'sms', 'email', 'webauthn', name='mfa_method_type', create_type=False),
            nullable=False
        ),
        sa.Column(
            'status',
            postgresql.ENUM('pending', 'active', 'disabled', name='mfa_method_status', create_type=False),
            nullable=False,
            server_default='pending'
        ),
        sa.Column('encrypted_secret', sa.Text(), nullable=True),
        sa.Column('mfa_metadata', postgresql.JSONB(), nullable=False, server_default='{}'),
        sa.Column('last_used_counter', sa.Integer(), nullable=True),
        sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('verified_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_user_mfa_methods_user_id', 'user_mfa_methods', ['user_id'])
    op.create_index('ix_user_mfa_methods_user_status', 'user_mfa_methods', ['user_id', 'status'])

    # Create mfa_recovery_codes table
    op.create_table(
        'mfa_recovery_codes',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('code_hash', sa.String(255), nullable=False),
        sa.Column('is_used', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('used_from_ip', sa.String(45), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_mfa_recovery_codes_user_id', 'mfa_recovery_codes', ['user_id'])
    op.create_index('ix_mfa_recovery_codes_user_unused', 'mfa_recovery_codes', ['user_id', 'is_used'])

    # Create trusted_devices table
    op.create_table(
        'trusted_devices',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('device_fingerprint', sa.String(64), nullable=False),
        sa.Column('device_name', sa.String(255), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_ip_address', sa.String(45), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_trusted_devices_user_id', 'trusted_devices', ['user_id'])
    op.create_index(
        'ix_trusted_devices_fingerprint',
        'trusted_devices',
        ['user_id', 'device_fingerprint'],
        unique=True
    )

    # Create user_oauth_accounts table
    op.create_table(
        'user_oauth_accounts',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('provider_id', sa.String(50), nullable=False),
        sa.Column('provider_user_id', sa.String(255), nullable=False),
        sa.Column('email', sa.String(320), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('last_login', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(
        'ix_user_oauth_provider_user',
        'user_oauth_accounts',
        ['provider_id', 'provider_user_id'],
        unique=True
    )
    op.create_index('ix_user_oauth_user', 'user_oauth_accounts', ['user_id'])


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_table('user_oauth_accounts')
    op.drop_table('trusted_devices')
    op.drop_table('mfa_recovery_codes')
    op.drop_table('user_mfa_methods')

    # Remove MFA columns from users
    op.drop_column('users', 'mfa_enforced_at')
    op.drop_column('users', 'mfa_enabled')

    # Drop enum types
    op.execute("DROP TYPE IF EXISTS mfa_method_status")
    op.execute("DROP TYPE IF EXISTS mfa_method_type")
