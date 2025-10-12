#!/bin/bash

# Bifrost Integrations - Start Development Environment
# Starts: Azurite, Workflows Engine, and SWA (which includes Management API + Client)

set -e

PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_ROOT"

echo "🚀 Starting Bifrost Integrations..."
echo ""

# 1. Start Azurite (if not already running)
if lsof -i:10002 > /dev/null 2>&1; then
    echo "✅ Azurite already running"
else
    echo "📦 Starting Azurite..."
    ./.specify/scripts/start-azurite.sh &
    sleep 2
fi

# 2. Start Workflows Engine (port 7072)
if lsof -i:7072 > /dev/null 2>&1; then
    echo "✅ Workflows Engine already running on port 7072"
else
    echo "🔄 Starting Workflows Engine..."
    cd workflows

    # Create venv if needed
    [ ! -d ".venv" ] && python3 -m venv .venv

    # Install dependencies if needed
    if [ ! -f ".venv/deps_installed" ]; then
        source .venv/bin/activate
        pip install -r requirements.txt
        touch .venv/deps_installed
    fi

    # Start in background
    source .venv/bin/activate
    func start --enableAuth --port 7072 > ../logs/workflows.log 2>&1 &
    echo $! > ../logs/workflows.pid
    cd ..
    sleep 2
fi

# 3. Start SWA (includes Management API + Client via Vite)
if lsof -i:4280 > /dev/null 2>&1; then
    echo "✅ SWA already running on port 4280"
else
    echo "🎨 Starting SWA (Client + Management API)..."
    cd client

    # Install Management API dependencies if needed
    if [ ! -f "api/.venv/deps_installed" ]; then
        cd api
        python3 -m venv .venv
        source .venv/bin/activate
        pip install -r requirements.txt
        touch .venv/deps_installed
        cd ..
    fi

    # Install client dependencies if needed
    [ ! -d "node_modules" ] && npm install

    # Start SWA (manages both API and client)
    # Use Node 20 for Azure Functions compatibility if available
    if command -v nvm &> /dev/null && nvm which 20 &> /dev/null; then
        nvm exec 20 swa start > ../logs/swa.log 2>&1 &
    else
        swa start > ../logs/swa.log 2>&1 &
    fi
    echo $! > ../logs/swa.pid
    cd ..
    sleep 3
fi

# 4. Initialize tables and seed data
if [ -f "client/api/shared/init_tables.py" ]; then
    echo "🗄️  Initializing tables..."
    cd client/api
    source .venv/bin/activate
    python3 shared/init_tables.py > /dev/null 2>&1 || true
    cd ../..
fi

if [ -f ".specify/scripts/seed-local-data.sh" ]; then
    echo "🌱 Seeding data..."
    ./.specify/scripts/seed-local-data.sh > /dev/null 2>&1 || true
fi

echo ""
echo "✅ All services started!"
echo ""
echo "🌐 URLs:"
echo "   • Client:          http://localhost:4280"
echo "   • Workflows API:   http://localhost:7072"
echo ""
echo "📝 Logs:"
echo "   • SWA:       tail -f logs/swa.log"
echo "   • Workflows: tail -f logs/workflows.log"
echo ""
echo "🛑 Stop: ./stop-dev.sh"
echo ""
