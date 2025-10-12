# Research: MSP Automation Platform MVP

**Phase**: 0 (Outline & Research)
**Date**: 2025-10-10
**Purpose**: Document technology decisions, best practices, and implementation patterns for MVP

## Overview

This document consolidates research findings for building a code-first MSP automation platform. All decisions align with the project constitution and prioritize developer experience, local debugging, and multi-tenancy.

---

## 1. Azure Functions V2 Programming Model (Python)

### Decision

Use Azure Functions Python v2 programming model with decorator-based HTTP triggers and blueprints for code organization.

### Rationale

- **Constitution Compliance**: Aligns with Principle I (Azure-First) and Principle III (Python Backend Standard)
- **Better developer experience**: Decorator syntax is more Pythonic than v1 JSON-based function.json
- **Code organization**: Blueprints allow grouping related functions (organizations, forms, permissions)
- **Local debugging**: Works seamlessly with VSCode Python debugger and func CLI
- **Type safety**: Integrates well with type hints and Pydantic models

### Implementation Pattern

```python
# function_app.py
import azure.functions as func
from functions import organizations_bp, forms_bp, permissions_bp

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

# Register blueprints
app.register_functions(organizations_bp)
app.register_functions(forms_bp)
app.register_functions(permissions_bp)

# functions/organizations.py
import azure.functions as func

bp = func.Blueprint()

@bp.route(route="organizations", methods=["GET", "POST"])
@require_auth  # Custom decorator for token validation
async def organizations(req: func.HttpRequest) -> func.HttpResponse:
    # Implementation
    pass
```

### Alternatives Considered

- **Functions v1**: Rejected due to poor DX (separate function.json files, harder to maintain)
- **FastAPI on App Service**: Rejected to stay within Azure Functions (serverless, better cold start for our scale)

### References

- [Azure Functions Python v2 docs](https://learn.microsoft.com/en-us/azure/azure-functions/functions-reference-python)
- Constitution Principle III: Python Backend Standard

---

## 2. Workflow Decorator Pattern & Auto-Registration

### Decision

Use Python decorators (`@workflow`, `@data_provider`, `@param`) to define workflows and automatically discover/register them at startup using module introspection.

### Rationale

- **Developer experience**: Minimal boilerplate - developers just write business logic
- **Discoverability**: Workflows automatically appear in metadata endpoint without manual registration
- **Type safety**: Decorators enforce parameter definitions and validation
- **Local debugging**: Functions are just Python functions - can be called directly with mock context
- **Metadata generation**: Decorators capture all metadata needed for form generation

### Implementation Pattern

```python
# shared/decorators.py
import inspect
import functools
from typing import Callable, Any, Dict, List
from shared.registry import workflow_registry, data_provider_registry

def workflow(
    name: str,
    description: str,
    category: str = "general",
    requires_org: bool = True
):
    """Decorator to register a workflow function."""
    def decorator(func: Callable) -> Callable:
        # Extract parameter metadata from @param decorators
        params = getattr(func, '_workflow_params', [])

        # Register in global registry
        workflow_registry.register(
            name=name,
            description=description,
            category=category,
            function=func,
            parameters=params,
            requires_org=requires_org
        )

        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Auto-load organization context if required
            if requires_org:
                context = await load_org_context(kwargs.get('org_id'))
                return await func(context, **kwargs)
            else:
                return await func(**kwargs)

        return wrapper
    return decorator

def param(name: str, type: str, required: bool = False, options_from: str = None):
    """Decorator to define workflow parameters."""
    def decorator(func: Callable) -> Callable:
        if not hasattr(func, '_workflow_params'):
            func._workflow_params = []

        func._workflow_params.append({
            'name': name,
            'type': type,
            'required': required,
            'data_provider': options_from
        })

        return func
    return decorator

def data_provider(name: str, description: str):
    """Decorator to register a data provider function."""
    def decorator(func: Callable) -> Callable:
        data_provider_registry.register(
            name=name,
            description=description,
            function=func
        )

        @functools.wraps(func)
        async def wrapper(context, **kwargs):
            result = await func(context, **kwargs)
            # Ensure result is list of {label, value} dicts
            return [{"label": r.get("label"), "value": r.get("value")} for r in result]

        return wrapper
    return decorator

# workflows/user_onboarding.py
from shared.decorators import workflow, param

@workflow(
    name="user_onboarding",
    description="Onboard new M365 user with license",
    category="user_management"
)
@param("first_name", type="string", required=True)
@param("last_name", type="string", required=True)
@param("license", type="string", required=True, options_from="get_available_licenses")
async def onboard_user(context, first_name, last_name, license):
    graph = context.get_integration('msgraph')
    # Business logic here
    return {"success": True, "user_id": "..."}
```

### Auto-Discovery at Startup

```python
# shared/registry.py
import importlib
import pkgutil
from pathlib import Path

class WorkflowRegistry:
    def __init__(self):
        self._workflows = {}

    def register(self, name, description, category, function, parameters, requires_org):
        self._workflows[name] = {
            'name': name,
            'description': description,
            'category': category,
            'function': function,
            'parameters': parameters,
            'requires_org': requires_org
        }

    def discover_workflows(self, package_name='workflows'):
        """Auto-discover all @workflow decorated functions."""
        import workflows  # Import the workflows package

        # Walk through all modules in the package
        for importer, modname, ispkg in pkgutil.walk_packages(
            path=workflows.__path__,
            prefix=f"{workflows.__name__}."
        ):
            importlib.import_module(modname)

        # Workflows are already registered via decorators during import
        return self._workflows

    def get_metadata(self):
        """Return metadata for all registered workflows."""
        return [
            {
                'name': wf['name'],
                'description': wf['description'],
                'category': wf['category'],
                'parameters': wf['parameters'],
                'requires_org': wf['requires_org']
            }
            for wf in self._workflows.values()
        ]

workflow_registry = WorkflowRegistry()

# In function_app.py startup
workflow_registry.discover_workflows()
data_provider_registry.discover_data_providers()
```

### Alternatives Considered

- **Manual registration**: Rejected - requires developers to remember to register workflows
- **Configuration files (YAML/JSON)**: Rejected - adds complexity, defeats code-first purpose
- **Class-based workflows**: Rejected - decorator pattern is more Pythonic

### References

- Python decorator best practices
- MODULE introspection with `pkgutil` and `importlib`

---

## 3. Multi-Tenant Table Storage Partitioning Strategy

### Decision

Use **organization ID as partition key** for all org-scoped entities. Implement **dual-indexing pattern** for bidirectional lookups (e.g., UserPermissions and OrgPermissions).

### Rationale

- **Constitution Compliance**: Required by Principle V (Multi-Tenancy by Design) and Principle II (Table Storage Only)
- **Performance**: Single-partition queries are <10ms for org-scoped data
- **Data isolation**: Partition-level isolation prevents cross-org data leakage
- **Scalability**: Azure Table Storage auto-scales with partition key distribution

### Table Design Patterns

| Table | PartitionKey | RowKey | Purpose |
|-------|--------------|--------|---------|
| **Organizations** | `"ORG"` | `{OrgId}` | List all orgs (single partition) |
| **OrgConfig** | `{OrgId}` | `"config:{key}"` | Org-specific configuration |
| **IntegrationConfig** | `{OrgId}` | `"integration:{type}"` | Integration settings per org |
| **Forms** | `{OrgId}` or `"GLOBAL"` | `{FormId}` | Org-specific or global forms |
| **UserPermissions** | `{UserId}` | `{OrgId}` | "What orgs can user access?" |
| **OrgPermissions** | `{OrgId}` | `{UserId}` | "Who can access this org?" |
| **WorkflowExecutions** | `{OrgId}` | `{ReverseTs}_{ExecId}` | Execution history per org |
| **UserExecutions** | `{UserId}` | `{ReverseTs}_{ExecId}` | Execution history per user |

### Dual-Indexing Implementation

```python
# shared/storage.py
from azure.data.tables.aio import TableServiceClient
from typing import Dict, Any

class TableStorageService:
    async def grant_permission(
        self,
        user_id: str,
        org_id: str,
        permissions: Dict[str, bool]
    ):
        """Grant permissions with dual-indexing pattern."""
        entity = {
            'PartitionKey': user_id,
            'RowKey': org_id,
            **permissions,  # CanExecuteWorkflows, CanManageConfig, etc.
            'GrantedBy': current_user_id,
            'GrantedAt': datetime.utcnow()
        }

        # Write to UserPermissions table (query by user)
        await self._table_client('UserPermissions').upsert_entity(entity)

        # Write to OrgPermissions table (query by org)
        entity_org = entity.copy()
        entity_org['PartitionKey'] = org_id
        entity_org['RowKey'] = user_id
        await self._table_client('OrgPermissions').upsert_entity(entity_org)
```

### Alternatives Considered

- **User ID as partition key for all tables**: Rejected - doesn't support org-scoped queries efficiently
- **Composite keys**: Not supported by Table Storage
- **Secondary indexes**: Table Storage doesn't support them - dual-indexing is the pattern

### References

- [Azure Table Storage best practices](https://learn.microsoft.com/en-us/azure/storage/tables/table-storage-design-guide)
- Constitution Principle V: Multi-Tenancy by Design
- PROJECT.md: Data Storage Strategy section

---

## 4. Organization Context Loading Pattern

### Decision

Use a **decorator pattern** to automatically load OrganizationContext once per request and pass it to workflow/data provider functions. Context includes org data, config, secrets, and pre-authenticated integration clients.

### Rationale

- **Developer experience**: Developers never manually load context - it's always available
- **Performance**: Load once per request, cached in request scope
- **Security**: Validates org access before loading context
- **Testability**: Easy to mock context for unit/integration tests

### Implementation Pattern

```python
# shared/context.py
from typing import Dict, Any, Optional
from dataclasses import dataclass
from azure.identity.aio import DefaultAzureCredential
from azure.keyvault.secrets.aio import SecretClient

@dataclass
class Organization:
    org_id: str
    name: str
    tenant_id: Optional[str]
    is_active: bool

@dataclass
class Caller:
    user_id: str
    email: str
    name: str

class OrganizationContext:
    def __init__(
        self,
        org: Organization,
        config: Dict[str, Any],
        integrations: Dict[str, Any],
        caller: Caller
    ):
        self.org = org
        self.config = config
        self._integrations = integrations
        self.caller = caller
        self._integration_clients = {}

    def get_integration(self, integration_name: str):
        """Get pre-authenticated integration client."""
        if integration_name not in self._integration_clients:
            self._integration_clients[integration_name] = self._create_integration_client(integration_name)
        return self._integration_clients[integration_name]

    async def _create_integration_client(self, name: str):
        """Factory for integration clients."""
        from shared.integrations import get_integration_client
        return await get_integration_client(
            name,
            self.org,
            self.config,
            self.secrets
        )

    @property
    def secrets(self):
        """Lazy-load secrets from Key Vault."""
        if not hasattr(self, '_secrets'):
            self._secrets = SecretsProxy(self.org.org_id)
        return self._secrets

@classmethod
async def load(cls, org_id: str, caller_token: str) -> 'OrganizationContext':
    """Load organization context from Table Storage and Key Vault."""
    # 1. Validate org exists
    org = await load_organization(org_id)
    if not org or not org.is_active:
        raise ValueError(f"Organization {org_id} not found or inactive")

    # 2. Load org config (single partition query - very fast)
    config = await load_org_config(org_id)

    # 3. Load integration config
    integrations = await load_integration_config(org_id)

    # 4. Extract caller from token
    caller = await extract_caller_from_token(caller_token)

    return cls(org, config, integrations, caller)

# Decorator usage
from shared.decorators import workflow_decorator

@workflow_decorator
async def requires_org_context(func):
    """Decorator to auto-load organization context."""
    @functools.wraps(func)
    async def wrapper(req: func.HttpRequest):
        org_id = req.headers.get('X-Organization-Id')
        token = req.headers.get('Authorization', '').replace('Bearer ', '')

        if not org_id:
            return func.HttpResponse("Missing X-Organization-Id header", status_code=400)

        # Load context
        context = await OrganizationContext.load(org_id, token)

        # Pass to function
        return await func(req, context)

    return wrapper
```

### Alternatives Considered

- **Manual context loading in each function**: Rejected - too much boilerplate
- **Global context variable**: Rejected - not thread-safe, breaks testability
- **Context manager pattern**: Considered but decorators provide better ergonomics

### References

- Python decorators and functools
- Dataclasses for structured data

---

## 5. Azure AD Authentication with MSAL (React)

### Decision

Use **@azure/msal-react** for React components and **@azure/msal-browser** for auth logic. Implement token interception for all API calls.

### Rationale

- **Constitution Compliance**: Required by Principle I (Azure-First Architecture)
- **Official Microsoft library**: Best support and documentation
- **React hooks**: Provides `useMsal`, `useAccount`, `useIsAuthenticated` hooks
- **Token caching**: Automatic token refresh and caching
- **Protected routes**: Easy integration with React Router

### Implementation Pattern

```typescript
// src/authConfig.ts
import { Configuration, PopupRequest } from "@azure/msal-browser";

export const msalConfig: Configuration = {
  auth: {
    clientId: import.meta.env.VITE_AZURE_CLIENT_ID,
    authority: `https://login.microsoftonline.com/${import.meta.env.VITE_AZURE_TENANT_ID}`,
    redirectUri: window.location.origin,
  },
  cache: {
    cacheLocation: "localStorage",
    storeAuthStateInCookie: false,
  },
};

export const loginRequest: PopupRequest = {
  scopes: ["User.Read", "api://msp-automation/Workflows.Execute"],
};

// src/App.tsx
import { MsalProvider } from "@azure/msal-react";
import { PublicClientApplication } from "@azure/msal-browser";
import { msalConfig } from "./authConfig";

const msalInstance = new PublicClientApplication(msalConfig);

function App() {
  return (
    <MsalProvider instance={msalInstance}>
      <Routes>
        {/* Routes here */}
      </Routes>
    </MsalProvider>
  );
}

// src/services/apiClient.ts
import axios from "axios";
import { msalInstance } from "../App";
import { loginRequest } from "../authConfig";

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_URL || "/api",
});

// Token interceptor
apiClient.interceptors.request.use(async (config) => {
  const accounts = msalInstance.getAllAccounts();

  if (accounts.length > 0) {
    const request = {
      ...loginRequest,
      account: accounts[0],
    };

    const response = await msalInstance.acquireTokenSilent(request);
    config.headers.Authorization = `Bearer ${response.accessToken}`;
  }

  return config;
});

export default apiClient;

// Protected route component
import { useIsAuthenticated } from "@azure/msal-react";
import { Navigate } from "react-router-dom";

function ProtectedRoute({ children }: { children: JSX.Element }) {
  const isAuthenticated = useIsAuthenticated();

  if (!isAuthenticated) {
    return <Navigate to="/login" />;
  }

  return children;
}
```

### Alternatives Considered

- **Custom OAuth implementation**: Rejected - reinventing the wheel, security risks
- **Auth0 or other 3rd party**: Rejected - violates Azure-First principle
- **Azure Static Web Apps built-in auth**: Considered but MSAL provides more flexibility

### References

- [@azure/msal-react documentation](https://github.com/AzureAD/microsoft-authentication-library-for-js/tree/dev/lib/msal-react)
- Azure AD app registration setup

---

## 6. Form Builder & Renderer Architecture

### Decision

Use a **JSON schema-based approach** where forms are defined as JSON with field definitions, validation rules, and data provider references. Implement a dynamic renderer that builds React components from schema.

### Rationale

- **Flexibility**: Non-developers can create forms via UI without code changes
- **Validation**: Centralized validation rules in schema
- **Dynamic options**: Data provider integration for dropdowns
- **Storage**: JSON schema fits in Table Storage (max 32KB per entity)

### Schema Structure

```typescript
// Form schema stored in Table Storage
interface FormSchema {
  id: string;
  name: string;
  description: string;
  linkedWorkflow: string;  // Workflow name to execute
  fields: FormField[];
}

interface FormField {
  name: string;           // Parameter name for workflow
  label: string;          // Display label
  type: 'text' | 'email' | 'number' | 'select' | 'checkbox' | 'textarea';
  required: boolean;
  validation?: {
    pattern?: string;     // Regex for validation
    min?: number;         // Min value/length
    max?: number;         // Max value/length
    message?: string;     // Custom error message
  };
  dataProvider?: string;  // Name of data provider for select options
  defaultValue?: any;
  placeholder?: string;
  helpText?: string;
}
```

### Form Renderer Implementation

```typescript
// src/components/forms/FormRenderer.tsx
import React, { useEffect, useState } from 'react';
import { FormSchema, FormField } from '../../types/form';
import { workflowClient } from '../../services/workflowClient';

interface FormRendererProps {
  schema: FormSchema;
  orgId: string;
  onSubmit: (data: Record<string, any>) => void;
}

export function FormRenderer({ schema, orgId, onSubmit }: FormRendererProps) {
  const [formData, setFormData] = useState<Record<string, any>>({});
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [options, setOptions] = useState<Record<string, Array<{label: string, value: string}>>>({});

  // Load data provider options for select fields
  useEffect(() => {
    const loadOptions = async () => {
      const selectFields = schema.fields.filter(f => f.type === 'select' && f.dataProvider);

      for (const field of selectFields) {
        if (field.dataProvider) {
          try {
            const data = await workflowClient.getDataProviderOptions(
              field.dataProvider,
              orgId
            );
            setOptions(prev => ({ ...prev, [field.name]: data }));
          } catch (error) {
            setErrors(prev => ({
              ...prev,
              [field.name]: `Failed to load options: ${error.message}`
            }));
          }
        }
      }
    };

    loadOptions();
  }, [schema, orgId]);

  const renderField = (field: FormField) => {
    switch (field.type) {
      case 'text':
      case 'email':
      case 'number':
        return (
          <input
            type={field.type}
            value={formData[field.name] || ''}
            onChange={(e) => setFormData({ ...formData, [field.name]: e.target.value })}
            placeholder={field.placeholder}
            required={field.required}
          />
        );

      case 'select':
        return (
          <select
            value={formData[field.name] || ''}
            onChange={(e) => setFormData({ ...formData, [field.name]: e.target.value })}
            required={field.required}
          >
            <option value="">-- Select --</option>
            {options[field.name]?.map(opt => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
        );

      case 'checkbox':
        return (
          <input
            type="checkbox"
            checked={formData[field.name] || false}
            onChange={(e) => setFormData({ ...formData, [field.name]: e.target.checked })}
          />
        );

      case 'textarea':
        return (
          <textarea
            value={formData[field.name] || ''}
            onChange={(e) => setFormData({ ...formData, [field.name]: e.target.value })}
            placeholder={field.placeholder}
            required={field.required}
          />
        );

      default:
        return null;
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    // Validate
    const newErrors: Record<string, string> = {};
    schema.fields.forEach(field => {
      if (field.required && !formData[field.name]) {
        newErrors[field.name] = `${field.label} is required`;
      }
      if (field.validation?.pattern && formData[field.name]) {
        const regex = new RegExp(field.validation.pattern);
        if (!regex.test(formData[field.name])) {
          newErrors[field.name] = field.validation.message || 'Invalid format';
        }
      }
    });

    if (Object.keys(newErrors).length > 0) {
      setErrors(newErrors);
      return;
    }

    // Submit
    onSubmit(formData);
  };

  return (
    <form onSubmit={handleSubmit}>
      <h2>{schema.name}</h2>
      <p>{schema.description}</p>

      {schema.fields.map(field => (
        <div key={field.name} className="form-field">
          <label>
            {field.label}
            {field.required && <span className="required">*</span>}
          </label>

          {renderField(field)}

          {field.helpText && <small>{field.helpText}</small>}
          {errors[field.name] && <span className="error">{errors[field.name]}</span>}
        </div>
      ))}

      <button type="submit">Execute Workflow</button>
    </form>
  );
}
```

### Form Builder (Admin UI)

Form builder provides drag-and-drop interface to create form schemas. Saves JSON to Table Storage.

### Alternatives Considered

- **React Hook Form with Zod**: Considered but requires code changes for each form (defeats purpose)
- **Formik + Yup**: Similar issue - requires code per form
- **JSON Schema Forms (@rjsf)**: Too heavyweight, poor UX
- **Custom schema**: Chosen for flexibility and simplicity

### References

- React controlled components
- JSON schema validation patterns

---

## 7. Local Development Setup

### Decision

Use **Azurite for local Table Storage emulation**, **Azure Functions Core Tools** for running Functions locally, and **React dev server** for the UI. All three run concurrently during development.

### Rationale

- **Constitution Compliance**: Required by Principle I and II (Azure-First, Table Storage Only)
- **Realistic testing**: Azurite accurately emulates Table Storage behavior
- **No cloud dependency**: Developers can work offline (except for Azure AD login)
- **Fast iteration**: Hot reload for React, fast restart for Functions

### Setup

```bash
# Install prerequisites
npm install -g azurite
npm install -g azure-functions-core-tools@4

# Terminal 1: Start Azurite
azurite --silent --location ./azurite

# Terminal 2: Start Management API (when ready)
cd management-api
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
func start --port 7071 --python

# Terminal 3: Start Workflow Engine (when ready)
cd workflow-engine
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
func start --port 7072 --python

# Terminal 4: Start React UI
cd client
npm install
npm run dev  # Vite dev server on port 5173
```

### Local Configuration

```json
// management-api/local.settings.json
{
  "IsEncrypted": false,
  "Values": {
    "AzureWebJobsStorage": "UseDevelopmentStorage=true",
    "FUNCTIONS_WORKER_RUNTIME": "python",
    "TableStorageConnectionString": "UseDevelopmentStorage=true",
    "KeyVaultUrl": "https://dev-keyvault.vault.azure.net/",
    "AzureAd__TenantId": "{your-tenant-id}",
    "AzureAd__ClientId": "{your-client-id}"
  }
}

// client/.env.local
VITE_API_URL=http://localhost:7071/api
VITE_WORKFLOW_URL=http://localhost:7072/api
VITE_AZURE_CLIENT_ID={your-client-id}
VITE_AZURE_TENANT_ID={your-tenant-id}
```

### Debugging

- **Python workflows**: Use VSCode Python debugger with launch.json configured for Azure Functions
- **React UI**: Use browser DevTools and React DevTools extension
- **Table Storage**: Use Azure Storage Explorer to browse Azurite data

### Alternatives Considered

- **Docker Compose for all services**: Considered but adds complexity for simple setup
- **Cloud-only development**: Rejected - slow iteration, requires internet, costs money
- **Mock storage in memory**: Rejected - doesn't match production behavior

### References

- [Azurite documentation](https://learn.microsoft.com/en-us/azure/storage/common/storage-use-azurite)
- [Azure Functions local development](https://learn.microsoft.com/en-us/azure/azure-functions/functions-develop-local)

---

## Summary of Decisions

| Area | Decision | Rationale |
|------|----------|-----------|
| Backend Framework | Azure Functions v2 (Python 3.11) | Constitution Principle I & III, serverless |
| Workflow Registration | Decorator pattern with auto-discovery | Best DX, minimal boilerplate |
| Storage Partitioning | Org ID as partition key | Multi-tenancy, performance (Principle V) |
| Context Loading | Decorator-based auto-loading | DX, performance, testability |
| Frontend Auth | @azure/msal-react | Official library, best support |
| Form Architecture | JSON schema with dynamic renderer | Flexibility, non-dev can create forms |
| Local Development | Azurite + func CLI + Vite | Fast iteration, offline capability |

All decisions align with project constitution and prioritize developer experience while maintaining multi-tenancy and security.
