# Authentication Model Fix

## Problem
The current authentication system incorrectly requires `X-Organization-Id` header in many places, but platform admins don't have an organization and should be able to operate globally.

## Core Principles

### 1. User Authentication
- **User is ALWAYS required** - every request must be authenticated
- Users are identified via Azure AD (production) or test headers (local dev)
- User ID is typically their email address

### 2. Organization Context
- **Organization is OPTIONAL** - depends on the user type
- Platform admins (IsPlatformAdmin=true, UserType=PLATFORM) have NO organization
- Regular users belong to ONE organization
- Organization context is passed via `X-Organization-Id` header when present

### 3. Permission Model
- **Platform admins can do everything**:
  - Access all organizations' data
  - View all execution history (across all orgs)
  - Manage all forms (org-specific and global)
  - Access all workflows
  - Manage all config
- **Regular users have limited access**:
  - Only their organization's data
  - Forms they have permission to execute (public or role-assigned)
  - Workflows via permitted forms
  - Limited config access

## Required Changes

### Management API (`client/api/`)

#### Forms Endpoints (`functions/forms.py`)
- [x] `GET /forms` - Already supports optional org (line 51: `require_org=False`)
- [ ] `GET /forms/{formId}` - Make org optional, try GLOBAL partition if no org
- [ ] `POST /forms/{formId}/submit` - Make org optional for platform admins
- [ ] `PUT /forms/{formId}` - Make org optional, but validate platform admin
- [ ] `DELETE /forms/{formId}` - Make org optional, but validate platform admin

#### Executions Endpoints (`functions/executions.py`)
- [ ] `GET /executions` - Make org optional for platform admins (fetch from all orgs)
- [ ] `GET /executions/{executionId}` - Make org optional, search across all orgs if platform admin

#### Other Endpoints
- [ ] Review all endpoints for unnecessary org requirement
- [ ] Add platform admin checks where needed

### Workflow Engine (`workflows/engine/`)

#### Middleware (`engine/shared/middleware.py`)
- [ ] `with_org_context` - Make org_id OPTIONAL
- [ ] Create `load_platform_admin_context` for platform admins without org
- [ ] Update `OrganizationContext` to support platform admins (org=None case)

#### Execute Endpoint (`engine/execute.py`)
- [ ] Support execution without org context (for platform admins testing workflows)
- [ ] Allow workflows to run in "global" mode when no org provided

### Client (`client/src/`)

#### API Client (`services/api.ts`)
- [ ] Handle missing `current_org_id` gracefully
- [ ] Don't send `X-Organization-Id` header if not present
- [ ] Update line 81-82 to only add header if contextOrgId exists

#### Components
- [ ] Add platform admin indicator in UI
- [ ] Show "Global" context when no org selected
- [ ] Allow org selection for platform admins

## Implementation Order

1. **Fix Management API forms endpoints** (highest priority - blocking current issue)
2. **Fix Management API executions endpoints** (needed for history page)
3. **Fix Workflow Engine middleware** (needed for workflow execution)
4. **Update Client** (needed for proper UX)
5. **Review and test** (end-to-end testing)

## Testing Checklist

### Platform Admin
- [ ] Can list all forms (no org filter)
- [ ] Can view specific form (GLOBAL partition)
- [ ] Can create forms (both org-specific and global)
- [ ] Can view all execution history (across all orgs)
- [ ] Can execute workflows (with org context or globally)

### Regular User
- [ ] Can only list forms for their org
- [ ] Can only view forms they have access to
- [ ] Cannot create forms
- [ ] Can only view their org's execution history
- [ ] Can execute workflows within their org context
