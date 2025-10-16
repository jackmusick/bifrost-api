# msp-automation-platform Development Guidelines

Auto-generated from all feature plans. Last updated: 2025-10-12

## Active Technologies

-   Python 3.11 (Azure Functions v2 programming model) + azure-functions, azure-data-tables, Pydantic for models, GitHub Actions for CI/CD (002-i-want-to)
-   Python 3.11 (Azure Functions v2 programming model) + azure-functions, azure-data-tables, aiohttp (for OAuth HTTP calls), pydantic (for models), cryptography (for token encryption) (004-oauth-helper-for)
-   Azure Table Storage (OAuth configs, credentials, status), Azure Key Vault (encryption keys for credentials at rest) (004-oauth-helper-for)
-   Python 3.11 (Azure Functions v2 programming model), TypeScript 4.9+ (frontend), Bicep/ARM (infrastructure) (005-migrate-to-azure)
-   Azure Table Storage (existing data), Azure Files (Hot tier for `/workspace` and `/tmp` mounts), Azure Blob Storage (logs), Azure Key Vault (secrets) (005-migrate-to-azure)

## Project Structure

```
src/
tests/
```

## Commands

cd src [ONLY COMMANDS FOR ACTIVE TECHNOLOGIES][ONLY COMMANDS FOR ACTIVE TECHNOLOGIES] pytest [ONLY COMMANDS FOR ACTIVE TECHNOLOGIES][ONLY COMMANDS FOR ACTIVE TECHNOLOGIES] ruff check .

## Code Style

Python 3.11 (Azure Functions v2 programming model): Follow standard conventions

## Recent Changes

-   005-migrate-to-azure: Added Python 3.11 (Azure Functions v2 programming model), TypeScript 4.9+ (frontend), Bicep/ARM (infrastructure)
-   004-oauth-helper-for: Added Python 3.11 (Azure Functions v2 programming model) + azure-functions, azure-data-tables, aiohttp (for OAuth HTTP calls), pydantic (for models), cryptography (for token encryption)
-   002-i-want-to: Added Python 3.11 (Azure Functions v2 programming model) + azure-functions, azure-data-tables, Pydantic for models, GitHub Actions for CI/CD

<!-- MANUAL ADDITIONS START -->

## Rules

-   ALWAYS generate Pydantic models in api/shared/models.py.
-   When defining new routes in api/:
    -   ALWAYS create a new function per beginning path (/discovery -> discovery.py). Sub routes and functions can go inside of this file.
    -   ALWAYS decorate HTTP functions with /api/shared/openapi_decorators.py
    -   ALWAYS use a Response and Request model when applicable
-   ALWAYS create and update unit and integration tests in /api/tests. Work is NOT complete until this is done and passing 100%.
-   ALWAYS run `npm run generate:types`in client/ after updating type definitions in the API.
    -   This should always be ran with the function running
    -   Types NEVER need to be manually generated in the API or Client -- our api/functions/openapi.py does this dynamically from models.py
-   ALWAYS make sure we're passing `npm run tsc` in the Client. DO NOT LEAVE ERRORS OR WARNINGS HERE.
-   ALWAYS run `npm run lint` in both the Client and the API and clean up issues before completing work.
-   ALWAYS create services files in the client/services for in interacting with new endpoints. Example:
-   When updating models.py, don't forget to update our seed file.
-   ALWAYS use the date formatting utilities from `@/lib/utils` for displaying dates/times in the client:
    -   `formatDate()` - Full date and time in user's local timezone
    -   `formatDateShort()` - Date only (no time)
    -   `formatTime()` - Time only
    -   `formatRelativeTime()` - Relative time (e.g., "2 hours ago")
    -   These utilities automatically handle UTC timestamps from the backend and convert to user's local timezone
    -   NEVER use `toLocaleString()`, `toLocaleDateString()`, or `toLocaleTimeString()` directly
-   DON'T ignore preexisting errors in typechecks or lint.

```
import { apiClient } from "@/lib/api-client";
import type { components } from "@/lib/v1";

// Re-export types for convenience
export type DataProviderOption = components["schemas"]["DataProviderOption"];
export type DataProviderResponse =
    components["schemas"]["DataProviderResponse"];

export type DataProvider = components["schemas"]["DataProviderMetadata"];
```

<!-- MANUAL ADDITIONS END -->
