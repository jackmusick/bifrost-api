# Data Model: Dynamic Data Provider Inputs

**Feature**: 007-in-our-applications
**Date**: 2025-10-22
**Status**: Complete

## Overview

This document defines the data model extensions required to support data provider inputs. The design extends existing models (FormField, DataProviderMetadata) without breaking backward compatibility.

## Entity Definitions

### 1. DataProviderInputConfig

**Purpose**: Represents how a single input parameter for a data provider is configured on a form field.

**Attributes**:
- `mode`: Enum("static", "fieldRef", "expression") - Configuration mode
- `value`: string | null - Static value (used when mode="static")
- `fieldName`: string | null - Referenced field name (used when mode="fieldRef")
- `expression`: string | null - JavaScript expression (used when mode="expression")

**Validation Rules**:
- Exactly one of {value, fieldName, expression} must be non-null based on mode
- mode="static" requires value
- mode="fieldRef" requires fieldName
- mode="expression" requires expression

**Python Model**:
```python
class DataProviderInputMode(str, Enum):
    STATIC = "static"
    FIELD_REF = "fieldRef"
    EXPRESSION = "expression"

class DataProviderInputConfig(BaseModel):
    """Configuration for a single data provider input parameter"""
    mode: DataProviderInputMode
    value: str | None = None
    fieldName: str | None = None
    expression: str | None = None

    @model_validator(mode='after')
    def validate_mode_data(self):
        """Ensure exactly one field is set based on mode"""
        if self.mode == DataProviderInputMode.STATIC:
            if not self.value:
                raise ValueError("value required for static mode")
            if self.fieldName or self.expression:
                raise ValueError("only value should be set for static mode")
        elif self.mode == DataProviderInputMode.FIELD_REF:
            if not self.fieldName:
                raise ValueError("fieldName required for fieldRef mode")
            if self.value or self.expression:
                raise ValueError("only fieldName should be set for fieldRef mode")
        elif self.mode == DataProviderInputMode.EXPRESSION:
            if not self.expression:
                raise ValueError("expression required for expression mode")
            if self.value or self.fieldName:
                raise ValueError("only expression should be set for expression mode")
        return self
```

**TypeScript Interface**:
```typescript
type DataProviderInputMode = "static" | "fieldRef" | "expression";

interface DataProviderInputConfig {
  mode: DataProviderInputMode;
  value?: string;        // Set when mode="static"
  fieldName?: string;    // Set when mode="fieldRef"
  expression?: string;   // Set when mode="expression"
}
```

**Relationships**:
- Embedded within FormField.dataProviderInputs dictionary
- Keys are parameter names from data provider's @param decorators
- One config per parameter

---

### 2. FormField (Extended)

**Purpose**: Form field definition, now with optional data provider input configuration.

**New Attributes**:
- `dataProviderInputs`: dict[str, DataProviderInputConfig] | null - Maps parameter names to input configurations

**Existing Attributes** (unchanged):
- `name`: string - Parameter name for workflow
- `label`: string - Display label
- `type`: FormFieldType enum
- `required`: boolean
- `validation`: dict | null
- `dataProvider`: string | null - Data provider name
- `defaultValue`: any | null
- `visibilityExpression`: string | null (existing field)

**Validation Rules**:
- dataProviderInputs can only be set if dataProvider is also set
- All required parameters from data provider must have configurations
- fieldName references in "fieldRef" mode must exist in form and appear earlier in field order
- No circular dependencies (validated separately)

**Python Model Extension**:
```python
class FormField(BaseModel):
    """Form field definition"""
    # ... existing fields ...
    dataProvider: str | None = Field(None, description="Data provider name")
    dataProviderInputs: dict[str, DataProviderInputConfig] | None = Field(
        None,
        description="Input configurations for data provider parameters"
    )

    @model_validator(mode='after')
    def validate_data_provider_inputs(self):
        """Ensure dataProviderInputs is only set when dataProvider is set"""
        if self.dataProviderInputs and not self.dataProvider:
            raise ValueError("dataProviderInputs requires dataProvider to be set")
        return self
```

**Storage**:
- Stored in Azure Table Storage as part of FormSchema JSON
- PartitionKey: Organization ID or "GLOBAL"
- RowKey: Form ID
- FormSchema.fields: list[FormField] (JSON serialized)

**Migration**:
- Backward compatible: dataProviderInputs is optional
- Existing forms without dataProviderInputs continue to work
- No database migration required (Table Storage is schema-less)

---

### 3. DataProviderMetadata (Extended)

**Purpose**: Metadata about a registered data provider function, now including parameter definitions.

**New Attributes**:
- `parameters`: list[WorkflowParameter] - Parameter definitions from @param decorators

**Existing Attributes** (unchanged):
- `name`: string - Data provider identifier
- `description`: string - Human-readable description
- `category`: string - Category for organization
- `cache_ttl_seconds`: int - Cache TTL

**Python Model Extension**:
```python
class DataProviderMetadata(BaseModel):
    """Data provider metadata from @data_provider decorator"""
    name: str
    description: str
    category: str = "General"
    cache_ttl_seconds: int = 300
    parameters: list[WorkflowParameter] = Field(default_factory=list)  # NEW
    function: Callable = Field(exclude=True)  # Function reference (not serialized)
```

**Relationships**:
- Parameters use WorkflowParameter model (already exists, used by workflows)
- Registered in global registry at module load time
- Exposed via /api/metadata endpoint

---

### 4. WorkflowParameter (Reused)

**Purpose**: Defines a single input parameter for a workflow or data provider.

**Attributes** (existing, no changes):
- `name`: string - Parameter name
- `type`: string - Parameter type (string, int, bool, float, json, list, email)
- `required`: boolean - Whether parameter is required
- `label`: string | null - Display label
- `dataProvider`: string | null - Data provider for options (not used for data provider params)
- `defaultValue`: any | null - Default value
- `helpText`: string | null - Help text
- `validation`: dict | null - Validation rules (min, max, pattern)
- `description`: string | null - Parameter description

**Python Model** (existing):
```python
class WorkflowParameter(BaseModel):
    """Workflow parameter metadata"""
    name: str
    type: str  # string, int, bool, float, json, list, email
    required: bool
    label: str | None = None
    dataProvider: str | None = None
    defaultValue: Any | None = None
    helpText: str | None = None
    validation: dict[str, Any] | None = None
    description: str | None = None
```

**Usage**:
- Shared by both workflows and data providers
- Populated by @param decorator
- Stored in registry metadata
- Used for validation at runtime

---

### 5. DataProviderRequest (Extended)

**Purpose**: Request model for calling a data provider endpoint.

**New Attributes**:
- `inputs`: dict[str, any] | null - Input parameter values

**Existing Attributes**:
- `orgId`: string | null - Organization context (if required)

**Python Model Extension**:
```python
class DataProviderRequest(BaseModel):
    """Request model for data provider endpoint"""
    orgId: str | None = Field(None, description="Organization ID for org-scoped providers")
    inputs: dict[str, Any] | None = Field(
        None,
        description="Input parameter values for data provider"
    )
```

**API Usage**:
```http
POST /api/data-providers/{provider_name}
Content-Type: application/json

{
  "orgId": "org-123",
  "inputs": {
    "token": "ghp_abc123...",
    "org": "microsoft"
  }
}
```

Or via query parameters:
```http
GET /api/data-providers/{provider_name}?inputs[token]=ghp_abc123...&inputs[org]=microsoft
```

---

### 6. DataProviderCacheEntry (Extended)

**Purpose**: Cached data provider result with input-aware cache key.

**Cache Key Format** (modified):
- Without inputs: `{provider_name}` (backward compatible)
- With inputs: `{provider_name}:{input_hash}`
- Input hash: First 16 chars of SHA-256 hash of sorted JSON representation

**Cache Key Computation**:
```python
def compute_cache_key(provider_name: str, inputs: dict[str, Any] | None) -> str:
    """Compute cache key for data provider with inputs"""
    if not inputs:
        return provider_name  # Backward compatible

    # Sort keys for deterministic hash
    input_str = json.dumps(inputs, sort_keys=True)
    input_hash = hashlib.sha256(input_str.encode()).hexdigest()[:16]
    return f"{provider_name}:{input_hash}"
```

**Storage**:
- In-memory cache (current implementation)
- Key: cache_key (as computed above)
- Value: DataProviderResponse
- TTL: From data provider metadata

---

## Data Flow Diagrams

### Form Configuration Flow (Form Builder)

```
1. User selects data provider for form field
   ↓
2. System fetches data provider metadata (/api/metadata)
   ↓
3. UI displays input configuration panel with all parameters
   ↓
4. For each parameter, user selects mode:
   - Static: Enters value directly
   - Field Reference: Selects from earlier fields
   - Expression: Writes JavaScript expression
   ↓
5. System validates configuration:
   - All required parameters configured
   - Field references valid and not circular
   - Expression syntax valid (basic check)
   ↓
6. Form saved with dataProviderInputs in FormField
```

### Form Runtime Flow (Form Renderer)

```
1. Form loads, field with dataProvider rendered
   ↓
2. For each data provider input:
   - mode="static": Use configured value
   - mode="fieldRef": Watch referenced field for changes
   - mode="expression": Evaluate expression with current context
   ↓
3. Check if all required inputs are satisfied:
   - YES: Enable field, fetch data provider options
   - NO: Disable field, show "Requires X" message
   ↓
4. When dependent field changes (blur event):
   - Re-evaluate input expressions
   - Check required inputs again
   - If satisfied: Refresh data provider options
   ↓
5. Data provider call:
   POST /api/data-providers/{name}
   Body: { inputs: { ... } }
   ↓
6. Response cached with input-aware key
   ↓
7. Options displayed in dropdown
```

### Data Provider Execution Flow (Backend)

```
1. Request arrives: POST /api/data-providers/{provider_name}
   ↓
2. Parse inputs from request body
   ↓
3. Look up data provider metadata in registry
   ↓
4. Validate inputs against parameter definitions:
   - All required parameters present
   - Types match definitions
   - Validation rules satisfied
   ↓
5. Compute cache key: provider_name:input_hash
   ↓
6. Check cache:
   - HIT: Return cached result
   - MISS: Continue to execution
   ↓
7. Call data provider function with inputs
   ↓
8. Store result in cache with TTL
   ↓
9. Return DataProviderResponse
```

## Validation Rules Summary

### At Form Save (Backend)

1. **Data Provider Inputs Validation**:
   - If dataProviderInputs is set, dataProvider must also be set
   - All required parameters from data provider metadata must have configurations
   - Field references must exist in form
   - Field references must appear earlier in field order (partial order check)

2. **Circular Dependency Detection**:
   - Build dependency graph from all fields with dataProviderInputs
   - Run cycle detection (DFS-based)
   - Reject form if any cycles found
   - Return specific error with cycle path

### At Data Provider Execution (Backend)

1. **Input Parameter Validation**:
   - All required parameters must be provided
   - Parameter types must match definitions (Pydantic coercion)
   - Validation rules applied (min, max, pattern, etc.)
   - Return 400 Bad Request with structured error if validation fails

2. **Authorization**:
   - User must have access to organization (if org-scoped)
   - Standard authentication applies (JWT validation)

### At Form Render (Frontend)

1. **Field Readiness Check**:
   - For each data provider input, evaluate based on mode
   - Check if all required inputs have valid values
   - Enable field only if all required inputs satisfied

2. **Expression Evaluation**:
   - Evaluate expressions in sandboxed context
   - Timeout after 50ms
   - Handle errors gracefully (treat as missing value)

## Migration Strategy

### Backward Compatibility

**Existing Forms**:
- Forms without dataProviderInputs continue to work
- Data providers without @param decorators work as before
- No changes to existing form data required

**New Forms**:
- dataProviderInputs is optional
- Can be added to existing forms without breaking changes
- Gradual rollout per form

### Database Changes

**None required** - Azure Table Storage is schema-less, JSON structure extends naturally.

### Code Changes

1. **Models** (shared/models.py):
   - Add DataProviderInputMode enum
   - Add DataProviderInputConfig model
   - Extend FormField with dataProviderInputs field
   - Extend DataProviderMetadata with parameters field
   - Extend DataProviderRequest with inputs field

2. **Decorators** (shared/decorators.py):
   - Modify @data_provider to collect @param decorators
   - Store parameters in DataProviderMetadata

3. **Handlers** (shared/handlers/):
   - Extend data provider handler to accept and validate inputs
   - Extend form validation to check data provider inputs
   - Add circular dependency detector

4. **Cache** (shared/handlers/data_providers_handlers.py):
   - Update cache key computation to include input hash

## Example Scenarios

### Scenario 1: GitHub Repositories Dropdown

**Form Configuration**:
```json
{
  "name": "github_repo",
  "label": "Select Repository",
  "type": "select",
  "required": true,
  "dataProvider": "get_github_repos",
  "dataProviderInputs": {
    "token": {
      "mode": "fieldRef",
      "fieldName": "github_token"
    },
    "org": {
      "mode": "static",
      "value": "microsoft"
    }
  }
}
```

**Data Provider Definition**:
```python
@data_provider(name="get_github_repos", description="...")
@param("token", type="string", label="GitHub Token", required=True)
@param("org", type="string", label="Organization", required=True)
async def get_github_repos(context, token, org):
    # Fetch repos from GitHub API
    repos = await fetch_github_repos(token, org)
    return [{"label": r.name, "value": r.id} for r in repos]
```

**Runtime Behavior**:
1. User enters token in github_token field
2. On blur, system evaluates inputs: token=<user_value>, org="microsoft"
3. Both required inputs satisfied → enable field
4. Call: POST /api/data-providers/get_github_repos with inputs
5. Cache key: `get_github_repos:a1b2c3d4...`
6. Options displayed in dropdown

### Scenario 2: Computed Expression Input

**Form Configuration**:
```json
{
  "name": "user_search",
  "label": "Search Users",
  "type": "select",
  "dataProvider": "search_users",
  "dataProviderInputs": {
    "query": {
      "mode": "expression",
      "expression": "context.field.first_name + ' ' + context.field.last_name"
    },
    "department": {
      "mode": "fieldRef",
      "fieldName": "dept_field"
    }
  }
}
```

**Runtime Behavior**:
1. User fills first_name="John" and last_name="Doe"
2. User selects department="Engineering"
3. On blur from last_name, expression evaluates: "John Doe"
4. Inputs: query="John Doe", department="Engineering"
5. Data provider called with computed inputs

### Scenario 3: Optional Input with Default

**Form Configuration**:
```json
{
  "name": "license_dropdown",
  "label": "Select License",
  "type": "select",
  "dataProvider": "get_licenses",
  "dataProviderInputs": {
    "include_trial": {
      "mode": "static",
      "value": "false"
    }
  }
}
```

**Data Provider Definition**:
```python
@data_provider(name="get_licenses", description="...")
@param("include_trial", type="bool", label="Include Trial", required=False, default_value=False)
async def get_licenses(context, include_trial=False):
    licenses = await fetch_licenses()
    if include_trial:
        licenses += await fetch_trial_licenses()
    return [{"label": l.name, "value": l.id} for l in licenses]
```

**Runtime Behavior**:
1. Field loads immediately (no required inputs)
2. Input: include_trial=false (static value)
3. Data provider returns only non-trial licenses

## Testing Data

### Test Form 1: Simple Field Reference

```json
{
  "formId": "test_001",
  "name": "GitHub Sync Setup",
  "fields": [
    {
      "name": "github_token",
      "label": "GitHub PAT",
      "type": "text",
      "required": true
    },
    {
      "name": "repo_dropdown",
      "label": "Select Repository",
      "type": "select",
      "required": true,
      "dataProvider": "get_github_repos",
      "dataProviderInputs": {
        "token": {
          "mode": "fieldRef",
          "fieldName": "github_token"
        }
      }
    }
  ]
}
```

### Test Form 2: Circular Dependency (Should Fail)

```json
{
  "formId": "test_002_invalid",
  "name": "Circular Dependency Test",
  "fields": [
    {
      "name": "field_a",
      "type": "select",
      "dataProvider": "provider_a",
      "dataProviderInputs": {
        "input_x": {
          "mode": "fieldRef",
          "fieldName": "field_b"
        }
      }
    },
    {
      "name": "field_b",
      "type": "select",
      "dataProvider": "provider_b",
      "dataProviderInputs": {
        "input_y": {
          "mode": "fieldRef",
          "fieldName": "field_a"
        }
      }
    }
  ]
}
```

**Expected Error**:
```json
{
  "error": "Circular dependency detected",
  "cycle": ["field_a", "field_b", "field_a"],
  "message": "Field 'field_a' depends on field_b, which depends on field_a (circular)"
}
```

### Test Form 3: Expression with Multiple Fields

```json
{
  "formId": "test_003",
  "name": "User Search",
  "fields": [
    {"name": "first_name", "label": "First Name", "type": "text"},
    {"name": "last_name", "label": "Last Name", "type": "text"},
    {
      "name": "user_dropdown",
      "label": "Select User",
      "type": "select",
      "dataProvider": "search_users",
      "dataProviderInputs": {
        "full_name": {
          "mode": "expression",
          "expression": "context.field.first_name + ' ' + context.field.last_name"
        }
      }
    }
  ]
}
```

## Summary

This data model extends the existing Bifrost form and data provider system with minimal changes:

1. **New Models**: DataProviderInputMode, DataProviderInputConfig
2. **Extended Models**: FormField (+ dataProviderInputs), DataProviderMetadata (+ parameters), DataProviderRequest (+ inputs)
3. **Reused Models**: WorkflowParameter (for data provider parameters)
4. **Backward Compatible**: All extensions are optional, existing forms work unchanged
5. **Table Storage**: No schema migration needed, JSON extends naturally

The design prioritizes:
- Consistency with existing workflow parameter patterns
- Backward compatibility
- Type safety with Pydantic validation
- Clear separation of concerns (config in FormField, metadata in DataProviderMetadata, runtime in Request)
