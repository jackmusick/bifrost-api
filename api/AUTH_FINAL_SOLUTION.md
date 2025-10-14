##

 The Ideal Auth Architecture

### Current Mess (3 different systems):

1. **auth.py** (730 lines)
   - Old: `@require_auth` → `req.user` (AuthenticatedUser model)
   - New: `@require_auth` → `req.principal` (FunctionKeyPrincipal/UserPrincipal)
   - Hardcoded "jack@gocovi.com" test users
   - Duplicate decorators with same name

2. **auth_headers.py** (303 lines)
   - `get_auth_headers()` - derives org from DB
   - `get_scope_context()` - also derives org from DB (redundant!)

3. **middleware.py** (244 lines)
   - `@with_org_context` - used by engine
   - Creates full `OrganizationContext` object
   - Calls `AuthenticationService` internally

**Total: 1,277 lines of auth code!**

---

## The Solution: Single Context Function

### New File: `request_context.py` (220 lines)

```python
from shared.request_context import get_request_context

# That's it! One function, one pattern.
context = get_request_context(req)

# Everything you need:
context.user_id        # User ID
context.email          # Email
context.org_id         # Org ID (or None for GLOBAL)
context.is_platform_admin
context.is_function_key
context.scope          # "org-123" or "GLOBAL" for DB queries
```

---

## How It Works

### 1. Azure Functions Handles Auth Level

```python
# function_app.py
app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)
```

This means Azure Functions automatically:
- Checks for function key (x-functions-key header or ?code param)
- Returns 401 if missing
- No Python code needed!

### 2. For Public Endpoints

```python
@bp.route(route="health", methods=["GET"], auth_level=func.AuthLevel.ANONYMOUS)
def public_health(req: func.HttpRequest):
    return func.HttpResponse('{"status": "ok"}')
```

### 3. For Context-Aware Endpoints

```python
@bp.route(route="organizations", methods=["GET"])
async def list_organizations(req: func.HttpRequest):
    # Get context (one line!)
    context = get_request_context(req)

    # Use it
    if context.is_platform_admin:
        # Return all orgs
        orgs = query_all_organizations()
    else:
        # Return user's org only
        orgs = query_organization(context.org_id)

    return func.HttpResponse(json.dumps(orgs))
```

### 4. For Workflow Execution

```python
@bp.route(route="workflows/{name}", methods=["POST"])
async def execute_workflow(req: func.HttpRequest):
    # Get context
    context = get_request_context(req)

    # Create full OrganizationContext for workflow
    org_context = await load_full_context(context)

    # Execute workflow
    result = await workflow_func(org_context)
```

---

## Context Determination Rules

### Function Key Auth:
```
x-functions-key: abc123
X-Organization-Id: org-456  (optional)

Result:
  user_id: "system"
  email: "system@local"
  org_id: "org-456" or None
  is_platform_admin: True
  is_function_key: True
```

### Easy Auth (Platform Admin):
```
X-MS-CLIENT-PRINCIPAL: <base64 encoded user>
X-Organization-Id: org-789  (optional)

Checks database: User is platform admin

Result:
  user_id: "user@example.com"
  email: "user@example.com"
  org_id: "org-789" or None (from header)
  is_platform_admin: True
  is_function_key: False
```

### Easy Auth (Regular User):
```
X-MS-CLIENT-PRINCIPAL: <base64 encoded user>
X-Organization-Id: (ignored if provided)

Looks up user in database: User belongs to org-123

Result:
  user_id: "user@example.com"
  email: "user@example.com"
  org_id: "org-123" (from database)
  is_platform_admin: False
  is_function_key: False
```

### Local Dev (No Auth):
```
(no headers)

Result:
  user_id: "local-dev"
  email: "local-dev@system.local"
  org_id: None (GLOBAL)
  is_platform_admin: True
  is_function_key: True
```

---

## Backwards Compatibility with Engine

The engine's `@with_org_context` middleware can be updated to use `get_request_context()`:

```python
# shared/middleware.py (simplified)
def with_org_context(handler):
    @functools.wraps(handler)
    async def wrapper(req: func.HttpRequest):
        # Get request context
        req_context = get_request_context(req)

        # Load full organization context
        org_context = await load_full_org_context(req_context)

        # Inject into request
        req.context = org_context

        return await handler(req)
    return wrapper

async def load_full_org_context(req_context: RequestContext) -> OrganizationContext:
    """Create full OrganizationContext from RequestContext"""
    # Load org data, config, etc.
    # This is what middleware.py already does, just use req_context instead
    ...
```

---

## Migration Plan

### Phase 1: Add New System (Non-Breaking)

1. Add `shared/request_context.py` (already done ✅)
2. Test in one endpoint to verify it works
3. Keep old code unchanged

### Phase 2: Migrate Management API

For each endpoint in `functions/`:

**Before:**
```python
from shared.auth import require_auth, is_platform_admin
from shared.auth_headers import get_scope_context

@bp.route(route="health/keyvault", methods=["GET"])
@require_auth
def keyvault_health(req: func.HttpRequest):
    user = req.user
    if not is_platform_admin(user.user_id):
        return error(403, "Forbidden")
```

**After:**
```python
from shared.request_context import get_request_context

@bp.route(route="health/keyvault", methods=["GET"])
def keyvault_health(req: func.HttpRequest):
    context = get_request_context(req)
    if not context.is_platform_admin:
        return error(403, "Forbidden")
```

### Phase 3: Simplify Engine Middleware

Update `shared/middleware.py`:

```python
from shared.request_context import get_request_context

def with_org_context(handler):
    async def wrapper(req: func.HttpRequest):
        # Use new context instead of AuthenticationService
        req_context = get_request_context(req)

        # Build full OrganizationContext
        org_context = await load_full_org_context(req_context)
        req.context = org_context

        return await handler(req)
    return wrapper
```

### Phase 4: Delete Old Code

Once all endpoints migrated:

```bash
# Delete old files
rm api/shared/auth_headers.py

# Clean up auth.py - keep only:
# - FunctionKeyPrincipal / UserPrincipal (used by tests)
# - AuthenticationError / AuthorizationError (exceptions)
# Delete everything else
```

---

## Benefits

| Aspect | Before | After |
|--------|--------|-------|
| **Files** | 3 files (auth.py, auth_headers.py, middleware.py) | 2 files (request_context.py, middleware.py) |
| **Lines** | 1,277 lines | ~400 lines |
| **Functions to know** | 6+ (require_auth, get_auth_headers, get_scope_context, etc.) | 1 (get_request_context) |
| **Decorators** | 3 decorators | 0 (Azure handles auth level) |
| **Hardcoded test users** | Yes ("jack@gocovi.com") | No |
| **Duplicate logic** | High (3 places check admin, 2 places derive org) | None |
| **Confusion** | High (which auth to use?) | None (one function) |

---

## Why This Is Better Than Current Code

### Problem 1: Too Many Ways to Get Context
**Before:** Choose from:
- `get_authenticated_user()` → old model
- `@require_auth` → which one? There are TWO!
- `get_auth_headers()` → one of two ways
- `get_scope_context()` → other way
- `@with_org_context` → only for engine

**After:** One function: `get_request_context()`

### Problem 2: Inconsistent Behavior
**Before:**
- Some functions check `is_platform_admin()`
- Others check `user.user_id` against hardcoded list
- Org derivation logic duplicated in 2 places
- Function key handling varies by endpoint

**After:**
- All logic in one place
- Consistent rules applied everywhere
- Single source of truth

### Problem 3: Test Users in Production
**Before:**
```python
# Hardcoded in auth.py line 82
email=test_email or 'jack@gocovi.com'  # BAD!
```

**After:**
- No hardcoded users
- Local dev uses generic "local-dev" user
- Real function keys for testing

---

## Answer to Your Question

> How is get_authenticated_user() used?

**Currently:** It's used in 2 places to get the old `AuthenticatedUser` model, which then needs:
1. Check if platform admin
2. Derive org from database
3. Handle test users for local dev

**What you want:** A single `get_context()` that does ALL of this in one call.

**That's exactly what `get_request_context()` does!**

```python
# Your ideal scenario:
context = get_request_context(req)

# Everything determined consistently:
✅ Parsed Easy Auth
✅ Determined if platform admin
✅ Derived org from DB (or GLOBAL if admin with no header)
✅ No hardcoded test users
✅ Works for function keys, users, and local dev
✅ Same result every time - CONSISTENT!
```

---

## Recommendation

**Implement `request_context.py` as the single source of truth:**

1. ✅ Already created (220 lines)
2. Use it in one endpoint to test
3. Gradually migrate all endpoints
4. Update `@with_org_context` to use it
5. Delete old auth code

**Result:** 68% less code, 100% consistent behavior, zero hardcoded test users.

This is what you asked for: ONE function that handles everything consistently.
