# Bifrost Integrations Platform

MSP automation platform built with FastAPI and React.

## Technologies

-   **Backend**: Python 3.11 (FastAPI), SQLAlchemy, Pydantic, PostgreSQL, RabbitMQ, Redis
-   **Frontend**: TypeScript 4.9+, React, Vite
-   **Storage**: PostgreSQL (data), Redis (cache/sessions), RabbitMQ (message queue)
-   **Infrastructure**: Docker, Docker Compose, GitHub Actions for CI/CD

## Project Structure

```
api/
├── src/              # FastAPI application
│   ├── handlers/     # HTTP endpoint handlers (thin layer)
│   ├── models/       # SQLAlchemy models
│   ├── jobs/         # Background job workers
│   └── main.py       # FastAPI app entry point
├── shared/           # Business logic, utilities
│   ├── models.py     # Pydantic models (source of truth)
│   └── ...
├── alembic/          # Database migrations
└── tests/            # Unit and integration tests

client/
├── src/
│   ├── services/     # API client wrappers
│   └── lib/
│       └── v1.d.ts   # Auto-generated TypeScript types
└── ...
```

## Project-Specific Rules

### Backend (Python/FastAPI)

-   **Models**: All Pydantic models MUST be defined in `api/shared/models.py`
-   **Routing**: Create one handler file per base route (e.g., `/discovery` → `discovery_handlers.py`)
    -   Sub-routes and related functions live in the same file
-   **Request/Response**: Always use Pydantic Request and Response models
-   **Business Logic**: MUST live in `api/shared/`, NOT in `api/src/handlers/`
    -   Handlers are thin HTTP handlers only
    -   Complex logic, algorithms, business rules go in shared modules
    -   Example: User provisioning logic lives in `shared/user_provisioning.py`

### Frontend (TypeScript/React)

-   **Type Generation**: Run `npm run generate:types` in `client/` after API changes
    -   Must run while API is running
    -   Types are auto-generated from OpenAPI spec based on `models.py`
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
    -   **IMPORTANT**: Always use `./test.sh` to run tests - it starts all required dependencies (PostgreSQL, RabbitMQ, Redis) in Docker
    -   Running pytest directly (`python -m pytest`) will FAIL for integration tests that need database access
    -   Run all tests: `./test.sh`
    -   Run specific test file: `./test.sh tests/integration/platform/test_sdk_from_workflow.py`
    -   Run specific test: `./test.sh tests/integration/platform/test_sdk_from_workflow.py::TestSDKFileOperations::test_file_path_sandboxing -v`
    -   Run with coverage: `./test.sh --coverage`
    -   Run E2E tests: `./test.sh --e2e`
-   **Type Checking**: Must pass `pyright` (API) and `npm run tsc` (client)
-   **Linting**: Must pass `ruff check` (API) and `npm run lint` (client)

### Commands

```bash
# Backend Testing (ALWAYS USE test.sh from repo root!)
./test.sh                                              # Run all tests with dependencies
./test.sh tests/unit/                                  # Run unit tests only
./test.sh tests/integration/                           # Run integration tests only
./test.sh tests/integration/platform/test_sdk.py      # Run specific file
./test.sh --coverage                                   # Run with coverage report
./test.sh --e2e                                        # Run E2E tests (starts full API stack)

# Backend Quality Checks
cd api
ruff check .                          # Lint Python
pyright                               # Type check Python

# Frontend
cd client
npm run generate:types                # Generate types from API (requires API running)
npm run tsc                           # Type check
npm run lint                          # Lint and format
npm run dev                           # Dev server

# Local development
docker compose up                     # Start PostgreSQL, RabbitMQ, Redis, API, Client
docker compose up -d postgres rabbitmq redis  # Start just infrastructure
cd api && uvicorn src.main:app --reload      # Start API with hot reload
```
