#!/bin/bash
# Generate TypeScript types from OpenAPI spec
#
# Usage:
#   ./scripts/generate-types.sh
#
# Prerequisites:
#   - API must be running (docker compose up or local)
#   - Node.js and npm must be available

set -e

API_URL="${API_URL:-http://localhost:8000}"
MAX_RETRIES=30
RETRY_INTERVAL=2

echo "Waiting for API to be ready at $API_URL..."

for i in $(seq 1 $MAX_RETRIES); do
    if curl -s "$API_URL/openapi.json" > /dev/null 2>&1; then
        echo "API is ready!"
        break
    fi

    if [ $i -eq $MAX_RETRIES ]; then
        echo "Error: API not available after $MAX_RETRIES attempts"
        exit 1
    fi

    echo "Attempt $i/$MAX_RETRIES - waiting ${RETRY_INTERVAL}s..."
    sleep $RETRY_INTERVAL
done

echo "Generating TypeScript types..."
cd "$(dirname "$0")/../client"
npm run generate:types

echo "Types generated successfully at client/src/lib/v1.d.ts"
