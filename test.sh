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
npx azurite --blobPort 10100 --queuePort 10101 --tablePort 10102 --inMemoryPersistence > /tmp/azurite-test.log 2>&1 &

# Wait for Azurite services to be ready
AZURITE_READY=false
echo "Waiting on Azurite..."
for i in {1..120}; do
    # Check if all three services are successfully listening
    if grep -q "Azurite Blob service is successfully listening" /tmp/azurite-test.log && \
       grep -q "Azurite Queue service is successfully listening" /tmp/azurite-test.log && \
       grep -q "Azurite Table service is successfully listening" /tmp/azurite-test.log; then
        echo "Azurite is ready!"
        AZURITE_READY=true
        break
    fi
    sleep 1
done

if [ "$AZURITE_READY" = false ]; then
    echo "ERROR: Azurite failed to start within 120 seconds"
    echo "Azurite log:"
    cat /tmp/azurite-test.log 2>/dev/null || echo "No log file found"
    exit 1
fi

# Start func on port 7777 with test connection string
echo "Starting func on port 7777..."

export AzureWebJobsStorage="DefaultEndpointsProtocol=http;AccountName=devstoreaccount1;AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;BlobEndpoint=http://localhost:10100/devstoreaccount1;QueueEndpoint=http://localhost:10101/devstoreaccount1;TableEndpoint=http://localhost:10102/devstoreaccount1;"
export FUNCTIONS_WORKER_RUNTIME="python"

# Create temporary directories for workspace and temp storage
export BIFROST_WORKSPACE_LOCATION="$(mktemp -d)"
export BIFROST_TEMP_LOCATION="$(mktemp -d)"
echo "Created test workspace: $BIFROST_WORKSPACE_LOCATION"
echo "Created test temp: $BIFROST_TEMP_LOCATION"

# # Show diagnostic info
# echo "=== Test Environment Diagnostics ==="
# echo "AzureWebJobsStorage: ${AzureWebJobsStorage:0:50}..."
# echo "AZURE_KEY_VAULT_URL: $AZURE_KEY_VAULT_URL"
# echo "===================================="

func start --port 7777 > /tmp/func-test.log 2>&1 &
FUNC_PID=$!

# Wait for func to be ready
READY=false
echo "Waiting on Azure Functions..."
for i in {1..120}; do
    if curl -s http://localhost:7777/api/openapi/v3.json > /dev/null 2>&1; then
        echo "Function app initialization complete!"
        READY=true
        break
    fi

    sleep 1
done

if [ "$READY" = false ]; then
    echo "ERROR: Azure Functions failed to start within 120 seconds"
    echo "Full func log:"
    cat /tmp/func-test.log 2>/dev/null || echo "No log file found"
    exit 1
fi

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
