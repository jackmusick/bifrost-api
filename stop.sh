#!/bin/bash

# Bifrost Integrations - Stop Development Services

PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_ROOT"

echo "🛑 Stopping services..."
echo ""

# 1. Stop SWA
pidfile="logs/swa.pid"
if [ -f "$pidfile" ]; then
    pid=$(cat "$pidfile")
    if kill $pid 2>/dev/null; then
        echo "✅ Stopped SWA"
    fi
    rm -f "$pidfile"
fi

# Stop by ports (backup for SWA)
for port in 4280 5173; do
    if lsof -ti:$port > /dev/null 2>&1; then
        kill $(lsof -ti:$port) 2>/dev/null || true
    fi
done

# 2. Stop Docker services
echo "🐳 Stopping Docker services..."
docker compose -f docker-compose.dev.yml down

echo ""
echo "✅ All services stopped"
echo ""
