#!/bin/bash
# Bifrost API - Test Runner
# Usage: ./test.sh [pytest args...]
#
# This script starts the PostgreSQL/RabbitMQ/Redis stack,
# runs database migrations, and executes tests.

set -e

# =============================================================================
# Configuration
# =============================================================================
COMPOSE_FILE="docker-compose.yml"
TEST_DB="bifrost_test"
COVERAGE=false
PYTEST_ARGS=()

# Parse command line arguments
for arg in "$@"; do
    if [ "$arg" = "--coverage" ]; then
        COVERAGE=true
    else
        PYTEST_ARGS+=("$arg")
    fi
done

# =============================================================================
# Cleanup function
# =============================================================================
cleanup() {
    echo ""
    echo "Cleaning up test environment..."
    docker compose -f "$COMPOSE_FILE" down -v 2>/dev/null || true
    echo "Cleanup complete"
}

# Trap to ensure cleanup on exit or Ctrl+C
trap cleanup EXIT INT TERM

# =============================================================================
# Start services
# =============================================================================
echo "============================================================"
echo "Bifrost API - Test Runner"
echo "============================================================"
echo ""

# Stop any existing containers
echo "Stopping any existing containers..."
docker compose -f "$COMPOSE_FILE" down -v 2>/dev/null || true

# Start services
echo "Starting PostgreSQL, RabbitMQ, and Redis..."
docker compose -f "$COMPOSE_FILE" up -d postgres rabbitmq redis

# Wait for PostgreSQL
echo "Waiting for PostgreSQL to be ready..."
for i in {1..60}; do
    if docker compose -f "$COMPOSE_FILE" exec -T postgres pg_isready -U bifrost -d bifrost > /dev/null 2>&1; then
        echo "PostgreSQL is ready!"
        break
    fi
    if [ $i -eq 60 ]; then
        echo "ERROR: PostgreSQL failed to start within 60 seconds"
        docker compose -f "$COMPOSE_FILE" logs postgres
        exit 1
    fi
    sleep 1
done

# Wait for RabbitMQ
echo "Waiting for RabbitMQ to be ready..."
for i in {1..60}; do
    if docker compose -f "$COMPOSE_FILE" exec -T rabbitmq rabbitmq-diagnostics check_running > /dev/null 2>&1; then
        echo "RabbitMQ is ready!"
        break
    fi
    if [ $i -eq 60 ]; then
        echo "ERROR: RabbitMQ failed to start within 60 seconds"
        docker compose -f "$COMPOSE_FILE" logs rabbitmq
        exit 1
    fi
    sleep 1
done

# Wait for Redis
echo "Waiting for Redis to be ready..."
for i in {1..30}; do
    if docker compose -f "$COMPOSE_FILE" exec -T redis redis-cli ping > /dev/null 2>&1; then
        echo "Redis is ready!"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "ERROR: Redis failed to start within 30 seconds"
        docker compose -f "$COMPOSE_FILE" logs redis
        exit 1
    fi
    sleep 1
done

# =============================================================================
# Set up test environment
# =============================================================================
echo ""
echo "Setting up test environment..."

# Export environment variables for tests
export DATABASE_URL="postgresql+asyncpg://bifrost:bifrost_dev@localhost:5432/bifrost"
export DATABASE_URL_SYNC="postgresql://bifrost:bifrost_dev@localhost:5432/bifrost"
export RABBITMQ_URL="amqp://bifrost:bifrost_dev@localhost:5672/"
export REDIS_URL="redis://localhost:6379/0"
export SECRET_KEY="test-secret-key-for-testing-only-32chars"
export ENVIRONMENT="testing"
export WORKSPACE_PATH="$(mktemp -d)"
export TEMP_PATH="$(mktemp -d)"

echo "Test workspace: $WORKSPACE_PATH"
echo "Test temp: $TEMP_PATH"

# =============================================================================
# Run migrations
# =============================================================================
echo ""
echo "Running database migrations..."
python -m alembic upgrade head

# =============================================================================
# Run tests
# =============================================================================
echo ""
echo "============================================================"
echo "Running tests..."
echo "============================================================"
echo ""

if [ "$COVERAGE" = true ]; then
    echo "Running tests with coverage..."
    if [ ${#PYTEST_ARGS[@]} -eq 0 ]; then
        pytest tests/ --cov=src --cov-report=term-missing --cov-report=xml -v
    else
        pytest "${PYTEST_ARGS[@]}" --cov=src --cov-report=term-missing --cov-report=xml
    fi
else
    if [ ${#PYTEST_ARGS[@]} -eq 0 ]; then
        pytest tests/ -v
    else
        pytest "${PYTEST_ARGS[@]}"
    fi
fi

echo ""
echo "============================================================"
echo "Tests completed!"
echo "============================================================"
