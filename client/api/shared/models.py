"""
Pydantic models for Bifrost Integrations
Request/response validation and serialization
"""

from datetime import datetime
from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field, field_validator, UUID4
from enum import Enum


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
    tenantId: Optional[str] = Field(
        None, description="Microsoft 365 GDAP tenant ID")
    isActive: bool = Field(default=True)
    createdAt: datetime
    createdBy: str
    updatedAt: datetime

    class Config:
        from_attributes = True  # Pydantic v2 - replaces orm_mode


class CreateOrganizationRequest(BaseModel):
    """Request model for creating an organization"""
    name: str = Field(..., min_length=1, max_length=200)
    tenantId: Optional[str] = None


class UpdateOrganizationRequest(BaseModel):
    """Request model for updating an organization"""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    tenantId: Optional[str] = None
    isActive: Optional[bool] = None


# ==================== CONFIG MODELS ====================

class Config(BaseModel):
    """Configuration entity (global or org-specific)"""
    key: str
    value: str
    type: ConfigType
    scope: Literal["GLOBAL", "org"] = Field(
        ..., description="GLOBAL for MSP-wide or 'org' for org-specific")
    orgId: Optional[str] = Field(
        None, description="Organization ID (only for org-specific config)")
    description: Optional[str] = None
    updatedAt: datetime
    updatedBy: str


class SetConfigRequest(BaseModel):
    """Request model for setting config"""
    key: str = Field(..., pattern=r"^[a-zA-Z0-9_]+$")
    value: str
    type: ConfigType
    scope: Literal["GLOBAL", "org"] = Field(
        default="GLOBAL", description="GLOBAL or org")
    description: Optional[str] = None


# ==================== INTEGRATION CONFIG MODELS ====================

class IntegrationConfig(BaseModel):
    """Integration configuration entity"""
    type: IntegrationType
    enabled: bool = Field(default=True)
    settings: Dict[str, Any] = Field(...,
                                     description="Integration-specific settings")
    updatedAt: datetime
    updatedBy: str


class SetIntegrationConfigRequest(BaseModel):
    """Request model for setting integration config"""
    type: IntegrationType
    enabled: bool = Field(default=True)
    settings: Dict[str, Any]

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
    lastLogin: Optional[datetime] = None
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
    description: Optional[str] = None
    isActive: bool = Field(default=True)
    createdBy: str
    createdAt: datetime
    updatedAt: datetime


class CreateRoleRequest(BaseModel):
    """Request model for creating a role"""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None


class UpdateRoleRequest(BaseModel):
    """Request model for updating a role"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None


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
    userIds: List[str] = Field(..., min_length=1,
                               description="List of user IDs to assign")


class AssignFormsToRoleRequest(BaseModel):
    """Request model for assigning forms to a role"""
    formIds: List[str] = Field(..., min_length=1,
                               description="List of form IDs to assign")


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


# ==================== FORM MODELS ====================

class FormFieldValidation(BaseModel):
    """Form field validation rules"""
    pattern: Optional[str] = None
    min: Optional[float] = None
    max: Optional[float] = None
    message: Optional[str] = None


class FormField(BaseModel):
    """Form field definition"""
    name: str = Field(..., description="Parameter name for workflow")
    label: str = Field(..., description="Display label")
    type: FormFieldType
    required: bool = Field(default=False)
    validation: Optional[Dict[str, Any]] = None
    dataProvider: Optional[str] = Field(
        None, description="Data provider name for dynamic options")
    defaultValue: Optional[Any] = None
    placeholder: Optional[str] = None
    helpText: Optional[str] = None


class FormSchema(BaseModel):
    """Form schema with field definitions"""
    fields: List[FormField] = Field(..., max_length=50,
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
    description: Optional[str] = None
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
    description: Optional[str] = None
    linkedWorkflow: str
    formSchema: FormSchema
    isGlobal: bool = Field(default=False)
    isPublic: bool = Field(
        default=False, description="If true, any authenticated user can execute")


class UpdateFormRequest(BaseModel):
    """Request model for updating a form"""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    linkedWorkflow: Optional[str] = None
    formSchema: Optional[FormSchema] = None


# ==================== WORKFLOW EXECUTION MODELS ====================

class WorkflowExecution(BaseModel):
    """Workflow execution entity"""
    executionId: str
    workflowName: str
    formId: Optional[str] = None
    executedBy: str
    status: ExecutionStatus
    inputData: Dict[str, Any]
    result: Optional[Dict[str, Any]] = None
    errorMessage: Optional[str] = None
    durationMs: Optional[int] = None
    startedAt: datetime
    completedAt: Optional[datetime] = None


class WorkflowExecutionRequest(BaseModel):
    """Request model for executing a workflow"""
    workflowName: str
    formId: Optional[str] = None
    inputData: Dict[str, Any]


class WorkflowExecutionResponse(BaseModel):
    """Response model for workflow execution initiation"""
    executionId: str
    status: ExecutionStatus
    message: str


# ==================== METADATA MODELS ====================

class WorkflowParameter(BaseModel):
    """Workflow parameter metadata"""
    name: str
    type: str  # string, int, bool, etc.
    required: bool
    dataProvider: Optional[str] = None
    description: Optional[str] = None


class WorkflowMetadata(BaseModel):
    """Workflow metadata from @workflow decorator"""
    name: str
    description: str
    category: str = Field(default="General")
    parameters: List[WorkflowParameter] = Field(default_factory=list)
    requiresOrg: bool = Field(
        default=True, description="Whether workflow requires org context")


class DataProviderMetadata(BaseModel):
    """Data provider metadata from @data_provider decorator"""
    name: str
    description: str


class MetadataResponse(BaseModel):
    """Response model for /admin/workflow endpoint"""
    workflows: List[WorkflowMetadata] = Field(default_factory=list)
    optionGenerators: List[DataProviderMetadata] = Field(
        default_factory=list, alias="option_generators")

    class Config:
        populate_by_name = True  # Pydantic v2 - allows using alias


# ==================== WORKFLOW KEY MODELS ====================

class WorkflowKey(BaseModel):
    """Workflow key for HTTP-triggered workflows"""
    scope: Literal["GLOBAL", "org"] = Field(
        ..., description="GLOBAL for MSP-wide or 'org' for org-specific")
    orgId: Optional[str] = Field(
        None, description="Organization ID (only for org-specific keys)")
    key: str = Field(..., description="The workflow key (masked in responses)")
    createdAt: datetime
    createdBy: str
    lastUsedAt: Optional[datetime] = None


class WorkflowKeyResponse(BaseModel):
    """Response model when generating a workflow key"""
    scope: Literal["GLOBAL", "org"]
    orgId: Optional[str] = None
    key: str = Field(...,
                     description="The full workflow key (only shown once)")
    createdAt: datetime
    createdBy: str
    message: str = Field(
        default="Store this key securely. It won't be shown again.")


# ==================== SECRET MODELS ====================

class SecretListResponse(BaseModel):
    """Response model for listing secrets"""
    secrets: List[str] = Field(...,
                               description="List of secret names available in Key Vault")
    orgId: Optional[str] = Field(
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
    value: Optional[str] = Field(
        None, description="Secret value (only shown immediately after create/update)")
    message: str = Field(..., description="Operation result message")


# ==================== HEALTH MODELS ====================

class KeyVaultHealthResponse(BaseModel):
    """Health check response for Azure Key Vault"""
    status: Literal["healthy", "degraded",
                    "unhealthy"] = Field(..., description="Health status")
    message: str = Field(..., description="Health status message")
    vaultUrl: Optional[str] = Field(
        None, description="Key Vault URL being monitored")
    canConnect: bool = Field(...,
                             description="Whether connection to Key Vault succeeded")
    canListSecrets: bool = Field(...,
                                 description="Whether listing secrets is permitted")
    canGetSecrets: bool = Field(...,
                                description="Whether reading secrets is permitted")
    secretCount: Optional[int] = Field(
        None, description="Number of secrets in Key Vault (if accessible)")
    lastChecked: datetime = Field(..., description="Timestamp of health check")


# ==================== ERROR MODEL ====================

class ErrorResponse(BaseModel):
    """API error response"""
    error: str = Field(..., description="Error code or type")
    message: str = Field(..., description="Human-readable error message")
    details: Optional[Dict[str, Any]] = None


# ==================== HELPER FUNCTIONS ====================

def entity_to_model(entity: dict, model_class: type[BaseModel]) -> BaseModel:
    """
    Convert Table Storage entity to Pydantic model

    Args:
        entity: Entity dictionary from Table Storage
        model_class: Pydantic model class to convert to

    Returns:
        Instance of the Pydantic model
    """
    # Remove Azure Table Storage metadata fields
    clean_entity = {k: v for k, v in entity.items() if not k.startswith(
        'odata') and k not in ['PartitionKey', 'RowKey', 'Timestamp', 'etag']}

    # Map entity fields to model fields (handle case differences)
    # For example: RowKey="org-123" -> id="org-123"
    if 'id' in model_class.model_fields and 'RowKey' in entity:
        clean_entity['id'] = entity['RowKey']

    return model_class(**clean_entity)


def model_to_entity(model: BaseModel, partition_key: str, row_key: str) -> dict:
    """
    Convert Pydantic model to Table Storage entity

    Args:
        model: Pydantic model instance
        partition_key: Partition key for the entity
        row_key: Row key for the entity

    Returns:
        Entity dictionary ready for Table Storage
    """
    entity = model.model_dump()
    entity['PartitionKey'] = partition_key
    entity['RowKey'] = row_key

    # Remove 'id' field if it exists (use RowKey instead)
    if 'id' in entity:
        del entity['id']

    return entity
