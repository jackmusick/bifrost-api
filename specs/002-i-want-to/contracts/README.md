# API Contracts: Workflow Engine and User Code Separation

**Feature**: 002-i-want-to
**Date**: 2025-10-12

## Overview

This feature does not introduce new public-facing API endpoints. Instead, it modifies the authentication behavior of existing workflow execution endpoints and adds internal contracts for import restrictions and audit logging.

## Modified Endpoints

### Workflow Execution (Modified Authentication)

**Endpoint**: `POST /api/workflows/{workflowName}`

**Changes**: Authentication now supports tiered approach with function keys

**Authentication** (Priority Order):
1. Function Key: `x-functions-key` header or `?code=` query parameter
2. User Auth: `X-MS-CLIENT-PRINCIPAL` header (Azure Easy Auth)
3. Reject: 403 Forbidden if neither present

**Request Headers** (Modified):
```
x-functions-key: <function-key>         # NEW: Bypass auth (optional)
X-MS-CLIENT-PRINCIPAL: <base64-jwt>     # Existing: User auth (optional)
X-Organization-Id: <org-id>             # Existing: Target org (required)
X-User-Id: <user-id>                    # Modified: Only used with function key auth
Content-Type: application/json
```

**Request Body**: Unchanged
```json
{
  "param1": "value1",
  "param2": "value2",
  "_formId": "optional-form-id"
}
```

**Response**: Unchanged
```json
{
  "executionId": "uuid",
  "status": "Success" | "Running" | "Failed",
  "result": {},
  "durationMs": 1234,
  "startedAt": "2025-10-12T14:30:00Z",
  "completedAt": "2025-10-12T14:30:01Z"
}
```

**Error Responses** (Modified):
```json
// 403 Forbidden - No authentication provided
{
  "error": "Unauthorized",
  "message": "Authentication required: Provide x-functions-key header or authenticate via Azure AD"
}

// 403 Forbidden - Invalid organization
{
  "error": "Forbidden",
  "message": "Organization 'invalid-org' not found or inactive"
}
```

**Examples**:

```bash
# Function key authentication (bypass)
curl -X POST https://api.example.com/api/workflows/user-onboarding \
  -H "x-functions-key: AbCdEf123456..." \
  -H "X-Organization-Id: test-org-1" \
  -H "X-User-Id: system@automation.local" \
  -H "Content-Type: application/json" \
  -d '{"userName": "john.doe", "email": "john@example.com"}'

# User authentication (Azure Easy Auth)
curl -X POST https://api.example.com/api/workflows/user-onboarding \
  -H "X-MS-CLIENT-PRINCIPAL: eyJ1c2VySWQiOiJhYmMxMjMiLCJ1c2VyRGV0YWlscyI6ImpvaG5AZXhhbXBsZS5jb20ifQ==" \
  -H "X-Organization-Id: test-org-1" \
  -H "Content-Type: application/json" \
  -d '{"userName": "john.doe"}'

# Local development (function key)
curl -X POST http://localhost:7071/api/workflows/user-onboarding \
  -H "x-functions-key: dev-key" \
  -H "X-Organization-Id: test-org-1" \
  -H "X-User-Id: jack@gocovi.com" \
  -H "Content-Type: application/json" \
  -d '{"userName": "test.user"}'
```

## Internal Contracts

### Import Restriction Contract

**Module**: `shared.import_restrictions`

**Public API**:

```python
def install_import_restrictions(workspace_paths: list[str]) -> None:
    """
    Install import restrictions before workspace code discovery.

    Must be called in function_app.py before importing any workspace modules.

    Args:
        workspace_paths: Absolute paths to workspace directories

    Raises:
        ValueError: If workspace_paths contains relative paths
    """

def remove_import_restrictions() -> None:
    """
    Remove import restrictions (useful for testing).

    Removes all WorkspaceImportRestrictor instances from sys.meta_path.
    """

class WorkspaceImportRestrictor(MetaPathFinder):
    """
    Meta path finder that blocks workspace code from importing engine modules.

    Blocked prefixes: engine.*, shared.* (except whitelisted exports)
    Allowed exports: shared.decorators, shared.context, shared.error_handling, shared.models
    """

    BLOCKED_PREFIXES: tuple[str, ...] = ('engine.', 'shared.')
    ALLOWED_SHARED_EXPORTS: set[str] = {
        'shared.decorators',
        'shared.context',
        'shared.error_handling',
        'shared.models'
    }

    def __init__(self, workspace_paths: list[str]) -> None:
        """
        Initialize restrictor with workspace paths.

        Args:
            workspace_paths: List of absolute directory paths considered "workspace code"
        """

    def find_spec(self, fullname: str, path: Any, target: Any) -> None:
        """
        Check if import should be blocked.

        Called automatically by Python's import system.

        Args:
            fullname: Fully qualified module name (e.g., "engine.shared.storage")
            path: Module search path
            target: Target module (optional)

        Returns:
            None: Allow import to proceed

        Raises:
            ImportError: If workspace code attempts to import blocked module
        """
```

**Error Messages**:

```python
# When workspace code attempts blocked import
ImportError: Workspace code cannot import engine module 'engine.shared.storage'. Use only the public API exported through 'shared.decorators', 'shared.context', 'shared.error_handling', and 'shared.models'. See documentation at /docs/workspace-api.md
```

**Usage Example**:

```python
# In function_app.py
from shared.import_restrictions import install_import_restrictions
import os

WORKSPACE_PATH = os.path.join(os.path.dirname(__file__), 'workspace')
install_import_restrictions([WORKSPACE_PATH])

# Now safe to import workspace code - restrictions active
import workflows  # Auto-discovers workflows in /workspace
```

### Authentication Service Contract

**Module**: `shared.auth`

**Public API**:

```python
@dataclass
class FunctionKeyPrincipal:
    """Authenticated principal via function key."""
    auth_type: str = "function_key"
    key_id: str = ""
    key_name: str = ""

@dataclass
class UserPrincipal:
    """Authenticated user via Easy Auth."""
    auth_type: str = "user"
    user_id: str = ""
    email: str = ""
    name: str = ""
    identity_provider: str = ""
    roles: list[str] = field(default_factory=list)

    @classmethod
    def from_client_principal(cls, principal_data: dict[str, Any]) -> 'UserPrincipal':
        """Parse X-MS-CLIENT-PRINCIPAL header data into UserPrincipal."""

class AuthenticationService:
    """Handles tiered authentication for Azure Functions."""

    async def authenticate(self, req: HttpRequest) -> tuple[bool, Optional[Union[FunctionKeyPrincipal, UserPrincipal]], Optional[str]]:
        """
        Authenticate request using tiered approach.

        Priority:
        1. Function key (x-functions-key header or code query param)
        2. User auth (X-MS-CLIENT-PRINCIPAL header)
        3. Reject

        Args:
            req: Azure Functions HttpRequest

        Returns:
            Tuple of (success, principal, error_message)
            - success: bool - True if authenticated
            - principal: FunctionKeyPrincipal | UserPrincipal | None
            - error_message: str | None - Error description if failed
        """

def require_auth(func: Callable) -> Callable:
    """
    Decorator to enforce tiered authentication on Azure Function endpoints.

    Attaches authenticated principal to req.principal for downstream use.
    Returns 403 Forbidden if authentication fails.

    Usage:
        @app.route(route="workflows", methods=["POST"])
        @require_auth
        async def execute_workflow(req: func.HttpRequest) -> func.HttpResponse:
            principal = req.principal  # FunctionKeyPrincipal or UserPrincipal
            ...
    """
```

**Authentication Flow**:

```
Request → @require_auth decorator
    ↓
AuthenticationService.authenticate()
    ↓
Check x-functions-key
    ↓ (if present & valid)
FunctionKeyPrincipal → Log audit event → Attach to req.principal → Continue
    ↓ (if not present)
Check X-MS-CLIENT-PRINCIPAL
    ↓ (if present & valid)
UserPrincipal → Attach to req.principal → Continue
    ↓ (if not present)
Return 403 Forbidden
```

### Audit Logging Contract

**Module**: `shared.audit`

**Public API**:

```python
class AuditLogger:
    """Structured audit logging to Table Storage."""

    async def log_function_key_access(
        self,
        key_id: str,
        key_name: str,
        org_id: str,
        endpoint: str,
        method: str,
        remote_addr: str,
        user_agent: str,
        status_code: int,
        details: dict[str, Any] = None
    ) -> None:
        """
        Log function key authentication usage.

        Creates entry in AuditLog table with EventType='function_key_access'.

        Args:
            key_id: Function key identifier
            key_name: Friendly key name
            org_id: Target organization ID
            endpoint: API endpoint path
            method: HTTP method
            remote_addr: Client IP address
            user_agent: Client user agent string
            status_code: HTTP response status
            details: Additional context (JSON-serializable)
        """

    async def log_cross_org_access(
        self,
        user_id: str,
        target_org_id: str,
        endpoint: str,
        method: str,
        remote_addr: str,
        status_code: int,
        details: dict[str, Any] = None
    ) -> None:
        """
        Log PlatformAdmin cross-organization access.

        Creates entry in AuditLog table with EventType='cross_org_access'.

        Args:
            user_id: Admin user ID
            target_org_id: Organization being accessed
            endpoint: API endpoint path
            method: HTTP method
            remote_addr: Client IP address
            status_code: HTTP response status
            details: Additional context (reason, support ticket, etc.)
        """

    async def log_import_violation_attempt(
        self,
        blocked_module: str,
        workspace_file: str,
        stack_trace: list[str]
    ) -> None:
        """
        Log attempted workspace→engine import violation.

        Creates entry in AuditLog table with EventType='engine_violation_attempt'.

        Args:
            blocked_module: Module name that was blocked
            workspace_file: Source file that attempted import
            stack_trace: Python stack trace (file:line format)
        """

def get_audit_logger() -> AuditLogger:
    """Get singleton AuditLogger instance."""
```

**AuditLog Table Schema**:

```python
# Entity structure
{
    "PartitionKey": "2025-10-12",  # Date (YYYY-MM-DD)
    "RowKey": "9999999999999_abc123",  # Reverse timestamp + UUID
    "EventType": "function_key_access",  # Event type
    "Timestamp": "2025-10-12T14:30:45.123Z",
    "KeyId": "default",
    "KeyName": "ci-cd-pipeline",
    "OrgId": "test-org-1",
    "Endpoint": "/api/workflows/user-onboarding",
    "Method": "POST",
    "RemoteAddr": "203.0.113.42",
    "UserAgent": "curl/7.68.0",
    "StatusCode": 200,
    "Details": "{\"duration_ms\": 234}"  # JSON string
}
```

## GitHub Actions Contract

**Workflow**: `.github/workflows/protect-engine.yml`

**Trigger Events**:
- `push` to branches: main, develop
- `pull_request` to branches: main, develop

**Job**: `validate-engine-protection`

**Outputs**: None (workflow fails if violations detected)

**Error Format**:
```
::error title=Protected Directory Violation::Modifications to /engine/* are not allowed from developer commits.
::error::The /engine directory is synchronized from the upstream repository only.
::error::Changed files: engine/shared/storage.py, engine/execute.py
```

**Success Conditions**:
- No files in `/engine/*` modified
- OR actor is `upstream-sync[bot]` or `github-actions[bot]`
- OR PR has `upstream-sync` label

**Failure Conditions**:
- Files in `/engine/*` modified by non-authorized actor
- Timeout exceeded (2 minutes)

## Backward Compatibility

**Existing Endpoints**: No breaking changes
- Existing authentication (X-MS-CLIENT-PRINCIPAL) continues to work
- Existing org context loading unchanged
- Existing workflow execution flow preserved

**New Capabilities** (Additive):
- Function key authentication support
- Audit logging for privileged access
- Import restrictions (runtime protection)
- GitHub Actions protection (commit-time protection)

**Migration**: Zero-downtime deployment
1. Deploy new authentication code (supports both old and new auth)
2. Deploy GitHub Action (validates new commits)
3. Deploy import restrictions (validates at runtime)
4. Create AuditLog table (auto-created on first use)

## Security Considerations

**Function Keys**:
- Treat as secrets (never commit to source control)
- Rotate every 90 days
- Use `x-functions-key` header (not query param) to avoid logging
- Restrict to known IP ranges in production

**Audit Logs**:
- Retain for 90 days minimum
- Monitor for anomalous patterns
- Alert on high-volume function key usage
- Review cross-org access regularly

**Import Restrictions**:
- Cannot be bypassed by workspace code
- Covers all import mechanisms (importlib, __import__, dynamic imports)
- Clear error messages guide developers to public API

## Testing Contracts

**Authentication Tests**:
```python
# Contract test: Function key auth
async def test_function_key_authentication():
    req = create_mock_request(
        headers={'x-functions-key': 'test-key'},
        params={'X-Organization-Id': 'test-org'}
    )
    response = await execute_workflow(req)
    assert response.status_code == 200

# Contract test: User auth
async def test_user_authentication():
    principal_b64 = base64.b64encode(json.dumps({
        'userId': 'user123',
        'userDetails': 'john@example.com',
        'userRoles': ['authenticated']
    }).encode()).decode()

    req = create_mock_request(
        headers={
            'X-MS-CLIENT-PRINCIPAL': principal_b64,
            'X-Organization-Id': 'test-org'
        }
    )
    response = await execute_workflow(req)
    assert response.status_code == 200

# Contract test: No auth
async def test_no_authentication():
    req = create_mock_request(headers={})
    response = await execute_workflow(req)
    assert response.status_code == 403
```

**Import Restriction Tests**:
```python
# Contract test: Blocked import
def test_workspace_cannot_import_engine():
    install_import_restrictions(['/workspace'])

    with pytest.raises(ImportError, match="cannot import engine module"):
        # Simulate import from workspace
        exec("from engine.shared.storage import get_table_storage_service")

# Contract test: Allowed import
def test_workspace_can_import_allowed_shared():
    install_import_restrictions(['/workspace'])

    # Should not raise
    from shared.decorators import workflow
    from shared.context import OrganizationContext
```

**GitHub Action Tests**:
```bash
# Manual test: Attempt to modify engine file
echo "# test change" >> engine/shared/storage.py
git add engine/shared/storage.py
git commit -m "test: attempt engine modification"
git push origin feature-branch

# Expected: GitHub Action fails with error message
# Expected: PR shows failed check with annotation
```

## Summary

This feature modifies authentication contracts (additive changes) and introduces internal contracts for import restrictions and audit logging. All changes are backward compatible with existing workflow execution endpoints.
