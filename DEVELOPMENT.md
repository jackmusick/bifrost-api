# Local Development Guide

This guide explains how to run Bifrost locally WITHOUT full Docker, for faster development and debugging.

## Strategy

**Infrastructure in Docker** (easiest):
- PostgreSQL
- RabbitMQ
- Redis

**Application locally** (easy debugging, instant reload):
- API (FastAPI)
- Worker (RabbitMQ consumers)
- Scheduler (APScheduler)
- Discovery (file watcher)
- Client (Vite dev server)

---

## Setup

### 1. Start Infrastructure

Start just the infrastructure services:

```bash
docker compose up -d postgres rabbitmq redis
```

Check they're healthy:
```bash
docker compose ps
```

### 2. Configure Environment

Create `.env` with local connection URLs:

```bash
# Run setup script first (generates secrets)
./setup.sh

# Then add these local connection URLs to .env
cat >> .env << 'EOF'

# Local development - connect to Docker infrastructure
BIFROST_DATABASE_URL=postgresql+asyncpg://bifrost:bifrost_dev@localhost:5432/bifrost
BIFROST_DATABASE_URL_SYNC=postgresql://bifrost:bifrost_dev@localhost:5432/bifrost
BIFROST_RABBITMQ_URL=amqp://bifrost:bifrost_dev@localhost:5672/
BIFROST_REDIS_URL=redis://localhost:6379/0
BIFROST_WORKSPACE_LOCATION=/tmp/bifrost-workspace
EOF
```

### 3. Run Database Migrations

```bash
cd api
alembic upgrade head
```

### 4. Start Services Locally

Open **4 terminal windows**:

**Terminal 1 - API:**
```bash
cd api
uvicorn src.main:app --reload --reload-dir src --reload-dir shared
```
Access at http://localhost:8000

**Terminal 2 - Worker:**
```bash
cd api
python -m src.worker.main
```

**Terminal 3 - Scheduler:**
```bash
cd api
python -m src.scheduler.main
```

**Terminal 4 - Discovery:**
```bash
cd api
python -m src.discovery.main
```

**Terminal 5 - Client:**
```bash
cd client
npm run dev
```
Access at http://localhost:3000

---

## Debugging

### VS Code Debugging

**API Debugging:**

1. Stop the API terminal
2. Use VS Code's "Python: FastAPI" debug configuration
3. Set breakpoints in your code

**Worker Debugging:**

1. Stop the worker terminal
2. Use VS Code's "Python: Worker" debug configuration
3. Set breakpoints in consumer code

### Client Debugging

- Use Chrome DevTools (F12)
- React DevTools extension
- Network tab to inspect API calls

---

## Running Tests

Tests require Docker infrastructure:

```bash
# Make sure infrastructure is running
docker compose up -d postgres rabbitmq redis

# Run all tests
./test.sh

# Run specific tests
./test.sh tests/integration/test_workflows.py -v

# Run with coverage
./test.sh --coverage
```

---

## Type Checking

```bash
# API
cd api
pyright

# Client
cd client
npm run tsc
```

---

## Generating Client Types

After changing API models, regenerate TypeScript types:

```bash
# Make sure API is running on http://localhost:8000
cd client
npm run generate:types
```

---

## Full Docker (Production-like)

When you need to test the full production stack:

```bash
# Production build
docker compose up

# Development with hot reload
docker compose -f docker-compose.yml -f docker-compose.dev.yml up
```

---

## Troubleshooting

### Port conflicts

Check if ports are in use:
```bash
lsof -i :5432  # PostgreSQL
lsof -i :5672  # RabbitMQ
lsof -i :6379  # Redis
lsof -i :8000  # API
lsof -i :3000  # Client
```

### Database connection issues

Verify PostgreSQL is accessible:
```bash
psql postgresql://bifrost:bifrost_dev@localhost:5432/bifrost -c "SELECT version();"
```

### RabbitMQ connection issues

Check RabbitMQ management UI:
http://localhost:15672 (user: `bifrost`, password from `.env`)

### Clear everything and start fresh

```bash
# Stop all containers
docker compose down -v

# Remove workspace
rm -rf /tmp/bifrost-workspace

# Restart infrastructure
docker compose up -d postgres rabbitmq redis

# Re-run migrations
cd api && alembic upgrade head
```

---

## Performance Tips

**Faster API reloads:**
- Use `--reload-dir` to only watch specific directories
- Already configured in the commands above

**Faster Client rebuilds:**
- Vite is already optimized for HMR
- Keep node_modules up to date

**Faster tests:**
- Run specific test files instead of full suite
- Use `-x` flag to stop on first failure

---

## Common Workflows

### Adding a new API endpoint

1. Add Pydantic models to `api/shared/models.py`
2. Add handler to appropriate router in `api/src/routers/`
3. Business logic goes in `api/shared/`
4. Run type check: `cd api && pyright`
5. Regenerate client types: `cd client && npm run generate:types`
6. Add client service function in `client/src/services/`
7. Write tests in `api/tests/`

### Working on the UI

1. Start only client and infrastructure:
   ```bash
   docker compose up -d postgres rabbitmq redis api
   cd client && npm run dev
   ```
2. Make changes in `client/src/`
3. Vite auto-reloads on save
4. No need to restart anything

### Debugging a workflow execution

1. Set breakpoint in `api/shared/engine.py` or consumer
2. Start worker in debug mode (VS Code debug config)
3. Trigger workflow from UI
4. Debugger pauses at your breakpoint

