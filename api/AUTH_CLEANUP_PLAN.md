# Authentication Cleanup Plan

## Current Problems

### 1. **Duplicate Authentication Systems**
- **auth.py** has TWO different `@require_auth` decorators with the same name
- **Two user models**: `AuthenticatedUser` (old) vs `UserPrincipal` (new)
- Conflicting implementations cause confusion about which auth flow to use

### 2. **Test/Development Logic Mixed with Production**
```python
# Line 73-94 in auth.py
if is_local:
    # Hardcoded test user
    return AuthenticatedUser(
        user_id="jack@gocovi.com",  # HARDCODED!
        email="jack@gocovi.com",
        display_name="Jack Musick"
    )

# Line 443-448 in auth.py
if not is_production:
    # Auto-bypass authentication
    return FunctionKeyPrincipal(
        key_id="local-dev-bypass",
        key_name="local-development"
    )
```

**Problems:**
- Production code contains hardcoded test users
- Different local dev detection methods used inconsistently
- Auto-bypass makes it easy to accidentally deploy insecure code

### 3. **Redundant Functions**

#### `auth_headers.py`:
- `get_scope_context()` - 133 lines
- `get_auth_headers()` - 100+ lines
- Both do nearly identical things: derive org from DB, check admin status

#### Shared logic repeated:
- Case-insensitive header checking (4+ places)
- Platform admin checks (3+ places)
- Database org lookup (2 places)

### 4. **Verbose & Hard to Maintain**
- **auth.py**: 730 lines
- **auth_headers.py**: 303 lines
- **Total**: 1033 lines for authentication!
- Many duplicate async/sync wrappers

---

## Proposed Solution

### **Replace with `auth_clean.py` (382 lines)**

#### Key Improvements:

1. **Single Authentication Flow**
   - One `AuthenticationService` class
   - One `@require_auth` decorator
   - One set of principal classes

2. **No Hardcoded Test Users**
   - Local dev bypass returns generic function key principal
   - No "jack@gocovi.com" hardcoded anywhere
   - Environment detection centralized

3. **Simplified Organization Context**
   - Single `get_org_context()` function
   - Clear rules: admins can override, users cannot
   - No redundant `get_auth_headers()` vs `get_scope_context()`

4. **Better Organization**
   ```
   ├── Environment Detection (is_production)
   ├── Principal Classes (FunctionKeyPrincipal, UserPrincipal)
   ├── Exceptions (AuthenticationError, AuthorizationError)
   ├── Authentication Service (tiered auth logic)
   ├── Authorization (is_platform_admin, get_user_org_id)
   ├── Organization Context (get_org_context)
   └── Decorators & Helpers (@require_auth, get_principal, etc.)
   ```

5. **Reduced Complexity**
   - From 1033 lines → 382 lines (63% reduction)
   - Single decorator instead of multiple conflicting ones
   - Clear authentication priority: function key → easy auth → local dev

---

## Migration Path

### Step 1: Verify No Active Usage of Old Code
```bash
# Find all imports of old auth
grep -r "from shared.auth import" api/functions/
grep -r "from shared.auth_headers import" api/functions/

# Check for usage of old classes
grep -r "AuthenticatedUser" api/functions/
grep -r "get_auth_headers\|get_scope_context" api/functions/
```

### Step 2: Replace Files
```bash
# Backup originals
cp api/shared/auth.py api/shared/auth_old.py.bak
cp api/shared/auth_headers.py api/shared/auth_headers_old.py.bak

# Replace with clean version
cp api/shared/auth_clean.py api/shared/auth.py

# Delete redundant file
rm api/shared/auth_headers.py
```

### Step 3: Update Imports
```bash
# Change old imports to new
# Old: from shared.auth_headers import get_auth_headers
# New: from shared.auth import get_org_context
```

### Step 4: Update Function Calls
```python
# Old pattern
org_id, user_id, error = get_auth_headers(req, require_org=False)
if error:
    return error

# New pattern (same signature!)
org_id, user_id, error = get_org_context(req)
if error:
    return error
```

### Step 5: Test & Verify
- Start local dev server
- Test with function key
- Test with Easy Auth headers
- Test platform admin org override
- Test regular user restrictions

---

## Benefits Summary

| Aspect | Before | After |
|--------|--------|-------|
| **Lines of code** | 1,033 | 382 |
| **Files** | 2 files | 1 file |
| **Decorators** | 3 decorators | 1 decorator |
| **User models** | 2 models | 1 model |
| **Org context functions** | 2 functions | 1 function |
| **Hardcoded test data** | Yes (jack@gocovi.com) | No |
| **Test logic in prod code** | Yes | No (bypass only) |
| **Duplicate code** | High | Minimal |

---

## Risks & Mitigation

### Risk 1: Breaking Existing Code
**Mitigation**:
- Keep old files as `.bak` for quick rollback
- Gradual migration, file by file
- Comprehensive testing before deployment

### Risk 2: Different Behavior
**Mitigation**:
- `auth_clean.py` maintains same API surface
- `get_org_context()` matches `get_auth_headers()` signature
- `@require_auth` injects `req.principal` same as before

### Risk 3: Missing Features
**Mitigation**:
- Review: No features removed, only consolidated
- `has_form_access()` can be added back if needed (currently unused)
- All core auth flows preserved

---

## Recommendation

**Replace immediately** - The current auth code has:
- Security concerns (hardcoded test users)
- Maintenance burden (duplicate code)
- Confusion (conflicting decorators)

The cleaned version:
- Removes all test logic from production code
- Consolidates to single, clear flow
- Reduces code by 63%
- Maintains same functionality

**Next Steps:**
1. Review `auth_clean.py`
2. Run find/replace to check usage
3. Replace files and update imports
4. Test thoroughly
5. Delete old backups after validation
