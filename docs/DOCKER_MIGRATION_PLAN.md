# Bifrost Docker Migration Plan

## Overview

Migrate from Azure-native services to a fully local, Docker-based stack that can be launched with a single `docker compose up` command.

## Current vs Target Architecture

| Component | Current (Azure) | Target (Local) |
|-----------|-----------------|----------------|
| HTTP API | Azure Functions v4 | **FastAPI** |
| Database | Azure Table Storage | **PostgreSQL 16** |
| Queue | Azure Queue Storage | **RabbitMQ** |
| File Storage | Azure Blob Storage | Local filesystem (already done) |
| Authentication | Azure Static Web Apps (Easy Auth) | **FastAPI-Users + OAuth** |
| Scheduler | Azure Timer Triggers | **APScheduler** (in jobs container) |
| Secrets | Azure Key Vault | **PostgreSQL + encryption** |

## Target Container Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           docker-compose.yml                            │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐                 │
│  │  postgres   │    │  rabbitmq   │    │   redis     │                 │
│  │   :5432     │    │   :5672     │    │   :6379     │                 │
│  │             │    │   :15672    │    │ (sessions)  │                 │
│  └──────┬──────┘    └──────┬──────┘    └──────┬──────┘                 │
│         │                  │                  │                         │
│         └────────────┬─────┴──────────────────┘                         │
│                      │                                                  │
│         ┌────────────┴────────────┐                                     │
│         ▼                         ▼                                     │
│  ┌─────────────┐           ┌─────────────┐                             │
│  │    api      │           │    jobs     │                             │
│  │   :8000     │           │  (worker)   │                             │
│  │             │           │             │                             │
│  │  FastAPI    │           │  Consumer   │                             │
│  │  REST API   │           │  Scheduler  │                             │
│  │  Auth       │           │  Timers     │                             │
│  └─────────────┘           └─────────────┘                             │
│                                                                         │
│  ┌─────────────┐  (Future - merged from separate repo)                 │
│  │   client    │                                                       │
│  │   :3000     │                                                       │
│  │   Vite/React│                                                       │
│  └─────────────┘                                                       │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

## Technology Choices

### 1. FastAPI (HTTP API)

**Why FastAPI:**
- Native async/await support (matches current async handlers)
- Automatic OpenAPI documentation (replaces current openapi_decorators.py)
- Pydantic native (already using Pydantic models)
- Dependency injection (replaces current decorator patterns)
- High performance (uvicorn/gunicorn)
- Large ecosystem and excellent documentation

**Migration complexity:** MEDIUM
- Current handlers in `shared/handlers/` are already decoupled from Azure Functions
- Blueprint routing → FastAPI routers
- `@openapi_endpoint` decorator → FastAPI native OpenAPI

### 2. PostgreSQL (Database)

**Why PostgreSQL:**
- ACID compliance, complex queries, JSON support
- Mature tooling (Alembic migrations, pgAdmin)
- SQLAlchemy/asyncpg for Python
- Can use JSONB for flexible schema (similar to Table Storage)

**Migration complexity:** HIGH
- Table Storage key-based access → SQL queries
- PartitionKey/RowKey patterns → proper indexes
- Need to redesign data models for relational structure

### 3. RabbitMQ (Message Queue)

**Why RabbitMQ:**
- Mature, battle-tested message broker
- Native support for dead-letter queues (poison queues)
- Management UI (port 15672)
- Python: `aio-pika` for async, `pika` for sync
- Supports delayed messages (for retry backoff)

**Migration complexity:** MEDIUM
- Current queue patterns map well to RabbitMQ
- `workflow-executions` → `workflow.executions` queue
- Poison queues → Dead Letter Exchanges

### 4. Redis (Session Store)

**Why Redis:**
- Fast session storage for auth tokens
- Cache layer for frequently accessed data
- Can store refresh tokens securely
- Pub/Sub for real-time features (replaces WebPubSub)

**Migration complexity:** LOW
- New addition, not replacing existing

### 5. FastAPI-Users + Authlib (Authentication)

**Why FastAPI-Users:**
- Built specifically for FastAPI
- Supports multiple auth strategies:
  - Local accounts (username/password)
  - OAuth2 (Google, Microsoft, GitHub, etc.)
  - JWT tokens
- Database agnostic (works with SQLAlchemy)
- Built-in password hashing, verification emails, etc.

**Components:**
- `fastapi-users` - User management
- `authlib` - OAuth client implementation
- `python-jose` - JWT tokens
- `passlib` - Password hashing

**Migration complexity:** HIGH
- Complete rewrite of auth layer
- Need to implement user registration, login, password reset
- OAuth provider configuration

### 6. APScheduler (Scheduler)

**Why APScheduler:**
- Mature Python scheduler
- Supports cron expressions
- Can use PostgreSQL as job store (persistent)
- Async support
- Already in Python ecosystem

**Replaces:**
- `schedule_processor` timer trigger
- `execution_cleanup` timer trigger
- `oauth_refresh_timer` timer trigger

**Migration complexity:** LOW
- Simple mapping of timer triggers to APScheduler jobs

---

## Directory Structure (Post-Migration)

```
bifrost/
├── docker-compose.yml
├── docker-compose.override.yml    # Dev overrides
├── .env.example
│
├── api/                           # FastAPI application
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py                    # FastAPI app entry
│   ├── config.py                  # Settings via pydantic-settings
│   │
│   ├── routers/                   # HTTP endpoints (from functions/http/)
│   │   ├── __init__.py
│   │   ├── workflows.py
│   │   ├── executions.py
│   │   ├── forms.py
│   │   ├── auth.py                # New: login, register, oauth
│   │   ├── users.py               # New: user management
│   │   └── ...
│   │
│   ├── models/                    # SQLAlchemy + Pydantic models
│   │   ├── __init__.py
│   │   ├── database.py            # SQLAlchemy models
│   │   └── schemas.py             # Pydantic schemas (from models.py)
│   │
│   ├── repositories/              # Data access (from shared/repositories/)
│   │   ├── __init__.py
│   │   ├── base.py                # Base repository with SQLAlchemy
│   │   ├── executions.py
│   │   ├── users.py
│   │   └── ...
│   │
│   ├── services/                  # Business logic (from shared/handlers/)
│   │   ├── __init__.py
│   │   ├── workflow_service.py
│   │   ├── execution_service.py
│   │   ├── auth_service.py        # New: authentication logic
│   │   └── ...
│   │
│   ├── core/                      # Core functionality
│   │   ├── __init__.py
│   │   ├── auth.py                # Auth dependencies
│   │   ├── database.py            # DB session management
│   │   ├── queue.py               # RabbitMQ client
│   │   └── security.py            # Password hashing, JWT
│   │
│   ├── engine/                    # Workflow execution engine
│   │   ├── __init__.py
│   │   └── engine.py              # From shared/engine.py
│   │
│   └── migrations/                # Alembic migrations
│       ├── versions/
│       └── env.py
│
├── jobs/                          # Background worker service
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py                    # Worker entry point
│   │
│   ├── consumers/                 # RabbitMQ consumers
│   │   ├── __init__.py
│   │   ├── workflow_consumer.py   # From worker.py
│   │   ├── git_sync_consumer.py   # From git_sync_worker.py
│   │   └── package_consumer.py    # From package_worker.py
│   │
│   ├── schedulers/                # Scheduled jobs
│   │   ├── __init__.py
│   │   ├── schedule_processor.py
│   │   ├── execution_cleanup.py
│   │   └── oauth_refresh.py
│   │
│   └── shared/                    # Shared with api (symlink or package)
│
├── client/                        # React frontend (merged later)
│   ├── Dockerfile
│   ├── package.json
│   └── src/
│
├── shared/                        # Shared Python code (installable package)
│   ├── setup.py
│   ├── bifrost_shared/
│   │   ├── __init__.py
│   │   ├── models.py              # Shared Pydantic models
│   │   ├── engine.py              # Workflow engine
│   │   └── ...
│
├── platform/                      # SDK for user workflows (unchanged)
│   └── ...
│
├── workspace/                     # User workflows (volume mount)
│   └── ...
│
└── scripts/
    ├── init-db.sh                 # Database initialization
    ├── seed-data.py               # Seed data (from api/seed_data.py)
    └── generate-types.sh          # TypeScript type generation
```

---

## Database Schema Design

### Core Tables

```sql
-- Organizations
CREATE TABLE organizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,
    settings JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Users (FastAPI-Users compatible)
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(320) UNIQUE NOT NULL,
    hashed_password VARCHAR(1024),
    is_active BOOLEAN DEFAULT TRUE,
    is_superuser BOOLEAN DEFAULT FALSE,
    is_verified BOOLEAN DEFAULT FALSE,
    organization_id UUID REFERENCES organizations(id),
    display_name VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- OAuth Accounts (for social login)
CREATE TABLE oauth_accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    oauth_name VARCHAR(100) NOT NULL,  -- 'google', 'microsoft', etc.
    access_token VARCHAR(1024) NOT NULL,
    refresh_token VARCHAR(1024),
    expires_at INTEGER,
    account_id VARCHAR(320) NOT NULL,
    account_email VARCHAR(320),
    UNIQUE(oauth_name, account_id)
);

-- Roles
CREATE TABLE roles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    description TEXT,
    permissions JSONB DEFAULT '[]',
    organization_id UUID REFERENCES organizations(id),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- User Roles
CREATE TABLE user_roles (
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    role_id UUID REFERENCES roles(id) ON DELETE CASCADE,
    PRIMARY KEY (user_id, role_id)
);

-- Workflow Executions
CREATE TABLE executions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workflow_name VARCHAR(255) NOT NULL,
    workflow_version VARCHAR(50),
    status VARCHAR(50) NOT NULL,  -- pending, running, completed, failed, cancelled
    parameters JSONB DEFAULT '{}',
    result JSONB,
    error TEXT,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    user_id UUID REFERENCES users(id),
    organization_id UUID REFERENCES organizations(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    -- Indexes for common queries
    CONSTRAINT valid_status CHECK (status IN ('pending', 'running', 'completed', 'failed', 'cancelled'))
);
CREATE INDEX idx_executions_org_status ON executions(organization_id, status);
CREATE INDEX idx_executions_created ON executions(created_at DESC);

-- Execution Logs (separate table for performance)
CREATE TABLE execution_logs (
    id BIGSERIAL PRIMARY KEY,
    execution_id UUID REFERENCES executions(id) ON DELETE CASCADE,
    level VARCHAR(20) NOT NULL,
    message TEXT NOT NULL,
    metadata JSONB,
    timestamp TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_execution_logs_exec ON execution_logs(execution_id, timestamp);

-- Forms
CREATE TABLE forms (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(100) NOT NULL,
    schema JSONB NOT NULL,
    settings JSONB DEFAULT '{}',
    organization_id UUID REFERENCES organizations(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(organization_id, slug)
);

-- Config (key-value store, replaces Azure Table Storage Config)
CREATE TABLE config (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID REFERENCES organizations(id),  -- NULL for global
    key VARCHAR(255) NOT NULL,
    value JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(organization_id, key)
);
CREATE INDEX idx_config_org ON config(organization_id);

-- Secrets (encrypted)
CREATE TABLE secrets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID REFERENCES organizations(id),  -- NULL for global
    name VARCHAR(255) NOT NULL,
    encrypted_value BYTEA NOT NULL,  -- AES-256 encrypted
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(organization_id, name)
);

-- OAuth Provider Configs (for integrations, not user auth)
CREATE TABLE oauth_providers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID REFERENCES organizations(id),
    provider_name VARCHAR(100) NOT NULL,
    client_id VARCHAR(255) NOT NULL,
    encrypted_client_secret BYTEA NOT NULL,
    scopes TEXT[],
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(organization_id, provider_name)
);

-- OAuth Tokens (for integration connections)
CREATE TABLE oauth_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID REFERENCES organizations(id),
    provider_id UUID REFERENCES oauth_providers(id),
    user_id UUID REFERENCES users(id),
    access_token_encrypted BYTEA NOT NULL,
    refresh_token_encrypted BYTEA,
    expires_at TIMESTAMPTZ,
    scopes TEXT[],
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Audit Log
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID REFERENCES organizations(id),
    user_id UUID REFERENCES users(id),
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(100),
    resource_id UUID,
    details JSONB,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_audit_org_time ON audit_logs(organization_id, created_at DESC);

-- Scheduled Jobs (for APScheduler persistence)
CREATE TABLE scheduled_jobs (
    id VARCHAR(191) PRIMARY KEY,
    next_run_time FLOAT,
    job_state BYTEA NOT NULL
);
CREATE INDEX idx_scheduled_jobs_next ON scheduled_jobs(next_run_time);
```

---

## RabbitMQ Queue Design

### Exchanges and Queues

```yaml
exchanges:
  - name: bifrost.direct
    type: direct
    durable: true

  - name: bifrost.dlx          # Dead Letter Exchange
    type: direct
    durable: true

queues:
  # Workflow execution
  - name: workflow.executions
    durable: true
    arguments:
      x-dead-letter-exchange: bifrost.dlx
      x-dead-letter-routing-key: workflow.executions.dead
      x-message-ttl: 3600000    # 1 hour TTL

  - name: workflow.executions.dead   # Poison queue
    durable: true

  # Git sync operations
  - name: git.sync
    durable: true
    arguments:
      x-dead-letter-exchange: bifrost.dlx
      x-dead-letter-routing-key: git.sync.dead

  - name: git.sync.dead
    durable: true

  # Package installations
  - name: packages.install
    durable: true
    arguments:
      x-dead-letter-exchange: bifrost.dlx
      x-dead-letter-routing-key: packages.install.dead

  - name: packages.install.dead
    durable: true

bindings:
  - exchange: bifrost.direct
    queue: workflow.executions
    routing_key: workflow.execute

  - exchange: bifrost.direct
    queue: git.sync
    routing_key: git.sync

  - exchange: bifrost.direct
    queue: packages.install
    routing_key: packages.install

  # Dead letter bindings
  - exchange: bifrost.dlx
    queue: workflow.executions.dead
    routing_key: workflow.executions.dead
```

### Message Formats

```python
# Workflow execution message
{
    "execution_id": "uuid",
    "workflow_name": "string",
    "org_id": "uuid",
    "user_id": "uuid",
    "parameters": {},
    "priority": 5,           # 1-10, default 5
    "retry_count": 0,
    "created_at": "iso8601"
}

# Git sync message
{
    "job_id": "uuid",
    "repo_url": "string",
    "branch": "string",
    "workspace_id": "uuid",
    "org_id": "uuid"
}

# Package install message
{
    "job_id": "uuid",
    "package_name": "string",
    "version": "string",
    "workspace_id": "uuid",
    "org_id": "uuid"
}
```

---

## Authentication Architecture

### Authentication Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Authentication Flows                              │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  LOCAL ACCOUNT FLOW:                                                │
│  ┌────────┐    ┌─────────┐    ┌──────────┐    ┌─────────┐         │
│  │ Client │───▶│ /login  │───▶│ Verify   │───▶│ Return  │         │
│  │        │    │         │    │ Password │    │ JWT     │         │
│  └────────┘    └─────────┘    └──────────┘    └─────────┘         │
│                                                                      │
│  OAUTH FLOW (Google, Microsoft, GitHub):                            │
│  ┌────────┐    ┌──────────────┐    ┌───────────────┐               │
│  │ Client │───▶│ /auth/google │───▶│ Google OAuth  │               │
│  │        │    │ /authorize   │    │ Consent       │               │
│  └────────┘    └──────────────┘    └───────┬───────┘               │
│       ▲                                     │                        │
│       │        ┌──────────────┐    ┌───────▼───────┐               │
│       └────────│ Return JWT   │◀───│ /auth/google  │               │
│                │ + Set Cookie │    │ /callback     │               │
│                └──────────────┘    └───────────────┘               │
│                                                                      │
│  TOKEN TYPES:                                                       │
│  • Access Token (JWT): 15 min expiry, stateless                    │
│  • Refresh Token: 7 days expiry, stored in Redis                   │
│  • Session Cookie: HTTP-only, secure, same-site                    │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### FastAPI-Users Integration

```python
# api/core/auth.py

from fastapi_users import FastAPIUsers
from fastapi_users.authentication import (
    AuthenticationBackend,
    BearerTransport,
    JWTStrategy,
    CookieTransport,
)
from fastapi_users.db import SQLAlchemyUserDatabase

# JWT Strategy
def get_jwt_strategy() -> JWTStrategy:
    return JWTStrategy(
        secret=settings.SECRET_KEY,
        lifetime_seconds=900,  # 15 minutes
    )

# Bearer token transport (for API clients)
bearer_transport = BearerTransport(tokenUrl="auth/jwt/login")

# Cookie transport (for browser clients)
cookie_transport = CookieTransport(
    cookie_name="bifrost_auth",
    cookie_max_age=3600,
    cookie_secure=True,
    cookie_httponly=True,
    cookie_samesite="lax",
)

# Authentication backends
jwt_backend = AuthenticationBackend(
    name="jwt",
    transport=bearer_transport,
    get_strategy=get_jwt_strategy,
)

cookie_backend = AuthenticationBackend(
    name="cookie",
    transport=cookie_transport,
    get_strategy=get_jwt_strategy,
)

# FastAPI Users instance
fastapi_users = FastAPIUsers[User, uuid.UUID](
    get_user_manager,
    [jwt_backend, cookie_backend],
)

# Dependencies
current_active_user = fastapi_users.current_user(active=True)
current_superuser = fastapi_users.current_user(active=True, superuser=True)
```

### OAuth Configuration

```python
# api/core/oauth.py

from httpx_oauth.clients.google import GoogleOAuth2
from httpx_oauth.clients.microsoft import MicrosoftGraphOAuth2
from httpx_oauth.clients.github import GitHubOAuth2

google_oauth_client = GoogleOAuth2(
    client_id=settings.GOOGLE_CLIENT_ID,
    client_secret=settings.GOOGLE_CLIENT_SECRET,
)

microsoft_oauth_client = MicrosoftGraphOAuth2(
    client_id=settings.MICROSOFT_CLIENT_ID,
    client_secret=settings.MICROSOFT_CLIENT_SECRET,
)

github_oauth_client = GitHubOAuth2(
    client_id=settings.GITHUB_CLIENT_ID,
    client_secret=settings.GITHUB_CLIENT_SECRET,
)
```

---

## Migration Phases

### Phase 1: Foundation (Week 1-2)
**Goal:** Set up infrastructure and basic API

- [ ] Create new docker-compose.yml with all services
- [ ] Set up PostgreSQL with initial schema
- [ ] Set up RabbitMQ with exchanges and queues
- [ ] Set up Redis for sessions
- [ ] Create FastAPI application skeleton
- [ ] Implement database connection and session management
- [ ] Create Alembic migration setup
- [ ] Implement basic health check endpoint

**Deliverable:** `docker compose up` starts all services, API returns health check

### Phase 2: Authentication (Week 2-3)
**Goal:** Complete auth system

- [ ] Integrate FastAPI-Users
- [ ] Implement local account registration/login
- [ ] Implement password reset flow
- [ ] Add Google OAuth
- [ ] Add Microsoft OAuth
- [ ] Add GitHub OAuth
- [ ] Implement JWT token handling
- [ ] Add refresh token rotation
- [ ] Create auth middleware/dependencies
- [ ] Implement organization context injection

**Deliverable:** Users can register, login, and use OAuth providers

### Phase 3: Core API Migration (Week 3-5)
**Goal:** Migrate all HTTP endpoints

- [ ] Migrate models.py to SQLAlchemy + Pydantic schemas
- [ ] Create base repository with SQLAlchemy
- [ ] Migrate repositories one by one:
  - [ ] UsersRepository
  - [ ] OrganizationsRepository
  - [ ] ExecutionsRepository
  - [ ] ConfigRepository
  - [ ] SecretsRepository
  - [ ] RolesRepository
  - [ ] FormsRepository
- [ ] Migrate handlers to FastAPI services
- [ ] Create FastAPI routers from function blueprints:
  - [ ] /workflows
  - [ ] /executions
  - [ ] /forms
  - [ ] /organizations
  - [ ] /users
  - [ ] /roles
  - [ ] /config
  - [ ] /secrets
  - [ ] /oauth (integration OAuth, not user auth)
  - [ ] /data-providers
  - [ ] /file-uploads
  - [ ] /health
  - [ ] /logs

**Deliverable:** All API endpoints functional with PostgreSQL backend

### Phase 4: Background Jobs (Week 5-6)
**Goal:** Migrate queue workers and schedulers

- [ ] Create jobs service container
- [ ] Implement RabbitMQ consumer base class
- [ ] Migrate workflow execution consumer
- [ ] Migrate git sync consumer
- [ ] Migrate package installation consumer
- [ ] Implement dead letter queue handler
- [ ] Set up APScheduler with PostgreSQL job store
- [ ] Migrate scheduled jobs:
  - [ ] Schedule processor
  - [ ] Execution cleanup
  - [ ] OAuth refresh
- [ ] Add consumer health checks

**Deliverable:** All background processing works via RabbitMQ

### Phase 5: Workflow Engine (Week 6-7)
**Goal:** Adapt execution engine

- [ ] Port engine.py to work outside Azure Functions
- [ ] Adapt execution logger for PostgreSQL
- [ ] Update discovery.py for new structure
- [ ] Test workflow execution end-to-end
- [ ] Verify hot-reload functionality
- [ ] Test all SDK features (bifrost module)

**Deliverable:** Workflows execute correctly in new architecture

### Phase 6: Frontend Integration (Week 7-8)
**Goal:** Integrate React frontend

- [ ] Merge client repo into /client directory
- [ ] Create client Dockerfile (Vite build + nginx)
- [ ] Update API client for new auth flow
- [ ] Update type generation for FastAPI OpenAPI
- [ ] Add client to docker-compose
- [ ] Configure nginx reverse proxy
- [ ] Test full end-to-end flows

**Deliverable:** Full stack runs with docker compose up

### Phase 7: Testing & Polish (Week 8-9)
**Goal:** Ensure quality and documentation

- [ ] Port existing tests to pytest
- [ ] Add integration tests for new components
- [ ] Create seed data script
- [ ] Write migration guide
- [ ] Update README and documentation
- [ ] Performance testing
- [ ] Security review

**Deliverable:** Production-ready local development environment

---

## Docker Compose Configuration

```yaml
# docker-compose.yml

version: '3.8'

services:
  # PostgreSQL Database
  postgres:
    image: postgres:16-alpine
    container_name: bifrost-postgres
    environment:
      POSTGRES_DB: bifrost
      POSTGRES_USER: bifrost
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-bifrost_dev}
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./scripts/init-db.sql:/docker-entrypoint-initdb.d/init.sql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U bifrost"]
      interval: 5s
      timeout: 5s
      retries: 5

  # RabbitMQ Message Broker
  rabbitmq:
    image: rabbitmq:3.13-management-alpine
    container_name: bifrost-rabbitmq
    environment:
      RABBITMQ_DEFAULT_USER: bifrost
      RABBITMQ_DEFAULT_PASS: ${RABBITMQ_PASSWORD:-bifrost_dev}
    ports:
      - "5672:5672"    # AMQP
      - "15672:15672"  # Management UI
    volumes:
      - rabbitmq_data:/var/lib/rabbitmq
      - ./scripts/rabbitmq-definitions.json:/etc/rabbitmq/definitions.json
    healthcheck:
      test: ["CMD", "rabbitmq-diagnostics", "check_running"]
      interval: 10s
      timeout: 10s
      retries: 5

  # Redis (Sessions & Cache)
  redis:
    image: redis:7-alpine
    container_name: bifrost-redis
    command: redis-server --appendonly yes
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 5s
      retries: 5

  # FastAPI Application
  api:
    build:
      context: ./api
      dockerfile: Dockerfile
    container_name: bifrost-api
    environment:
      DATABASE_URL: postgresql+asyncpg://bifrost:${POSTGRES_PASSWORD:-bifrost_dev}@postgres:5432/bifrost
      RABBITMQ_URL: amqp://bifrost:${RABBITMQ_PASSWORD:-bifrost_dev}@rabbitmq:5672/
      REDIS_URL: redis://redis:6379/0
      SECRET_KEY: ${SECRET_KEY:-dev-secret-key-change-in-production}
      CORS_ORIGINS: ${CORS_ORIGINS:-http://localhost:3000}
      WORKSPACE_PATH: /workspace
      TEMP_PATH: /tmp/bifrost
      # OAuth (optional)
      GOOGLE_CLIENT_ID: ${GOOGLE_CLIENT_ID:-}
      GOOGLE_CLIENT_SECRET: ${GOOGLE_CLIENT_SECRET:-}
      MICROSOFT_CLIENT_ID: ${MICROSOFT_CLIENT_ID:-}
      MICROSOFT_CLIENT_SECRET: ${MICROSOFT_CLIENT_SECRET:-}
      GITHUB_CLIENT_ID: ${GITHUB_CLIENT_ID:-}
      GITHUB_CLIENT_SECRET: ${GITHUB_CLIENT_SECRET:-}
    ports:
      - "8000:8000"
    volumes:
      - ./api:/app
      - ./workspace:/workspace
      - ./platform:/platform
      - bifrost_temp:/tmp/bifrost
    depends_on:
      postgres:
        condition: service_healthy
      rabbitmq:
        condition: service_healthy
      redis:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 10s
      timeout: 5s
      retries: 5
    command: >
      sh -c "alembic upgrade head &&
             uvicorn main:app --host 0.0.0.0 --port 8000 --reload"

  # Background Jobs Worker
  jobs:
    build:
      context: ./jobs
      dockerfile: Dockerfile
    container_name: bifrost-jobs
    environment:
      DATABASE_URL: postgresql+asyncpg://bifrost:${POSTGRES_PASSWORD:-bifrost_dev}@postgres:5432/bifrost
      RABBITMQ_URL: amqp://bifrost:${RABBITMQ_PASSWORD:-bifrost_dev}@rabbitmq:5672/
      REDIS_URL: redis://redis:6379/0
      SECRET_KEY: ${SECRET_KEY:-dev-secret-key-change-in-production}
      WORKSPACE_PATH: /workspace
      TEMP_PATH: /tmp/bifrost
    volumes:
      - ./jobs:/app
      - ./workspace:/workspace
      - ./platform:/platform
      - bifrost_temp:/tmp/bifrost
    depends_on:
      postgres:
        condition: service_healthy
      rabbitmq:
        condition: service_healthy
      api:
        condition: service_healthy
    command: python main.py

  # React Frontend (future)
  # client:
  #   build:
  #     context: ./client
  #     dockerfile: Dockerfile
  #   container_name: bifrost-client
  #   ports:
  #     - "3000:80"
  #   depends_on:
  #     - api
  #   environment:
  #     VITE_API_URL: http://localhost:8000

volumes:
  postgres_data:
  rabbitmq_data:
  redis_data:
  bifrost_temp:
```

---

## Environment Variables

```bash
# .env.example

# Database
POSTGRES_PASSWORD=your_secure_password

# RabbitMQ
RABBITMQ_PASSWORD=your_secure_password

# Security
SECRET_KEY=your-256-bit-secret-key-here

# CORS
CORS_ORIGINS=http://localhost:3000,http://localhost:8000

# OAuth Providers (optional - for social login)
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
MICROSOFT_CLIENT_ID=
MICROSOFT_CLIENT_SECRET=
GITHUB_CLIENT_ID=
GITHUB_CLIENT_SECRET=

# File paths
WORKSPACE_PATH=/workspace
TEMP_PATH=/tmp/bifrost
```

---

## Key Code Changes

### 1. Replace Azure Functions with FastAPI Routers

**Before (Azure Functions):**
```python
# functions/http/workflows.py
bp = func.Blueprint()

@bp.route(route="workflows", methods=["GET"])
@openapi_endpoint(...)
async def list_workflows(req: func.HttpRequest) -> func.HttpResponse:
    context = get_execution_context(req)
    result = await list_workflows_handler(context)
    return func.HttpResponse(result.model_dump_json(), mimetype="application/json")
```

**After (FastAPI):**
```python
# api/routers/workflows.py
from fastapi import APIRouter, Depends
from api.core.auth import current_active_user, get_org_context

router = APIRouter(prefix="/workflows", tags=["workflows"])

@router.get("/", response_model=ListWorkflowsResponse)
async def list_workflows(
    user: User = Depends(current_active_user),
    context: ExecutionContext = Depends(get_org_context),
):
    return await workflow_service.list_workflows(context)
```

### 2. Replace Table Storage with SQLAlchemy

**Before (Table Storage):**
```python
# shared/repositories/executions.py
class ExecutionsRepository:
    def __init__(self, table_service: TableStorageService):
        self.table = table_service

    async def get(self, execution_id: str) -> Execution:
        entity = await self.table.get_entity("Entities", org_id, f"execution:{execution_id}")
        return Execution(**entity)
```

**After (SQLAlchemy):**
```python
# api/repositories/executions.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

class ExecutionsRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, execution_id: UUID) -> Execution:
        result = await self.session.execute(
            select(ExecutionModel).where(ExecutionModel.id == execution_id)
        )
        return result.scalar_one_or_none()
```

### 3. Replace Azure Queue with RabbitMQ

**Before (Azure Queue):**
```python
# functions/queue/worker.py
@bp.queue_trigger(arg_name="msg", queue_name="workflow-executions")
async def workflow_worker(msg: func.QueueMessage):
    data = json.loads(msg.get_body().decode())
    await execute_workflow(data)
```

**After (RabbitMQ with aio-pika):**
```python
# jobs/consumers/workflow_consumer.py
import aio_pika

async def workflow_consumer(message: aio_pika.IncomingMessage):
    async with message.process():
        data = json.loads(message.body.decode())
        await execute_workflow(data)

async def start_consumer():
    connection = await aio_pika.connect_robust(settings.RABBITMQ_URL)
    channel = await connection.channel()
    queue = await channel.declare_queue("workflow.executions", durable=True)
    await queue.consume(workflow_consumer)
```

---

## Risk Assessment

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Data migration complexity | High | Medium | Create comprehensive migration scripts, test with production data copy |
| Auth system security gaps | High | Low | Security audit, use battle-tested libraries (FastAPI-Users) |
| Performance regression | Medium | Medium | Load testing, proper indexing, connection pooling |
| Breaking existing workflows | High | Low | Comprehensive SDK testing, version compatibility layer |
| Team learning curve | Medium | Medium | Documentation, pairing sessions, phased rollout |
| Integration OAuth breaking | Medium | Low | Keep OAuth token storage compatible, test each provider |

---

## Success Criteria

1. **Functionality:** All existing features work in new architecture
2. **Performance:** API response times within 20% of current
3. **Developer Experience:** `docker compose up` to fully functional environment in < 2 minutes
4. **Testing:** Test coverage maintained or improved
5. **Security:** Pass security audit for auth system
6. **Documentation:** Complete migration guide and updated README

---

## Open Questions

1. **Data Migration:** How will we migrate existing Table Storage data to PostgreSQL?
2. **Backward Compatibility:** Do we need to support Azure deployment alongside Docker?
3. **WebPubSub Replacement:** Should we use Redis Pub/Sub or WebSockets for real-time logs?
4. **Multi-tenancy:** Current org scoping via partition keys - how to handle in PostgreSQL?
5. **File Storage:** Keep local filesystem or add MinIO for S3-compatible object storage?
