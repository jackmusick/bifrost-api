# Data Model: Bifrost Integrations MVP

**Phase**: 1 (Design & Contracts)
**Date**: 2025-10-10
**Purpose**: Define all entities, relationships, and Azure Table Storage schema

## Overview

This document defines the data model for the Bifrost Integrations. All persistent data is stored in Azure Table Storage using org-scoped partitioning for multi-tenancy. Dual-indexing patterns are used for bidirectional queries.

---

## Entity Relationship Diagram

```
┌──────────────┐         ┌──────────────┐
│ Organization │◄────────┤    User      │
└──────────────┘   n:m   └──────────────┘
       │                        │
       │ 1:n                    │ 1:n
       │                        │
       ▼                        ▼
┌──────────────┐         ┌──────────────┐
│OrgPermissions│         │UserPermissions│
│(by OrgId)    │         │(by UserId)    │
└──────────────┘         └──────────────┘
    (Dual-indexed - same data, different partition keys)

┌──────────────┐
│ Organization │
└──────────────┘
       │
       │ 1:n
       ▼
┌──────────────┐
│  OrgConfig   │
└──────────────┘

┌──────────────┐
│ Organization │
└──────────────┘
       │
       │ 1:n
       ▼
┌──────────────┐
│Integration   │
│   Config     │
└──────────────┘

┌──────────────┐         ┌──────────────┐
│ Organization │         │   Workflow   │
│  OR GLOBAL   │         │  (metadata)  │
└──────────────┘         └──────────────┘
       │                        │
       │ 1:n                    │ 1:1
       ▼                        ▼
┌──────────────┐────────►┌──────────────┐
│     Form     │         │  FormField   │
└──────────────┘         │  (embedded)  │
                         └──────────────┘

┌──────────────┐         ┌──────────────┐
│ Organization │         │   Workflow   │
└──────────────┘         │  (metadata)  │
       │                        │
       │ 1:n                    │
       ▼                        │
┌──────────────┐         ┌──────────────┐
│  Workflow    │         │    User      │
│  Execution   │         └──────────────┘
│  (by OrgId)  │                │
└──────────────┘                │
                                │ 1:n
                                ▼
                         ┌──────────────┐
                         │    User      │
                         │  Executions  │
                         │  (by UserId) │
                         └──────────────┘
    (Dual-indexed - execution history by org and by user)
```

---

## Table: Organizations

**Purpose**: Master list of client organizations

**Partition Strategy**: Single partition ("ORG") for easy listing of all organizations

| Field        | Type     | Required | Description                                   |
| ------------ | -------- | -------- | --------------------------------------------- |
| PartitionKey | string   | ✅       | Always "ORG"                                  |
| RowKey       | string   | ✅       | Organization ID (GUID)                        |
| Name         | string   | ✅       | Organization display name                     |
| TenantId     | string   | ❌       | Microsoft 365 GDAP tenant ID (GUID, nullable) |
| IsActive     | boolean  | ✅       | Whether org is active (soft delete)           |
| CreatedAt    | datetime | ✅       | UTC timestamp of creation                     |
| CreatedBy    | string   | ✅       | User ID who created the org                   |
| UpdatedAt    | datetime | ✅       | UTC timestamp of last update                  |

**Indexes**:

-   Primary: PartitionKey + RowKey

**Query Patterns**:

```python
# List all organizations
orgs = table_client.query_entities(filter="PartitionKey eq 'ORG'")

# Get specific organization
org = table_client.get_entity(partition_key="ORG", row_key=org_id)
```

**Example Entity**:

```json
{
    "PartitionKey": "ORG",
    "RowKey": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "Name": "Acme Corp",
    "TenantId": "12345678-1234-1234-1234-123456789012",
    "IsActive": true,
    "CreatedAt": "2025-01-15T10:30:00Z",
    "CreatedBy": "user-123",
    "UpdatedAt": "2025-01-15T10:30:00Z"
}
```

---

## Table: Config

**Purpose**: Configuration key-value pairs (global MSP-level OR organization-specific)

**Partition Strategy**: Partition by "GLOBAL" for MSP-wide config OR OrgId for org-specific overrides

| Field        | Type     | Required | Description                                                              |
| ------------ | -------- | -------- | ------------------------------------------------------------------------ |
| PartitionKey | string   | ✅       | "GLOBAL" for MSP-wide config OR Organization ID (GUID) for org overrides |
| RowKey       | string   | ✅       | "config:{key}" (e.g., "config:halo_api_url")                             |
| Value        | string   | ✅       | Configuration value (JSON for complex types)                             |
| Type         | string   | ✅       | "string", "int", "bool", "json", "secret_ref"                            |
| Description  | string   | ❌       | Human-readable description of config                                     |
| UpdatedAt    | datetime | ✅       | UTC timestamp of last update                                             |
| UpdatedBy    | string   | ✅       | User ID who last updated this config                                     |

**Lookup Order** (in workflow code):

1. Check org-specific: `PartitionKey={orgId}`
2. Fallback to global: `PartitionKey="GLOBAL"`
3. Return None if not found in either

**Query Patterns**:

```python
# Get all global config
global_config = table_client.query_entities(
    filter="PartitionKey eq 'GLOBAL' and RowKey ge 'config:' and RowKey lt 'config;'"
)

# Get all config for an org (overrides only)
org_config = table_client.query_entities(
    filter=f"PartitionKey eq '{org_id}' and RowKey ge 'config:' and RowKey lt 'config;'"
)

# Get specific config with fallback (in workflow context)
def get_config(key: str, org_id: str = None) -> Optional[str]:
    # 1. Try org-specific if org_id provided
    if org_id:
        try:
            item = table_client.get_entity(partition_key=org_id, row_key=f"config:{key}")
            return item['Value']
        except ResourceNotFoundError:
            pass

    # 2. Fallback to global
    try:
        item = table_client.get_entity(partition_key="GLOBAL", row_key=f"config:{key}")
        return item['Value']
    except ResourceNotFoundError:
        return None
```

**Example Entities**:

```json
// Global config (MSP environment variable)
{
  "PartitionKey": "GLOBAL",
  "RowKey": "config:halo_api_url",
  "Value": "https://acme-msp.halopsa.com/api",
  "Type": "string",
  "Description": "HaloPSA API base URL for MSP",
  "UpdatedAt": "2025-01-15T10:30:00Z",
  "UpdatedBy": "user-123"
}

// Org-specific config (mapping data)
{
  "PartitionKey": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "RowKey": "config:halo_client_id",
  "Value": "client-456",
  "Type": "string",
  "Description": "This organization's HaloPSA client ID",
  "UpdatedAt": "2025-01-15T11:00:00Z",
  "UpdatedBy": "user-123"
}
```

---

## Table: IntegrationConfig

**Purpose**: External service integration settings per organization

**Partition Strategy**: Partition by OrgId

| Field        | Type     | Required | Description                                        |
| ------------ | -------- | -------- | -------------------------------------------------- |
| PartitionKey | string   | ✅       | Organization ID (GUID)                             |
| RowKey       | string   | ✅       | "integration:{type}" (e.g., "integration:msgraph") |
| Enabled      | boolean  | ✅       | Whether integration is enabled                     |
| Settings     | string   | ✅       | JSON string with integration-specific settings     |
| UpdatedAt    | datetime | ✅       | UTC timestamp of last update                       |
| UpdatedBy    | string   | ✅       | User ID who last updated                           |

**Supported Integration Types**:

-   `msgraph`: Microsoft Graph API (requires tenant_id, client_id, client_secret_ref)
-   `halopsa`: HaloPSA API (requires api_url, api_key_ref, client_id)

**Query Patterns**:

```python
# Get all integrations for an org
integrations = table_client.query_entities(
    filter=f"PartitionKey eq '{org_id}' and RowKey ge 'integration:' and RowKey lt 'integration;'"
)

# Get specific integration
msgraph_config = table_client.get_entity(partition_key=org_id, row_key="integration:msgraph")
```

**Example Entity**:

```json
{
    "PartitionKey": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "RowKey": "integration:msgraph",
    "Enabled": true,
    "Settings": "{\"tenant_id\":\"12345678-1234-1234-1234-123456789012\",\"client_id\":\"app-123\",\"client_secret_ref\":\"a1b2c3d4--msgraph-secret\"}",
    "UpdatedAt": "2025-01-15T10:30:00Z",
    "UpdatedBy": "user-123"
}
```

---

## Table: Users

**Purpose**: Directory of all platform users (MSP technicians AND organization users)

**Partition Strategy**: Single partition ("USER") for user listing

| Field        | Type     | Required | Description                                         |
| ------------ | -------- | -------- | --------------------------------------------------- |
| PartitionKey | string   | ✅       | Always "USER"                                       |
| RowKey       | string   | ✅       | User ID from Azure AD (GUID)                        |
| Email        | string   | ✅       | User email address                                  |
| DisplayName  | string   | ✅       | User display name                                   |
| UserType     | string   | ✅       | "MSP" (technician) or "ORG" (organization user)     |
| IsMspAdmin   | boolean  | ✅       | Whether user is MSP admin (only for UserType="MSP") |
| IsActive     | boolean  | ✅       | Whether user is active (soft delete)                |
| LastLogin    | datetime | ❌       | UTC timestamp of last login                         |
| CreatedAt    | datetime | ✅       | UTC timestamp when user first logged in             |

**User Types**:

-   **MSP**: Internal MSP technicians who manage platform, create workflows, configure orgs
-   **ORG**: External organization users who can only execute assigned forms for their organization(s)

**Query Patterns**:

```python
# List all users
users = table_client.query_entities(filter="PartitionKey eq 'USER'")

# List only MSP technicians
msp_users = table_client.query_entities(filter="PartitionKey eq 'USER' and UserType eq 'MSP'")

# List only organization users
org_users = table_client.query_entities(filter="PartitionKey eq 'USER' and UserType eq 'ORG'")

# Get specific user
user = table_client.get_entity(partition_key="USER", row_key=user_id)
```

**Example Entities**:

```json
// MSP Technician
{
  "PartitionKey": "USER",
  "RowKey": "user-abc123",
  "Email": "john.doe@acme-msp.com",
  "DisplayName": "John Doe",
  "UserType": "MSP",
  "IsMspAdmin": true,
  "IsActive": true,
  "LastLogin": "2025-01-15T14:22:00Z",
  "CreatedAt": "2024-12-01T08:00:00Z"
}

// Organization User (external client)
{
  "PartitionKey": "USER",
  "RowKey": "user-xyz789",
  "Email": "jane.smith@clientcorp.com",
  "DisplayName": "Jane Smith",
  "UserType": "ORG",
  "IsMspAdmin": false,
  "IsActive": true,
  "LastLogin": "2025-01-15T10:30:00Z",
  "CreatedAt": "2025-01-10T09:00:00Z"
}
```

---

## Table: UserPermissions (Dual-Indexed with OrgPermissions)

**Purpose**: "What organizations can this user access?" query

**Partition Strategy**: Partition by UserId

| Field               | Type     | Required | Description                        |
| ------------------- | -------- | -------- | ---------------------------------- |
| PartitionKey        | string   | ✅       | User ID (GUID)                     |
| RowKey              | string   | ✅       | Organization ID (GUID)             |
| CanExecuteWorkflows | boolean  | ✅       | Can execute workflows for this org |
| CanManageConfig     | boolean  | ✅       | Can manage org configuration       |
| CanManageForms      | boolean  | ✅       | Can create/edit forms              |
| CanViewHistory      | boolean  | ✅       | Can view execution history         |
| GrantedBy           | string   | ✅       | User ID who granted permissions    |
| GrantedAt           | datetime | ✅       | UTC timestamp when granted         |

**Query Patterns**:

```python
# Get all orgs a user can access
user_perms = table_client.query_entities(filter=f"PartitionKey eq '{user_id}'")

# Check if user has permission for specific org
perm = table_client.get_entity(partition_key=user_id, row_key=org_id)
if perm.CanExecuteWorkflows:
    # Allow workflow execution
```

---

## Table: OrgPermissions (Dual-Indexed with UserPermissions)

**Purpose**: "Who can access this organization?" query

**Partition Strategy**: Partition by OrgId

| Field               | Type     | Required | Description                        |
| ------------------- | -------- | -------- | ---------------------------------- |
| PartitionKey        | string   | ✅       | Organization ID (GUID)             |
| RowKey              | string   | ✅       | User ID (GUID)                     |
| CanExecuteWorkflows | boolean  | ✅       | Can execute workflows for this org |
| CanManageConfig     | boolean  | ✅       | Can manage org configuration       |
| CanManageForms      | boolean  | ✅       | Can create/edit forms              |
| CanViewHistory      | boolean  | ✅       | Can view execution history         |
| GrantedBy           | string   | ✅       | User ID who granted permissions    |
| GrantedAt           | datetime | ✅       | UTC timestamp when granted         |

**Query Patterns**:

```python
# Get all users who can access an org
org_users = table_client.query_entities(filter=f"PartitionKey eq '{org_id}'")
```

**Important**: UserPermissions and OrgPermissions tables contain the same data with different partition keys. Both must be updated atomically when granting/revoking permissions.

---

## Table: Forms

**Purpose**: Form definitions with fields and linked workflows

**Partition Strategy**: Partition by OrgId OR "GLOBAL" for shared forms

| Field          | Type     | Required | Description                                   |
| -------------- | -------- | -------- | --------------------------------------------- |
| PartitionKey   | string   | ✅       | Organization ID (GUID) or "GLOBAL"            |
| RowKey         | string   | ✅       | Form ID (GUID)                                |
| Name           | string   | ✅       | Form display name                             |
| Description    | string   | ❌       | Form description                              |
| FormSchema     | string   | ✅       | JSON string with field definitions (max 32KB) |
| LinkedWorkflow | string   | ✅       | Workflow name to execute                      |
| IsActive       | boolean  | ✅       | Whether form is active                        |
| CreatedBy      | string   | ✅       | User ID who created form                      |
| CreatedAt      | datetime | ✅       | UTC timestamp of creation                     |
| UpdatedAt      | datetime | ✅       | UTC timestamp of last update                  |

**FormSchema Structure** (stored as JSON string):

```typescript
{
    fields: [
        {
            name: string, // Parameter name for workflow
            label: string, // Display label
            type:
                "text" |
                "email" |
                "number" |
                "select" |
                "checkbox" |
                "textarea",
            required: boolean,
            validation: {
                pattern: string, // Regex
                min: number,
                max: number,
                message: string,
            },
            dataProvider: string, // Data provider name for select fields
            defaultValue: any,
            placeholder: string,
            helpText: string,
        },
    ];
}
```

**Query Patterns**:

```python
# Get all forms for an org
org_forms = table_client.query_entities(filter=f"PartitionKey eq '{org_id}'")

# Get global forms
global_forms = table_client.query_entities(filter="PartitionKey eq 'GLOBAL'")

# Get specific form
form = table_client.get_entity(partition_key=org_id, row_key=form_id)
```

**Example Entity**:

```json
{
    "PartitionKey": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "RowKey": "form-123",
    "Name": "New User Onboarding",
    "Description": "Creates a new M365 user with licenses",
    "FormSchema": "{\"fields\":[{\"name\":\"first_name\",\"label\":\"First Name\",\"type\":\"text\",\"required\":true},{\"name\":\"license\",\"label\":\"License\",\"type\":\"select\",\"required\":true,\"dataProvider\":\"get_available_licenses\"}]}",
    "LinkedWorkflow": "user_onboarding",
    "IsActive": true,
    "CreatedBy": "user-123",
    "CreatedAt": "2025-01-15T10:00:00Z",
    "UpdatedAt": "2025-01-15T10:00:00Z"
}
```

---

## Table: Roles

**Purpose**: Role definitions for controlling form access (primarily for organization users)

**Partition Strategy**: Single partition ("ROLE") for easy role listing

| Field        | Type     | Required | Description                                |
| ------------ | -------- | -------- | ------------------------------------------ |
| PartitionKey | string   | ✅       | Always "ROLE"                              |
| RowKey       | string   | ✅       | Role ID (GUID)                             |
| Name         | string   | ✅       | Role display name (e.g., "Billing Admins") |
| Description  | string   | ❌       | Human-readable description                 |
| IsActive     | boolean  | ✅       | Whether role is active                     |
| CreatedBy    | string   | ✅       | User ID who created role                   |
| CreatedAt    | datetime | ✅       | UTC timestamp of creation                  |
| UpdatedAt    | datetime | ✅       | UTC timestamp of last update               |

**Query Patterns**:

```python
# List all roles
roles = table_client.query_entities(filter="PartitionKey eq 'ROLE'")

# Get specific role
role = table_client.get_entity(partition_key="ROLE", row_key=role_id)
```

**Example Entity**:

```json
{
    "PartitionKey": "ROLE",
    "RowKey": "role-billing-123",
    "Name": "Billing Admins",
    "Description": "Can execute billing-related workflows",
    "IsActive": true,
    "CreatedBy": "user-123",
    "CreatedAt": "2025-01-15T10:00:00Z",
    "UpdatedAt": "2025-01-15T10:00:00Z"
}
```

---

## Table: UserRoles

**Purpose**: Many-to-many relationship between users and roles

**Partition Strategy**: Partition by UserId for "what roles does this user have?"

| Field        | Type     | Required | Description                   |
| ------------ | -------- | -------- | ----------------------------- |
| PartitionKey | string   | ✅       | User ID (GUID)                |
| RowKey       | string   | ✅       | Role ID (GUID)                |
| AssignedBy   | string   | ✅       | User ID who assigned the role |
| AssignedAt   | datetime | ✅       | UTC timestamp when assigned   |

**Query Patterns**:

```python
# Get all roles for a user
user_roles = table_client.query_entities(filter=f"PartitionKey eq '{user_id}'")

# Check if user has specific role
try:
    role = table_client.get_entity(partition_key=user_id, row_key=role_id)
    has_role = True
except ResourceNotFoundError:
    has_role = False
```

**Example Entity**:

```json
{
    "PartitionKey": "user-xyz789",
    "RowKey": "role-billing-123",
    "AssignedBy": "user-abc123",
    "AssignedAt": "2025-01-15T11:00:00Z"
}
```

---

## Table: FormRoles

**Purpose**: Which roles can access which forms (form access control)

**Partition Strategy**: Partition by FormId for "who can access this form?"

| Field        | Type     | Required | Description                |
| ------------ | -------- | -------- | -------------------------- |
| PartitionKey | string   | ✅       | Form ID (GUID)             |
| RowKey       | string   | ✅       | Role ID (GUID)             |
| AssignedBy   | string   | ✅       | User ID who granted access |
| AssignedAt   | datetime | ✅       | UTC timestamp when granted |

**Access Logic**:

-   **MSP users**: Always have access to all forms (bypass role check)
-   **ORG users**: Can only execute forms where they have a matching role in FormRoles table
-   **POC**: For POC, can skip FormRoles and allow all ORG users access to all forms

**Query Patterns**:

```python
# Get all roles that can access a form
form_roles = table_client.query_entities(filter=f"PartitionKey eq '{form_id}'")

# Check if user can access form (via their roles)
user_roles = get_user_roles(user_id)
form_roles = get_form_roles(form_id)
can_access = any(role in form_roles for role in user_roles)
```

**Example Entity**:

```json
{
    "PartitionKey": "form-123",
    "RowKey": "role-billing-123",
    "AssignedBy": "user-abc123",
    "AssignedAt": "2025-01-15T12:00:00Z"
}
```

---

## Table: WorkflowExecutions (Dual-Indexed with UserExecutions)

**Purpose**: Execution history by organization

**Partition Strategy**: Partition by OrgId, RowKey uses reverse timestamp for DESC ordering

| Field        | Type     | Required | Description                               |
| ------------ | -------- | -------- | ----------------------------------------- |
| PartitionKey | string   | ✅       | Organization ID (GUID)                    |
| RowKey       | string   | ✅       | {ReverseTimestamp}\_{ExecutionId}         |
| ExecutionId  | string   | ✅       | Execution ID (GUID)                       |
| WorkflowName | string   | ✅       | Name of executed workflow                 |
| FormId       | string   | ❌       | Form ID if triggered by form submission   |
| ExecutedBy   | string   | ✅       | User ID who executed                      |
| Status       | string   | ✅       | "Pending", "Running", "Success", "Failed" |
| InputData    | string   | ✅       | JSON string with input parameters         |
| Result       | string   | ❌       | JSON string with workflow output          |
| ErrorMessage | string   | ❌       | Error message if failed                   |
| DurationMs   | number   | ❌       | Execution duration in milliseconds        |
| StartedAt    | datetime | ✅       | UTC timestamp when started                |
| CompletedAt  | datetime | ❌       | UTC timestamp when completed              |

**ReverseTimestamp Calculation**:

```python
reverse_ts = 9999999999999 - int(time.time() * 1000)
row_key = f"{reverse_ts}_{execution_id}"
```

**Query Patterns**:

```python
# Get recent executions for an org (automatically sorted DESC by time)
executions = table_client.query_entities(
    filter=f"PartitionKey eq '{org_id}'"
).take(50)

# Get specific execution
execution = table_client.get_entity(partition_key=org_id, row_key=row_key)
```

**Example Entity**:

```json
{
    "PartitionKey": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "RowKey": "9999999970000000000_exec-123",
    "ExecutionId": "exec-123",
    "WorkflowName": "user_onboarding",
    "FormId": "form-123",
    "ExecutedBy": "user-abc123",
    "Status": "Success",
    "InputData": "{\"first_name\":\"John\",\"last_name\":\"Doe\",\"license\":\"license-123\"}",
    "Result": "{\"success\":true,\"user_id\":\"new-user-456\"}",
    "ErrorMessage": null,
    "DurationMs": 2350,
    "StartedAt": "2025-01-15T14:30:00Z",
    "CompletedAt": "2025-01-15T14:30:02Z"
}
```

---

## Table: UserExecutions (Dual-Indexed with WorkflowExecutions)

**Purpose**: Execution history by user ("My Executions")

**Partition Strategy**: Partition by UserId

| Field        | Type     | Required | Description                                       |
| ------------ | -------- | -------- | ------------------------------------------------- |
| PartitionKey | string   | ✅       | User ID (GUID)                                    |
| RowKey       | string   | ✅       | {ReverseTimestamp}\_{ExecutionId}                 |
| ExecutionId  | string   | ✅       | Execution ID (GUID) - links to WorkflowExecutions |
| OrgId        | string   | ✅       | Organization ID                                   |
| WorkflowName | string   | ✅       | Name of executed workflow                         |
| Status       | string   | ✅       | "Pending", "Running", "Success", "Failed"         |
| StartedAt    | datetime | ✅       | UTC timestamp when started                        |

**Query Patterns**:

```python
# Get user's recent executions across all orgs
user_execs = table_client.query_entities(
    filter=f"PartitionKey eq '{user_id}'"
).take(50)
```

**Important**: WorkflowExecutions and UserExecutions tables store related but not identical data. WorkflowExecutions has full details; UserExecutions has summary data for fast user queries.

---

## Non-Persisted Entities (Metadata Only)

### Workflow (Metadata)

Workflows are not stored in Table Storage. They exist as Python functions with `@workflow` decorator and are registered in memory at startup.

**Metadata Structure**:

```typescript
{
  name: string,
  description: string,
  category: string,
  parameters: [
    {
      name: string,
      type: string,
      required: boolean,
      dataProvider?: string
    }
  ],
  requires_org: boolean
}
```

### DataProvider (Metadata)

Data providers are not stored. They exist as Python functions with `@data_provider` decorator.

**Metadata Structure**:

```typescript
{
  name: string,
  description: string
}
```

---

## Entity Validation Rules

### Organization

-   Name: Required, 1-200 characters
-   TenantId: Optional, GUID format if provided
-   IsActive: Required, boolean

### OrgConfig

-   Key: Required, alphanumeric with underscores
-   Value: Required, max 10KB (Table Storage column limit)
-   Type: Must be one of: "string", "int", "bool", "json", "secret_ref"

### Form

-   Name: Required, 1-200 characters
-   FormSchema: Required, valid JSON, max 32KB
-   LinkedWorkflow: Required, must match registered workflow name
-   Fields in schema: Max 50 fields per form

### WorkflowExecution

-   Status: Must be one of: "Pending", "Running", "Success", "Failed"
-   InputData: Required, valid JSON
-   Result: Optional, valid JSON if present

---

## Data Retention & Archival

-   **Execution history**: Retained for 90 days by default (configurable)
-   **Audit logs**: Retained for 1 year
-   **Archived data**: Moved to Blob Storage with Table Storage pointer after retention period

---

## Performance Considerations

-   **Single-partition queries**: <10ms for org-scoped data
-   **Form schema**: Keep under 32KB (consider moving large forms to Blob Storage if needed)
-   **Execution results**: If >32KB, store in Blob Storage and reference in table
-   **Dual-indexing**: Accept eventual consistency - write to both tables but tolerate brief inconsistency

---

## Security & Compliance

-   **PII**: User email and name are PII - handle according to GDPR/compliance requirements
-   **Secrets**: NEVER store secrets in Table Storage - always use Key Vault with references
-   **Partition-level isolation**: Org-scoped partitions prevent cross-org queries
-   **Audit trail**: All writes include UpdatedBy/CreatedBy for audit purposes
