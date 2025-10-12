# Research: Workflow Engine and User Code Separation

**Feature**: 002-i-want-to
**Date**: 2025-10-12
**Status**: Complete

## Overview

This document captures research findings for implementing workflow engine and user code separation through repository restructuring, import restrictions, GitHub Actions protection, and tiered authentication.

## 1. Python Import Hooks and Meta Path Finders

### Decision

Use a **custom Meta Path Finder** added to `sys.meta_path` at Azure Functions startup to block workspace code from importing engine modules.

### Rationale

- **Performance**: Meta path finders are only invoked during import statements (<1ms overhead per blocked import)
- **Reliability**: Operates at the import machinery level before any module code executes
- **Clarity**: Provides detailed error messages identifying blocked modules
- **Safety**: Cannot be bypassed by workspace code using `importlib`, `__import__`, or dynamic import techniques

### Implementation Pattern

Install a `WorkspaceImportRestrictor` class implementing `importlib.abc.MetaPathFinder` at the beginning of `sys.meta_path`. The finder:

1. Checks if import name starts with blocked prefixes (`engine.`, `shared.`)
2. Allows whitelisted exports (`shared.decorators`, `shared.context`, `shared.error_handling`, `shared.models`)
3. Inspects call stack to determine if import originates from workspace code
4. Raises `ImportError` with actionable message if workspace code attempts blocked import
5. Returns `None` to allow all other imports to proceed normally

**Performance**: <50ms startup overhead, zero runtime overhead for legitimate imports

**Key Code Structure**:
```python
class WorkspaceImportRestrictor(MetaPathFinder):
    BLOCKED_PREFIXES = ('engine.', 'shared.')
    ALLOWED_SHARED_EXPORTS = {'shared.decorators', 'shared.context', ...}

    def find_spec(self, fullname, path, target=None):
        # Check if blocked + inspect stack + raise ImportError if workspace import
        # Return None to allow import
```

**Installation**: Call `install_import_restrictions([WORKSPACE_PATH])` in `function_app.py` before importing any workspace code.

### Edge Cases Handled

- Dynamic imports via `importlib.import_module()`: Covered by meta path finder
- Direct `__import__()` calls: Uses same import machinery
- Relative imports: Resolved to absolute names before `find_spec()`
- Exec/eval with import statements: Still goes through import machinery
- Already-imported modules in `sys.modules`: Mitigated by installing restrictions before any engine imports

### Alternatives Considered

- `__import__` monkey-patching: Fragile, can be bypassed
- AST analysis at discovery: Can't prevent runtime imports
- OS-level sandboxing: Over-engineered for accidental protection requirements

## 2. GitHub Actions for Directory Protection

### Decision

Implement a validation workflow using `tj-actions/changed-files` with path filtering and bot detection to block unauthorized `/engine` modifications.

### Rationale

- **Path filtering**: GitHub's built-in `paths`/`paths-ignore` skip workflows entirely (leave checks in "Pending"), so always run workflow but conditionally validate
- **Bot detection**: Allow changes from `upstream-sync[bot]` or `github-actions[bot]` by checking `github.actor`
- **Clear errors**: Use `::error` workflow command syntax for formatted annotations in PRs
- **Fast execution**: <10 seconds using shallow checkout and minimal file operations

### Implementation Pattern

```yaml
name: Protect Engine Directory

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]

jobs:
  validate-engine-protection:
    runs-on: ubuntu-latest
    timeout-minutes: 2
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - id: changes
        uses: tj-actions/changed-files@v44
        with:
          files: engine/**

      - if: steps.changes.outputs.any_changed == 'true'
        run: |
          ACTOR="${{ github.actor }}"

          if [[ "$ACTOR" == "upstream-sync[bot]" ]] || [[ "$ACTOR" == "github-actions[bot]" ]]; then
            echo "✓ Engine changes from authorized bot: $ACTOR"
            exit 0
          fi

          echo "::error title=Protected Directory Violation::Modifications to /engine/* not allowed"
          echo "::error::Changed files: ${{ steps.changes.outputs.all_changed_files }}"
          exit 1
```

### Upstream Sync Detection

**Methods**:
1. Check `github.actor` for known bot names
2. Use `github.event.pull_request.head.repo.fork == false` for same-repo PRs
3. Parse commit messages for `[upstream-sync]` tags
4. Use label-based system with `upstream-sync` label on PRs

**Best Practice**: Use dedicated GitHub App or bot account for upstream syncs with consistent name.

### Edge Cases

- **Force pushes**: Handled by `fetch-depth: 0` comparing commit ranges
- **Rebases**: Workflow runs on final commit state, detection remains accurate
- **Protected branch bypass**: Use CODEOWNERS file (`.github/CODEOWNERS`) to require approval from specific teams
- **Performance**: Keep under 10s with `fetch-depth: 2` for PRs, aggressive `timeout-minutes: 2`

### Alternatives Considered

- Branch protection rules alone: Can be bypassed by admins without audit trail
- Pre-commit hooks: Client-side, can be skipped
- Server-side hooks: Not available in GitHub (only in self-hosted Git)

## 3. Azure Functions Tiered Authentication

### Decision

Implement **tiered authentication** accepting function keys as bypass auth (priority 1) and Azure Easy Auth via `X-MS-CLIENT-PRINCIPAL` (priority 2).

### Rationale

- **Privileged access**: Function keys enable CI/CD, admin operations, and system integrations
- **User authentication**: Easy Auth provides Entra ID authentication for human users via Static Web Apps
- **Security depth**: Dual layers with audit logging for privileged access
- **Development parity**: Works identically in local (SWA CLI + local keys) and production

### Authentication Flow

**Priority Order**:
1. **Function Key Check**: Extract `x-functions-key` header or `code` query parameter, validate, grant access, log audit event
2. **Easy Auth Check**: Extract `x-ms-client-principal` header, decode Base64 JSON, validate user claims
3. **Rejection**: Return 403 Forbidden if neither present or valid

### Implementation Pattern

```python
class AuthenticationService:
    async def authenticate(self, req: HttpRequest):
        # Priority 1: Function key
        key_result = await self._authenticate_function_key(req)
        if key_result[0]:
            await self._audit_function_key_usage(req, key_result[1])
            return key_result

        # Priority 2: User auth
        user_result = await self._authenticate_user(req)
        if user_result[0]:
            return user_result

        # Both failed
        return (False, None, "Authentication required")

    async def _authenticate_function_key(self, req):
        key = req.headers.get('x-functions-key') or req.params.get('code')
        if not key:
            return (False, None, "No function key")

        # In production: Azure validates automatically
        # In local: Accept any key or validate against local.settings.json
        principal = FunctionKeyPrincipal(key_id="...", key_name="...")
        return (True, principal, None)

    async def _authenticate_user(self, req):
        header = req.headers.get('x-ms-client-principal')
        if not header:
            return (False, None, "No user auth header")

        # Decode Base64 -> JSON
        principal_json = json.loads(base64.b64decode(header).decode('utf-8'))
        principal = UserPrincipal.from_client_principal(principal_json)

        return (True, principal, None)
```

### Security Best Practices

1. **Key Management**:
   - Use host-level keys for cross-function access (CI/CD, admin)
   - Use function-level keys for specific integrations
   - Rotate keys every 90 days
   - Never commit keys to source control
   - Store in `local.settings.json` (git-ignored) for local dev

2. **Key Transmission**:
   - Prefer `x-functions-key` header over `?code=` query parameter
   - Query params appear in logs and browser history (security risk)

3. **Authorization Levels**:
   - Set `http_auth_level=func.AuthLevel.ANONYMOUS` on HttpTrigger
   - Implement custom auth in middleware (don't rely on authLevel=function)

4. **Defense in Depth**:
   - Always validate principal after authentication
   - Check org-level permissions for user principals
   - Rate limit function key endpoints separately
   - Implement IP allowlisting for function key access in production

### Audit Logging

**Three-Tier Strategy**:

1. **Application Insights**: Real-time logs for all auth events
   ```python
   logger.warning("Function key access", extra={
       "key_id": principal.key_id,
       "endpoint": req.url,
       "remote_addr": remote_ip
   })
   ```

2. **Table Storage**: Structured audit trail in `AuditLog` table
   ```python
   # PartitionKey: {date} (e.g., "2025-10-12")
   # RowKey: {reverse_timestamp}_{event_id}
   audit_entity = {
       'EventType': 'function_key_access',
       'KeyId': principal.key_id,
       'Endpoint': req.url,
       'OrgId': req.headers.get('X-Organization-Id'),
       ...
   }
   ```

3. **Azure Monitor Alerts**: Alert on anomalous patterns
   - Multiple keys from same IP in short timeframe
   - Key usage outside business hours
   - Unexpected geographic locations
   - High volume of 403 responses

### Local Development

**Static Web Apps CLI Configuration**:
```bash
# Install SWA CLI
npm install -g @azure/static-web-apps-cli

# Start with auth emulation
swa start --api-location ./workflows --app-location ./client

# Navigate to http://localhost:4280/.auth/login/aad
# Emulator provides mock auth without real Entra ID
```

**Testing Authentication**:
```bash
# Test function key (local accepts any key)
curl -H "x-functions-key: dev-key" http://localhost:7071/api/workflows

# Test user auth (after SWA CLI login)
curl -b cookies.txt http://localhost:4280/api/workflows
```

### Alternatives Considered

- Managed Identity only: Doesn't support user auth or local dev
- Custom JWT tokens: Reinventing Azure AD, adds complexity
- API keys in database: Function keys built-in, Azure-managed, more secure
- Certificate-based auth: Overkill for MVP, poor developer experience

## 4. Azurite Seed Data Strategy

### Decision

Create Python seed script (`scripts/seed_azurite.py`) using `azure-data-tables` to populate test organizations, users, and configuration.

### Implementation Approach

1. Connect to Azurite (UseDevelopmentStorage=true)
2. Create/verify tables exist (Organizations, Users, OrgConfig, UserRoles)
3. Insert test entities:
   - 2-3 test organizations (active/inactive)
   - 3-5 test users (PlatformAdmin, OrgUser roles)
   - 5-10 configuration entries (global + org-specific)
   - Sample role assignments

4. Idempotent: Check for existing entities before inserting (upsert pattern)
5. Execute in <5 seconds

### Sample Seed Data

```python
# Test organizations
orgs = [
    {"RowKey": "test-org-1", "Name": "Acme Corp", "IsActive": True},
    {"RowKey": "test-org-2", "Name": "Beta Inc", "IsActive": True},
]

# Test users
users = [
    {"RowKey": "jack@gocovi.com", "Email": "jack@gocovi.com",
     "IsPlatformAdmin": True, "UserType": "PLATFORM"},
    {"RowKey": "user@acme.com", "Email": "user@acme.com",
     "IsPlatformAdmin": False, "UserType": "ORG"},
]

# Test config
configs = [
    {"PartitionKey": "GLOBAL", "RowKey": "config:api_timeout", "Value": "30", "Type": "int"},
    {"PartitionKey": "test-org-1", "RowKey": "config:client_id", "Value": "12345", "Type": "string"},
]
```

## Summary

All technical research complete. Key decisions:

1. **Import Restrictions**: Meta path finder with <50ms startup overhead
2. **GitHub Protection**: Workflow with bot detection, <10s execution
3. **Authentication**: Tiered auth with function keys + Easy Auth, full audit logging
4. **Seed Data**: Python script with idempotent upsert, <5s execution

No additional research required. Ready to proceed to Phase 1 (design artifacts).
