# Remaining Service Migrations

## Pattern to Follow

Replace:
```typescript
import { api } from './api'
import type { SomeType } from '@/types/sometype'
```

With:
```typescript
import { apiClient } from '@/lib/api-client'
import type { components } from '@/lib/v1'
```

## Remaining Files

### 1. config.ts
- Replace all `api.get/post/put/delete` with `apiClient.GET/POST/PUT/DELETE`
- Use `components['schemas']['ConfigType']` etc for types

### 2. executions.ts
- Update to use new paths
- Use client types from `@/lib/client-types` for `ExecutionListResponse`, `ExecutionFilters`

### 3. oauth.ts
- Use client types from `@/lib/client-types` for `OAUTH_PROVIDER_PRESETS`, helper functions

### 4. secrets.ts
- Straightforward migration following the pattern

### 5. dataProviders.ts
- Already updated with generated types!
- Just needs import path update from `@/types/generated/api` to `@/lib/v1`

### 6. workflowKeys.ts
- Straightforward migration

## Quick Commands

To check which files still need updating:
```bash
cd /Users/jack/GitHub/bifrost-integrations/client/src/services
grep -l "from './api'" *.ts
```

To check which files still import from old types:
```bash
grep -l "@/types/" *.ts | grep -v "@/lib"
```
