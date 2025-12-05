"""
Process-isolated execution for workflows, scripts, and data providers.

This module provides:
- Process pool management for isolated execution
- Guaranteed cancellation via SIGTERM/SIGKILL
- Timeout enforcement at the process level
- Redis-based communication between parent and worker

Architecture:
    Consumer (main process)
    └── ProcessPool
        ├── Worker Process 1 (isolated)
        ├── Worker Process 2 (isolated)
        └── Worker Process N (isolated)

Each worker process:
- Reads execution context from Redis
- Runs the workflow/script in complete isolation
- Writes logs to Redis Stream (real-time)
- Writes result to Redis on completion
- Can be killed with SIGKILL if stuck
"""

from .pool import ExecutionPool, get_execution_pool, shutdown_pool
from .worker import run_in_worker

__all__ = [
    "ExecutionPool",
    "get_execution_pool",
    "shutdown_pool",
    "run_in_worker",
]
