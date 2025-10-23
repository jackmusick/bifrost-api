#!/bin/bash
set -e

# Parse command line arguments
COVERAGE=false
PYTEST_ARGS=()

for arg in "$@"; do
    if [ "$arg" = "--coverage" ]; then
        COVERAGE=true
    else
        PYTEST_ARGS+=("$arg")
    fi
done

# Cleanup function - always runs on exit
cleanup() {
    echo "Cleaning up test services..."
    lsof -ti:7777 | xargs kill -9 2>/dev/null || true
    pkill -9 -f "azurite.*10100" 2>/dev/null || true
}

# Trap to ensure cleanup on exit or Ctrl+C
trap cleanup EXIT INT TERM

# Kill any existing test processes
cleanup

# Start Azurite on test ports (in-memory)
echo "Starting Azurite on test ports (10100-10102)..."
npx azurite --blobPort 10100 --queuePort 10101 --tablePort 10102 --inMemoryPersistence --silent &
sleep 15

# Start func on port 7777 with test connection string
echo "Starting func on port 7777..."

export AzureWebJobsStorage="DefaultEndpointsProtocol=http;AccountName=devstoreaccount1;AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;BlobEndpoint=http://localhost:10100/devstoreaccount1;QueueEndpoint=http://localhost:10101/devstoreaccount1;TableEndpoint=http://localhost:10102/devstoreaccount1;"
export FUNCTIONS_WORKER_RUNTIME="python"

# Show diagnostic info
echo "=== Test Environment Diagnostics ==="
echo "Python: $(python --version)"
echo "AzureWebJobsStorage: ${AzureWebJobsStorage:0:50}..."
echo "AZURE_KEY_VAULT_URL: $AZURE_KEY_VAULT_URL"
echo "Azure Identity available: $(python -c 'import azure.identity; print("Yes")' 2>/dev/null || echo "No")"
echo "===================================="

func start --port 7777 > /tmp/func-test.log 2>&1 &
FUNC_PID=$!

# Wait for func to be ready
echo "Waiting for func to be ready..."
READY=false
for i in {1..60}; do
    if curl -s http://localhost:7777/api/openapi/v3.json > /dev/null 2>&1; then
        echo "Services ready!"
        READY=true
        break
    fi

    if [ $((i % 10)) -eq 0 ]; then
        echo "Still waiting... ($i/60 seconds)"
    fi
    sleep 1
done

if [ "$READY" = false ]; then
    echo "ERROR: Azure Functions failed to start within 60 seconds"
    echo "Full func log:"
    cat /tmp/func-test.log 2>/dev/null || echo "No log file found"
    exit 1
fi

echo "Giving the queue a few more seconds..."
sleep 10

# Run pytest with or without coverage
if [ "$COVERAGE" = true ]; then
    echo "Running tests with coverage..."
    if [ ${#PYTEST_ARGS[@]} -eq 0 ]; then
        pytest tests/ --cov=shared --cov=functions --cov-report=term-missing --cov-report=xml -v
    else
        pytest "${PYTEST_ARGS[@]}" --cov=shared --cov=functions --cov-report=term-missing --cov-report=xml
    fi
else
    if [ ${#PYTEST_ARGS[@]} -eq 0 ]; then
        pytest tests/ -v
    else
        pytest "${PYTEST_ARGS[@]}"
    fi
fi
