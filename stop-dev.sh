#!/bin/bash

# MSP Automation Platform - Stop Development Services

PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_ROOT"

echo "🛑 Stopping services..."
echo ""

# Stop by PID files
for service in swa workflows; do
    pidfile="logs/${service}.pid"
    if [ -f "$pidfile" ]; then
        pid=$(cat "$pidfile")
        if kill $pid 2>/dev/null; then
            echo "✅ Stopped $service"
        fi
        rm -f "$pidfile"
    fi
done

# Stop by ports (backup)
for port in 4280 5173 7072; do
    if lsof -ti:$port > /dev/null 2>&1; then
        kill $(lsof -ti:$port) 2>/dev/null || true
    fi
done

# Optionally stop Azurite
read -p "Stop Azurite? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    lsof -ti:10002 > /dev/null 2>&1 && kill $(lsof -ti:10002) 2>/dev/null || true
    echo "✅ Stopped Azurite"
else
    echo "⏭️  Keeping Azurite running"
fi

echo ""
echo "✅ Services stopped"
echo ""
