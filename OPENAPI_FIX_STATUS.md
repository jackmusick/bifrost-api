# OpenAPI Type Generation Fix - Status Report

## Problem
Frontend TypeScript types are manually defined instead of auto-generated from OpenAPI spec. This causes:
- Type mismatches between frontend and backend
- Build failures when API changes
- Manual maintenance burden

## Root Cause
Routers define their own local Pydantic models instead of importing from `shared/models.py`, so models don't appear in OpenAPI spec even though they're defined.

## Solution Strategy
Update all routers to import Pydantic models from `shared/models.py` instead of defining them locally. This ensures FastAPI includes them in the OpenAPI spec.

---

## Progress

### ✅ Completed

1. **workflow_keys.py router** - Updated to import `WorkflowKeyCreateRequest` and `WorkflowKeyResponse` from shared/models
   - Changed `workflow_id` → `workflow_name` in shared/models.py to match actual usage

2. **executions.py router** - Updated logs endpoint
   - Changed from `list[dict]` to `list[ExecutionLog]` return type
   - Updated repository to convert ORM models to Pydantic ExecutionLog models
   - ExecutionLog now appears in OpenAPI spec

3. **auth.py router** - Updated to import models from shared/models
   - Imported `OAuthProviderInfo` and `AuthStatusResponse` from shared/models
   - Removed local definitions
   - OAuthProviderInfo appears in OpenAPI as `shared__models__OAuthProviderInfo` (namespaced)

4. **Frontend fixes**
   - Fixed SourceControlPanel.tsx: `is_git_repo` → `initialized`, `changed_files` array handling
   - Fixed HttpTriggerDialog.tsx and WorkflowKeys.tsx: added missing `disable_global_key` field
   - Fixed auth.ts: updated to use `shared__models__OAuthProviderInfo` namespaced type
   - Fixed websocket.ts: now uses auto-generated ExecutionLog type

---

## Remaining Work

### Models NOT in OpenAPI (No Router Uses Them)

These models exist in `shared/models.py` but no router endpoint uses them:

1. **DataProviderOption / DataProviderResponse**
   - Defined in shared/models.py
   - Frontend: `client/src/services/dataProviders.ts` has manual types
   - **Action needed**: Update `data_providers.py` router to use these models OR implement the data provider endpoints

2. **FileConflictResponse**
   - Defined in shared/models.py
   - Frontend: `client/src/services/fileService.ts` has manual type
   - **Action needed**: Find where file conflicts are returned and use the Pydantic model

3. **ScriptExecutionRequest / ScriptExecutionResponse**
   - Defined in shared/models.py
   - Frontend: `client/src/services/scriptService.ts` calls `/api/scripts/execute` (doesn't exist)
   - **Action needed**: Create scripts router OR remove frontend service if not needed

4. **SearchRequest / SearchResult / SearchResponse**
   - Defined in shared/models.py
   - Frontend: `client/src/services/searchService.ts` calls `/api/editor/search` (doesn't exist)
   - **Action needed**: Create editor search router OR remove frontend service if not needed

5. **TrustedDeviceInfo**
   - Frontend tries to import but doesn't exist in shared/models.py
   - **Action needed**: Either add to shared/models.py or remove from frontend

---

## Remaining TypeScript Errors (21 total)

```
src/components/editor/SearchPanel.tsx(60,22): Property 'total_files_searched' does not exist
src/components/editor/SearchPanel.tsx(61,16): Property 'total_files_searched' does not exist
src/components/editor/SearchPanel.tsx(195,25): Property 'total_files_searched' does not exist
src/components/editor/SearchPanel.tsx(196,22): Property 'total_files_searched' does not exist
src/components/editor/SearchPanel.tsx(199,22): Property 'truncated' does not exist
src/components/forms/FormRenderer.tsx(49,11): Property 'description' does not exist on DataProviderOption
src/components/forms/FormRenderer.tsx(49,44): Property 'description' does not exist on DataProviderOption
src/hooks/useAutoSave.ts(156,25): Property 'reason' does not exist on FileConflictResponse
src/hooks/useSaveQueue.ts(48,26): Property 'reason' does not exist on FileConflictResponse
src/hooks/useSaveQueue.ts(52,27): Property 'reason' does not exist on FileConflictResponse
src/services/auth.ts(131,52): Cannot find name 'TrustedDevice'
src/services/github.ts(77,40): Cannot find name 'CommitRequest'
src/services/sdkScannerService.ts(74,29): 'result.issues' is possibly 'undefined' (6x)
src/services/workflows.ts(23,5): Type '{ reload_file: string; } | {}' not assignable to 'undefined'
```

---

## Recommended Next Steps

### Option 1: Implement Missing Routers (Proper Solution)
Create routers that use the shared/models.py types:
- `api/src/routers/search.py` - use SearchRequest/SearchResponse
- `api/src/routers/scripts.py` - use ScriptExecutionRequest/ScriptExecutionResponse
- Update existing routers to use DataProviderOption/Response, FileConflictResponse

### Option 2: Remove Unused Frontend Services
If these features aren't being used:
- Remove searchService.ts, scriptService.ts
- Update dataProviders.ts, fileService.ts to not use the missing types
- Clean up components that reference them

### Option 3: Hybrid (Recommended)
1. Implement routers for features that ARE being used (check frontend for actual usage)
2. Remove services for features that AREN'T being used
3. Fix remaining misc errors (TrustedDevice, CommitRequest, nullability checks)

---

## How to Continue

1. **Check frontend usage**: Grep for `searchService`, `scriptService`, `dataProvidersService` to see if they're actually called
2. **For used services**: Create routers with proper shared/models imports
3. **For unused services**: Delete or comment out
4. **Register new routers**: Add to `api/src/main.py` router includes
5. **Regenerate types**: `docker exec bifrost-api curl -s http://localhost:8000/openapi.json > /tmp/openapi.json && cd client && npx openapi-typescript /tmp/openapi.json -o src/lib/v1.d.ts`
6. **Fix remaining errors**: TrustedDevice, CommitRequest, nullability issues

---

## Key Files

### Backend
- `api/shared/models.py` - Source of truth for all Pydantic models
- `api/src/routers/*.py` - All routers that need to import from shared/models
- `api/src/main.py` - Router registration

### Frontend
- `client/src/lib/v1.d.ts` - Auto-generated types (DO NOT EDIT)
- `client/src/services/*.ts` - Service files that import from v1.d.ts

### Commands
- **Regenerate types**: `cd client && npm run generate:types` (requires API running)
- **Type check**: `cd client && npm run tsc`
- **Run tests**: `./test.sh` (from repo root, starts all dependencies)
