#!/bin/bash

# MSP Automation Platform - Stop Development Services

set -e

PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_ROOT"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}🛑 Stopping MSP Automation Platform Development Environment...${NC}"
echo ""

# Function to kill process by PID file
kill_by_pidfile() {
    local pidfile=$1
    local name=$2

    if [ -f "$pidfile" ]; then
        local pid=$(cat "$pidfile")
        if ps -p $pid > /dev/null 2>&1; then
            echo -e "${YELLOW}Stopping $name (PID: $pid)...${NC}"
            kill $pid 2>/dev/null || true
            sleep 1
            # Force kill if still running
            if ps -p $pid > /dev/null 2>&1; then
                kill -9 $pid 2>/dev/null || true
            fi
            echo -e "${GREEN}✅ $name stopped${NC}"
        else
            echo -e "${YELLOW}⚠️  $name was not running${NC}"
        fi
        rm -f "$pidfile"
    else
        echo -e "${YELLOW}⚠️  No PID file for $name${NC}"
    fi
}

# Function to kill process by port
kill_by_port() {
    local port=$1
    local name=$2

    local pid=$(lsof -ti:$port 2>/dev/null || echo "")
    if [ -n "$pid" ]; then
        echo -e "${YELLOW}Stopping $name on port $port (PID: $pid)...${NC}"
        kill $pid 2>/dev/null || true
        sleep 1
        # Force kill if still running
        if lsof -ti:$port > /dev/null 2>&1; then
            kill -9 $(lsof -ti:$port) 2>/dev/null || true
        fi
        echo -e "${GREEN}✅ $name stopped${NC}"
    else
        echo -e "${YELLOW}⚠️  Nothing running on port $port${NC}"
    fi
}

# Stop services

# 1. Stop Client
echo -e "${RED}Stopping Client...${NC}"
kill_by_pidfile "logs/client.pid" "Client"
kill_by_port 4280 "SWA Emulator"
kill_by_port 5173 "Vite Dev Server"
echo ""

# 2. Stop Workflows
echo -e "${RED}Stopping Workflows...${NC}"
kill_by_pidfile "logs/workflows.pid" "Workflows"
kill_by_port 7072 "Workflows Functions"
echo ""

# 3. Stop API
echo -e "${RED}Stopping API...${NC}"
kill_by_pidfile "logs/api.pid" "API"
kill_by_port 7071 "API Functions"
echo ""

# 4. Stop Azurite (optional - you may want to keep it running)
read -p "Stop Azurite? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${RED}Stopping Azurite...${NC}"
    kill_by_port 10002 "Azurite"
    echo ""
else
    echo -e "${YELLOW}⏭️  Keeping Azurite running${NC}"
    echo ""
fi

# Clean up log files
if [ -d "logs" ]; then
    echo -e "${YELLOW}Cleaning up log files...${NC}"
    rm -f logs/*.pid
    # Keep log files for debugging
    echo -e "${GREEN}✅ Log files preserved in logs/ directory${NC}"
fi

echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✅ All services stopped${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
