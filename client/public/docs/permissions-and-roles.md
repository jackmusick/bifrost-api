# Permissions and Roles Guide

This guide covers the permission system, user roles, and access control mechanisms in the Bifrost Integrations platform.

## Table of Contents

- [Overview](#overview)
- [User Roles](#user-roles)
- [Permissions](#permissions)
- [Organization Access](#organization-access)
- [Workflow Permissions](#workflow-permissions)
- [Integration Access](#integration-access)
- [Security Best Practices](#security-best-practices)

---

## Overview

Bifrost Integrations implements a comprehensive role-based access control (RBAC) system that ensures:

- **Principle of Least Privilege**: Users only have access to what they need
- **Multi-Tenant Isolation**: Complete data separation between organizations
- **Granular Control**: Fine-grained permissions for different actions
- **Audit Trail**: Complete logging of all access and actions

### Security Layers

```
┌─────────────────────────────────────────────────────────────┐
│                    Authentication                           │
│  • Azure AD Integration                                    │
│  • Function Key Authentication                             │
│  • Multi-Factor Authentication                             │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Authorization                            │
│  • Role-Based Access Control                               │
│  • Organization Isolation                                  │
│  • Workflow Permissions                                    │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Access Control                           │
│  • Data Access Policies                                    │
│  • Integration Permissions                                 │
│  • API Rate Limiting                                       │
└─────────────────────────────────────────────────────────────┘
```

---

## User Roles

### PlatformAdmin

**Description**: Full administrative access to the entire platform

**Capabilities**:
- Manage all organizations
- Create, update, delete organizations
- Manage platform-wide settings
- Access all workflows across all organizations
- View audit logs and system metrics
- Manage integrations and connections
- Configure platform security settings

**Use Cases**:
- Platform maintenance and administration
- Cross-organization support and troubleshooting
- System configuration and optimization

**Permissions**:
```json
{
  "organizations": ["create", "read", "update", "delete"],
  "workflows": ["create", "read", "update", "delete", "execute"],
  "integrations": ["create", "read", "update", "delete", "configure"],
  "users": ["create", "read", "update", "delete"],
  "audit_logs": ["read"],
  "platform_settings": ["read", "update"],
  "cross_org_access": true
}
```

### OrgAdmin

**Description**: Administrative access within a specific organization

**Capabilities**:
- Manage organization settings and configuration
- Manage users within the organization
- Create, update, delete workflows for the organization
- Configure integrations for the organization
- View organization audit logs
- Manage organization-specific secrets and credentials

**Use Cases**:
- Organization administration
- Workflow development and management
- Integration configuration
- User management within organization

**Permissions**:
```json
{
  "organization": ["read", "update"],
  "workflows": ["create", "read", "update", "delete", "execute"],
  "integrations": ["create", "read", "update", "delete", "configure"],
  "users": ["create", "read", "update", "delete"],
  "audit_logs": ["read"],
  "secrets": ["create", "read", "update", "delete"],
  "cross_org_access": false
}
```

### WorkflowDeveloper

**Description**: Can create and modify workflows within an organization

**Capabilities**:
- Create, update, delete workflows
- Execute workflows
- View workflow execution history
- Access organization configuration for workflow development
- Use organization integrations in workflows

**Use Cases**:
- Workflow development
- Business process automation
- Integration development

**Permissions**:
```json
{
  "workflows": ["create", "read", "update", "delete", "execute"],
  "integrations": ["read", "execute"],
  "organization": ["read"],
  "audit_logs": ["read"],
  "cross_org_access": false
}
```

### WorkflowUser

**Description**: Can execute workflows but cannot modify them

**Capabilities**:
- Execute approved workflows
- View own execution history
- Access workflow forms
- View workflow results

**Use Cases**:
- Day-to-day workflow execution
- Task automation
- Report generation

**Permissions**:
```json
{
  "workflows": ["execute"],
  "executions": ["read", "create"],
  "organization": ["read"],
  "cross_org_access": false
}
```

### ReadOnlyUser

**Description**: Read-only access to organization data

**Capabilities**:
- View workflows and their configurations
- View execution history and results
- View organization settings
- Access reports and dashboards

**Use Cases**:
- Auditing and compliance
- Monitoring and reporting
- Management oversight

**Permissions**:
```json
{
  "workflows": ["read"],
  "executions": ["read"],
  "organization": ["read"],
  "audit_logs": ["read"],
  "cross_org_access": false
}
```

---

## Permissions

### Permission Categories

#### Organization Permissions

| Permission | Description | PlatformAdmin | OrgAdmin | WorkflowDeveloper | WorkflowUser | ReadOnlyUser |
|------------|-------------|---------------|----------|------------------|--------------|--------------|
| `create` | Create new organizations | ✅ | ❌ | ❌ | ❌ | ❌ |
| `read` | View organization details | ✅ | ✅ | ✅ | ✅ | ✅ |
| `update` | Modify organization settings | ✅ | ✅ | ❌ | ❌ | ❌ |
| `delete` | Delete organizations | ✅ | ❌ | ❌ | ❌ | ❌ |

#### Workflow Permissions

| Permission | Description | PlatformAdmin | OrgAdmin | WorkflowDeveloper | WorkflowUser | ReadOnlyUser |
|------------|-------------|---------------|----------|------------------|--------------|--------------|
| `create` | Create new workflows | ✅ | ✅ | ✅ | ❌ | ❌ |
| `read` | View workflow configurations | ✅ | ✅ | ✅ | ✅ | ✅ |
| `update` | Modify workflow code | ✅ | ✅ | ✅ | ❌ | ❌ |
| `delete` | Delete workflows | ✅ | ✅ | ✅ | ❌ | ❌ |
| `execute` | Run workflows | ✅ | ✅ | ✅ | ✅ | ❌ |

#### Integration Permissions

| Permission | Description | PlatformAdmin | OrgAdmin | WorkflowDeveloper | WorkflowUser | ReadOnlyUser |
|------------|-------------|---------------|----------|------------------|--------------|--------------|
| `create` | Create new integrations | ✅ | ✅ | ❌ | ❌ | ❌ |
| `read` | View integration configurations | ✅ | ✅ | ✅ | ❌ | ❌ |
| `update` | Modify integration settings | ✅ | ✅ | ❌ | ❌ | ❌ |
| `delete` | Delete integrations | ✅ | ✅ | ❌ | ❌ | ❌ |
| `configure` | Configure OAuth and credentials | ✅ | ✅ | ❌ | ❌ | ❌ |
| `execute` | Use integrations in workflows | ✅ | ✅ | ✅ | ❌ | ❌ |

#### User Management Permissions

| Permission | Description | PlatformAdmin | OrgAdmin | WorkflowDeveloper | WorkflowUser | ReadOnlyUser |
|------------|-------------|---------------|----------|------------------|--------------|--------------|
| `create` | Create new users | ✅ | ✅ | ❌ | ❌ | ❌ |
| `read` | View user information | ✅ | ✅ | ✅ | ✅ | ✅ |
| `update` | Modify user roles and settings | ✅ | ✅ | ❌ | ❌ | ❌ |
| `delete` | Delete users | ✅ | ✅ | ❌ | ❌ | ❌ |

### Permission Inheritance

Permissions follow a hierarchical model where higher roles inherit all permissions of lower roles:

```
PlatformAdmin
├── OrgAdmin permissions
│   ├── WorkflowDeveloper permissions
│   │   ├── WorkflowUser permissions
│   │   │   └── ReadOnlyUser permissions
│   │   └── Additional workflow development permissions
│   └── Additional organization management permissions
└── Additional platform-wide permissions
```

---

## Organization Access

### Organization Membership

Users can be members of multiple organizations with different roles in each:

```json
{
  "user_id": "user-123",
  "memberships": [
    {
      "organization_id": "org-abc",
      "organization_name": "Client A",
      "role": "OrgAdmin",
      "permissions": ["organization:read", "organization:update", "workflows:*"]
    },
    {
      "organization_id": "org-def",
      "organization_name": "Client B",
      "role": "WorkflowDeveloper",
      "permissions": ["workflows:*", "integrations:execute"]
    },
    {
      "organization_id": "org-ghi",
      "organization_name": "Client C",
      "role": "WorkflowUser",
      "permissions": ["workflows:execute"]
    }
  ]
}
```

### Cross-Organization Access

**PlatformAdmin Only**: Only PlatformAdmins can access data across organizations, and all such access is audited:

```json
{
  "audit_event": {
    "timestamp": "2024-01-01T12:00:00Z",
    "user_id": "admin-user",
    "action": "cross_org_access",
    "target_org": "org-abc",
    "reason": "support_ticket_12345",
    "ip_address": "192.168.1.100",
    "user_agent": "Mozilla/5.0..."
  }
}
```

### Organization Isolation Enforcement

The platform enforces strict isolation at multiple levels:

#### 1. Data Level
- All database queries are automatically filtered by organization
- Users can only access data from their own organizations
- Cross-organization queries are blocked unless explicitly authorized

#### 2. API Level
- All API requests require organization context
- Organization validation is enforced in middleware
- Unauthorized access attempts are logged and blocked

#### 3. Workflow Level
- Workflows execute with organization-scoped context
- Integrations use organization-specific credentials
- Secrets are isolated per organization

---

## Workflow Permissions

### Workflow Access Control

Workflows have their own permission settings that can override user roles:

```python
@workflow(
    name="sensitive_workflow",
    description="Workflow with restricted access",
    category="administration",
    required_role="OrgAdmin",  # Only OrgAdmins can execute
    expose_in_forms=False      # Not available in forms
)
async def sensitive_workflow(context):
    # Sensitive operations
    pass
```

### Workflow Categories and Access

Different workflow categories have different default access requirements:

| Category | Default Required Role | Description |
|----------|---------------------|-------------|
| `user_management` | WorkflowDeveloper | User creation, updates, deactivation |
| `administration` | OrgAdmin | System administration tasks |
| `integration` | WorkflowDeveloper | Data synchronization and integration |
| `reporting` | WorkflowUser | Report generation and data analysis |
| `automation` | WorkflowDeveloper | Scheduled and automated tasks |
| `examples` | WorkflowUser | Example and template workflows |

### Workflow Execution Permissions

Users can only execute workflows they have permission for:

```python
# Permission check before execution
async def can_execute_workflow(user, workflow):
    user_role = get_user_role_in_org(user.id, workflow.organization_id)
    workflow_required_role = workflow.required_role
    
    return role_hierarchy[user_role] >= role_hierarchy[workflow_required_role]
```

---

## Integration Access

### Integration Scoping

Integrations are scoped at the organization level:

```json
{
  "integration_id": "msgraph-org-abc",
  "organization_id": "org-abc",
  "integration_type": "msgraph",
  "credentials": {
    "tenant_id": "tenant-abc",
    "client_id": "client-abc",
    "client_secret": "secret-abc"  # Encrypted and stored in Key Vault
  },
  "permissions": {
    "allowed_scopes": ["User.ReadWrite.All", "Group.ReadWrite.All"],
    "access_policy": "organization_only"
  }
}
```

### OAuth Connection Management

OAuth connections are managed per organization:

```python
# OAuth connections are isolated by organization
async def get_oauth_connection(context, provider_name):
    # Automatically scoped to organization
    connection_key = f"{context.org_id}--{provider_name}"
    
    # Retrieve organization-specific credentials
    credentials = await keyvault.get_secret(connection_key)
    
    return OAuthCredentials(credentials)
```

### Integration Usage Permissions

Different roles have different integration access levels:

| Role | Integration Permissions |
|------|------------------------|
| PlatformAdmin | Full access to all integrations across all organizations |
| OrgAdmin | Create, configure, and use integrations within organization |
| WorkflowDeveloper | Use existing integrations in workflows |
| WorkflowUser | Use integrations only through approved workflows |
| ReadOnlyUser | No direct integration access |

---

## Security Best Practices

### 1. Principle of Least Privilege

**Assign Minimum Required Permissions**:
```json
// ✅ Good - Specific permissions
{
  "role": "WorkflowUser",
  "permissions": ["workflows:execute", "executions:read"]
}

// ❌ Bad - Over-privileged
{
  "role": "OrgAdmin",
  "permissions": ["*"]  // Too broad
}
```

### 2. Regular Permission Audits

**Review User Access Quarterly**:
```python
# Audit script to check for over-privileged users
async def audit_user_permissions():
    suspicious_users = []
    
    for user in get_all_users():
        for membership in user.memberships:
            if membership.role == "OrgAdmin" and user.last_login > 90_days_ago:
                suspicious_users.append({
                    "user": user.email,
                    "organization": membership.organization_name,
                    "role": membership.role,
                    "last_login": user.last_login,
                    "issue": "Inactive admin user"
                })
    
    return suspicious_users
```

### 3. Separation of Duties

**Avoid Conflicting Roles**:
- Don't give the same user both development and admin roles in production
- Use different accounts for development and administration
- Implement approval workflows for sensitive operations

### 4. Temporary Access Elevation

**Just-In-Time Access**:
```python
# Temporary role elevation for specific tasks
async def grant_temporary_access(user_id, target_role, duration_hours, reason):
    elevation = TemporaryElevation(
        user_id=user_id,
        target_role=target_role,
        expires_at=datetime.now() + timedelta(hours=duration_hours),
        reason=reason,
        approved_by=current_user.id
    )
    
    await save_elevation(elevation)
    
    # Log the elevation
    context.log("warning", "Temporary access granted", {
        "user_id": user_id,
        "target_role": target_role,
        "duration": duration_hours,
        "reason": reason
    })
```

### 5. Multi-Factor Authentication

**Enforce MFA for Sensitive Roles**:
```json
{
  "mfa_requirements": {
    "PlatformAdmin": "required",
    "OrgAdmin": "required",
    "WorkflowDeveloper": "optional",
    "WorkflowUser": "optional",
    "ReadOnlyUser": "optional"
  }
}
```

### 6. Session Management

**Secure Session Configuration**:
```json
{
  "session_settings": {
    "timeout_minutes": {
      "PlatformAdmin": 30,
      "OrgAdmin": 60,
      "WorkflowDeveloper": 120,
      "WorkflowUser": 240,
      "ReadOnlyUser": 480
    },
    "require_reauth_for_sensitive_ops": true,
    "concurrent_sessions": {
      "PlatformAdmin": 1,
      "OrgAdmin": 2,
      "WorkflowDeveloper": 3,
      "WorkflowUser": 5,
      "ReadOnlyUser": 10
    }
  }
}
```

---

## Audit and Compliance

### Comprehensive Audit Logging

All permission-related actions are logged:

```json
{
  "audit_log": {
    "timestamp": "2024-01-01T12:00:00Z",
    "event_type": "permission_change",
    "user_id": "admin-123",
    "target_user": "user-456",
    "organization_id": "org-abc",
    "action": "role_assignment",
    "details": {
      "old_role": "WorkflowUser",
      "new_role": "WorkflowDeveloper",
      "reason": "Project requirement"
    },
    "ip_address": "192.168.1.100",
    "user_agent": "Mozilla/5.0...",
    "session_id": "sess-789"
  }
}
```

### Compliance Reporting

Generate compliance reports for audits:

```python
async def generate_access_report(organization_id, date_range):
    report = {
        "organization_id": organization_id,
        "date_range": date_range,
        "users_with_access": [],
        "permission_changes": [],
        "cross_org_access": [],
        "failed_access_attempts": []
    }
    
    # Compile user access data
    for user in get_organization_users(organization_id):
        report["users_with_access"].append({
            "user_id": user.id,
            "email": user.email,
            "role": user.role,
            "last_login": user.last_login,
            "permissions": get_user_permissions(user.id, organization_id)
        })
    
    return report
```

### Security Monitoring

Real-time security monitoring for suspicious activities:

```python
async def detect_suspicious_activity():
    alerts = []
    
    # Check for multiple failed logins
    failed_logins = get_recent_failed_logins(minutes=15)
    if len(failed_logins) > 10:
        alerts.append({
            "type": "brute_force_attempt",
            "severity": "high",
            "details": f"{len(failed_logins)} failed login attempts"
        })
    
    # Check for privilege escalation
    role_changes = get_recent_role_changes(hours=24)
    for change in role_changes:
        if is_privilege_escalation(change):
            alerts.append({
                "type": "privilege_escalation",
                "severity": "medium",
                "details": change
            })
    
    return alerts
```

This comprehensive permission system ensures that Bifrost Integrations maintains enterprise-grade security while providing the flexibility needed for different user roles and organizational structures.