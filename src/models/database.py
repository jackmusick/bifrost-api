"""
SQLAlchemy Database Models

These models define the PostgreSQL database schema.
They mirror the existing Azure Table Storage entities for migration compatibility.
"""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database import Base
from src.models.enums import ConfigType, ExecutionStatus, FormAccessLevel, UserType

if TYPE_CHECKING:
    pass


# =============================================================================
# Organization
# =============================================================================

class Organization(Base):
    """
    Organization entity.

    Organizations group users and resources together.
    """
    __tablename__ = "organizations"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    domain: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="Email domain for auto-provisioning (e.g., 'acme.com')"
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    settings: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )
    created_by: Mapped[str] = mapped_column(String(255), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )

    # Relationships
    users: Mapped[list["User"]] = relationship(back_populates="organization")
    forms: Mapped[list["Form"]] = relationship(back_populates="organization")
    executions: Mapped[list["Execution"]] = relationship(back_populates="organization")
    configs: Mapped[list["Config"]] = relationship(back_populates="organization")

    __table_args__ = (
        Index("ix_organizations_slug", "slug"),
        Index("ix_organizations_domain", "domain"),
    )


# =============================================================================
# User
# =============================================================================

class User(Base):
    """
    User entity.

    Supports both local accounts and OAuth-linked accounts.
    Compatible with FastAPI-Users patterns.
    """
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4
    )
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False)
    hashed_password: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Status flags
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)

    # User type (for migration compatibility)
    user_type: Mapped[UserType] = mapped_column(
        SAEnum(UserType, name="user_type"),
        default=UserType.ORG
    )

    # Organization membership (nullable for platform admins)
    organization_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("organizations.id"),
        nullable=True
    )

    # Timestamps
    last_login: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )

    # Relationships
    organization: Mapped["Organization | None"] = relationship(back_populates="users")
    roles: Mapped[list["UserRole"]] = relationship(back_populates="user")
    executions: Mapped[list["Execution"]] = relationship(back_populates="executed_by_user")

    __table_args__ = (
        Index("ix_users_email", "email"),
        Index("ix_users_organization_id", "organization_id"),
    )


# =============================================================================
# Role and User-Role Association
# =============================================================================

class Role(Base):
    """
    Role entity for role-based access control.
    """
    __tablename__ = "roles"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    permissions: Mapped[list] = mapped_column(JSONB, default=list)
    organization_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("organizations.id"),
        nullable=True,
        comment="NULL for global roles"
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )

    # Relationships
    users: Mapped[list["UserRole"]] = relationship(back_populates="role")

    __table_args__ = (
        Index("ix_roles_organization_id", "organization_id"),
    )


class UserRole(Base):
    """
    User-Role association table.
    """
    __tablename__ = "user_roles"

    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True
    )
    role_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("roles.id", ondelete="CASCADE"),
        primary_key=True
    )
    assigned_by: Mapped[str] = mapped_column(String(255), nullable=False)
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    # Relationships
    user: Mapped["User"] = relationship(back_populates="roles")
    role: Mapped["Role"] = relationship(back_populates="users")


# =============================================================================
# Form
# =============================================================================

class Form(Base):
    """
    Form entity for workflow input collection.
    """
    __tablename__ = "forms"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    workflow_name: Mapped[str] = mapped_column(String(255), nullable=False)

    # Form schema stored as JSONB
    schema: Mapped[dict] = mapped_column(JSONB, nullable=False)

    # Access control
    access_level: Mapped[FormAccessLevel] = mapped_column(
        SAEnum(FormAccessLevel, name="form_access_level"),
        default=FormAccessLevel.ROLE_BASED
    )

    # Settings
    settings: Mapped[dict] = mapped_column(JSONB, default=dict)

    # Organization scope (NULL for global forms)
    organization_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("organizations.id"),
        nullable=True
    )

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )

    # Relationships
    organization: Mapped["Organization | None"] = relationship(back_populates="forms")
    executions: Mapped[list["Execution"]] = relationship(back_populates="form")

    __table_args__ = (
        Index("ix_forms_organization_slug", "organization_id", "slug", unique=True),
        Index("ix_forms_workflow_name", "workflow_name"),
    )


class FormRole(Base):
    """
    Form-Role association table.

    Controls which roles have access to which forms.
    """
    __tablename__ = "form_roles"

    form_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("forms.id", ondelete="CASCADE"),
        primary_key=True
    )
    role_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("roles.id", ondelete="CASCADE"),
        primary_key=True
    )
    assigned_by: Mapped[str] = mapped_column(String(255), nullable=False)
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )


# =============================================================================
# Execution
# =============================================================================

class Execution(Base):
    """
    Workflow execution record.
    """
    __tablename__ = "executions"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4
    )
    workflow_name: Mapped[str] = mapped_column(String(255), nullable=False)
    workflow_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    status: Mapped[ExecutionStatus] = mapped_column(
        SAEnum(ExecutionStatus, name="execution_status"),
        default=ExecutionStatus.PENDING
    )

    # Input and output
    parameters: Mapped[dict] = mapped_column(JSONB, default=dict)
    result: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    result_type: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment="json, html, text, etc."
    )
    result_in_blob: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        comment="True if result is stored in blob storage"
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Timing
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Associations
    executed_by: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False
    )
    executed_by_name: Mapped[str] = mapped_column(String(255), nullable=False)
    organization_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("organizations.id"),
        nullable=True
    )
    form_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("forms.id"),
        nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    # Relationships
    executed_by_user: Mapped["User"] = relationship(back_populates="executions")
    organization: Mapped["Organization | None"] = relationship(back_populates="executions")
    form: Mapped["Form | None"] = relationship(back_populates="executions")
    logs: Mapped[list["ExecutionLog"]] = relationship(
        back_populates="execution",
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_executions_org_status", "organization_id", "status"),
        Index("ix_executions_created", "created_at", postgresql_using="btree"),
        Index("ix_executions_user", "executed_by"),
        Index("ix_executions_workflow", "workflow_name"),
    )


class ExecutionLog(Base):
    """
    Execution log entries.

    Stored separately for performance (can be thousands per execution).
    """
    __tablename__ = "execution_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    execution_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("executions.id", ondelete="CASCADE"),
        nullable=False
    )
    level: Mapped[str] = mapped_column(String(20), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    # Relationships
    execution: Mapped["Execution"] = relationship(back_populates="logs")

    __table_args__ = (
        Index("ix_execution_logs_exec_time", "execution_id", "timestamp"),
    )


# =============================================================================
# Config
# =============================================================================

class Config(Base):
    """
    Configuration key-value store.

    Replaces Azure Table Storage Config table.
    """
    __tablename__ = "configs"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4
    )
    organization_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("organizations.id"),
        nullable=True,
        comment="NULL for global config"
    )
    key: Mapped[str] = mapped_column(String(255), nullable=False)
    value: Mapped[dict] = mapped_column(JSONB, nullable=False)
    config_type: Mapped[ConfigType] = mapped_column(
        SAEnum(ConfigType, name="config_type"),
        default=ConfigType.STRING
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )
    updated_by: Mapped[str] = mapped_column(String(255), nullable=False)

    # Relationships
    organization: Mapped["Organization | None"] = relationship(back_populates="configs")

    __table_args__ = (
        Index("ix_configs_org_key", "organization_id", "key", unique=True),
    )


# =============================================================================
# Secret
# =============================================================================

class Secret(Base):
    """
    Encrypted secret storage.

    Replaces Azure Key Vault for local development.
    Secrets are encrypted using Fernet (AES-128-CBC with HMAC).
    Values are stored as base64-encoded encrypted strings.
    """
    __tablename__ = "secrets"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4
    )
    organization_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("organizations.id"),
        nullable=True,
        comment="NULL for global secrets"
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    encrypted_value: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Base64-encoded Fernet-encrypted value"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )

    __table_args__ = (
        Index("ix_secrets_org_name", "organization_id", "name", unique=True),
    )


# =============================================================================
# OAuth (for integrations, not user auth)
# =============================================================================

class OAuthProvider(Base):
    """
    OAuth provider configuration for integrations.

    Stores client credentials for connecting to external services.
    """
    __tablename__ = "oauth_providers"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4
    )
    organization_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("organizations.id"),
        nullable=True
    )
    provider_name: Mapped[str] = mapped_column(String(100), nullable=False)
    client_id: Mapped[str] = mapped_column(String(255), nullable=False)
    encrypted_client_secret: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    scopes: Mapped[list] = mapped_column(JSONB, default=list)
    metadata: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )

    # Relationships
    tokens: Mapped[list["OAuthToken"]] = relationship(back_populates="provider")

    __table_args__ = (
        Index("ix_oauth_providers_org_name", "organization_id", "provider_name", unique=True),
    )


class OAuthToken(Base):
    """
    OAuth tokens for integration connections.
    """
    __tablename__ = "oauth_tokens"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4
    )
    organization_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("organizations.id"),
        nullable=True
    )
    provider_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("oauth_providers.id"),
        nullable=False
    )
    user_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True
    )
    encrypted_access_token: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    encrypted_refresh_token: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    scopes: Mapped[list] = mapped_column(JSONB, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )

    # Relationships
    provider: Mapped["OAuthProvider"] = relationship(back_populates="tokens")


# =============================================================================
# Audit Log
# =============================================================================

class AuditLog(Base):
    """
    Audit log for tracking user actions.
    """
    __tablename__ = "audit_logs"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4
    )
    organization_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("organizations.id"),
        nullable=True
    )
    user_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True
    )
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    resource_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    details: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    __table_args__ = (
        Index("ix_audit_logs_org_time", "organization_id", "created_at"),
        Index("ix_audit_logs_user", "user_id"),
    )
