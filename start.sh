#!/bin/bash

# Bifrost Integrations - Start Development Environment
# Starts: Docker (Azurite + Workflows Engine) and SWA (Management API + Client)

set -e

PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_ROOT"

echo "🚀 Starting Bifrost Integrations..."
echo ""

# 1. Start Docker services (Azurite + Workflows Engine)
echo "🐳 Starting Docker services (Azurite + Workflows Engine)..."
ENABLE_DEBUGGING=true docker compose -f docker-compose.dev.yml up --build -d

echo "⏳ Waiting for services to be ready..."
sleep 5

# Wait for Functions to be healthy
max_attempts=30
attempt=0
while [ $attempt -lt $max_attempts ]; do
    if curl -s http://localhost:7071/api/health > /dev/null 2>&1; then
        echo "✅ Workflows Engine ready"
        break
    fi
    attempt=$((attempt + 1))
    sleep 1
done

if [ $attempt -eq $max_attempts ]; then
    echo "⚠️  Warning: Workflows Engine not responding after 30s"
fi

# 2. Start SWA (includes Management API + Client via Vite)
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

    # Create logs directory if needed
    mkdir -p ../logs

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

# 3. Initialize tables and seed data
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
echo "   • Workflows API:   http://localhost:7071"
echo ""
echo "📝 Logs:"
echo "   • Docker:    docker compose -f docker-compose.dev.yml logs -f"
echo "   • SWA:       tail -f logs/swa.log"
echo ""
echo "🐛 Debug:"
echo "   • Use VS Code 'Attach to Docker Functions' launch config"
echo "   • Or attach manually to localhost:5678"
echo ""
echo "🛑 Stop: ./stop.sh"
echo ""
