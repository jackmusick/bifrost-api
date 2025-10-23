# Quickstart Guide: Dynamic Data Provider Inputs

**Feature**: 007-in-our-applications
**Audience**: Developers implementing this feature
**Estimated Reading Time**: 15 minutes

## Overview

This guide walks you through implementing data provider input parameters, from backend decorator usage to frontend form configuration. By the end, you'll be able to create data providers that accept parameters and configure forms to pass values dynamically.

## Prerequisites

- Familiarity with the existing `@workflow` and `@param` decorator pattern
- Understanding of Azure Functions and Python async/await
- Basic React/TypeScript knowledge for frontend components
- Understanding of the existing form builder and visibilityExpression feature

## Part 1: Backend - Creating a Data Provider with Parameters

### Step 1: Define a Data Provider with @param Decorators

```python
# File: platform/my_integrations.py

from bifrost import data_provider, param

@data_provider(
    name="get_github_repos",
    description="Fetch repositories from GitHub for a given organization",
    category="GitHub",
    cache_ttl_seconds=300
)
@param("token", type="string", label="GitHub Token", required=True,
       help_text="Personal access token with repo scope")
@param("org", type="string", label="Organization", required=False,
       default_value=None, help_text="GitHub organization name (optional)")
async def get_github_repos(context, token, org=None):
    """
    Fetch GitHub repositories using the provided token and optional org filter.

    Args:
        context: Execution context
        token: GitHub personal access token
        org: Optional organization name to filter repos

    Returns:
        List of DataProviderOption dicts with label, value, and metadata
    """
    import aiohttp

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json"
    }

    if org:
        url = f"https://api.github.com/orgs/{org}/repos"
    else:
        url = "https://api.github.com/user/repos"

    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as resp:
            if resp.status != 200:
                raise Exception(f"GitHub API error: {resp.status}")

            repos = await resp.json()

    return [
        {
            "label": repo["name"],
            "value": repo["full_name"],
            "metadata": {
                "stars": repo["stargazers_count"],
                "private": repo["private"],
                "url": repo["html_url"]
            }
        }
        for repo in repos
    ]
```

**Key Points**:
- Use same `@param` decorator as workflows
- Parameters become function arguments (after `context`)
- Order doesn't matter (matched by name)
- Required parameters must not have defaults in function signature
- Optional parameters should have defaults matching `default_value`

### Step 2: Test the Data Provider Locally

```python
# File: tests/integration/test_github_data_provider.py

import pytest
from platform.my_integrations import get_github_repos

@pytest.mark.asyncio
async def test_get_github_repos_with_org(mock_context):
    """Test data provider with all parameters"""
    # Mock context with necessary integrations
    options = await get_github_repos(
        mock_context,
        token="ghp_test_token",
        org="microsoft"
    )

    assert isinstance(options, list)
    assert len(options) > 0
    assert all("label" in opt and "value" in opt for opt in options)

@pytest.mark.asyncio
async def test_get_github_repos_without_org(mock_context):
    """Test data provider with optional parameter omitted"""
    options = await get_github_repos(
        mock_context,
        token="ghp_test_token",
        org=None  # or omit entirely
    )

    assert isinstance(options, list)

@pytest.mark.asyncio
async def test_get_github_repos_invalid_token(mock_context):
    """Test data provider with invalid input"""
    with pytest.raises(Exception, match="GitHub API error"):
        await get_github_repos(
            mock_context,
            token="invalid_token",
            org="microsoft"
        )
```

### Step 3: Verify Metadata API Returns Parameters

```bash
# Start local functions
func start

# Query metadata endpoint
curl http://localhost:7071/api/metadata

# Expected response includes:
{
  "dataProviders": [
    {
      "name": "get_github_repos",
      "description": "Fetch repositories from GitHub...",
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

## Part 2: Backend - Calling Data Provider with Inputs

### Step 1: Test Data Provider Execution via API

```bash
# Using POST with JSON body
curl -X POST http://localhost:7071/api/data-providers/get_github_repos \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <your-jwt>" \
  -d '{
    "inputs": {
      "token": "ghp_your_actual_token",
      "org": "microsoft"
    }
  }'

# Using GET with query parameters
curl "http://localhost:7071/api/data-providers/get_github_repos?inputs[token]=ghp_token&inputs[org]=microsoft" \
  -H "Authorization: Bearer <your-jwt>"
```

### Step 2: Verify Cache Key Isolation

```python
# File: tests/integration/test_data_provider_caching.py

@pytest.mark.asyncio
async def test_cache_key_includes_inputs(test_client):
    """Verify different inputs produce different cache entries"""

    # Call 1: org=microsoft
    response1 = await test_client.post(
        "/api/data-providers/get_github_repos",
        json={"inputs": {"token": "test", "org": "microsoft"}}
    )
    assert response1.status_code == 200
    assert response1.json()["cached"] == False

    # Call 2: org=google (different input, should NOT be cached)
    response2 = await test_client.post(
        "/api/data-providers/get_github_repos",
        json={"inputs": {"token": "test", "org": "google"}}
    )
    assert response2.status_code == 200
    assert response2.json()["cached"] == False

    # Call 3: org=microsoft again (should be cached)
    response3 = await test_client.post(
        "/api/data-providers/get_github_repos",
        json={"inputs": {"token": "test", "org": "microsoft"}}
    )
    assert response3.status_code == 200
    assert response3.json()["cached"] == True
```

## Part 3: Backend - Form Validation

### Step 1: Create Form with Data Provider Inputs

```python
# File: tests/contract/test_form_with_data_provider_inputs.py

@pytest.mark.asyncio
async def test_create_form_with_field_reference(test_client):
    """Test creating a form with field reference input"""

    form_data = {
        "name": "GitHub Sync Setup",
        "description": "Configure GitHub integration",
        "schema": {
            "fields": [
                {
                    "name": "github_token",
                    "label": "GitHub Personal Access Token",
                    "type": "text",
                    "required": True
                },
                {
                    "name": "repository",
                    "label": "Select Repository",
                    "type": "select",
                    "required": True,
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

    response = await test_client.post("/api/forms", json=form_data)
    assert response.status_code == 201

    form = response.json()
    assert form["schema"]["fields"][1]["dataProviderInputs"]["token"]["mode"] == "fieldRef"
```

### Step 2: Test Circular Dependency Detection

```python
@pytest.mark.asyncio
async def test_circular_dependency_rejected(test_client):
    """Test that circular dependencies are rejected"""

    form_data = {
        "name": "Invalid Form",
        "description": "Form with circular dependency",
        "schema": {
            "fields": [
                {
                    "name": "field_a",
                    "type": "select",
                    "label": "Field A",
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
                    "label": "Field B",
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
    }

    response = await test_client.post("/api/forms", json=form_data)
    assert response.status_code == 400

    error = response.json()
    assert "Circular dependency" in error["message"]
    assert "cycle" in error["details"]
    assert error["details"]["cycle"] == ["field_a", "field_b", "field_a"]
```

## Part 4: Frontend - Form Builder UI

### Step 1: Fetch Data Provider Metadata

```typescript
// File: client/src/services/dataProviderService.ts

export interface DataProviderParameter {
  name: string;
  type: string;
  required: boolean;
  label?: string;
  defaultValue?: any;
  helpText?: string;
}

export interface DataProviderMetadata {
  name: string;
  description: string;
  category?: string;
  cacheTtlSeconds?: number;
  parameters: DataProviderParameter[];
}

export async function getDataProviderMetadata(): Promise<DataProviderMetadata[]> {
  const response = await apiClient.get<{ dataProviders: DataProviderMetadata[] }>(
    '/api/metadata'
  );
  return response.dataProviders;
}
```

### Step 2: Build Input Configuration UI Component

```typescript
// File: client/src/components/FormBuilder/DataProviderInputConfig.tsx

import React, { useState, useEffect } from 'react';
import { DataProviderMetadata, DataProviderParameter } from '@/services/dataProviderService';

interface Props {
  dataProvider: DataProviderMetadata;
  existingInputs?: Record<string, DataProviderInputConfig>;
  availableFields: Array<{ name: string; label: string }>;
  onChange: (inputs: Record<string, DataProviderInputConfig>) => void;
}

export function DataProviderInputConfig({
  dataProvider,
  existingInputs = {},
  availableFields,
  onChange
}: Props) {
  const [inputs, setInputs] = useState(existingInputs);

  // Update parent when inputs change
  useEffect(() => {
    onChange(inputs);
  }, [inputs, onChange]);

  const handleModeChange = (paramName: string, mode: DataProviderInputMode) => {
    setInputs(prev => ({
      ...prev,
      [paramName]: {
        mode,
        value: mode === 'static' ? prev[paramName]?.value || '' : undefined,
        fieldName: mode === 'fieldRef' ? prev[paramName]?.fieldName || '' : undefined,
        expression: mode === 'expression' ? prev[paramName]?.expression || '' : undefined,
      }
    }));
  };

  const handleValueChange = (paramName: string, field: string, value: string) => {
    setInputs(prev => ({
      ...prev,
      [paramName]: {
        ...prev[paramName],
        [field]: value
      }
    }));
  };

  return (
    <div className="data-provider-inputs">
      <h4>Data Provider Inputs</h4>
      {dataProvider.parameters.map((param) => (
        <div key={param.name} className="input-config">
          <label>
            {param.label || param.name}
            {param.required && <span className="required">*</span>}
          </label>
          {param.helpText && <p className="help-text">{param.helpText}</p>}

          <select
            value={inputs[param.name]?.mode || 'static'}
            onChange={(e) => handleModeChange(param.name, e.target.value as DataProviderInputMode)}
          >
            <option value="static">Static Value</option>
            <option value="fieldRef">Field Reference</option>
            <option value="expression">JavaScript Expression</option>
          </select>

          {inputs[param.name]?.mode === 'static' && (
            <input
              type="text"
              value={inputs[param.name]?.value || ''}
              onChange={(e) => handleValueChange(param.name, 'value', e.target.value)}
              placeholder="Enter value"
            />
          )}

          {inputs[param.name]?.mode === 'fieldRef' && (
            <select
              value={inputs[param.name]?.fieldName || ''}
              onChange={(e) => handleValueChange(param.name, 'fieldName', e.target.value)}
            >
              <option value="">Select field...</option>
              {availableFields.map(field => (
                <option key={field.name} value={field.name}>
                  {field.label}
                </option>
              ))}
            </select>
          )}

          {inputs[param.name]?.mode === 'expression' && (
            <textarea
              value={inputs[param.name]?.expression || ''}
              onChange={(e) => handleValueChange(param.name, 'expression', e.target.value)}
              placeholder="e.g., context.field.first_name + ' ' + context.field.last_name"
              rows={3}
            />
          )}
        </div>
      ))}
    </div>
  );
}
```

## Part 5: Frontend - Form Runtime with Dynamic Refresh

### Step 1: Create Hook for Managing Data Provider Inputs

```typescript
// File: client/src/hooks/useDataProviderInputs.ts

import { useState, useEffect, useCallback } from 'react';
import { evaluateExpression } from '@/utils/expressionEvaluator';

interface UseDataProviderInputsOptions {
  dataProviderInputs: Record<string, DataProviderInputConfig>;
  formValues: Record<string, any>;
  workflowContext?: any;
  parameters: DataProviderParameter[];
}

export function useDataProviderInputs({
  dataProviderInputs,
  formValues,
  workflowContext,
  parameters
}: UseDataProviderInputsOptions) {
  const [evaluatedInputs, setEvaluatedInputs] = useState<Record<string, any>>({});
  const [isReady, setIsReady] = useState(false);
  const [missingRequired, setMissingRequired] = useState<string[]>([]);

  // Evaluate inputs based on mode
  const evaluateInputs = useCallback(() => {
    const context = {
      field: formValues,
      workflow: workflowContext
    };

    const evaluated: Record<string, any> = {};
    const missing: string[] = [];

    for (const [paramName, config] of Object.entries(dataProviderInputs)) {
      const param = parameters.find(p => p.name === paramName);

      if (config.mode === 'static') {
        evaluated[paramName] = config.value;
      } else if (config.mode === 'fieldRef') {
        evaluated[paramName] = formValues[config.fieldName!];
      } else if (config.mode === 'expression') {
        try {
          evaluated[paramName] = evaluateExpression(config.expression!, context);
        } catch (error) {
          console.error(`Expression evaluation error for ${paramName}:`, error);
          evaluated[paramName] = undefined;
        }
      }

      // Check if required parameter is missing
      if (param?.required && !evaluated[paramName]) {
        missing.push(param.label || paramName);
      }
    }

    setEvaluatedInputs(evaluated);
    setMissingRequired(missing);
    setIsReady(missing.length === 0);
  }, [dataProviderInputs, formValues, workflowContext, parameters]);

  // Re-evaluate when dependencies change
  useEffect(() => {
    evaluateInputs();
  }, [evaluateInputs]);

  return {
    inputs: evaluatedInputs,
    isReady,
    missingRequired
  };
}
```

### Step 2: Dynamic Data Provider Field Component

```typescript
// File: client/src/components/FormRenderer/DynamicDataProviderField.tsx

import React, { useState, useEffect } from 'react';
import { useDataProviderInputs } from '@/hooks/useDataProviderInputs';
import { executeDataProvider } from '@/services/dataProviderService';

interface Props {
  field: FormField;
  value: string | undefined;
  onChange: (value: string) => void;
  formValues: Record<string, any>;
  workflowContext?: any;
  dataProviderMetadata: DataProviderMetadata;
}

export function DynamicDataProviderField({
  field,
  value,
  onChange,
  formValues,
  workflowContext,
  dataProviderMetadata
}: Props) {
  const [options, setOptions] = useState<DataProviderOption[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const { inputs, isReady, missingRequired } = useDataProviderInputs({
    dataProviderInputs: field.dataProviderInputs || {},
    formValues,
    workflowContext,
    parameters: dataProviderMetadata.parameters
  });

  // Fetch options when ready
  useEffect(() => {
    if (!isReady) {
      setOptions([]);
      return;
    }

    const fetchOptions = async () => {
      setLoading(true);
      setError(null);

      try {
        const response = await executeDataProvider(field.dataProvider!, inputs);
        setOptions(response.options);
      } catch (err: any) {
        setError(err.message || 'Failed to load options');
        setOptions([]);
      } finally {
        setLoading(false);
      }
    };

    fetchOptions();
  }, [field.dataProvider, inputs, isReady]);

  // Disabled state message
  const getDisabledMessage = () => {
    if (missingRequired.length === 0) return '';
    return `Requires: ${missingRequired.join(', ')}`;
  };

  return (
    <div className="dynamic-data-provider-field">
      <label>{field.label}</label>

      <select
        value={value || ''}
        onChange={(e) => onChange(e.target.value)}
        disabled={!isReady || loading}
      >
        <option value="">
          {loading ? 'Loading...' : !isReady ? getDisabledMessage() : 'Select an option...'}
        </option>
        {options.map(opt => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>

      {error && <div className="error-message">{error}</div>}
    </div>
  );
}
```

### Step 3: Register Blur Event Handlers

```typescript
// File: client/src/components/FormRenderer/FormRenderer.tsx

export function FormRenderer({ form }: Props) {
  const [formValues, setFormValues] = useState<Record<string, any>>({});
  const [fieldDependencies, setFieldDependencies] = useState<Map<string, Set<string>>>(new Map());

  // Build dependency map on mount
  useEffect(() => {
    const deps = new Map<string, Set<string>>();

    for (const field of form.schema.fields) {
      if (field.dataProviderInputs) {
        for (const config of Object.values(field.dataProviderInputs)) {
          if (config.mode === 'fieldRef') {
            const dependents = deps.get(config.fieldName!) || new Set();
            dependents.add(field.name);
            deps.set(config.fieldName!, dependents);
          } else if (config.mode === 'expression') {
            // Parse expression for field references
            const refs = extractFieldReferences(config.expression!);
            refs.forEach(ref => {
              const dependents = deps.get(ref) || new Set();
              dependents.add(field.name);
              deps.set(ref, dependents);
            });
          }
        }
      }
    }

    setFieldDependencies(deps);
  }, [form]);

  // Handle blur event - trigger refresh of dependent fields
  const handleFieldBlur = (fieldName: string) => {
    const dependentFields = fieldDependencies.get(fieldName);
    if (dependentFields) {
      // Trigger re-render of dependent fields
      // (useDataProviderInputs hook will detect change and re-evaluate)
      setFormValues(prev => ({ ...prev })); // Force update
    }
  };

  return (
    <form>
      {form.schema.fields.map(field => (
        <div key={field.name}>
          {field.dataProvider ? (
            <DynamicDataProviderField
              field={field}
              value={formValues[field.name]}
              onChange={(val) => setFormValues(prev => ({ ...prev, [field.name]: val }))}
              formValues={formValues}
              dataProviderMetadata={/* ... */}
            />
          ) : (
            <input
              type="text"
              value={formValues[field.name] || ''}
              onChange={(e) => setFormValues(prev => ({ ...prev, [field.name]: e.target.value }))}
              onBlur={() => handleFieldBlur(field.name)}
            />
          )}
        </div>
      ))}
    </form>
  );
}
```

## Common Patterns

### Pattern 1: Token + Resource Selection

**Use Case**: User enters API token, then selects resource requiring that token.

```json
{
  "fields": [
    { "name": "api_token", "type": "text", "label": "API Token" },
    {
      "name": "resource",
      "type": "select",
      "label": "Select Resource",
      "dataProvider": "get_resources",
      "dataProviderInputs": {
        "token": { "mode": "fieldRef", "fieldName": "api_token" }
      }
    }
  ]
}
```

### Pattern 2: Cascading Dropdowns

**Use Case**: Country → State → City selection.

```json
{
  "fields": [
    { "name": "country", "type": "select", "dataProvider": "get_countries" },
    {
      "name": "state",
      "type": "select",
      "dataProvider": "get_states",
      "dataProviderInputs": {
        "country_code": { "mode": "fieldRef", "fieldName": "country" }
      }
    },
    {
      "name": "city",
      "type": "select",
      "dataProvider": "get_cities",
      "dataProviderInputs": {
        "state_code": { "mode": "fieldRef", "fieldName": "state" }
      }
    }
  ]
}
```

### Pattern 3: Computed Search Query

**Use Case**: Search for users by combining first and last name.

```json
{
  "fields": [
    { "name": "first_name", "type": "text", "label": "First Name" },
    { "name": "last_name", "type": "text", "label": "Last Name" },
    {
      "name": "user_selection",
      "type": "select",
      "dataProvider": "search_users",
      "dataProviderInputs": {
        "query": {
          "mode": "expression",
          "expression": "context.field.first_name + ' ' + context.field.last_name"
        }
      }
    }
  ]
}
```

## Troubleshooting

### Problem: Data provider not refreshing on field change

**Solution**: Ensure blur event handler is registered on the referenced field. Check that `useDataProviderInputs` hook is re-evaluating when `formValues` changes.

### Problem: "Required parameter missing" error

**Solution**: Check that all required parameters have configurations in `dataProviderInputs`. Verify input mode matches the parameter name exactly.

### Problem: Circular dependency not detected

**Solution**: Verify form validation is running on save. Check that dependency graph builder correctly parses both `fieldRef` and `expression` modes for references.

### Problem: Cache returning stale data with different inputs

**Solution**: Verify cache key includes input hash. Check backend logs to see computed cache keys.

### Problem: Expression evaluation fails silently

**Solution**: Check browser console for expression evaluation errors. Verify expression syntax and that referenced fields exist in context.

## Next Steps

1. **Read the full specification**: [spec.md](./spec.md)
2. **Review data model details**: [data-model.md](./data-model.md)
3. **Study API contracts**: [contracts/README.md](./contracts/README.md)
4. **Review research decisions**: [research.md](./research.md)
5. **Start implementation**: Follow [tasks.md](./tasks.md) (generated via `/speckit.tasks`)

## Resources

- **Existing Workflow Parameters**: `shared/decorators.py::@param`
- **Existing Expression Evaluator**: `client/src/utils/expressionEvaluator.ts`
- **Form Validation**: `shared/handlers/forms_handlers.py`
- **Data Provider Cache**: `shared/handlers/data_providers_handlers.py`
- **Form Builder**: `client/src/components/FormBuilder/`

## Questions?

Refer to the full specification or reach out to the team for clarification on any aspect of this feature.
