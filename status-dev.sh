#!/bin/bash

# MSP Automation Platform - Check Development Services Status

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🔍 MSP Automation Platform - Service Status${NC}"
echo ""

# Function to check if a port is in use
check_service() {
    local port=$1
    local name=$2
    local url=$3

    if lsof -i:$port > /dev/null 2>&1; then
        local pid=$(lsof -ti:$port)
        if [ -n "$url" ] && curl -s "$url" > /dev/null 2>&1; then
            echo -e "${GREEN}✅ $name${NC} - Running on port $port (PID: $pid) - ${GREEN}Healthy${NC}"
        else
            echo -e "${YELLOW}⚠️  $name${NC} - Running on port $port (PID: $pid) - ${YELLOW}Not responding${NC}"
        fi
    else
        echo -e "${RED}❌ $name${NC} - Not running"
    fi
}

# Check all services
check_service 4280 "Client (SWA Emulator)  " "http://localhost:4280"
check_service 5173 "Vite Dev Server        " "http://localhost:5173"
check_service 7071 "API (Azure Functions) " "http://localhost:7071/api/health"
check_service 7072 "Workflows Engine      " ""
check_service 10002 "Azurite (Storage)     " "http://127.0.0.1:10002/devstoreaccount1?comp=list"

echo ""
echo -e "${BLUE}📊 Quick Access URLs:${NC}"
echo -e "   • Main App:  ${GREEN}http://localhost:4280${NC}"
echo -e "   • API Docs:  ${GREEN}http://localhost:7071/api/health${NC}"
echo ""
