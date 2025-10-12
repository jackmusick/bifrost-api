#!/bin/bash

# MSP Automation Platform - Development Startup Script
# Starts all required services: Azurite, API, Workflows, and Client

set -e

echo "🚀 Starting MSP Automation Platform Development Environment..."
echo ""

PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_ROOT"

# Create logs directory if it doesn't exist
mkdir -p logs

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to check if a port is in use
check_port() {
    lsof -i :"$1" > /dev/null 2>&1
}

# Function to wait for a service to be ready
wait_for_service() {
    local url=$1
    local name=$2
    local max_attempts=30
    local attempt=0

    echo -e "${YELLOW}⏳ Waiting for $name to be ready...${NC}"

    while [ $attempt -lt $max_attempts ]; do
        if curl -s "$url" > /dev/null 2>&1; then
            echo -e "${GREEN}✅ $name is ready!${NC}"
            return 0
        fi
        attempt=$((attempt + 1))
        sleep 1
    done

    echo -e "${YELLOW}⚠️  $name may not be ready yet, continuing anyway...${NC}"
    return 1
}

# 1. Start Azurite (if not already running)
echo -e "${BLUE}📦 Step 1/4: Starting Azurite (Azure Storage Emulator)...${NC}"
if check_port 10002; then
    echo -e "${GREEN}✅ Azurite is already running${NC}"
else
    ./.specify/scripts/start-azurite.sh &
    wait_for_service "http://127.0.0.1:10002/devstoreaccount1?comp=list" "Azurite"
fi
echo ""

# 2. Start API (Azure Functions)
echo -e "${BLUE}⚙️  Step 2/4: Starting API (Azure Functions)...${NC}"
if check_port 7071; then
    echo -e "${GREEN}✅ API is already running on port 7071${NC}"
else
    cd api

    # Check if virtual environment exists
    if [ ! -d ".venv" ]; then
        echo -e "${YELLOW}Creating Python virtual environment...${NC}"
        python3 -m venv .venv
    fi

    # Activate and install dependencies
    source .venv/bin/activate

    if [ ! -f ".venv/dependencies_installed" ]; then
        echo -e "${YELLOW}Installing API dependencies...${NC}"
        pip install -r requirements.txt > /dev/null 2>&1
        touch .venv/dependencies_installed
    fi

    # Start Azure Functions in background
    echo -e "${YELLOW}Starting Azure Functions host...${NC}"
    func start --verbose > ../logs/api.log 2>&1 &
    API_PID=$!
    echo $API_PID > ../logs/api.pid

    cd ..
    wait_for_service "http://localhost:7071/api/health" "API"

    # Initialize tables if needed
    echo -e "${YELLOW}Initializing database tables...${NC}"
    cd api
    source .venv/bin/activate
    python3 shared/init_tables.py > /dev/null 2>&1 && echo -e "${GREEN}✅ Tables initialized${NC}" || echo -e "${YELLOW}⚠️  Table initialization skipped (may already exist)${NC}"
    cd ..
fi
echo ""

# 3. Start Workflows (Azure Functions)
echo -e "${BLUE}🔄 Step 3/4: Starting Workflows Engine...${NC}"
if check_port 7072; then
    echo -e "${GREEN}✅ Workflows are already running on port 7072${NC}"
else
    cd workflows

    # Check if virtual environment exists
    if [ ! -d ".venv" ]; then
        echo -e "${YELLOW}Creating Python virtual environment...${NC}"
        python3 -m venv .venv
    fi

    # Activate and install dependencies
    source .venv/bin/activate

    if [ ! -f ".venv/dependencies_installed" ]; then
        echo -e "${YELLOW}Installing workflow dependencies...${NC}"
        pip install -r requirements.txt > /dev/null 2>&1
        touch .venv/dependencies_installed
    fi

    # Start Azure Functions in background (different port)
    echo -e "${YELLOW}Starting Workflows Functions host...${NC}"
    func start --port 7072 --verbose > ../logs/workflows.log 2>&1 &
    WORKFLOWS_PID=$!
    echo $WORKFLOWS_PID > ../logs/workflows.pid

    cd ..
    sleep 3  # Give it a moment to start
    echo -e "${GREEN}✅ Workflows engine started${NC}"
fi
echo ""

# 4. Start Client (Vite + SWA)
echo -e "${BLUE}🎨 Step 4/4: Starting Client (Vite + Azure SWA Emulator)...${NC}"
if check_port 4280; then
    echo -e "${GREEN}✅ Client is already running on port 4280${NC}"
else
    cd client

    # Install dependencies if needed
    if [ ! -d "node_modules" ]; then
        echo -e "${YELLOW}Installing client dependencies...${NC}"
        npm install > /dev/null 2>&1
    fi

    # Start client in background
    echo -e "${YELLOW}Starting Vite dev server and SWA emulator...${NC}"
    npm run dev > ../logs/client.log 2>&1 &
    CLIENT_PID=$!
    echo $CLIENT_PID > ../logs/client.pid

    cd ..
    wait_for_service "http://localhost:4280" "Client"
fi
echo ""

# Optional: Seed test data if script exists
if [ -f ".specify/scripts/seed-local-data.sh" ]; then
    echo -e "${BLUE}🌱 Seeding test data...${NC}"
    ./.specify/scripts/seed-local-data.sh > /dev/null 2>&1 && echo -e "${GREEN}✅ Test data seeded${NC}" || echo -e "${YELLOW}⚠️  Data seeding skipped (may already exist)${NC}"
fi

echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✅ All services started successfully!${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${BLUE}🌐 Service URLs:${NC}"
echo -e "   • Client (UI):       ${GREEN}http://localhost:4280${NC}"
echo -e "   • Vite Dev Server:   ${GREEN}http://localhost:5173${NC}"
echo -e "   • API:               ${GREEN}http://localhost:7071${NC}"
echo -e "   • Workflows:         ${GREEN}http://localhost:7072${NC}"
echo -e "   • Azurite (Storage): ${GREEN}http://localhost:10002${NC}"
echo ""
echo -e "${BLUE}📝 Logs:${NC}"
echo -e "   • API:       tail -f logs/api.log"
echo -e "   • Workflows: tail -f logs/workflows.log"
echo -e "   • Client:    tail -f logs/client.log"
echo ""
echo -e "${BLUE}🛑 To stop all services:${NC}"
echo -e "   ./stop-dev.sh"
echo ""
echo -e "${YELLOW}💡 Next steps:${NC}"
echo -e "   1. Open ${GREEN}http://localhost:4280${NC} in your browser"
echo -e "   2. Navigate to 'Forms' to create or execute forms"
echo -e "   3. Check logs if you encounter any issues (see above)"
echo ""
