# Debugging Guide

This guide explains how to debug Azure Functions locally using VS Code and Docker.

## Prerequisites

- Docker Desktop installed and running
- VS Code with Python extension installed
- Python Debugger (debugpy) extension for VS Code

## Quick Start

### Option 1: Automatic Launch (Recommended)

1. Open VS Code in the repository root
2. Open a Python file in `workflows/` (e.g., `workflows/function_app.py`)
3. Set a breakpoint by clicking to the left of a line number
4. Press **F5** or go to **Run > Start Debugging**
5. Select **"Attach to Docker Functions"** from the dropdown
6. VS Code will automatically:
   - Start Docker Compose with debugging enabled
   - Wait for the container to be ready
   - Attach the debugger
7. Your breakpoint will be hit when the function is triggered

### Option 2: Manual Launch

If containers are already running with debugging enabled:

1. Run the task: **Terminal > Run Task > Start Docker with Debugging**
2. Wait for the message: `Waiting for debugger to attach...`
3. Press **F5** and select **"Attach to Docker Functions (Manual)"**
4. Set breakpoints and trigger your functions

## Available VS Code Tasks

Access tasks via **Terminal > Run Task**:

- **Start Docker with Debugging** - Starts containers with debugpy enabled (port 5678)
- **Start Docker (No Debugging)** - Starts containers normally (faster startup)
- **Stop Docker** - Stops all containers
- **Restart Docker with Debugging** - Full restart with debugging enabled
- **View Docker Logs** - Watch container logs in real-time

## How It Works

### Debug Mode (ENABLE_DEBUGGING=true)

When debugging is enabled:

1. Container starts with `debugpy` listening on port 5678
2. Container **waits** for VS Code to attach before starting Azure Functions
3. Once debugger attaches, Azure Functions starts normally
4. Breakpoints work for all Python code in `/workflows`

### Normal Mode (Default)

When debugging is disabled (default):

1. Container starts immediately without debugpy
2. Azure Functions starts right away (faster)
3. No debugging capabilities

## Environment Variables

- `ENABLE_DEBUGGING=true` - Enables debugpy and waits for debugger attach
- `ENABLE_DEBUGGING=false` or unset - Normal startup (default)

## Port Mappings

- `7071` - Azure Functions HTTP endpoint
- `5678` - Debugpy debugging port (when ENABLE_DEBUGGING=true)
- `10000-10002` - Azurite storage emulator (Blob, Queue, Table)

## Troubleshooting

### Debugger won't connect

```bash
# Check if debugging is enabled
docker compose -f docker-compose.dev.yml logs functions | grep debug

# Should see: "Waiting for debugger to attach..."
```

### Container stuck waiting for debugger

This is **normal behavior** when `ENABLE_DEBUGGING=true`. The container waits until you attach VS Code. If you want to run without waiting, use:

```bash
docker compose -f docker-compose.dev.yml down
docker compose -f docker-compose.dev.yml up -d  # No debugging
```

### Breakpoints not hitting

1. Verify the debugger is attached (VS Code debug toolbar should be visible)
2. Check that your code is in `/workflows` directory
3. Ensure the function is being triggered (check logs)
4. Try setting `"justMyCode": false` in launch.json (already configured)

### Port conflicts

If port 5678 is already in use:

```bash
# Find what's using the port
lsof -i :5678

# Stop the process or change the port in docker-compose.dev.yml
```

## Example: Debugging a Function

1. Open `workflows/function_app.py`
2. Add a breakpoint on a function handler line
3. Press **F5** and select **"Attach to Docker Functions"**
4. Wait for "Debugger attached" message
5. Trigger your function (e.g., `curl http://localhost:7071/api/your-function`)
6. Debugger pauses at breakpoint
7. Inspect variables, step through code, etc.

## Live Code Reload

The `/workflows` directory is mounted as a volume, so code changes are reflected immediately:

1. Make changes to Python files
2. Save the file
3. Azure Functions automatically reloads the module
4. No need to rebuild or restart the container (unless changing requirements.txt)

## Rebuilding After Dependency Changes

If you modify `requirements.txt`:

```bash
docker compose -f docker-compose.dev.yml down
docker compose -f docker-compose.dev.yml up -d --build
```

Or use the VS Code task: **Restart Docker with Debugging**
