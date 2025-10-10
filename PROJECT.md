# MSP Automation Platform - Project Documentation

**Version:** 1.0  
**Last Updated:** 2025-01-10

---

## Table of Contents
1. [Project Overview](#project-overview)
2. [Architecture](#architecture)
3. [This Project](#this-project) ⚠️ PROJECT-SPECIFIC
4. [Related Projects](#related-projects)
5. [Authentication & Authorization](#authentication--authorization)
6. [Data Storage Strategy](#data-storage-strategy)
7. [Communication Patterns](#communication-patterns)
8. [Key Concepts](#key-concepts)
9. [Development Setup](#development-setup) ⚠️ PROJECT-SPECIFIC
10. [Deployment](#deployment)
11. [Common Tasks](#common-tasks) ⚠️ PROJECT-SPECIFIC

---

## Project Overview

The **MSP Automation Platform** is an internal tool for managing client automation workflows. It replaces Rewst with a code-driven, Azure-native solution that gives us full control over automation logic while providing a user-friendly interface for our techs.

### Goals
- **Code-driven automation**: Write workflows in Python, not drag-and-drop
- **Dynamic forms**: Forms with option generators (like Rewst)
- **Multi-tenant**: Support multiple client organizations with GDAP
- **Fast execution**: Sub-second workflow startup using Azure Table Storage
- **Cost-effective**: All-Azure stack leveraging our CSP pricing
- **Simple deployment**: Table Storage only, no SQL required

### What This Platform Does
1. **Client Management**: Links clients to GDAP tenants, stores config
2. **Form Builder**: Creates forms with dynamic fields for techs to submit
3. **Workflow Execution**: Runs Python-based automation workflows
4. **Integration Management**: Connects to Microsoft Graph, HaloPSA, etc.
5. **Audit & History**: Tracks all workflow executions

---

## Architecture

### High-Level Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     Azure AD App Registration                │
│              (Single sign-on for all components)             │
└─────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              │               │               │
              ▼               ▼               ▼
    ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
    │   Static    │  │ Management  │  │  Workflow   │
    │  Web App    │  │    API      │  │   Engine    │
    │  (React)   │  │   (.Python)    │  │  (Python)   │
    └─────────────┘  └─────────────┘  └─────────────┘
         │ UI              │ CRUD           │ Automation
         └─────────────────┴────────────────┘
                          │
         ┌────────────────┼────────────────┐
         │                │                │
         ▼                ▼                ▼
    ┌─────────┐    ┌──────────┐    ┌──────────┐
    │  Table  │    │   Key    │    │   Blob   │
    │ Storage │    │  Vault   │    │ Storage  │
    └─────────┘    └──────────┘    └──────────┘
    All Data        Secrets         Logs/Files
```

### Components

| Component | Technology | Purpose | Repository |
|-----------|-----------|---------|------------|
| **Management UI** | React + Azure Static Web Apps | User interface for techs | `client` |
| **Management API** | Azure Functions (Python 3.11) | CRUD operations for forms, orgs, users | `msp-automation-api` |
| **Workflow Engine** | Azure Functions (Python 3.11) | Execute automation workflows | `msp-automation-workflows` |
| **Table Storage** | Azure Table Storage | ALL persistent data | Shared |
| **Key Vault** | Azure Key Vault | Secrets and API keys | Shared |
| **Blob Storage** | Azure Blob Storage | Logs, reports, file uploads | Shared |
| **App Registration** | Azure AD | Authentication for all components | Shared |

### Why This Stack?

- **All-Azure**: Single ecosystem, unified billing, familiar tooling
- **React + Python**: Modern, popular stack - easy to find contributors
- **Python for all backend**: Share code between API and Workflows (single language, consistent patterns)
- **Table Storage Only**: No SQL means simpler setup, cheaper cost, easier for open-source contributors
- **Bring Your Own Functions**: Static Web App links to external Functions apps for full control
- **Fast**: Table Storage queries are sub-10ms for single-partition reads
- **Scalable**: Automatic horizontal scaling with partition keys

### Why No SQL Database?

**Table Storage handles everything because:**
1. ✅ **Access patterns are simple** - Most queries are "get all data for org X" (single partition)
2. ✅ **Scales automatically** - No capacity planning, just works
3. ✅ **Dirt cheap** - $0.045/GB + $0.00036 per 10k ops vs $5+/month for SQL
4. ✅ **Simpler deployment** - Just `azurite` locally, no SQL setup
5. ✅ **Open-source friendly** - Contributors don't need SQL Server
6. ✅ **Fast enough** - Sub-second queries for single-org operations

**Trade-offs we accept:**
- ❌ No complex cross-org reporting (use Application Insights or export to blob)
- ❌ No full-text search (filter in-memory, data sets are small per org)
- ❌ Denormalized data with dual indexing (storage is cheap)
- ✅ Perfect for MSP use case where operations are org-scoped

---

## This Project

⚠️ **PROJECT-SPECIFIC SECTION** - This section varies by repository.

### For `client` (Static Web App)

**Purpose:** User-facing web application for managing clients, forms, and viewing workflow executions.

**Technology:**
- React 18+ with TypeScript
- Azure Static Web Apps
- React Router for navigation
- Axios or Fetch for API calls
- Linked to both Functions apps via "bring your own functions"

**Key Responsibilities:**
- Client/organization management UI
- Form builder and form rendering
- Workflow discovery and manual execution
- Execution history viewing
- User permission management

**Project Structure:**
```
client/
├── src/
│   ├── components/          # Reusable React components
│   │   ├── forms/          # Form builder, renderer
│   │   ├── organizations/  # Org management
│   │   ├── workflows/      # Workflow list, execution
│   │   └── common/         # Buttons, inputs, layouts
│   ├── services/           # API clients
│   │   ├── apiClient.ts
│   │   ├── workflowClient.ts
│   │   └── authService.ts
│   ├── types/              # TypeScript interfaces
│   ├── pages/              # Route components
│   ├── hooks/              # Custom React hooks
│   └── App.tsx             # Main app component
├── public/
├── staticwebapp.config.json  # Routes, auth config
├── package.json
├── tsconfig.json
├── PROJECT.md              # This file
└── README.md
```

**Key Files:**
- `staticwebapp.config.json` - Configures linked Functions apps and auth
- `src/services/apiClient.ts` - Management API client
- `src/services/workflowClient.ts` - Workflow Engine client

---

### For `msp-automation-api` (Management API)

**Purpose:** RESTful API for CRUD operations on forms, organizations, users, and execution history.

**Technology:**
- Azure Functions (Python 3.11, v2 programming model)
- azure-data-tables for Table Storage
- FastAPI patterns (route decorators, dependency injection)

**Key Responsibilities:**
- CRUD endpoints for Forms, Organizations, Users
- User permission management
- Execution history queries and reporting
- Organization config management (Table Storage)

**Project Structure:**
```
msp-automation-api/
├── functions/              # HTTP-triggered endpoints
│   ├── organizations.py   # Org CRUD
│   ├── forms.py           # Form CRUD
│   ├── users.py           # User/permission CRUD
│   ├── executions.py      # History queries
│   └── permissions.py     # Permission checks
├── shared/                # Shared with workflows
│   ├── storage.py         # TableStorageService
│   ├── auth.py            # Token verification
│   ├── models.py          # Pydantic models
│   └── middleware.py      # Auth middleware
├── function_app.py        # Entry point
├── requirements.txt
├── host.json
├── local.settings.json
├── PROJECT.md             # This file
└── README.md
```

**Key Patterns:**
- All endpoints validate Azure AD tokens
- Permission checking on every request via decorators
- Returns only data user has access to (org-scoped filtering)
- Shares `shared/` module with workflow engine

---

### For `msp-automation-workflows` (Workflow Engine)

**Purpose:** Execute automation workflows with Python, integrating with Microsoft Graph, HaloPSA, and other services.

**Technology:**
- Azure Functions (Python 3.11)
- Decorator-based workflow registration
- Azure Table Storage for org context
- aiohttp for async HTTP calls

**Key Responsibilities:**
- Execute automation workflows
- Provide option generator functions for dynamic form fields
- Load organization context (config, secrets, integrations)
- Expose metadata endpoint for workflow discovery

**Project Structure:**
```
msp-automation-workflows/
├── workflows/               # Main automation workflows
│   ├── user_onboarding.py
│   ├── license_management.py
│   ├── device_offboarding.py
│   └── __init__.py
├── options/                # Option generators for forms
│   ├── get_available_licenses.py
│   ├── get_security_groups.py
│   ├── get_client_list.py
│   └── __init__.py
├── shared/                 # Shared utilities
│   ├── decorators.py       # @workflow, @option_generator
│   ├── context.py          # OrganizationContext class
│   ├── registry.py         # Workflow metadata registry
│   ├── storage.py          # Table Storage helpers
│   ├── integrations/       # Integration clients
│   │   ├── msgraph.py
│   │   ├── halopsa.py
│   │   └── base.py
│   └── error_handling.py
├── admin/                  # Admin endpoints
│   └── metadata.py         # GET /admin/metadata
├── function_app.py         # Entry point, registers functions
├── requirements.txt
├── host.json
├── local.settings.json
├── PROJECT.md              # This file
└── README.md
```

**Key Patterns:**
- All workflows use `@workflow` decorator
- All option generators use `@option_generator` decorator
- Organization context automatically loaded from headers
- Developers just write business logic

---

## Related Projects

| Project | Repository | Description |
|---------|-----------|-------------|
| **Management UI** | `msp-automation-ui` | React frontend |
| **Management API** | `msp-automation-api` | Python API for CRUD operations |
| **Workflow Engine** | `msp-automation-workflows` | Python automation workflows |

**How They Work Together:**
1. User logs into Management UI via Azure AD
2. UI calls Management API to load forms, orgs, etc.
3. UI calls Workflow Engine to execute workflows or get dynamic options
4. Management API can also call Workflow Engine (e.g., to trigger background jobs)
5. All three share same Azure AD app registration for auth
6. All three read/write to same Table Storage account

---

## Authentication & Authorization

### Azure AD App Registration

**Single app registration** used by all components:

```json
{
  "displayName": "MSP Automation Platform",
  "signInAudience": "AzureADMyOrg",
  "api": {
    "requestedAccessTokenVersion": 2,
    "oauth2PermissionScopes": [
      {
        "id": "...",
        "value": "Workflows.Execute",
        "adminConsentDisplayName": "Execute workflows"
      },
      {
        "id": "...",
        "value": "Forms.Manage",
        "adminConsentDisplayName": "Manage forms"
      },
      {
        "id": "...",
        "value": "Organizations.Manage",
        "adminConsentDisplayName": "Manage organizations"
      }
    ]
  }
}
```

### Authentication Flow

1. **User Login**
   ```
   User → Static Web App → Azure AD login
   Azure AD → Issues JWT token
   Token stored in browser (HTTP-only cookie or localStorage)
   ```

2. **API Calls**
   ```
   Static Web App → Management API
   Headers:
     Authorization: Bearer {jwt_token}
     X-Organization-Id: {guid}
   
   Management API:
   - Validates token with Azure AD
   - Extracts user claims (user_id, email, roles)
   - Checks permissions for organization
   - Processes request
   ```

3. **Workflow Execution**
   ```
   Static Web App → Workflow Engine
   Headers:
     Authorization: Bearer {jwt_token}
     X-Organization-Id: {guid}
   
   Workflow Engine:
   - Validates token (via decorator)
   - Loads organization context from Table Storage
   - Checks user has permission to execute workflows for this org
   - Runs workflow
   ```

### Bring Your Own Functions Integration

Static Web App is configured to forward requests to external Functions apps:

```json
// staticwebapp.config.json
{
  "routes": [
    {
      "route": "/api/*",
      "allowedRoles": ["authenticated"]
    }
  ],
  "linkedBackends": [
    {
      "backendId": "management-api",
      "endpoint": "https://msp-automation-api.azurewebsites.net"
    },
    {
      "backendId": "workflow-engine",
      "endpoint": "https://msp-automation-workflows.azurewebsites.net"
    }
  ],
  "auth": {
    "identityProviders": {
      "azureActiveDirectory": {
        "userDetailsClaim": "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/name",
        "registration": {
          "openIdIssuer": "https://login.microsoftonline.com/{tenant-id}/v2.0",
          "clientIdSettingName": "AZURE_CLIENT_ID",
          "clientSecretSettingName": "AZURE_CLIENT_SECRET"
        }
      }
    }
  }
}
```

**Benefits:**
- Static Web App handles auth
- Automatically forwards `Authorization` header to Functions
- Functions just validate token
- No CORS issues (same auth context)

### Authorization Model

**Application-level permissions** stored in Table Storage:

**UserPermissions Table:**
```
PartitionKey: {UserId} (for "what orgs can this user access?")
RowKey: {OrgId}
Properties:
  - CanExecuteWorkflows (bool)
  - CanManageConfig (bool)
  - CanManageForms (bool)
  - CanViewHistory (bool)
  - GrantedBy (string, user ID)
  - GrantedAt (datetime)
```

**OrgPermissions Table (mirror for reverse lookup):**
```
PartitionKey: {OrgId} (for "who has access to this org?")
RowKey: {UserId}
Properties:
  - (same as above)
```

**Dual indexing pattern:**
- Write to both tables when granting/revoking permissions
- Query UserPermissions when you have UserId, need OrgIds
- Query OrgPermissions when you have OrgId, need UserIds
- Storage is cheap, fast queries are worth it

**Permission checking** in Management API:

```csharp
public class PermissionService
{
    private readonly TableClient _userPermissionsTable;
    private readonly TableClient _orgPermissionsTable;
    
    public async Task<bool> CanExecuteWorkflows(string userId, string orgId)
    {
        try
        {
            var entity = await _userPermissionsTable.GetEntityAsync<PermissionEntity>(
                partitionKey: userId,
                rowKey: orgId
            );
            return entity.Value.CanExecuteWorkflows;
        }
        catch (RequestFailedException ex) when (ex.Status == 404)
        {
            return false;
        }
    }
    
    public async Task<List<string>> GetPermittedOrganizations(string userId)
    {
        var query = _userPermissionsTable.QueryAsync<PermissionEntity>(
            filter: $"PartitionKey eq '{userId}'"
        );
        
        var orgIds = new List<string>();
        await foreach (var entity in query)
        {
            orgIds.Add(entity.RowKey);
        }
        return orgIds;
    }
}
```

**Permission checking** in Workflow Engine:

```python
# shared/decorators.py
async def verify_permission(token: str, org_id: str, permission: str) -> bool:
    """
    Calls Management API to check if user has permission.
    Token is validated by Management API.
    """
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{MANAGEMENT_API_URL}/api/permissions/check",
            headers={"Authorization": f"Bearer {token}"},
            json={"org_id": org_id, "permission": permission}
        ) as response:
            if response.status == 200:
                result = await response.json()
                return result.get("allowed", False)
            return False
```

---

## Data Storage Strategy

### Storage Architecture

All persistent data lives in **Azure Table Storage**. Different entity types use different partitioning strategies optimized for their access patterns.

| Table | Partition Strategy | Purpose |
|-------|-------------------|---------|
| **Organizations** | Single partition ("ORG") | List all orgs |
| **OrgConfig** | By OrgId | Fast org config lookup |
| **IntegrationConfig** | By OrgId | Integration settings per org |
| **Forms** | By OrgId or "GLOBAL" | Forms scoped to org or global |
| **Users** | Single partition ("USER") | User directory |
| **UserPermissions** | By UserId | "What orgs can user access?" |
| **OrgPermissions** | By OrgId | "Who can access this org?" |
| **WorkflowExecutions** | By OrgId | Execution history per org |
| **UserExecutions** | By UserId | Execution history per user |
| **AuditLogs** | By OrgId | Audit trail per org |

### Table Storage Schema

#### Organizations
```
Table: Organizations
PartitionKey: "ORG"
RowKey: {OrgId} (guid)
Properties:
  - Name (string)
  - TenantId (guid, nullable) - GDAP tenant link
  - IsActive (bool)
  - CreatedAt (datetime)
  - CreatedBy (string, user ID)
  - UpdatedAt (datetime)
```

**Query examples:**
```csharp
// List all orgs
var orgs = tableClient.QueryAsync<OrgEntity>(filter: "PartitionKey eq 'ORG'");

// Get specific org
var org = await tableClient.GetEntityAsync<OrgEntity>("ORG", orgId);
```

#### Organization Config
```
Table: OrgConfig
PartitionKey: {OrgId}
RowKey: "config:{ConfigKey}" (e.g., "config:halo_client_id")
Properties:
  - Value (string)
  - Type (string: "string", "int", "bool", "secret_ref")
  - UpdatedAt (datetime)
  - UpdatedBy (string, user ID)
  - Description (string, optional)
```

**Query examples:**
```csharp
// Get all config for an org
var config = tableClient.QueryAsync<ConfigEntity>(
    filter: $"PartitionKey eq '{orgId}' and RowKey ge 'config:' and RowKey lt 'config;'"
);

// Get specific config value
var item = await tableClient.GetEntityAsync<ConfigEntity>(orgId, "config:halo_client_id");
```

#### Integration Config
```
Table: IntegrationConfig
PartitionKey: {OrgId}
RowKey: "integration:{IntegrationType}" (e.g., "integration:msgraph")
Properties:
  - Enabled (bool)
  - Settings (string, JSON)
  - UpdatedAt (datetime)
  - UpdatedBy (string)
```

#### Forms
```
Table: Forms
PartitionKey: {OrgId} or "GLOBAL"
RowKey: {FormId} (guid)
Properties:
  - Name (string)
  - Description (string)
  - FormSchema (string, JSON, max 32KB)
  - LinkedWorkflow (string)
  - IsActive (bool)
  - CreatedBy (string, user ID)
  - CreatedAt (datetime)
  - UpdatedAt (datetime)
```

**Query examples:**
```csharp
// Get all forms for an org
var forms = tableClient.QueryAsync<FormEntity>(
    filter: $"PartitionKey eq '{orgId}'"
);

// Get global forms
var globalForms = tableClient.QueryAsync<FormEntity>(
    filter: "PartitionKey eq 'GLOBAL'"
);

// Get specific form
var form = await tableClient.GetEntityAsync<FormEntity>(orgId, formId);
```

#### Users
```
Table: Users
PartitionKey: "USER"
RowKey: {UserId} (Azure AD user ID, guid)
Properties:
  - Email (string)
  - DisplayName (string)
  - IsActive (bool)
  - LastLogin (datetime)
  - CreatedAt (datetime)
```

#### User Permissions (Dual-Indexed)

**UserPermissions Table:**
```
Table: UserPermissions
PartitionKey: {UserId}
RowKey: {OrgId}
Properties:
  - CanExecuteWorkflows (bool)
  - CanManageConfig (bool)
  - CanManageForms (bool)
  - CanViewHistory (bool)
  - GrantedBy (string, user ID)
  - GrantedAt (datetime)
```

**OrgPermissions Table (mirror):**
```
Table: OrgPermissions
PartitionKey: {OrgId}
RowKey: {UserId}
Properties:
  - (same as UserPermissions)
```

**Why dual indexing?**
- Query by UserId when you need "what orgs can this user access?"
- Query by OrgId when you need "who has access to this org?"
- Write to both tables when granting/revoking (storage is cheap)
- Fast queries are worth the duplication

#### Workflow Executions (Dual-Indexed)

**WorkflowExecutions Table:**
```
Table: WorkflowExecutions
PartitionKey: {OrgId}
RowKey: {ReverseTimestamp}_{ExecutionId}
  (ReverseTimestamp = 9999999999999 - timestamp for DESC order)
Properties:
  - ExecutionId (guid)
  - WorkflowName (string)
  - FormId (guid, nullable)
  - ExecutedBy (string, user ID)
  - Status (string: "Pending", "Running", "Success", "Failed")
  - InputData (string, JSON)
  - Result (string, JSON)
  - ErrorMessage (string, nullable)
  - DurationMs (int)
  - StartedAt (datetime)
  - CompletedAt (datetime, nullable)
```

**UserExecutions Table (mirror for user-scoped queries):**
```
Table: UserExecutions
PartitionKey: {UserId}
RowKey: {ReverseTimestamp}_{ExecutionId}
Properties:
  - ExecutionId (guid)
  - OrgId (guid)
  - WorkflowName (string)
  - Status (string)
  - StartedAt (datetime)
```

**Query examples:**
```csharp
// Get recent executions for an org
var executions = tableClient.QueryAsync<ExecutionEntity>(
    filter: $"PartitionKey eq '{orgId}'"
).OrderBy(e => e.RowKey).Take(50);

// Get user's recent executions (across all orgs)
var userExecutions = userExecutionsTable.QueryAsync<UserExecutionEntity>(
    filter: $"PartitionKey eq '{userId}'"
).Take(50);

// Get specific execution
var execution = await tableClient.GetEntityAsync<ExecutionEntity>(orgId, rowKey);
```

#### Audit Logs
```
Table: AuditLogs
PartitionKey: {OrgId}
RowKey: {ReverseTimestamp}_{LogId}
Properties:
  - LogId (guid)
  - UserId (string)
  - Action (string, e.g., "Form.Create", "Workflow.Execute")
  - EntityType (string)
  - EntityId (string)
  - Details (string, JSON)
  - IpAddress (string)
  - Timestamp (datetime)
```

### Data Access Patterns

**Hot Path (Workflow Execution):**
```python
# Workflow Engine reads from Table Storage
# 1. Organizations table (PartitionKey="ORG", RowKey=org_id) - validate org exists
# 2. OrgConfig table (PartitionKey=org_id) - get all config
# 3. IntegrationConfig table (PartitionKey=org_id) - get integration settings
# 4. Key Vault (as needed) - get secrets
# Total: ~10-20ms for context loading

# Workflow Engine writes to Table Storage (async)
# Log execution to WorkflowExecutions and UserExecutions tables
# This doesn't block the workflow response
```

**Cold Path (Management UI):**
```python
# Management API reads/writes to Table Storage
# Queries with filtering, pagination
# Less frequent but may need to load more data

# Example: Get all forms user can access
async def get_user_forms(user_id: str, storage: TableStorageService):
    permitted_org_ids = await permission_service.get_permitted_organizations(user_id)
    forms = []
    
    # Query each org's forms (concurrent)
    tasks = []
    for org_id in permitted_org_ids:
        task = storage.query_async(
            "Forms",
            filter=f"PartitionKey eq '{org_id}'"
        )
        tasks.append(task)
    
    results = await asyncio.gather(*tasks)
    for org_forms in results:
        forms.extend(org_forms)
    
    # Also get global forms
    global_forms = await storage.query_async(
        "Forms",
        filter="PartitionKey eq 'GLOBAL'"
    )
    forms.extend(global_forms)
    
    # Sort and return
    return sorted(forms, key=lambda f: f.created_at, reverse=True)[:50]
```

### Handling Table Storage "Limitations"

**1. No JOINs**
- Denormalize data where needed
- Store FormName in WorkflowExecution (avoid lookup)
- Cache frequently accessed data in memory

**2. No full-text search**
- Most queries are org-scoped (fast)
- For admin searches, load all data and filter client-side
- Or use Azure Cognitive Search if needed

**3. No complex filtering**
- Partition queries are lightning fast
- Additional filtering happens in-memory (data sets are small per org)
- For complex analytics, export to blob storage and use Azure Data Explorer

**4. No transactions across partitions**
- Use dual-indexing pattern (write to multiple tables)
- Accept eventual consistency for some operations
- Most operations are isolated to one partition anyway

**5. 1MB entity size limit**
- Forms schema stored as JSON string (max 32KB typically)
- Large execution results stored in Blob Storage, reference in entity
- Logs go to Blob Storage with entity pointing to blob URL

### Why This Works for MSPs

**Typical MSP data scale:**
- 50-200 client organizations
- 10-100 forms per org
- 100-1000 workflow executions per day
- 5-50 users (techs)

**At this scale:**
- ✅ Single-org queries return < 100 items (instant)
- ✅ Cross-org queries load < 10k items (filter in-memory, still fast)
- ✅ Total storage: < 1GB ($0.045/month)
- ✅ Operations: ~100k/day ($0.36/month)
- ✅ Total cost: < $1/month vs $5+/month for SQL

**When you'd need SQL:**
- 1000+ orgs with complex cross-org analytics
- Real-time dashboards with 10+ complex queries per second
- Compliance requirements for ACID transactions
- Third-party BI tools need direct database access

---

## Communication Patterns

### Static Web App → Management API

**Pattern:** Direct HTTP calls with auth header

```typescript
// src/services/apiClient.ts
import axios from 'axios';

class ApiClient {
  private client = axios.create({
    baseURL: process.env.REACT_APP_API_URL || '/api',
  });

  constructor() {
    // Add auth token to all requests
    this.client.interceptors.request.use(async (config) => {
      const token = await getAccessToken();
      config.headers.Authorization = `Bearer ${token}`;
      return config;
    });
  }

  async getOrganizations(): Promise<Organization[]> {
    const response = await this.client.get('/organizations');
    return response.data;
  }

  async createForm(request: CreateFormRequest, orgId: string): Promise<Form> {
    const response = await this.client.post('/forms', request, {
      headers: {
        'X-Organization-Id': orgId,
      },
    });
    return response.data;
  }
}

export const apiClient = new ApiClient();
```

### Static Web App → Workflow Engine

**Pattern:** HTTP calls with auth + org context headers

```typescript
// src/services/workflowClient.ts
import axios from 'axios';

class WorkflowClient {
  private client = axios.create({
    baseURL: process.env.REACT_APP_WORKFLOW_URL || '/api/workflows',
  });

  constructor() {
    this.client.interceptors.request.use(async (config) => {
      const token = await getAccessToken();
      config.headers.Authorization = `Bearer ${token}`;
      return config;
    });
  }

  async getOptions(optionGeneratorName: string, orgId: string): Promise<OptionItem[]> {
    const response = await this.client.get(`/options/${optionGeneratorName}`, {
      headers: {
        'X-Organization-Id': orgId,
      },
    });
    return response.data;
  }

  async executeWorkflow(
    workflowName: string,
    orgId: string,
    parameters: any
  ): Promise<WorkflowResult> {
    const response = await this.client.post(`/${workflowName}`, parameters, {
      headers: {
        'X-Organization-Id': orgId,
      },
    });
    return response.data;
  }
}

export const workflowClient = new WorkflowClient();
```

### Management API → Workflow Engine

**Pattern:** Server-to-server calls for background jobs

```python
# shared/workflow_client.py in Management API
import aiohttp
from typing import Any, Dict

class WorkflowClient:
    def __init__(self, workflow_url: str, token_provider):
        self.workflow_url = workflow_url
        self.token_provider = token_provider
    
    async def trigger_workflow(
        self,
        workflow_name: str,
        org_id: str,
        parameters: Dict[str, Any]
    ):
        """Trigger a workflow from Management API (server-to-server)."""
        # Get machine-to-machine token
        token = await self.token_provider.get_service_token()
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.workflow_url}/workflows/{workflow_name}",
                headers={
                    "Authorization": f"Bearer {token}",
                    "X-Organization-Id": org_id
                },
                json=parameters
            ) as response:
                response.raise_for_status()
                return await response.json()
```

### Workflow Engine → Management API

**Pattern:** Permission checks and execution logging

```python
# shared/decorators.py
async def verify_permission(token: str, org_id: str) -> bool:
    """Check if user can execute workflows for this org."""
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{MANAGEMENT_API_URL}/api/permissions/check",
            headers={"Authorization": f"Bearer {token}"},
            json={"org_id": org_id, "permission": "execute_workflows"}
        ) as response:
            return response.status == 200

async def log_execution(org_id: str, workflow_name: str, result: dict, user_id: str):
    """Log workflow execution to Table Storage (via API)."""
    async with aiohttp.ClientSession() as session:
        await session.post(
            f"{MANAGEMENT_API_URL}/api/executions",
            json={
                "org_id": org_id,
                "workflow_name": workflow_name,
                "status": "success" if result.get("success") else "failed",
                "result": result,
                "executed_by": user_id
            }
        )
```

---

## Key Concepts

### Organization Context

**Every workflow automatically gets rich context:**

```python
@workflow(name="user_onboarding", requires_org=True)
async def onboard_user(context, first_name, last_name, email, license):
    # context is automatically loaded by decorator from Table Storage
    
    # Organization info
    org_name = context.org.name
    tenant_id = context.org.tenant_id
    
    # Config from OrgConfig table
    default_location = context.config.get('default_office_location')
    naming_template = context.config.get('user_naming_template')
    
    # Secrets from Key Vault (lazy-loaded)
    api_key = await context.secrets.get('halopsa_api_key')
    
    # Pre-authenticated integrations
    graph = context.get_integration('msgraph')
    halo = context.get_integration('halopsa')
    
    # Caller info (who ran this)
    caller_email = context.caller.email
    caller_id = context.caller.user_id
```

**Context loading (under the hood):**

```python
# shared/context.py
class OrganizationContext:
    @classmethod
    async def load(cls, org_id: str, caller_token: str):
        # 1. Validate org exists
        org = await load_organization(org_id)  # Table Storage query
        if not org or not org.is_active:
            raise ValueError(f"Organization {org_id} not found or inactive")
        
        # 2. Load all config for this org (single partition query)
        config = await load_org_config(org_id)  # Very fast
        
        # 3. Load integration config
        integrations = await load_integration_config(org_id)
        
        # 4. Extract caller from token
        caller = await extract_caller_from_token(caller_token)
        
        context = cls(org, config, integrations, caller)
        return context
```

**Developers never touch:**
- ❌ Reading `X-Organization-Id` header
- ❌ Querying Table Storage for org config
- ❌ Validating org exists
- ❌ Checking permissions
- ❌ Authenticating to integrations

### Workflow Decorators

**Basic workflow:**

```python
@workflow(
    name="user_onboarding",
    description="Onboards a new M365 user with license assignment",
    category="user_management"
)
@param("first_name", type="string", required=True)
@param("last_name", type="string", required=True)
@param("email", type="email", required=True)
@param("license", type="string", required=True, options_from="get_available_licenses")
async def onboard_user(context, first_name, last_name, email, license):
    # Business logic only
    graph = context.get_integration('msgraph')
    
    user = await graph.create_user(
        givenName=first_name,
        surname=last_name,
        userPrincipalName=email
    )
    
    await graph.assign_license(user.id, license)
    
    return {
        "user_id": user.id,
        "upn": email,
        "success": True
    }
```

**Option generator:**

```python
@option_generator(
    name="get_available_licenses",
    description="Returns available M365 licenses for an organization"
)
async def get_licenses(context):
    graph = context.get_integration('msgraph')
    skus = await graph.get_subscribed_skus()
    
    return [
        {"label": sku.skuPartNumber, "value": sku.skuId}
        for sku in skus
        if sku.consumedUnits < sku.prepaidUnits.enabled
    ]
```

**Workflow without org context:**

```python
@workflow(
    name="validate_email",
    description="Validates email format and DNS",
    requires_org=False  # No org context needed
)
@param("email", type="email", required=True)
async def validate_email(email):
    # No context parameter
    # Can be called without X-Organization-Id header
    import re
    import dns.resolver
    
    if not re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', email):
        return {"valid": False, "reason": "Invalid format"}
    
    domain = email.split('@')[1]
    try:
        dns.resolver.resolve(domain, 'MX')
        return {"valid": True}
    except:
        return {"valid": False, "reason": "No MX records"}
```

### Integration Clients

**Integrations are pre-authenticated and ready to use:**

```python
# workflows/user_onboarding.py
async def onboard_user(context, ...):
    # Get Microsoft Graph client (already authenticated for this org's tenant)
    graph = context.get_integration('msgraph')
    
    # Use it directly
    user = await graph.create_user(...)
    await graph.assign_license(user.id, license_id)
    
    # Get HaloPSA client (already authenticated with org's API key)
    halo = context.get_integration('halopsa')
    
    # Use it directly
    await halo.create_activity(
        client_id=context.config['halo_client_id'],
        note=f"User {email} onboarded by {context.caller.email}"
    )
```

**Under the hood:**

```python
# shared/integrations/msgraph.py
class MicrosoftGraphClient:
    def __init__(self, tenant_id: str, client_id: str, client_secret: str):
        self.tenant_id = tenant_id
        self._token = None
        self._token_expires = None
        self._credentials = ClientSecretCredential(tenant_id, client_id, client_secret)
        
    async def _ensure_authenticated(self):
        if not self._token or datetime.now() >= self._token_expires:
            token_response = await self._credentials.get_token(
                "https://graph.microsoft.com/.default"
            )
            self._token = token_response.token
            self._token_expires = datetime.fromtimestamp(token_response.expires_on)
    
    async def create_user(self, **kwargs):
        await self._ensure_authenticated()
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://graph.microsoft.com/v1.0/users",
                headers={"Authorization": f"Bearer {self._token}"},
                json=kwargs
            ) as response:
                response.raise_for_status()
                return await response.json()
```

### Form Schema

**Forms are defined in JSON:**

```json
{
  "name": "New User Onboarding",
  "description": "Creates a new M365 user with licenses",
  "workflow": "user_onboarding",
  "fields": [
    {
      "name": "first_name",
      "label": "First Name",
      "type": "text",
      "required": true
    },
    {
      "name": "last_name",
      "label": "Last Name",
      "type": "text",
      "required": true
    },
    {
      "name": "email",
      "label": "Email Address",
      "type": "email",
      "required": true,
      "validation": {
        "pattern": "^[\\w\\.-]+@[\\w\\.-]+\\.\\w+$"
      }
    },
    {
      "name": "license",
      "label": "License",
      "type": "select",
      "required": true,
      "options": {
        "source": "option_generator",
        "generator": "get_available_licenses"
      }
    }
  ]
}
```

**At form load:**
1. UI renders form fields from schema
2. For `license` field with `option_generator` source:
   - UI calls `GET /options/get_available_licenses`
   - Headers: `X-Organization-Id: {guid}`
   - Gets back `[{"label": "E3", "value": "..."}, ...]`
   - Populates dropdown

**On submit:**
1. UI sends `POST /workflows/user_onboarding`
2. Headers: `X-Organization-Id: {guid}`, `Authorization: Bearer {token}`
3. Body: `{"first_name": "John", "last_name": "Doe", "email": "...", "license": "..."}`
4. Workflow executes and returns result

### Dual Indexing Pattern

**Problem:** Need to query data by different keys efficiently.

**Example:** User permissions
- Query 1: "What orgs can user X access?" (partition by UserId)
- Query 2: "Who can access org Y?" (partition by OrgId)

**Solution:** Maintain two tables with different partition keys.

```csharp
// Granting permission (write to both tables)
public async Task GrantPermission(string userId, string orgId, Permissions permissions)
{
    var entity = new PermissionEntity
    {
        CanExecuteWorkflows = permissions.CanExecuteWorkflows,
        CanManageConfig = permissions.CanManageConfig,
        CanManageForms = permissions.CanManageForms,
        CanViewHistory = permissions.CanViewHistory,
        GrantedBy = currentUserId,
        GrantedAt = DateTime.UtcNow
    };
    
    // Write to UserPermissions table (partition by user)
    await _userPermissionsTable.UpsertEntityAsync(new TableEntity(userId, orgId, entity));
    
    // Write to OrgPermissions table (partition by org)
    await _orgPermissionsTable.UpsertEntityAsync(new TableEntity(orgId, userId, entity));
}

// Query by user
public async Task<List<string>> GetUserOrganizations(string userId)
{
    var query = _userPermissionsTable.QueryAsync<PermissionEntity>(
        filter: $"PartitionKey eq '{userId}'"
    );
    
    var orgIds = new List<string>();
    await foreach (var entity in query)
    {
        orgIds.Add(entity.RowKey);
    }
    return orgIds;
}

// Query by org
public async Task<List<string>> GetOrgUsers(string orgId)
{
    var query = _orgPermissionsTable.QueryAsync<PermissionEntity>(
        filter: $"PartitionKey eq '{orgId}'"
    );
    
    var userIds = new List<string>();
    await foreach (var entity in query)
    {
        userIds.Add(entity.RowKey);
    }
    return userIds;
}
```

**Trade-offs:**
- ✅ Both queries are fast (single partition scan)
- ✅ Storage is cheap (duplicate data is fine)
- ⚠️ Must keep tables in sync (write to both)
- ⚠️ Eventual consistency if writes fail

---

## Development Setup

⚠️ **PROJECT-SPECIFIC SECTION**

### For `client` (Static Web App)

**Prerequisites:**
- Node.js 18+ and npm
- Azure Static Web Apps CLI: `npm install -g @azure/static-web-apps-cli`

**Local Development:**

```bash
# Clone and setup
git clone https://github.com/your-org/msp-automation-ui.git
cd msp-automation-ui

# Install dependencies
npm install

# Configure environment
cp .env.example .env.local
# Edit .env.local with local Function URLs

# Run locally
npm start

# Or with Static Web Apps CLI (includes auth emulation)
swa start http://localhost:3000 --api-location http://localhost:7071
```

**Configuration:**

```bash
# .env.local
REACT_APP_API_URL=http://localhost:7071/api
REACT_APP_WORKFLOW_URL=http://localhost:7072/api
REACT_APP_AZURE_CLIENT_ID=your-client-id
REACT_APP_AZURE_TENANT_ID=your-tenant-id
```

**Key Scripts:**
```json
// package.json
{
  "scripts": {
    "start": "react-scripts start",
    "build": "react-scripts build",
    "test": "react-scripts test",
    "lint": "eslint src/**/*.{ts,tsx}"
  }
}
```

---

### For `msp-automation-api` (Management API)

**Prerequisites:**
- Python 3.11
- Azure Functions Core Tools: `npm install -g azure-functions-core-tools@4`
- Azurite: `npm install -g azurite`

**Local Development:**

```bash
# Clone and setup
git clone https://github.com/your-org/msp-automation-api.git
cd msp-automation-api

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start Azurite
azurite --silent --location ./azurite &

# Configure local settings
cp local.settings.example.json local.settings.json
# Edit local.settings.json

# Run locally
func start --port 7071 --python
```

**Configuration:**

```json
// local.settings.json
{
  "IsEncrypted": false,
  "Values": {
    "AzureWebJobsStorage": "UseDevelopmentStorage=true",
    "FUNCTIONS_WORKER_RUNTIME": "python",
    "TableStorageConnectionString": "UseDevelopmentStorage=true",
    "KeyVaultUrl": "https://your-keyvault.vault.azure.net/",
    "AzureAd__TenantId": "{tenant-id}",
    "AzureAd__ClientId": "{client-id}",
    "WorkflowEngineUrl": "http://localhost:7072"
  }
}
```

**Seeding local data:**

```bash
# Create sample organizations and config
python tools/seed_data.py
```

---

### For `msp-automation-workflows` (Workflow Engine)

**Prerequisites:**
- Python 3.11
- Azure Functions Core Tools: `npm install -g azure-functions-core-tools@4`
- Azurite: `npm install -g azurite`

**Local Development:**

```bash
# Clone and setup
git clone https://github.com/your-org/msp-automation-workflows.git
cd msp-automation-workflows

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start Azurite
azurite --silent --location ./azurite &

# Configure local settings
cp local.settings.example.json local.settings.json
# Edit local.settings.json

# Run locally
func start --port 7072 --python
```

**Configuration:**

```json
// local.settings.json
{
  "IsEncrypted": false,
  "Values": {
    "AzureWebJobsStorage": "UseDevelopmentStorage=true",
    "FUNCTIONS_WORKER_RUNTIME": "python",
    "TableStorageConnectionString": "UseDevelopmentStorage=true",
    "KeyVaultUrl": "https://your-keyvault.vault.azure.net/",
    "ManagementApiUrl": "http://localhost:7071",
    "AzureAd__TenantId": "{tenant-id}",
    "AzureAd__ClientId": "{client-id}"
  }
}
```

**Development Tips:**
- Use `@workflow(requires_org=False)` for testing without org context
- Mock integrations in tests: `context.get_integration = Mock(return_value=mock_client)`
- Check `/admin/metadata` endpoint to see all registered workflows
- Use `pytest` for unit tests: `pytest tests/`

---

## Deployment

### Infrastructure as Code (Bicep)

**Main template:**

```bicep
// main.bicep
param location string = 'eastus'
param environment string

// Shared resources
module tableStorage './modules/table-storage.bicep' = {
  name: 'table-storage'
  params: {
    location: location
    environment: environment
  }
}

module keyVault './modules/key-vault.bicep' = {
  name: 'key-vault'
  params: {
    location: location
    environment: environment
  }
}

module blobStorage './modules/blob-storage.bicep' = {
  name: 'blob-storage'
  params: {
    location: location
    environment: environment
  }
}

// Applications
module staticWebApp './modules/static-web-app.bicep' = {
  name: 'static-web-app'
  params: {
    location: location
    environment: environment
  }
}

module managementApi './modules/function-app-dotnet.bicep' = {
  name: 'management-api'
  params: {
    location: location
    environment: environment
    tableStorageConnectionString: tableStorage.outputs.connectionString
    keyVaultUrl: keyVault.outputs.vaultUri
  }
}

module workflowEngine './modules/function-app-python.bicep' = {
  name: 'workflow-engine'
  params: {
    location: location
    environment: environment
    tableStorageConnectionString: tableStorage.outputs.connectionString
    keyVaultUrl: keyVault.outputs.vaultUri
    managementApiUrl: managementApi.outputs.functionAppUrl
  }
}

// Monitoring
module appInsights './modules/app-insights.bicep' = {
  name: 'app-insights'
  params: {
    location: location
    environment: environment
  }
}
```

### CI/CD with GitHub Actions

**Static Web App:**

```yaml
# .github/workflows/deploy-ui.yml
name: Deploy UI
on:
  push:
    branches: [main]
    paths:
      - 'src/**'
      - 'public/**'
      - 'package.json'
      - '.github/workflows/deploy-ui.yml'

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '18'
      
      - name: Install dependencies
        run: npm ci
      
      - name: Build
        run: npm run build
        env:
          REACT_APP_API_URL: ${{ secrets.API_URL }}
          REACT_APP_WORKFLOW_URL: ${{ secrets.WORKFLOW_URL }}
      
      - name: Deploy to Azure Static Web Apps
        uses: Azure/static-web-apps-deploy@v1
        with:
          azure_static_web_apps_api_token: ${{ secrets.AZURE_STATIC_WEB_APPS_API_TOKEN }}
          repo_token: ${{ secrets.GITHUB_TOKEN }}
          action: "upload"
          app_location: "build"
          api_location: ""  # We're using BYOF
```

**Management API:**

```yaml
# .github/workflows/deploy-api.yml
name: Deploy Management API
on:
  push:
    branches: [main]
    paths:
      - 'functions/**'
      - 'shared/**'
      - 'requirements.txt'
      - '.github/workflows/deploy-api.yml'

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
      
      - name: Deploy to Azure Functions
        uses: Azure/functions-action@v1
        with:
          app-name: msp-automation-api-prod
          package: .
          publish-profile: ${{ secrets.AZURE_FUNCTIONAPP_PUBLISH_PROFILE_API }}
```

**Workflow Engine:**

```yaml
# .github/workflows/deploy-workflows.yml
name: Deploy Workflow Engine
on:
  push:
    branches: [main]
    paths:
      - 'workflows/**'
      - 'shared/**'
      - '.github/workflows/deploy-workflows.yml'

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
      
      - name: Deploy to Azure Functions
        uses: Azure/functions-action@v1
        with:
          app-name: msp-automation-workflows-prod
          package: .
          publish-profile: ${{ secrets.AZURE_FUNCTIONAPP_PUBLISH_PROFILE_WORKFLOWS }}
```

### Environments

| Environment | Branch | Purpose |
|-------------|--------|---------|
| **Development** | `develop` | Local testing, feature development |
| **Staging** | `staging` | Pre-production testing |
| **Production** | `main` | Live system |

---

## Common Tasks

⚠️ **PROJECT-SPECIFIC SECTION**

### For `msp-automation-ui`

**Add a new page:**

```bash
# Create new React page component
mkdir -p src/pages
cat > src/pages/MyPage.tsx << 'EOF'
import React from 'react';

const MyPage: React.FC = () => {
  return (
    <div>
      <h1>My Page</h1>
    </div>
  );
};

export default MyPage;
EOF

# Add route in App.tsx
# <Route path="/my-page" element={<MyPage />} />
```

**Add form field type:**

```typescript
// src/components/forms/FormRenderer.tsx
const renderField = (field: FormField) => {
  switch (field.type) {
    case 'text':
      return <InputText field={field} />;
    case 'my_new_type':
      return <MyNewFieldComponent field={field} />;
    default:
      return null;
  }
};
```

**Call Management API:**

```typescript
// src/services/apiClient.ts
async getOrganizations(): Promise<Organization[]> {
  const response = await this.client.get('/organizations');
  return response.data;
}
```

---

### For `msp-automation-api`

**Add new API endpoint:**

```python
# functions/my_endpoint.py
import azure.functions as func
from shared.storage import TableStorageService
from shared.auth import require_auth

bp = func.Blueprint()

@bp.route(route="mydata", methods=["GET"])
@require_auth
async def get_my_data(req: func.HttpRequest) -> func.HttpResponse:
    user_id = req.user_id  # Set by @require_auth decorator
    org_id = req.headers.get("X-Organization-Id")
    
    # Query Table Storage
    storage = TableStorageService()
    data = await storage.query(
        "MyTable",
        filter=f"PartitionKey eq '{org_id}'"
    )
    
    return func.HttpResponse(
        json.dumps(data),
        mimetype="application/json"
    )
```

**Query Table Storage:**

```python
# shared/storage.py
from azure.data.tables.aio import TableServiceClient
from typing import List, Dict, Any

class TableStorageService:
    def __init__(self, connection_string: str):
        self.client = TableServiceClient.from_connection_string(connection_string)
    
    async def query(
        self,
        table_name: str,
        filter: str
    ) -> List[Dict[str, Any]]:
        table_client = self.client.get_table_client(table_name)
        
        results = []
        async for entity in table_client.query_entities(filter):
            results.append(dict(entity))
        return results
    
    async def upsert(self, table_name: str, entity: Dict[str, Any]):
        table_client = self.client.get_table_client(table_name)
        await table_client.upsert_entity(entity)
```

---

### For `msp-automation-workflows`

**Add new workflow:**

```python
# workflows/my_new_workflow.py
from shared.decorators import workflow, param

@workflow(
    name="my_new_workflow",
    description="Does something useful",
    category="my_category"
)
@param("input_param", type="string", required=True)
async def my_new_workflow(context, input_param):
    """
    This workflow is automatically discovered by the metadata endpoint.
    It will appear in the Management UI immediately.
    """
    
    # Use org context
    config_value = context.config.get('some_setting')
    
    # Use integrations
    graph = context.get_integration('msgraph')
    
    # Do work
    result = await do_something(input_param)
    
    # Return result (shown in UI)
    return {
        "success": True,
        "data": result
    }
```

**Add new option generator:**

```python
# options/my_options.py
from shared.decorators import option_generator

@option_generator(
    name="get_my_options",
    description="Returns options for a form field"
)
async def get_my_options(context):
    """
    This is automatically available to forms.
    Set field options_from="get_my_options" in form schema.
    """
    
    # Get data from somewhere
    items = await fetch_items(context)
    
    # Return as label/value pairs
    return [
        {"label": item.display_name, "value": item.id}
        for item in items
    ]
```

**Add new integration:**

```python
# shared/integrations/my_service.py
from .base import BaseIntegration
import aiohttp

class MyServiceClient(BaseIntegration):
    def __init__(self, api_key: str, base_url: str):
        self.api_key = api_key
        self.base_url = base_url
        self._session = None
    
    async def _ensure_session(self):
        if not self._session:
            self._session = aiohttp.ClientSession(
                headers={"Authorization": f"Bearer {self.api_key}"}
            )
    
    async def do_something(self, param):
        await self._ensure_session()
        async with self._session.get(f"{self.base_url}/endpoint") as response:
            response.raise_for_status()
            return await response.json()
    
    async def close(self):
        if self._session:
            await self._session.close()
```

```python
# shared/integrations/__init__.py
from .my_service import MyServiceClient

async def get_integration_client(integration_name, org, config, secrets):
    if integration_name == "my_service":
        api_key = await secrets.get('my_service_api_key')
        return MyServiceClient(api_key, config.get('my_service_url'))
    elif integration_name == "msgraph":
        # ...
    # ... other integrations
```

**Load org context from Table Storage:**

```python
# shared/storage.py
from azure.data.tables.aio import TableServiceClient

async def load_org_config(org_id: str) -> dict:
    """Load all config for an org from Table Storage."""
    table_client = get_table_client("OrgConfig")
    
    config = {}
    async for entity in table_client.query_entities(
        query_filter=f"PartitionKey eq '{org_id}' and RowKey ge 'config:' and RowKey lt 'config;'"
    ):
        key = entity['RowKey'].replace('config:', '')
        config[key] = entity['Value']
    
    return config
```

**Test workflow locally:**

```bash
# Without org context (for testing)
curl -X POST http://localhost:7072/workflows/my_new_workflow \
  -H "Content-Type: application/json" \
  -d '{"input_param": "test value"}'

# With org context
curl -X POST http://localhost:7072/workflows/my_new_workflow \
  -H "Content-Type: application/json" \
  -H "X-Organization-Id: 12345678-1234-1234-1234-123456789012" \
  -H "Authorization: Bearer {token}" \
  -d '{"input_param": "test value"}'

# Check registered workflows
curl http://localhost:7072/admin/metadata
```

---

## Additional Resources

- **Azure Static Web Apps Docs**: https://learn.microsoft.com/en-us/azure/static-web-apps/
- **Azure Functions Docs**: https://learn.microsoft.com/en-us/azure/azure-functions/
- **Python Azure Functions**: https://learn.microsoft.com/en-us/azure/azure-functions/functions-reference-python
- **Azure Table Storage**: https://learn.microsoft.com/en-us/azure/storage/tables/
- **azure-data-tables SDK (Python)**: https://learn.microsoft.com/en-us/python/api/overview/azure/data-tables-readme
- **Microsoft Graph SDK**: https://learn.microsoft.com/en-us/graph/sdks/sdks-overview

---

## Questions or Issues?

- **Architecture questions**: Check this doc first, then ask in #automation-platform Slack
- **Bugs**: Open an issue in the relevant repo
- **Feature requests**: Discuss in #automation-platform, then create issue
- **Deployment issues**: Check Azure Portal logs, Application Insights
- **Table Storage questions**: See Azure Storage Explorer for browsing data locally

---

## Why Table Storage Only?

This is an intentional architectural decision:

**✅ Advantages:**
- Simple deployment (just Azurite locally)
- Cheaper ($1/month vs $5-15/month for SQL)
- Faster for single-org queries (< 10ms)
- Easier for open-source contributors (no SQL setup)
- Auto-scaling with no capacity planning

**⚠️ Trade-offs we accept:**
- No complex cross-org reporting (use App Insights or export to blob)
- No full-text search (filter in-memory, datasets are small)
- Dual-indexing for some queries (storage is cheap)
- No foreign keys (enforce in application code)

**💡 When to reconsider:**
- 1000+ orgs with heavy cross-org analytics
- Real-time dashboards with 100+ complex queries/second
- Compliance requires ACID transactions
- Third-party tools need direct database access

For typical MSP usage (50-200 orgs, 10-100 forms, 100-1000 workflows/day), Table Storage is perfect.

---

*Last updated: 2025-01-10 - This document should be kept in sync across all three repositories*