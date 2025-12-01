"""
SQLAlchemy ORM Models for Bifrost

Pure database models using SQLAlchemy 2.0 declarative style.
These models define the database schema and relationships.

For API schemas (Create/Update/Public), see schemas.py
"""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum as SQLAlchemyEnum,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from src.models.enums import (
    ConfigType,
    ExecutionStatus,
    FormAccessLevel,
    MFAMethodStatus,
    MFAMethodType,
    UserType,
)

if TYPE_CHECKING:
    pass


class Base(DeclarativeBase):
    """Base class for all ORM models."""
    pass


# =============================================================================
# Organization
# =============================================================================


class Organization(Base):
    """Organization database table."""
    __tablename__ = "organizations"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(255))
    domain: Mapped[str | None] = mapped_column(String(255), default=None)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    settings: Mapped[dict] = mapped_column(JSONB, default={})
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, server_default=text("NOW()")
    )
    created_by: Mapped[str] = mapped_column(String(255))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, server_default=text("NOW()"),
        onupdate=datetime.utcnow
    )

    # Relationships
    users: Mapped[list["User"]] = relationship(back_populates="organization")
    forms: Mapped[list["Form"]] = relationship(back_populates="organization")
    executions: Mapped[list["Execution"]] = relationship(back_populates="organization")
    configs: Mapped[list["Config"]] = relationship(back_populates="organization")

    __table_args__ = (
        Index("ix_organizations_domain", "domain"),
    )


# =============================================================================
# User
# =============================================================================


class User(Base):
    """User database table."""
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    email: Mapped[str] = mapped_column(String(320), unique=True)
    name: Mapped[str | None] = mapped_column(String(255), default=None)
    hashed_password: Mapped[str | None] = mapped_column(String(1024), default=None)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    is_registered: Mapped[bool] = mapped_column(Boolean, default=True)
    mfa_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    mfa_enforced_at: Mapped[datetime | None] = mapped_column(DateTime, default=None)
    user_type: Mapped[UserType] = mapped_column(
        SQLAlchemyEnum(
            UserType,
            name="user_type",
            create_type=False,
            values_callable=lambda x: [e.value for e in x]
        ),
        default=UserType.ORG
    )
    organization_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("organizations.id"), default=None
    )
    last_login: Mapped[datetime | None] = mapped_column(DateTime, default=None)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, server_default=text("NOW()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, server_default=text("NOW()"),
        onupdate=datetime.utcnow
    )

    # Relationships
    organization: Mapped[Organization | None] = relationship(back_populates="users")
    roles: Mapped[list["UserRole"]] = relationship(back_populates="user")
    executions: Mapped[list["Execution"]] = relationship(back_populates="executed_by_user")
    mfa_methods: Mapped[list["UserMFAMethod"]] = relationship(back_populates="user")
    recovery_codes: Mapped[list["MFARecoveryCode"]] = relationship(back_populates="user")
    trusted_devices: Mapped[list["TrustedDevice"]] = relationship(back_populates="user")
    oauth_accounts: Mapped[list["UserOAuthAccount"]] = relationship(back_populates="user")

    __table_args__ = (
        Index("ix_users_email", "email"),
        Index("ix_users_organization_id", "organization_id"),
    )


# =============================================================================
# Role
# =============================================================================


class Role(Base):
    """Role database table."""
    __tablename__ = "roles"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str | None] = mapped_column(Text, default=None)
    permissions: Mapped[list] = mapped_column(JSONB, default=[])
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    organization_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("organizations.id"), default=None
    )
    created_by: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, server_default=text("NOW()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, server_default=text("NOW()"),
        onupdate=datetime.utcnow
    )

    # Relationships
    users: Mapped[list["UserRole"]] = relationship(back_populates="role")

    __table_args__ = (
        Index("ix_roles_organization_id", "organization_id"),
    )


class UserRole(Base):
    """User-Role association table."""
    __tablename__ = "user_roles"

    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), primary_key=True)
    role_id: Mapped[UUID] = mapped_column(ForeignKey("roles.id"), primary_key=True)
    assigned_by: Mapped[str] = mapped_column(String(255))
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, server_default=text("NOW()")
    )

    # Relationships
    user: Mapped[User] = relationship(back_populates="roles")
    role: Mapped[Role] = relationship(back_populates="users")


# =============================================================================
# Form
# =============================================================================


class Form(Base):
    """Form database table."""
    __tablename__ = "forms"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text, default=None)
    linked_workflow: Mapped[str | None] = mapped_column(String(255), default=None)
    launch_workflow_id: Mapped[str | None] = mapped_column(String(255), default=None)
    default_launch_params: Mapped[dict | None] = mapped_column(JSONB, default=None)
    allowed_query_params: Mapped[list | None] = mapped_column(JSONB, default=None)
    form_schema: Mapped[dict | None] = mapped_column(JSONB, default=None)
    assigned_roles: Mapped[list | None] = mapped_column(JSONB, default=None)
    access_level: Mapped[FormAccessLevel] = mapped_column(
        SQLAlchemyEnum(
            FormAccessLevel,
            name="form_access_level",
            create_type=False,
            values_callable=lambda x: [e.value for e in x]
        ),
        default=FormAccessLevel.ROLE_BASED
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    organization_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("organizations.id"), default=None
    )
    created_by: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, server_default=text("NOW()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, server_default=text("NOW()"),
        onupdate=datetime.utcnow
    )

    # Relationships
    organization: Mapped[Organization | None] = relationship(back_populates="forms")
    executions: Mapped[list["Execution"]] = relationship(back_populates="form")


class FormRole(Base):
    """Form-Role association table."""
    __tablename__ = "form_roles"

    form_id: Mapped[UUID] = mapped_column(ForeignKey("forms.id"), primary_key=True)
    role_id: Mapped[UUID] = mapped_column(ForeignKey("roles.id"), primary_key=True)
    assigned_by: Mapped[str] = mapped_column(String(255))
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, server_default=text("NOW()")
    )


# =============================================================================
# Execution
# =============================================================================


class Execution(Base):
    """Execution database table."""
    __tablename__ = "executions"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    workflow_name: Mapped[str] = mapped_column(String(255))
    workflow_version: Mapped[str | None] = mapped_column(String(50), default=None)
    status: Mapped[ExecutionStatus] = mapped_column(
        SQLAlchemyEnum(
            ExecutionStatus,
            name="execution_status",
            create_type=False,
            values_callable=lambda x: [e.value for e in x]
        ),
        default=ExecutionStatus.PENDING
    )
    parameters: Mapped[dict] = mapped_column(JSONB, default={})
    result: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    result_type: Mapped[str | None] = mapped_column(String(50), default=None)
    variables: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, default=None)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, default=None)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, default=None)
    duration_ms: Mapped[int | None] = mapped_column(Integer, default=None)
    executed_by: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    executed_by_name: Mapped[str] = mapped_column(String(255))
    organization_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("organizations.id"), default=None
    )
    form_id: Mapped[UUID | None] = mapped_column(ForeignKey("forms.id"), default=None)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, server_default=text("NOW()")
    )

    # Relationships
    executed_by_user: Mapped[User] = relationship(back_populates="executions")
    organization: Mapped[Organization | None] = relationship(back_populates="executions")
    form: Mapped[Form | None] = relationship(back_populates="executions")
    logs: Mapped[list["ExecutionLog"]] = relationship(back_populates="execution")

    __table_args__ = (
        Index("ix_executions_org_status", "organization_id", "status"),
        Index("ix_executions_created", "created_at"),
        Index("ix_executions_user", "executed_by"),
        Index("ix_executions_workflow", "workflow_name"),
    )


class ExecutionLog(Base):
    """Execution log entries."""
    __tablename__ = "execution_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    execution_id: Mapped[UUID] = mapped_column(ForeignKey("executions.id"))
    level: Mapped[str] = mapped_column(String(20))
    message: Mapped[str] = mapped_column(Text)
    log_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, server_default=text("NOW()")
    )

    # Relationships
    execution: Mapped[Execution] = relationship(back_populates="logs")

    __table_args__ = (
        Index("ix_execution_logs_exec_time", "execution_id", "timestamp"),
    )


# =============================================================================
# Config
# =============================================================================


class Config(Base):
    """Configuration key-value store."""
    __tablename__ = "configs"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    key: Mapped[str] = mapped_column(String(255))
    value: Mapped[dict] = mapped_column(JSONB, nullable=False)
    config_type: Mapped[ConfigType] = mapped_column(
        SQLAlchemyEnum(
            ConfigType,
            name="config_type",
            create_type=False,
            values_callable=lambda x: [e.value for e in x]
        ),
        default=ConfigType.STRING
    )
    description: Mapped[str | None] = mapped_column(Text, default=None)
    organization_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("organizations.id"), default=None
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, server_default=text("NOW()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, server_default=text("NOW()"),
        onupdate=datetime.utcnow
    )
    updated_by: Mapped[str] = mapped_column(String(255))

    # Relationships
    organization: Mapped[Organization | None] = relationship(back_populates="configs")

    __table_args__ = (
        Index("ix_configs_org_key", "organization_id", "key", unique=True),
    )


# =============================================================================
# Workflow Keys (API keys for workflow execution)
# =============================================================================


class WorkflowKey(Base):
    """
    Workflow API keys for HTTP access without user authentication.

    - workflow_name=NULL means global key (works for all workflows)
    - workflow_name set means key only works for that specific workflow
    """
    __tablename__ = "workflow_keys"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    workflow_name: Mapped[str | None] = mapped_column(String(255), default=None)
    hashed_key: Mapped[str] = mapped_column(String(64))  # SHA-256 hash
    description: Mapped[str | None] = mapped_column(Text, default=None)
    created_by: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, server_default=text("NOW()")
    )
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime, default=None)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, default=None)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime, default=None)
    revoked_by: Mapped[str | None] = mapped_column(String(255), default=None)

    __table_args__ = (
        Index("ix_workflow_keys_hashed", "hashed_key"),
        Index("ix_workflow_keys_workflow", "workflow_name"),
    )


# =============================================================================
# OAuth (for integrations)
# =============================================================================


class OAuthProvider(Base):
    """OAuth provider configuration."""
    __tablename__ = "oauth_providers"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    provider_name: Mapped[str] = mapped_column(String(100))
    display_name: Mapped[str | None] = mapped_column(String(255), default=None)
    description: Mapped[str | None] = mapped_column(Text, default=None)
    oauth_flow_type: Mapped[str] = mapped_column(String(50), default="authorization_code")
    client_id: Mapped[str] = mapped_column(String(255))
    encrypted_client_secret: Mapped[bytes] = mapped_column(LargeBinary)
    authorization_url: Mapped[str | None] = mapped_column(String(500), default=None)
    token_url: Mapped[str | None] = mapped_column(String(500), default=None)
    scopes: Mapped[list] = mapped_column(JSONB, default=[])
    redirect_uri: Mapped[str | None] = mapped_column(String(500), default=None)
    status: Mapped[str] = mapped_column(String(50), default="not_connected")
    status_message: Mapped[str | None] = mapped_column(Text, default=None)
    last_token_refresh: Mapped[datetime | None] = mapped_column(DateTime, default=None)
    provider_metadata: Mapped[dict] = mapped_column(JSONB, default={})
    organization_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("organizations.id"), default=None
    )
    created_by: Mapped[str | None] = mapped_column(String(255), default=None)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, server_default=text("NOW()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, server_default=text("NOW()"),
        onupdate=datetime.utcnow
    )

    # Relationships
    tokens: Mapped[list["OAuthToken"]] = relationship(back_populates="provider")

    __table_args__ = (
        Index("ix_oauth_providers_org_name", "organization_id", "provider_name", unique=True),
    )


class OAuthToken(Base):
    """OAuth tokens for integration connections."""
    __tablename__ = "oauth_tokens"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("organizations.id"), default=None
    )
    provider_id: Mapped[UUID] = mapped_column(ForeignKey("oauth_providers.id"))
    user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"), default=None)
    encrypted_access_token: Mapped[bytes] = mapped_column(LargeBinary)
    encrypted_refresh_token: Mapped[bytes | None] = mapped_column(LargeBinary, default=None)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, default=None)
    scopes: Mapped[list] = mapped_column(JSONB, default=[])
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, server_default=text("NOW()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, server_default=text("NOW()"),
        onupdate=datetime.utcnow
    )

    # Relationships
    provider: Mapped[OAuthProvider] = relationship(back_populates="tokens")


# =============================================================================
# Audit Log
# =============================================================================


class AuditLog(Base):
    """Audit log for tracking user actions."""
    __tablename__ = "audit_logs"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("organizations.id"), default=None
    )
    user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"), default=None)
    action: Mapped[str] = mapped_column(String(100))
    resource_type: Mapped[str | None] = mapped_column(String(100), default=None)
    resource_id: Mapped[UUID | None] = mapped_column(default=None)
    details: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), default=None)
    user_agent: Mapped[str | None] = mapped_column(Text, default=None)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, server_default=text("NOW()")
    )

    __table_args__ = (
        Index("ix_audit_logs_org_time", "organization_id", "created_at"),
        Index("ix_audit_logs_user", "user_id"),
    )


# =============================================================================
# MFA
# =============================================================================


class UserMFAMethod(Base):
    """User MFA method enrollment."""
    __tablename__ = "user_mfa_methods"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    method_type: Mapped[MFAMethodType] = mapped_column(
        SQLAlchemyEnum(
            MFAMethodType,
            name="mfa_method_type",
            create_type=False,
            values_callable=lambda x: [e.value for e in x]
        )
    )
    status: Mapped[MFAMethodStatus] = mapped_column(
        SQLAlchemyEnum(
            MFAMethodStatus,
            name="mfa_method_status",
            create_type=False,
            values_callable=lambda x: [e.value for e in x]
        ),
        default=MFAMethodStatus.PENDING
    )
    encrypted_secret: Mapped[str | None] = mapped_column(Text, default=None)
    mfa_metadata: Mapped[dict] = mapped_column(JSONB, default={})
    last_used_counter: Mapped[int | None] = mapped_column(Integer, default=None)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime, default=None)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, server_default=text("NOW()")
    )
    verified_at: Mapped[datetime | None] = mapped_column(DateTime, default=None)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, server_default=text("NOW()"),
        onupdate=datetime.utcnow
    )

    # Relationships
    user: Mapped[User] = relationship(back_populates="mfa_methods")

    __table_args__ = (
        Index("ix_user_mfa_methods_user_id", "user_id"),
        Index("ix_user_mfa_methods_user_status", "user_id", "status"),
    )


class MFARecoveryCode(Base):
    """MFA recovery codes."""
    __tablename__ = "mfa_recovery_codes"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    code_hash: Mapped[str] = mapped_column(String(255))
    is_used: Mapped[bool] = mapped_column(Boolean, default=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime, default=None)
    used_from_ip: Mapped[str | None] = mapped_column(String(45), default=None)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, server_default=text("NOW()")
    )

    # Relationships
    user: Mapped[User] = relationship(back_populates="recovery_codes")

    __table_args__ = (
        Index("ix_mfa_recovery_codes_user_id", "user_id"),
        Index("ix_mfa_recovery_codes_user_unused", "user_id", "is_used"),
    )


class TrustedDevice(Base):
    """Trusted devices that can bypass MFA."""
    __tablename__ = "trusted_devices"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    device_fingerprint: Mapped[str] = mapped_column(String(64))
    device_name: Mapped[str | None] = mapped_column(String(255), default=None)
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime, default=None)
    last_ip_address: Mapped[str | None] = mapped_column(String(45), default=None)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, server_default=text("NOW()")
    )

    # Relationships
    user: Mapped[User] = relationship(back_populates="trusted_devices")

    __table_args__ = (
        Index("ix_trusted_devices_user_id", "user_id"),
        Index("ix_trusted_devices_fingerprint", "user_id", "device_fingerprint", unique=True),
    )


class UserOAuthAccount(Base):
    """Links OAuth accounts to users for SSO."""
    __tablename__ = "user_oauth_accounts"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    provider_id: Mapped[str] = mapped_column(String(50))
    provider_user_id: Mapped[str] = mapped_column(String(255))
    email: Mapped[str] = mapped_column(String(320))
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, server_default=text("NOW()")
    )
    last_login: Mapped[datetime | None] = mapped_column(DateTime, default=None)

    # Relationships
    user: Mapped[User] = relationship(back_populates="oauth_accounts")

    __table_args__ = (
        Index("ix_user_oauth_provider_user", "provider_id", "provider_user_id", unique=True),
        Index("ix_user_oauth_user", "user_id"),
    )
