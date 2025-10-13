#!/bin/bash

# Script to retrieve Azure Functions keys from local development environment

set -e

echo "🔑 Retrieving Function Keys from Docker container..."
echo ""

# Wait for container to be ready
max_attempts=30
attempt=0
while [ $attempt -lt $max_attempts ]; do
    if docker exec bifrost-integrations-functions-1 test -d /azure-functions-host 2>/dev/null; then
        break
    fi
    attempt=$((attempt + 1))
    sleep 1
done

# Check if keys are stored in the container's secrets directory
echo "Checking for host keys..."
docker exec bifrost-integrations-functions-1 find /azure-functions-host -name "*.json" -path "*/secrets/*" 2>/dev/null || true

# Try to get keys from the data directory
echo ""
echo "Checking /data directory for secrets..."
docker exec bifrost-integrations-functions-1 find /data -name "*.json" 2>/dev/null || true

# Check if there's a secrets directory in the mounted volume
echo ""
echo "Checking mounted wwwroot for secrets..."
docker exec bifrost-integrations-functions-1 find /home/site/wwwroot -name "*.json" -path "*/secrets/*" 2>/dev/null || true

echo ""
echo "📝 For local development, you can use the admin API:"
echo "   curl http://localhost:7071/admin/host/systemkeys/_master"
echo ""
echo "Or check the logs for the master key on first startup:"
echo "   docker compose -f docker-compose.dev.yml logs functions | grep -i \"master\\|key\""
echo ""
