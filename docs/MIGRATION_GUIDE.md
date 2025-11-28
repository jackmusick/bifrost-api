# Bifrost API Migration Guide

This document describes the migration from Azure-native services (Azure Functions, Table Storage, Queue Storage) to a local Docker-based stack (FastAPI, PostgreSQL, RabbitMQ, Redis).

## Table of Contents

1. [Overview](#overview)
2. [Architecture Changes](#architecture-changes)
3. [Quick Start](#quick-start)
4. [Database Migrations](#database-migrations)
5. [Authentication](#authentication)
6. [Configuration](#configuration)
7. [Testing](#testing)
8. [Gradual Migration Strategy](#gradual-migration-strategy)

---

## Overview

### Why Migrate?

- **Local Development**: Run everything with `docker compose up` - no Azure account needed
- **Simplified Testing**: No Azurite emulator or Azure Functions Core Tools required
- **Standard Technologies**: PostgreSQL, RabbitMQ, and Redis are widely supported
- **Faster Iteration**: Hot-reload without function restarts

### What's Changing?

| Component | Before (Azure) | After (Local) |
|-----------|----------------|---------------|
| HTTP API | Azure Functions v4 | FastAPI |
| Database | Azure Table Storage | PostgreSQL 16 |
| Queue | Azure Queue Storage | RabbitMQ |
| Cache/Sessions | N/A | Redis |
| Auth | Azure Easy Auth | JWT (local accounts) |
| Secrets | Azure Key Vault | PostgreSQL (encrypted) |
| Scheduler | Timer Triggers | APScheduler |

---

## Architecture Changes

### New Directory Structure

```
bifrost-api/
├── src/                          # NEW: FastAPI application
│   ├── main.py                   # Application entry point
│   ├── config.py                 # Configuration (pydantic-settings)
│   ├── core/                     # Core functionality
│   │   ├── database.py           # SQLAlchemy setup
│   │   ├── security.py           # Password hashing, JWT
│   │   └── auth.py               # Authentication dependencies
│   ├── models/                   # SQLAlchemy + Pydantic models
│   │   ├── database.py           # SQLAlchemy ORM models
│   │   └── enums.py              # Enumeration types
│   ├── repositories/             # Data access layer
│   │   ├── base.py               # Base repository
│   │   ├── users.py              # User repository
│   │   └── organizations.py      # Organization repository
│   ├── routers/                  # FastAPI routers (endpoints)
│   │   ├── health.py             # Health checks
│   │   └── auth.py               # Authentication endpoints
│   ├── services/                 # Business logic
│   └── jobs/                     # Background workers
│       ├── main.py               # Worker entry point
│       ├── consumers/            # RabbitMQ consumers
│       └── schedulers/           # APScheduler jobs
├── alembic/                      # NEW: Database migrations
│   ├── env.py                    # Migration environment
│   └── versions/                 # Migration scripts
├── shared/                       # EXISTING: Keep for compatibility
├── functions/                    # EXISTING: Azure Functions (deprecated)
├── platform/                     # EXISTING: SDK (unchanged)
├── docker-compose.new.yml        # NEW: Docker stack
├── Dockerfile.api                # NEW: API container
├── Dockerfile.jobs               # NEW: Jobs container
├── requirements-new.txt          # NEW: Python dependencies
└── test-new.sh                   # NEW: Test runner
```

### Service Containers

The new stack runs 5 containers:

1. **postgres** (port 5432) - Database
2. **rabbitmq** (ports 5672, 15672) - Message queue + management UI
3. **redis** (port 6379) - Cache and sessions
4. **api** (port 8000) - FastAPI application
5. **jobs** - Background worker (RabbitMQ consumer + scheduler)

---

## Quick Start

### 1. Start the Stack

```bash
# Start all services
docker compose -f docker-compose.new.yml up

# Or start in detached mode
docker compose -f docker-compose.new.yml up -d
```

### 2. Access Services

- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **RabbitMQ UI**: http://localhost:15672 (bifrost/bifrost_dev)

### 3. Default Credentials

In development mode, a default admin user is created:
- **Email**: admin@localhost
- **Password**: admin

### 4. Login

```bash
# Get access token
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin@localhost&password=admin"

# Use token in requests
curl http://localhost:8000/auth/me \
  -H "Authorization: Bearer <access_token>"
```

---

## Database Migrations

### How It Works

We use [Alembic](https://alembic.sqlalchemy.org/) for database schema migrations.

### Running Migrations

```bash
# Apply all pending migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# View migration history
alembic history

# Generate new migration (autogenerate from models)
alembic revision --autogenerate -m "Add new feature"
```

### Migration Files

Migrations are stored in `alembic/versions/`. Each migration has:
- `upgrade()` - Apply changes
- `downgrade()` - Rollback changes

### Initial Schema

The initial migration (`001_initial`) creates all tables:
- `organizations` - Organization entities
- `users` - User accounts
- `roles` / `user_roles` - Role-based access control
- `forms` - Form definitions
- `executions` / `execution_logs` - Workflow executions
- `configs` - Key-value configuration
- `secrets` - Encrypted secret storage
- `oauth_providers` / `oauth_tokens` - OAuth integration
- `audit_logs` - Audit trail

### Creating New Migrations

When you modify `src/models/database.py`:

```bash
# Auto-generate migration from model changes
alembic revision --autogenerate -m "Description of changes"

# Review the generated migration in alembic/versions/
# Then apply it
alembic upgrade head
```

---

## Authentication

### JWT Token Authentication

The new stack uses JWT (JSON Web Tokens) for authentication:

1. **Login** → Returns access token (30 min) + refresh token (7 days)
2. **Access Token** → Include in `Authorization: Bearer <token>` header
3. **Refresh** → Exchange refresh token for new access token

### Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/auth/login` | POST | Login with email/password |
| `/auth/refresh` | POST | Refresh access token |
| `/auth/me` | GET | Get current user info |
| `/auth/register` | POST | Register new user (dev only) |

### Development Mode Bypass

In development mode (`ENVIRONMENT=development`), requests without tokens use the default dev user (superuser privileges).

### Migrating from Azure Easy Auth

| Azure Easy Auth | New JWT Auth |
|-----------------|--------------|
| `X-MS-CLIENT-PRINCIPAL` header | `Authorization: Bearer <token>` |
| Automatic user provisioning | Manual registration or admin creation |
| Azure AD identity | Local database identity |

---

## Configuration

### Environment Variables

Copy `.env.new.example` to `.env`:

```bash
cp .env.new.example .env
```

Key variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `ENVIRONMENT` | development | development, testing, production |
| `DATABASE_URL` | postgresql+asyncpg://... | PostgreSQL connection (async) |
| `RABBITMQ_URL` | amqp://... | RabbitMQ connection |
| `REDIS_URL` | redis://... | Redis connection |
| `SECRET_KEY` | (dev key) | JWT signing key (32+ chars) |
| `DEV_USER_EMAIL` | admin@localhost | Default dev user |
| `DEV_USER_PASSWORD` | admin | Default dev password |

### Config vs Settings

| Settings (env vars) | Config (database) |
|---------------------|-------------------|
| Infrastructure config | Application config |
| Set at deployment | Runtime configurable |
| Same across instances | Per-org or global |

---

## Testing

### Running Tests

```bash
# Start test services and run tests
./test-new.sh

# Run with coverage
./test-new.sh --coverage

# Run specific test file
./test-new.sh tests/unit/test_auth.py

# Run specific test
./test-new.sh tests/unit/test_auth.py::test_login -v
```

### Test Architecture

Tests use:
- **pytest** - Test framework
- **pytest-asyncio** - Async test support
- **httpx** - FastAPI TestClient

Each test gets:
- Fresh database (rolled back after each test)
- Isolated RabbitMQ queues
- Clean Redis state

### Writing Tests

```python
import pytest
from httpx import AsyncClient
from src.main import app

@pytest.mark.asyncio
async def test_health_check():
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
```

---

## Gradual Migration Strategy

The codebase supports running both stacks during migration:

### Phase 1: Infrastructure (Current)
- [x] Docker Compose with PostgreSQL, RabbitMQ, Redis
- [x] FastAPI application skeleton
- [x] SQLAlchemy models
- [x] Alembic migrations
- [x] JWT authentication
- [x] Basic repositories

### Phase 2: Core Endpoints
- [ ] Health/metrics endpoints
- [ ] Organization CRUD
- [ ] User management
- [ ] Role/permission management

### Phase 3: Workflow Features
- [ ] Form management
- [ ] Workflow discovery
- [ ] Execution management
- [ ] Real-time logs (WebSocket)

### Phase 4: Background Jobs
- [ ] RabbitMQ workflow consumer
- [ ] Git sync consumer
- [ ] Package installation consumer
- [ ] Scheduled job processor

### Phase 5: Full Migration
- [ ] Port all existing tests
- [ ] Remove Azure Functions code
- [ ] Update CI/CD pipelines

---

## Comparison: Old vs New

### API Endpoints

| Feature | Azure Functions | FastAPI |
|---------|----------------|---------|
| Definition | Blueprint + route decorator | Router + path decorator |
| Auth | `@require_auth` decorator | `Depends(get_current_user)` |
| Validation | Manual Pydantic | Automatic from type hints |
| OpenAPI | Manual decorators | Automatic generation |

### Data Access

| Feature | Table Storage | PostgreSQL |
|---------|---------------|------------|
| Queries | OData filter strings | SQLAlchemy expressions |
| Relationships | Manual dual-indexing | Foreign keys + JOINs |
| Transactions | Best-effort | ACID transactions |
| Schema | Schemaless | Typed columns |

### Background Jobs

| Feature | Azure Queue | RabbitMQ |
|---------|-------------|----------|
| Triggers | `@queue_trigger` decorator | aio-pika consumer |
| Dead letters | Poison queues | Dead letter exchanges |
| Scheduling | Timer triggers | APScheduler |

---

## Troubleshooting

### Database Connection Failed

```bash
# Check PostgreSQL is running
docker compose -f docker-compose.new.yml ps postgres

# View logs
docker compose -f docker-compose.new.yml logs postgres
```

### Migration Failed

```bash
# Check current migration state
alembic current

# View migration history
alembic history --verbose

# Manually mark as complete (if needed)
alembic stamp head
```

### RabbitMQ Connection Failed

```bash
# Check RabbitMQ is healthy
docker compose -f docker-compose.new.yml exec rabbitmq rabbitmq-diagnostics check_running

# Access management UI
open http://localhost:15672
```

### Reset Everything

```bash
# Stop and remove all containers + volumes
docker compose -f docker-compose.new.yml down -v

# Start fresh
docker compose -f docker-compose.new.yml up
```
