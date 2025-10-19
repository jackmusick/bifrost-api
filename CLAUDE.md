# Bifrost Integrations Platform

MSP automation platform built with Azure Functions and TypeScript.

## Technologies

-   **Backend**: Python 3.11 (Azure Functions v2), azure-functions, azure-data-tables, Pydantic, cryptography
-   **Frontend**: TypeScript 4.9+, React, Vite
-   **Storage**: Azure Table Storage, Azure Blob Storage, Azure Key Vault
-   **Infrastructure**: Bicep/ARM templates, GitHub Actions for CI/CD

## Project Structure

```
api/
├── functions/        # HTTP endpoint handlers (thin layer)
├── shared/          # Business logic, models, utilities
│   ├── models.py    # Pydantic models (source of truth)
│   └── ...
└── tests/           # Unit and integration tests

client/
├── src/
│   ├── services/    # API client wrappers
│   └── lib/
│       └── v1.d.ts  # Auto-generated TypeScript types
└── ...
```

## Project-Specific Rules

### Backend (Python/Azure Functions)

-   **Models**: All Pydantic models MUST be defined in `api/shared/models.py`
-   **Routing**: Create one function file per base route (e.g., `/discovery` → `discovery.py`)
    -   Sub-routes and related functions live in the same file
-   **Decorators**: Always use `@api/shared/openapi_decorators.py` on HTTP functions
-   **Request/Response**: Always use Pydantic Request and Response models
-   **Business Logic**: MUST live in `api/shared/`, NOT in `api/functions/`
    -   Functions are thin HTTP handlers only
    -   Complex logic, algorithms, business rules go in shared modules
    -   Example: User provisioning logic lives in `shared/user_provisioning.py`

### Frontend (TypeScript/React)

-   **Type Generation**: Run `npm run generate:types` in `client/` after API changes
    -   Must run while function app is running
    -   Types are auto-generated from `api/functions/openapi.py` based on `models.py`
    -   Never manually write TypeScript types for API endpoints
-   **API Services**: Create service files in `client/src/services/` for new endpoints

Example service pattern:
```typescript
import { apiClient } from "@/lib/api-client";
import type { components } from "@/lib/v1";

// Re-export types for convenience
export type DataProvider = components["schemas"]["DataProviderMetadata"];
export type DataProviderResponse = components["schemas"]["DataProviderResponse"];

export async function getDataProviders() {
  return apiClient.get<DataProviderResponse>("/api/data-providers");
}
```

### Testing & Quality

-   **Tests**: All work requires unit and integration tests in `api/tests/`
    -   **Integration Tests**: Use isolated testing environment with `docker-compose.testing.yml`
    -   Start test services: `docker compose -f docker-compose.testing.yml up -d`
    -   Run integration tests: `python -m pytest api/tests/integration/ -v`
    -   Stop test services: `docker compose -f docker-compose.testing.yml down`
-   **Type Checking**: Must pass `npm run typecheck` (API) and `npm run tsc` (client)
-   **Linting**: Must pass `npm run lint` in both API and client
-   **Seed Data**: Update `api/seed_data.py` when models change

### Commands

```bash
# Backend
cd api
python -m pytest tests/ -v           # Run tests
ruff check .                          # Lint Python
npx pyright                           # Type check Python

# Frontend
cd client
npm run generate:types                # Generate types from API
npm run tsc                           # Type check
npm run lint                          # Lint and format
npm run dev                           # Dev server

# Local development
docker compose up                     # Start Azurite + dependencies

# Testing
docker compose -f docker-compose.testing.yml up -d    # Start test services
python -m pytest api/tests/integration/ -v             # Run integration tests
docker compose -f docker-compose.testing.yml down     # Stop test services
```
