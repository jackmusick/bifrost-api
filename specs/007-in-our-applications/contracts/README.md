# API Contracts: Dynamic Data Provider Inputs

## Overview

This directory contains API contract specifications for the Dynamic Data Provider Inputs feature. These contracts define the request/response formats for both backend and frontend components.

## Contract Files

### 1. data-providers-api.yaml

OpenAPI 3.0 specification for the enhanced data provider and form management endpoints.

**Key Changes from v1.0**:

1. **DataProviderMetadata**: Now includes `parameters` array (list of WorkflowParameter)
2. **DataProviderRequest**: Now includes `inputs` object for parameter values
3. **FormField**: Now includes `dataProviderInputs` object for input configurations
4. **New Types**:
   - `DataProviderInputMode` enum (static, fieldRef, expression)
   - `DataProviderInputConfig` object (mode + value/fieldName/expression)

**Endpoints Modified**:
- `GET /api/metadata` - Returns data provider parameters
- `POST /api/data-providers/{providerName}` - Accepts input parameters
- `GET /api/data-providers/{providerName}` - Accepts inputs via query params
- `POST /api/forms` - Validates dataProviderInputs
- `PUT /api/forms/{formId}` - Validates dataProviderInputs

## Usage Examples

### 1. Fetch Data Provider Metadata

Get list of all data providers with their parameter definitions.

**Request**:
```http
GET /api/metadata
Authorization: Bearer <token>
```

**Response**:
```json
{
  "workflows": [...],
  "dataProviders": [
    {
      "name": "get_github_repos",
      "description": "Fetch GitHub repositories",
      "category": "GitHub",
      "cacheTtlSeconds": 300,
      "parameters": [
        {
          "name": "token",
          "type": "string",
          "required": true,
          "label": "GitHub Token",
          "helpText": "Personal access token with repo scope"
        },
        {
          "name": "org",
          "type": "string",
          "required": false,
          "label": "Organization",
          "defaultValue": null
        }
      ]
    }
  ]
}
```

### 2. Execute Data Provider with Inputs (POST)

Call a data provider with input parameters.

**Request**:
```http
POST /api/data-providers/get_github_repos
Authorization: Bearer <token>
Content-Type: application/json

{
  "orgId": "org-123",
  "inputs": {
    "token": "ghp_abc123...",
    "org": "microsoft"
  }
}
```

**Response**:
```json
{
  "provider": "get_github_repos",
  "cached": false,
  "cacheExpiresAt": "2025-10-22T23:00:00Z",
  "options": [
    {
      "label": "vscode",
      "value": "microsoft/vscode",
      "metadata": { "stars": 158000 }
    },
    {
      "label": "TypeScript",
      "value": "microsoft/TypeScript",
      "metadata": { "stars": 98000 }
    }
  ]
}
```

### 3. Execute Data Provider with Inputs (GET)

Alternative using query parameters (useful for caching).

**Request**:
```http
GET /api/data-providers/get_github_repos?inputs[token]=ghp_abc&inputs[org]=microsoft
Authorization: Bearer <token>
```

**Response**: Same as POST

### 4. Create Form with Data Provider Inputs

Create a form with a field that has data provider input configuration.

**Request**:
```http
POST /api/forms
Authorization: Bearer <token>
Content-Type: application/json

{
  "name": "GitHub Sync Setup",
  "description": "Configure GitHub integration",
  "orgId": "org-123",
  "schema": {
    "fields": [
      {
        "name": "github_token",
        "label": "GitHub Personal Access Token",
        "type": "text",
        "required": true
      },
      {
        "name": "repository",
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
    ]
  }
}
```

**Response**:
```json
{
  "formId": "form-456",
  "name": "GitHub Sync Setup",
  "description": "Configure GitHub integration",
  "orgId": "org-123",
  "schema": { ... },
  "createdAt": "2025-10-22T12:00:00Z",
  "createdBy": "user@example.com"
}
```

### 5. Validation Error - Missing Required Parameter

**Request**:
```http
POST /api/forms
...
{
  "schema": {
    "fields": [
      {
        "name": "repo_field",
        "type": "select",
        "dataProvider": "get_github_repos",
        "dataProviderInputs": {
          "org": { "mode": "static", "value": "microsoft" }
        }
      }
    ]
  }
}
```

**Response** (400 Bad Request):
```json
{
  "error": "Validation failed",
  "message": "Data provider 'get_github_repos' requires parameter 'token' but no configuration provided",
  "details": {
    "field": "repo_field",
    "provider": "get_github_repos",
    "missingParams": ["token"]
  }
}
```

### 6. Validation Error - Circular Dependency

**Request**:
```http
POST /api/forms
...
{
  "schema": {
    "fields": [
      {
        "name": "field_a",
        "type": "select",
        "dataProvider": "provider_a",
        "dataProviderInputs": {
          "input_x": { "mode": "fieldRef", "fieldName": "field_b" }
        }
      },
      {
        "name": "field_b",
        "type": "select",
        "dataProvider": "provider_b",
        "dataProviderInputs": {
          "input_y": { "mode": "fieldRef", "fieldName": "field_a" }
        }
      }
    ]
  }
}
```

**Response** (400 Bad Request):
```json
{
  "error": "Validation failed",
  "message": "Circular dependency detected: field_a → field_b → field_a",
  "details": {
    "cycle": ["field_a", "field_b", "field_a"]
  }
}
```

### 7. Validation Error - Invalid Input Value

**Request**:
```http
POST /api/data-providers/get_user_licenses
Content-Type: application/json

{
  "inputs": {
    "max_results": "not_a_number"
  }
}
```

**Response** (400 Bad Request):
```json
{
  "error": "Validation failed",
  "message": "Parameter 'max_results' must be of type int",
  "details": {
    "parameter": "max_results",
    "expectedType": "int",
    "receivedValue": "not_a_number"
  }
}
```

## Frontend Contract (TypeScript)

While the backend uses OpenAPI, the frontend client should use these TypeScript interfaces:

```typescript
// Data provider input configuration
type DataProviderInputMode = "static" | "fieldRef" | "expression";

interface DataProviderInputConfig {
  mode: DataProviderInputMode;
  value?: string;       // Set when mode="static"
  fieldName?: string;   // Set when mode="fieldRef"
  expression?: string;  // Set when mode="expression"
}

// Extended FormField
interface FormField {
  name: string;
  label: string;
  type: FormFieldType;
  required?: boolean;
  validation?: Record<string, any>;
  dataProvider?: string;
  dataProviderInputs?: Record<string, DataProviderInputConfig>;
  defaultValue?: any;
  visibilityExpression?: string;
}

// Data provider metadata with parameters
interface DataProviderMetadata {
  name: string;
  description: string;
  category?: string;
  cacheTtlSeconds?: number;
  parameters: WorkflowParameter[];
}

// Data provider request
interface DataProviderRequest {
  orgId?: string;
  inputs?: Record<string, any>;
}

// Data provider response
interface DataProviderResponse {
  provider: string;
  options: DataProviderOption[];
  cached: boolean;
  cacheExpiresAt: string;
}

interface DataProviderOption {
  label: string;
  value: string;
  metadata?: Record<string, any>;
}
```

## Validation Rules

### Backend Validation (at Form Save)

1. **DataProviderInputs consistency**:
   - If `dataProviderInputs` is set, `dataProvider` must also be set
   - All required parameters from data provider must have configurations
   - Field references must exist in the form
   - Field references must appear earlier in field order (no forward refs)

2. **Circular dependency detection**:
   - Build dependency graph from all fields
   - Run cycle detection algorithm
   - Return specific error with cycle path if found

3. **Input mode validation**:
   - mode="static" requires value field
   - mode="fieldRef" requires fieldName field
   - mode="expression" requires expression field

### Runtime Validation (at Data Provider Execution)

1. **Parameter presence**:
   - All required parameters must be provided in inputs
   - Optional parameters can be omitted (use defaults)

2. **Type validation**:
   - Parameter values must match declared types
   - Pydantic handles type coercion (e.g., "123" → 123 for int)

3. **Validation rules**:
   - Apply min/max/pattern rules from parameter definitions
   - Return structured error for validation failures

### Frontend Validation (at Form Render)

1. **Field readiness**:
   - Evaluate all dataProviderInputs based on mode
   - Check if all required parameters have valid values
   - Disable field if any required parameter is missing/invalid

2. **Expression evaluation**:
   - Evaluate expressions in sandboxed context
   - Handle errors gracefully (treat as missing value)
   - Timeout after 50ms

## Migration Path

### Backward Compatibility

**Phase 1**: Deploy backend changes
- Existing data providers without @param decorators work unchanged
- Existing forms without dataProviderInputs work unchanged
- New metadata field (parameters) defaults to empty array

**Phase 2**: Update data providers
- Add @param decorators to data providers needing inputs
- Deploy updated data providers
- Forms can now configure inputs for these providers

**Phase 3**: Update forms
- Forms can be updated to use dataProviderInputs
- Old forms continue to work
- Gradual migration form by form

## Testing Checklist

### Contract Tests

- [ ] GET /api/metadata returns parameters for data providers with @param
- [ ] POST /api/data-providers/{name} accepts inputs object
- [ ] POST /api/data-providers/{name} validates required parameters
- [ ] POST /api/data-providers/{name} validates parameter types
- [ ] GET /api/data-providers/{name} accepts inputs via query params
- [ ] POST /api/forms validates dataProviderInputs (required params)
- [ ] POST /api/forms detects circular dependencies
- [ ] PUT /api/forms validates dataProviderInputs

### Integration Tests

- [ ] Data provider with required input rejects calls without it
- [ ] Data provider with optional input uses default when omitted
- [ ] Data provider with inputs caches correctly (different cache keys)
- [ ] Form save rejects circular dependency A→B→A
- [ ] Form save rejects circular dependency A→B→C→A
- [ ] Form save allows valid dependency chain A→B→C

### E2E Tests (Frontend)

- [ ] Form builder displays input config UI for data provider with params
- [ ] Static input mode saves and loads correctly
- [ ] Field reference input mode shows only earlier fields
- [ ] Expression input mode evaluates correctly
- [ ] Dropdown disables when required input missing
- [ ] Dropdown enables when required input satisfied
- [ ] Dropdown refreshes on blur from dependent field
- [ ] Error message displays when data provider fails

## Notes

- All timestamps are in ISO 8601 format (UTC)
- Cache keys include input parameter hash for correct cache isolation
- Expression evaluation is sandboxed (same as visibilityExpression)
- Circular dependency errors include the full cycle path for debugging
