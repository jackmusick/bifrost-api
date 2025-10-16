"""
Pydantic models for Bifrost Integrations
Request/response validation and serialization
"""

from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

# ==================== PUBLIC API ====================
# All models exported for OpenAPI spec generation

__all__ = [
    # Enums
    'ConfigType',
    'ExecutionStatus',
    'FormFieldType',
    'IntegrationType',
    'UserType',

    # Organizations
    'Organization',
    'CreateOrganizationRequest',
    'UpdateOrganizationRequest',

    # Config
    'Config',
    'SetConfigRequest',

    # Integration Config
    'IntegrationConfig',
    'SetIntegrationConfigRequest',

    # Users & Roles
    'User',
    'Role',
    'CreateRoleRequest',
    'UpdateRoleRequest',
    'UserRole',
    'FormRole',
    'RoleUsersResponse',
    'RoleFormsResponse',
    'AssignUsersToRoleRequest',
    'AssignFormsToRoleRequest',

    # Permissions
    'UserPermission',
    'PermissionsData',
    'GrantPermissionsRequest',
    'UserRolesResponse',
    'UserFormsResponse',

    # Forms
    'FormFieldValidation',
    'FormField',
    'FormSchema',
    'Form',
    'CreateFormRequest',
    'UpdateFormRequest',
    'FormExecuteRequest',

    # Workflow Execution
    'WorkflowExecution',
    'WorkflowExecutionRequest',
    'WorkflowExecutionResponse',
    'ExecutionsListResponse',

    # Metadata
    'WorkflowParameter',
    'WorkflowMetadata',
    'DataProviderMetadata',
    'MetadataResponse',

    # Data Providers
    'DataProviderOption',
    'DataProviderResponse',

    # Secrets
    'SecretListResponse',
    'SecretCreateRequest',
    'SecretUpdateRequest',
    'SecretResponse',

    # Health
    'HealthCheck',
    'GeneralHealthResponse',
    'KeyVaultHealthResponse',

    # Dashboard
    'ExecutionStats',
    'RecentFailure',
    'DashboardMetricsResponse',

    # OAuth (not a BaseModel, but exported for workflows)
    'OAuthCredentials',
    'OAuthCallbackRequest',
    'OAuthCallbackResponse',

    # Common
    'ErrorResponse',

    # Helper functions
    'generate_entity_id',
    'parse_row_key',
    'parse_composite_row_key',
    'entity_to_model',
    'model_to_entity',
]


# ==================== ENUMS ====================

class ConfigType(str, Enum):
    """Configuration value types"""
    STRING = "string"
    INT = "int"
    BOOL = "bool"
    JSON = "json"
    SECRET_REF = "secret_ref"


class ExecutionStatus(str, Enum):
    """Workflow execution status"""
    PENDING = "Pending"
    RUNNING = "Running"
    SUCCESS = "Success"
    FAILED = "Failed"


class FormFieldType(str, Enum):
    """Form field types"""
    TEXT = "text"
    EMAIL = "email"
    NUMBER = "number"
    SELECT = "select"
    CHECKBOX = "checkbox"
    TEXTAREA = "textarea"


class IntegrationType(str, Enum):
    """Supported integration types"""
    MSGRAPH = "msgraph"
    HALOPSA = "halopsa"


class UserType(str, Enum):
    """User type - Platform admin or organization user"""
    PLATFORM = "PLATFORM"
    ORG = "ORG"


# ==================== ORGANIZATION MODELS ====================

class Organization(BaseModel):
    """Organization entity (response model)"""
    id: str = Field(..., description="Organization ID (GUID)")
    name: str = Field(..., min_length=1, max_length=200)
    tenantId: str | None = Field(
        None, description="Microsoft 365 GDAP tenant ID (auto-generated if not provided)")
    domain: str | None = Field(
        None, description="Email domain for auto-provisioning users (e.g., 'acme.com')")
    isActive: bool = Field(default=True)
    createdAt: datetime
    createdBy: str
    updatedAt: datetime

    class Config:
        from_attributes = True  # Pydantic v2 - replaces orm_mode


class CreateOrganizationRequest(BaseModel):
    """Request model for creating an organization"""
    name: str = Field(..., min_length=1, max_length=200)
    domain: str | None = Field(
        None, description="Email domain for auto-provisioning users (e.g., 'acme.com')")

    @field_validator('domain')
    @classmethod
    def validate_domain(cls, v):
        """Validate domain format (no @ symbol, just the domain)"""
        if v is not None:
            v = v.strip().lower()
            if '@' in v:
                raise ValueError("Domain should not include '@' symbol (e.g., use 'acme.com' not '@acme.com')")
            if not v or '.' not in v:
                raise ValueError("Domain must be a valid format (e.g., 'acme.com')")
        return v


class UpdateOrganizationRequest(BaseModel):
    """Request model for updating an organization"""
    name: str | None = Field(None, min_length=1, max_length=200)
    tenantId: str | None = None
    domain: str | None = Field(None, description="Email domain for auto-provisioning users")
    isActive: bool | None = None

    @field_validator('domain')
    @classmethod
    def validate_domain(cls, v):
        """Validate domain format (no @ symbol, just the domain)"""
        if v is not None:
            v = v.strip().lower()
            if '@' in v:
                raise ValueError("Domain should not include '@' symbol (e.g., use 'acme.com' not '@acme.com')")
            if not v or '.' not in v:
                raise ValueError("Domain must be a valid format (e.g., 'acme.com')")
        return v


# ==================== CONFIG MODELS ====================

class Config(BaseModel):
    """Configuration entity (global or org-specific)"""
    key: str
    value: str
    type: ConfigType
    scope: Literal["GLOBAL", "org"] = Field(
        ..., description="GLOBAL for MSP-wide or 'org' for org-specific")
    orgId: str | None = Field(
        None, description="Organization ID (only for org-specific config)")
    description: str | None = None
    updatedAt: datetime
    updatedBy: str


class SetConfigRequest(BaseModel):
    """Request model for setting config"""
    key: str = Field(..., pattern=r"^[a-zA-Z0-9_]+$")
    value: str
    type: ConfigType
    description: str | None = None


# ==================== INTEGRATION CONFIG MODELS ====================

class IntegrationConfig(BaseModel):
    """Integration configuration entity"""
    type: IntegrationType
    enabled: bool = Field(default=True)
    settings: dict[str, Any] = Field(...,
                                     description="Integration-specific settings")
    updatedAt: datetime
    updatedBy: str


class SetIntegrationConfigRequest(BaseModel):
    """Request model for setting integration config"""
    type: IntegrationType
    enabled: bool = Field(default=True)
    settings: dict[str, Any]

    @field_validator('settings')
    @classmethod
    def validate_settings(cls, v, info):
        """Validate integration-specific settings"""
        integration_type = info.data.get('type')

        if integration_type == IntegrationType.MSGRAPH:
            required_keys = {'tenant_id', 'client_id', 'client_secret_ref'}
            if not required_keys.issubset(v.keys()):
                raise ValueError(
                    f"Microsoft Graph integration requires: {required_keys}")

        elif integration_type == IntegrationType.HALOPSA:
            required_keys = {'api_url', 'client_id', 'api_key_ref'}
            if not required_keys.issubset(v.keys()):
                raise ValueError(
                    f"HaloPSA integration requires: {required_keys}")

        return v


# ==================== USER MODELS ====================

class User(BaseModel):
    """User entity"""
    id: str = Field(..., description="User ID from Azure AD")
    email: str
    displayName: str
    userType: UserType = Field(
        default=UserType.PLATFORM, description="Platform admin or organization user")
    isPlatformAdmin: bool = Field(
        default=False, description="Whether user is platform admin")
    isActive: bool = Field(default=True)
    lastLogin: datetime | None = None
    createdAt: datetime

    @field_validator('isPlatformAdmin')
    @classmethod
    def validate_platform_admin(cls, v, info):
        """Validate that only PLATFORM users can be admins"""
        user_type = info.data.get('userType')
        if v and user_type != UserType.PLATFORM:
            raise ValueError("Only PLATFORM users can be admins")
        return v


# ==================== ROLE MODELS ====================

class Role(BaseModel):
    """Role entity for organization users"""
    id: str = Field(..., description="Role ID (GUID)")
    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = None
    isActive: bool = Field(default=True)
    createdBy: str
    createdAt: datetime
    updatedAt: datetime


class CreateRoleRequest(BaseModel):
    """Request model for creating a role"""
    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = None


class UpdateRoleRequest(BaseModel):
    """Request model for updating a role"""
    name: str | None = Field(None, min_length=1, max_length=100)
    description: str | None = None


class UserRole(BaseModel):
    """User-to-Role assignment entity"""
    userId: str
    roleId: str
    assignedBy: str
    assignedAt: datetime


class FormRole(BaseModel):
    """Form-to-Role access control entity"""
    formId: str
    roleId: str
    assignedBy: str
    assignedAt: datetime


class AssignUsersToRoleRequest(BaseModel):
    """Request model for assigning users to a role"""
    userIds: list[str] = Field(..., min_length=1,
                               description="List of user IDs to assign")


class AssignFormsToRoleRequest(BaseModel):
    """Request model for assigning forms to a role"""
    formIds: list[str] = Field(..., min_length=1,
                               description="List of form IDs to assign")


class RoleUsersResponse(BaseModel):
    """Response model for getting users assigned to a role"""
    userIds: list[str] = Field(..., description="List of user IDs assigned to the role")


class RoleFormsResponse(BaseModel):
    """Response model for getting forms assigned to a role"""
    formIds: list[str] = Field(..., description="List of form IDs assigned to the role")


# ==================== PERMISSION MODELS ====================

class UserPermission(BaseModel):
    """User permission entity"""
    userId: str
    orgId: str
    canExecuteWorkflows: bool = Field(default=False)
    canManageConfig: bool = Field(default=False)
    canManageForms: bool = Field(default=False)
    canViewHistory: bool = Field(default=False)
    grantedBy: str
    grantedAt: datetime


class PermissionsData(BaseModel):
    """Permissions data for grant request"""
    canExecuteWorkflows: bool
    canManageConfig: bool
    canManageForms: bool
    canViewHistory: bool


class GrantPermissionsRequest(BaseModel):
    """Request model for granting permissions"""
    userId: str
    orgId: str
    permissions: PermissionsData


class UserRolesResponse(BaseModel):
    """Response model for getting roles assigned to a user"""
    roleIds: list[str] = Field(..., description="List of role IDs assigned to the user")


class UserFormsResponse(BaseModel):
    """Response model for getting forms accessible to a user"""
    userType: UserType = Field(..., description="User type (PLATFORM or ORG)")
    hasAccessToAllForms: bool = Field(..., description="Whether user has access to all forms")
    formIds: list[str] = Field(default_factory=list, description="List of form IDs user can access (empty if hasAccessToAllForms=true)")


# ==================== FORM MODELS ====================

class FormFieldValidation(BaseModel):
    """Form field validation rules"""
    pattern: str | None = None
    min: float | None = None
    max: float | None = None
    message: str | None = None


class FormField(BaseModel):
    """Form field definition"""
    name: str = Field(..., description="Parameter name for workflow")
    label: str = Field(..., description="Display label")
    type: FormFieldType
    required: bool = Field(default=False)
    validation: dict[str, Any] | None = None
    dataProvider: str | None = Field(
        None, description="Data provider name for dynamic options")
    defaultValue: Any | None = None
    placeholder: str | None = None
    helpText: str | None = None


class FormSchema(BaseModel):
    """Form schema with field definitions"""
    fields: list[FormField] = Field(..., max_length=50,
                                    description="Max 50 fields per form")

    @field_validator('fields')
    @classmethod
    def validate_unique_names(cls, v):
        """Ensure field names are unique"""
        names = [field.name for field in v]
        if len(names) != len(set(names)):
            raise ValueError("Field names must be unique")
        return v


class Form(BaseModel):
    """Form entity (response model)"""
    id: str
    orgId: str = Field(..., description="Organization ID or 'GLOBAL'")
    name: str = Field(..., min_length=1, max_length=200)
    description: str | None = None
    linkedWorkflow: str = Field(..., description="Workflow name to execute")
    formSchema: FormSchema
    isActive: bool = Field(default=True)
    isGlobal: bool = Field(default=False)
    isPublic: bool = Field(
        default=False, description="If true, any authenticated user can execute. If false, only users in assigned groups can execute.")
    createdBy: str
    createdAt: datetime
    updatedAt: datetime


class CreateFormRequest(BaseModel):
    """Request model for creating a form"""
    name: str = Field(..., min_length=1, max_length=200)
    description: str | None = None
    linkedWorkflow: str
    formSchema: FormSchema
    isGlobal: bool = Field(default=False)
    isPublic: bool = Field(
        default=False, description="If true, any authenticated user can execute")


class UpdateFormRequest(BaseModel):
    """Request model for updating a form"""
    name: str | None = Field(None, min_length=1, max_length=200)
    description: str | None = None
    linkedWorkflow: str | None = None
    formSchema: FormSchema | None = None
    isActive: bool | None = None


class FormExecuteRequest(BaseModel):
    """Request model for executing a form"""
    form_data: dict[str, Any] = Field(..., description="Form field values")


# ==================== WORKFLOW EXECUTION MODELS ====================

class WorkflowExecution(BaseModel):
    """Workflow execution entity"""
    executionId: str
    workflowName: str
    formId: str | None = None
    executedBy: str
    status: ExecutionStatus
    inputData: dict[str, Any]
    result: dict[str, Any] | None = None
    errorMessage: str | None = None
    durationMs: int | None = None
    startedAt: datetime
    completedAt: datetime | None = None


class WorkflowExecutionRequest(BaseModel):
    """Request model for executing a workflow"""
    inputData: dict[str, Any] = Field(default_factory=dict, description="Workflow input parameters")
    formId: str | None = Field(None, description="Optional form ID that triggered this execution")


class WorkflowExecutionResponse(BaseModel):
    """Response model for workflow execution"""
    executionId: str
    status: ExecutionStatus
    result: dict[str, Any] | None = None
    error: str | None = None
    errorType: str | None = None
    details: dict[str, Any] | None = None
    durationMs: int | None = None
    startedAt: datetime | None = None
    completedAt: datetime | None = None


class ExecutionsListResponse(BaseModel):
    """Response model for listing workflow executions"""
    executions: list[WorkflowExecution] = Field(..., description="List of workflow executions")


# ==================== METADATA MODELS ====================

class WorkflowParameter(BaseModel):
    """Workflow parameter metadata"""
    name: str
    type: str  # string, int, bool, etc.
    required: bool
    dataProvider: str | None = None
    description: str | None = None


class WorkflowMetadata(BaseModel):
    """Workflow metadata from @workflow decorator"""
    name: str
    description: str
    category: str = Field(default="General")
    parameters: list[WorkflowParameter] = Field(default_factory=list)
    requiresOrg: bool = Field(
        default=True, description="Whether workflow requires org context")


class DataProviderMetadata(BaseModel):
    """Data provider metadata from @data_provider decorator"""
    name: str
    description: str


class MetadataResponse(BaseModel):
    """Response model for /admin/workflow endpoint"""
    workflows: list[WorkflowMetadata] = Field(default_factory=list)
    optionGenerators: list[DataProviderMetadata] = Field(
        default_factory=list, alias="option_generators")

    class Config:
        populate_by_name = True  # Pydantic v2 - allows using alias


# ==================== DATA PROVIDER RESPONSE MODELS ====================

class DataProviderOption(BaseModel):
    """Data provider option item"""
    label: str
    value: str
    metadata: dict[str, Any] | None = None


class DataProviderResponse(BaseModel):
    """Response model for data provider endpoint"""
    provider: str = Field(..., description="Name of the data provider")
    options: list[DataProviderOption] = Field(..., description="List of options returned by the provider")
    cached: bool = Field(..., description="Whether this result was served from cache")
    cacheExpiresAt: str = Field(..., alias="cache_expires_at", description="Cache expiration timestamp")

    class Config:
        populate_by_name = True  # Pydantic v2 - allows using alias


# ==================== SECRET MODELS ====================

class SecretListResponse(BaseModel):
    """Response model for listing secrets"""
    secrets: list[str] = Field(...,
                               description="List of secret names available in Key Vault")
    orgId: str | None = Field(
        None, description="Organization ID filter (if applied)")
    count: int = Field(..., description="Total number of secrets returned")


class SecretCreateRequest(BaseModel):
    """Request model for creating a secret"""
    orgId: str = Field(...,
                       description="Organization ID or 'GLOBAL' for platform-wide")
    secretKey: str = Field(..., pattern=r"^[a-zA-Z0-9_-]+$",
                           description="Secret key (alphanumeric, hyphens, underscores)")
    value: str = Field(..., min_length=1, description="Secret value")

    @field_validator('secretKey')
    @classmethod
    def validate_secret_key(cls, v):
        """Validate secret key follows naming conventions"""
        if len(v) > 100:
            raise ValueError("Secret key must be 100 characters or less")
        return v


class SecretUpdateRequest(BaseModel):
    """Request model for updating a secret"""
    value: str = Field(..., min_length=1, description="New secret value")


class SecretResponse(BaseModel):
    """Response model for secret operations"""
    name: str = Field(...,
                      description="Full secret name in Key Vault (e.g., org-123--api-key)")
    orgId: str = Field(..., description="Organization ID or 'GLOBAL'")
    secretKey: str = Field(..., description="Secret key portion")
    value: str | None = Field(
        None, description="Secret value (only shown immediately after create/update)")
    message: str = Field(..., description="Operation result message")


# ==================== HEALTH MODELS ====================

class HealthCheck(BaseModel):
    """Individual health check result"""
    service: str = Field(..., description="Display name of the service (e.g., 'API', 'Key Vault')")
    healthy: bool = Field(..., description="Whether the service is healthy")
    message: str = Field(..., description="Health check message")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional service-specific metadata")


class GeneralHealthResponse(BaseModel):
    """General health check response with multiple service checks"""
    status: Literal["healthy", "degraded", "unhealthy"] = Field(..., description="Overall system health status")
    service: str = Field(default="Bifrost Integrations API", description="Service name")
    timestamp: datetime = Field(..., description="Health check timestamp")
    checks: list[HealthCheck] = Field(..., description="Individual service health checks")


class KeyVaultHealthResponse(BaseModel):
    """Health check response for Azure Key Vault"""
    status: Literal["healthy", "degraded",
                    "unhealthy"] = Field(..., description="Health status")
    message: str = Field(..., description="Health status message")
    vaultUrl: str | None = Field(
        None, description="Key Vault URL being monitored")
    canConnect: bool = Field(...,
                             description="Whether connection to Key Vault succeeded")
    canListSecrets: bool = Field(...,
                                 description="Whether listing secrets is permitted")
    canGetSecrets: bool = Field(...,
                                description="Whether reading secrets is permitted")
    secretCount: int | None = Field(
        None, description="Number of secrets in Key Vault (if accessible)")
    lastChecked: datetime = Field(..., description="Timestamp of health check")


# ==================== OAUTH MODELS ====================

class OAuthCallbackRequest(BaseModel):
    """Request model for OAuth callback endpoint"""
    code: str = Field(..., description="Authorization code from OAuth provider")
    state: str | None = Field(None, description="State parameter for CSRF protection")


class OAuthCallbackResponse(BaseModel):
    """Response model for OAuth callback endpoint"""
    success: bool = Field(..., description="Whether the OAuth connection was successful")
    message: str = Field(..., description="Status message")
    status: str = Field(..., description="Connection status")
    connection_name: str = Field(..., description="Name of the OAuth connection")
    warning: str | None = Field(None, description="Warning message (e.g., missing refresh token)")


class OAuthCredentials:
    """
    OAuth credentials object for workflows

    Provides access to OAuth access_token and refresh_token
    for making authenticated API calls to third-party services
    """

    def __init__(
        self,
        connection_name: str,
        access_token: str,
        token_type: str,
        expires_at: datetime,
        refresh_token: str | None = None,
        scopes: str = ""
    ):
        self.connection_name = connection_name
        self.access_token = access_token
        self.token_type = token_type
        self.expires_at = expires_at
        self.refresh_token = refresh_token
        self.scopes = scopes

    def is_expired(self) -> bool:
        """Check if access token is expired"""
        return datetime.utcnow() >= self.expires_at

    def get_auth_header(self) -> str:
        """Get formatted Authorization header value"""
        return f"{self.token_type} {self.access_token}"

    def __repr__(self) -> str:
        return f"<OAuthCredentials connection={self.connection_name} expires_at={self.expires_at}>"


# ==================== DASHBOARD MODELS ====================

class ExecutionStats(BaseModel):
    """Execution statistics for dashboard"""
    totalExecutions: int
    successCount: int
    failedCount: int
    runningCount: int
    pendingCount: int
    successRate: float
    avgDurationSeconds: float


class RecentFailure(BaseModel):
    """Recent failed execution info"""
    executionId: str
    workflowName: str
    errorMessage: str | None
    startedAt: str | None


class DashboardMetricsResponse(BaseModel):
    """Dashboard metrics response"""
    workflowCount: int
    dataProviderCount: int
    formCount: int
    executionStats: ExecutionStats
    recentFailures: list[RecentFailure]


# ==================== ERROR MODEL ====================

class ErrorResponse(BaseModel):
    """API error response"""
    error: str = Field(..., description="Error code or type")
    message: str = Field(..., description="Human-readable error message")
    details: dict[str, Any] | None = None


# ==================== HELPER FUNCTIONS ====================

import uuid


def generate_entity_id() -> str:
    """
    Generate UUID for entity IDs.

    Returns:
        UUID string (e.g., "550e8400-e29b-41d4-a716-446655440000")
    """
    return str(uuid.uuid4())


def parse_row_key(row_key: str) -> tuple[str, str]:
    """
    Parse 'type:id' row keys.

    Examples:
        "form:7c9e6679-7425-40de-944b-e07fc1f90ae7" → ("form", "7c9e6679-7425-40de-944b-e07fc1f90ae7")
        "config:workflow_key" → ("config", "workflow_key")
        "execution:9999999999999_uuid" → ("execution", "9999999999999_uuid")

    Args:
        row_key: Row key string

    Returns:
        Tuple of (entity_type, entity_id)
    """
    parts = row_key.split(':', 1)
    return parts[0], parts[1] if len(parts) > 1 else ""


def parse_composite_row_key(row_key: str, expected_parts: int) -> list[str]:
    """
    Parse multi-part row keys like 'assignedrole:role_uuid:user_id'.

    Examples:
        "assignedrole:a3b2c1d4-...:user-456" → ["assignedrole", "a3b2c1d4-...", "user-456"]
        "formrole:7c9e6679-...:a3b2c1d4-..." → ["formrole", "7c9e6679-...", "a3b2c1d4-..."]

    Args:
        row_key: Row key string
        expected_parts: Expected number of parts

    Returns:
        List of row key parts

    Raises:
        ValueError: If row key doesn't have expected number of parts
    """
    parts = row_key.split(':')
    if len(parts) != expected_parts:
        raise ValueError(f"Expected {expected_parts} parts in row key, got {len(parts)}: {row_key}")
    return parts


def entity_to_model(entity: dict, model_class: type[BaseModel]) -> BaseModel:
    """
    Convert Table Storage entity to Pydantic model.
    Handles composite row keys (type:uuid or type:id1:id2).

    Args:
        entity: Entity dictionary from Table Storage
        model_class: Pydantic model class to convert to

    Returns:
        Instance of the Pydantic model
    """
    # Remove Azure Table Storage metadata fields
    clean_entity = {k: v for k, v in entity.items() if not k.startswith(
        'odata') and k not in ['PartitionKey', 'RowKey', 'Timestamp', 'etag']}

    # Extract ID from row key (e.g., "form:7c9e6679-..." → "7c9e6679-...")
    if 'id' in model_class.model_fields and 'RowKey' in entity:
        row_key = entity['RowKey']
        entity_type, entity_id = parse_row_key(row_key)
        clean_entity['id'] = entity_id

    # Handle composite keys for junction tables (UserRole, FormRole, etc.)
    if 'userId' in model_class.model_fields and 'roleId' in model_class.model_fields:
        # e.g., "userrole:user-123:a3b2c1d4-5678-90ab-cdef-1234567890ab"
        parts = parse_composite_row_key(entity['RowKey'], 3)
        clean_entity['userId'] = parts[1]
        clean_entity['roleId'] = parts[2]  # UUID

    if 'formId' in model_class.model_fields and 'roleId' in model_class.model_fields:
        # e.g., "formrole:form_uuid:role_uuid"
        parts = parse_composite_row_key(entity['RowKey'], 3)
        clean_entity['formId'] = parts[1]  # UUID
        clean_entity['roleId'] = parts[2]  # UUID

    return model_class(**clean_entity)


def model_to_entity(
    model: BaseModel,
    partition_key: str,
    row_key: str,
    entity_type: str | None = None,
    generate_id: bool = False
) -> dict:
    """
    Convert Pydantic model to Table Storage entity.
    Constructs row key like 'type:uuid' if entity_type provided.
    Generates UUID if generate_id=True and model has no id.

    Args:
        model: Pydantic model instance
        partition_key: Partition key for the entity
        row_key: Row key for the entity (ignored if entity_type provided)
        entity_type: Optional entity type for composite row key construction
        generate_id: Whether to generate UUID if model has no id

    Returns:
        Entity dictionary ready for Table Storage
    """
    entity = model.model_dump()
    entity['PartitionKey'] = partition_key

    # Generate UUID if needed
    if generate_id and 'id' not in entity:
        entity['id'] = generate_entity_id()

    # Construct composite row key if entity_type provided
    if entity_type and 'id' in entity:
        entity['RowKey'] = f"{entity_type}:{entity['id']}"
        del entity['id']  # Remove id field, RowKey contains the UUID
    else:
        entity['RowKey'] = row_key

    return entity
