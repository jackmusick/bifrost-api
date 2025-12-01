"""
Bifrost Models

ORM models (database tables):
    from src.models import Organization, User, Form

Pydantic schemas (API request/response):
    from src.models import OrganizationCreate, OrganizationPublic
"""

# ORM models (database tables)
from src.models.orm import (
    Base,
    Organization,
    User,
    Role,
    UserRole,
    Form,
    FormRole,
    Execution,
    ExecutionLog,
    Config,
    WorkflowKey,
    OAuthProvider,
    OAuthToken,
    AuditLog,
    UserMFAMethod,
    MFARecoveryCode,
    TrustedDevice,
    UserOAuthAccount,
)

# Pydantic schemas (API request/response)
from src.models.schemas import (
    # Organization
    OrganizationBase,
    OrganizationCreate,
    OrganizationUpdate,
    OrganizationPublic,
    # User
    UserBase,
    UserCreate,
    UserUpdate,
    UserPublic,
    # Role
    RoleBase,
    RoleCreate,
    RoleUpdate,
    RolePublic,
    # Form
    FormBase,
    FormCreate,
    FormUpdate,
    FormPublic,
    # Execution
    ExecutionBase,
    ExecutionCreate,
    ExecutionUpdate,
    ExecutionPublic,
    # Config
    ConfigBase,
    ConfigCreate,
    ConfigUpdate,
    ConfigPublic,
    # OAuth
    OAuthProviderBase,
    OAuthProviderCreate,
    OAuthProviderUpdate,
    OAuthProviderPublic,
    # Request/Response models
    UserRolesResponse,
    UserFormsResponse,
    RoleUsersResponse,
    RoleFormsResponse,
    AssignUsersToRoleRequest,
    AssignFormsToRoleRequest,
)

# Enums
from src.models.enums import (
    ExecutionStatus,
    UserType,
    FormAccessLevel,
    FormFieldType,
    ConfigType,
    MFAMethodType,
    MFAMethodStatus,
)

__all__ = [
    # Base
    "Base",
    # ORM models
    "Organization",
    "User",
    "Role",
    "UserRole",
    "Form",
    "FormRole",
    "Execution",
    "ExecutionLog",
    "Config",
    "WorkflowKey",
    "OAuthProvider",
    "OAuthToken",
    "AuditLog",
    "UserMFAMethod",
    "MFARecoveryCode",
    "TrustedDevice",
    "UserOAuthAccount",
    # Organization schemas
    "OrganizationBase",
    "OrganizationCreate",
    "OrganizationUpdate",
    "OrganizationPublic",
    # User schemas
    "UserBase",
    "UserCreate",
    "UserUpdate",
    "UserPublic",
    # Role schemas
    "RoleBase",
    "RoleCreate",
    "RoleUpdate",
    "RolePublic",
    # Form schemas
    "FormBase",
    "FormCreate",
    "FormUpdate",
    "FormPublic",
    # Execution schemas
    "ExecutionBase",
    "ExecutionCreate",
    "ExecutionUpdate",
    "ExecutionPublic",
    # Config schemas
    "ConfigBase",
    "ConfigCreate",
    "ConfigUpdate",
    "ConfigPublic",
    # OAuth schemas
    "OAuthProviderBase",
    "OAuthProviderCreate",
    "OAuthProviderUpdate",
    "OAuthProviderPublic",
    # Request/Response models
    "UserRolesResponse",
    "UserFormsResponse",
    "RoleUsersResponse",
    "RoleFormsResponse",
    "AssignUsersToRoleRequest",
    "AssignFormsToRoleRequest",
    # Enums
    "ExecutionStatus",
    "UserType",
    "FormAccessLevel",
    "FormFieldType",
    "ConfigType",
    "MFAMethodType",
    "MFAMethodStatus",
]
