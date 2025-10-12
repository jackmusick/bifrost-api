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


# ==================== ORGCONFIG MODELS ====================

class OrgConfig(BaseModel):
    """Organization configuration entity"""
    key: str
    value: str
    type: ConfigType
    description: Optional[str] = None
    updatedAt: datetime
    updatedBy: str


class SetConfigRequest(BaseModel):
    """Request model for setting config"""
    key: str = Field(..., pattern=r"^[a-zA-Z0-9_]+$")
    value: str
    type: ConfigType
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
    isActive: bool = Field(default=True)
    lastLogin: Optional[datetime] = None
    createdAt: datetime


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
    validation: Optional[FormFieldValidation] = None
    dataProvider: Optional[str] = Field(
        None, description="Data provider name for select fields")
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
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    linkedWorkflow: str = Field(..., description="Workflow name to execute")
    formSchema: FormSchema
    isActive: bool = Field(default=True)
    createdBy: str
    createdAt: datetime
    updatedAt: datetime


class CreateFormRequest(BaseModel):
    """Request model for creating a form"""
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    linkedWorkflow: str
    formSchema: FormSchema


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
    """Response model for workflow execution"""
    executionId: str
    status: ExecutionStatus
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    errorType: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    durationMs: Optional[int] = None
    startedAt: Optional[datetime] = None
    completedAt: Optional[datetime] = None


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
