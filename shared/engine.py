"""
Unified Execution Engine
Single source of truth for all code execution (workflows, scripts, data providers)
"""

import logging
import sys
from contextlib import redirect_stdout, redirect_stderr
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from io import StringIO
from pathlib import Path
from typing import Any

from shared.context import Caller, ExecutionContext, Organization
from shared.error_handling import WorkflowError
from shared.models import ExecutionStatus
from shared.registry import FunctionMetadata, get_registry
from shared.repositories.execution_logs import get_execution_logs_repository

logger = logging.getLogger(__name__)

# Import bifrost context management for SDK support
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

try:
    from bifrost._context import set_execution_context, clear_execution_context
    BIFROST_CONTEXT_AVAILABLE = True
except ImportError:
    logger.warning(
        "Bifrost SDK not available - user workflows cannot use bifrost SDK")
    BIFROST_CONTEXT_AVAILABLE = False


# Simple in-memory cache for data provider results
_cache: dict[str, dict[str, Any]] = {}


@dataclass
class ExecutionRequest:
    """Request to execute code or registered function"""
    execution_id: str
    caller: Caller
    organization: Organization | None
    config: dict[str, Any]

    # EITHER inline code OR function name (mutually exclusive)
    code: str | None = None              # Base64 Python code
    name: str | None = None              # Registered function name

    # Parameters
    parameters: dict[str, Any] = field(default_factory=dict)

    # Flags
    transient: bool = False              # Don't write to DB
    no_cache: bool = False               # For data providers
    is_platform_admin: bool = False       # For platform admin executions

    # Real-time updates
    broadcaster: Any = None              # WebPubSubBroadcaster for streaming logs


@dataclass
class ExecutionResult:
    """Result of code/function execution"""
    execution_id: str
    status: ExecutionStatus
    result: Any
    duration_ms: int

    # Captured data
    logs: list[dict[str, Any]] = field(default_factory=list)
    variables: dict[str, Any] | None = None  # Only for inline scripts
    state_snapshots: list[dict[str, Any]] = field(default_factory=list)
    integration_calls: list[dict[str, Any]] = field(default_factory=list)

    # Error details
    error_message: str | None = None
    error_type: str | None = None

    # Data provider specific
    cached: bool = False
    cache_expires_at: str | None = None


async def execute(request: ExecutionRequest) -> ExecutionResult:
    """
    Unified execution engine for all code execution.

    Handles:
    - Inline Python scripts (request.code set)
    - Registered workflows (request.name set, has "workflow" tag)
    - Registered data providers (request.name set, has "data_provider" tag)

    Args:
        request: ExecutionRequest with execution details

    Returns:
        ExecutionResult with execution outcome

    Raises:
        ValueError: If neither code nor name provided, or if name not found
    """
    start_time = datetime.utcnow()

    # Resolve what we're executing
    metadata: FunctionMetadata | None = None
    func = None
    is_script = False

    if request.code and request.name:
        raise ValueError(
            "Cannot provide both code and name - they are mutually exclusive")

    if request.code:
        # Executing inline script
        is_script = True
        metadata = None
        func = None
    elif request.name:
        # Executing registered function
        registry = get_registry()
        metadata = registry.get_function(request.name)
        if not metadata:
            raise ValueError(
                f"Function '{request.name}' not found in registry")
        func = metadata.function
        is_script = False
    else:
        raise ValueError("Must provide either code or name")

    # Create execution context
    context = ExecutionContext(
        user_id=request.caller.user_id,
        email=request.caller.email,
        name=request.caller.name,
        scope=request.organization.id if request.organization else "GLOBAL",
        organization=request.organization,
        is_platform_admin=request.is_platform_admin,
        is_function_key=False,  # Engine executions are not function key based
        execution_id=request.execution_id,
        _config=request.config
    )

    # Set bifrost SDK context if available
    if BIFROST_CONTEXT_AVAILABLE:
        set_execution_context(context)
        logger.debug(
            f"Set bifrost execution context for execution {request.execution_id}")

    # Set up stdout/stderr capture
    # Python's logging writes to stderr by default, so we'll capture it naturally
    logger_output: list[dict[str, Any]] = []
    stdout_capture = StringIO()
    stderr_capture = StringIO()
    # For captured logging (scripts and workflows)
    captured_logs: list[str] = []

    try:
        with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
            # Check cache for data providers
            if metadata and "data_provider" in metadata.tags and not request.no_cache:
                cache_key = _compute_cache_key(
                    request.name or "",
                    request.parameters,
                    request.organization.id if request.organization else None
                )
                cached_result = _check_cache(cache_key)
                if cached_result:
                    return _build_cached_result(
                        request.execution_id,
                        cached_result,
                        start_time
                    )

            # Execute based on type
            if is_script:
                assert request.code is not None
                result, captured_variables, captured_logs = await _execute_script(
                    request.code,
                    context,
                    request.name or "script"
                )
            else:
                # Execute workflow/data provider
                assert func is not None

                # Always capture logs AND variables for all executions
                # Filtering based on permissions happens at API response level
                result, captured_variables, captured_logs = await _execute_workflow_with_trace(
                    func,
                    context,
                    request.parameters,
                    execution_id=request.execution_id,
                    broadcaster=request.broadcaster
                )

                # Cache if data provider
                if metadata and "data_provider" in metadata.tags:
                    cache_key = _compute_cache_key(
                        request.name or "",
                        request.parameters,
                        request.organization.id if request.organization else None
                    )
                    _cache_result(cache_key, result,
                                  metadata.cache_ttl_seconds)

        # Process captured logs (from scripts or workflows with platform admin)
        logger.info(
            f"Processing {len(captured_logs)} captured logs for execution {request.execution_id}")
        for log_line in captured_logs:
            # Parse format: [LEVEL] message
            level = 'info'
            message = log_line

            if log_line.startswith('[INFO]'):
                level = 'info'
                message = log_line[6:].strip()
            elif log_line.startswith('[WARNING]') or log_line.startswith('[WARN]'):
                level = 'warning'
                message = log_line[log_line.index(']')+1:].strip()
            elif log_line.startswith('[ERROR]'):
                level = 'error'
                message = log_line[7:].strip()
            elif log_line.startswith('[DEBUG]'):
                level = 'debug'
                message = log_line[7:].strip()

            logger_output.append({
                'timestamp': datetime.utcnow().isoformat(),
                'level': level,
                'message': message,
                'source': 'script' if is_script else 'workflow'
            })

        # Calculate duration
        end_time = datetime.utcnow()
        duration_ms = int((end_time - start_time).total_seconds() * 1000)

        # Determine execution status based on result
        # If result is a dict with success=false (explicitly false), mark as COMPLETED_WITH_ERRORS
        status = ExecutionStatus.SUCCESS
        if isinstance(result, dict) and result.get('success') is False:
            status = ExecutionStatus.COMPLETED_WITH_ERRORS

        return ExecutionResult(
            execution_id=request.execution_id,
            status=status,
            result=result,
            duration_ms=duration_ms,
            logs=logger_output,
            variables=captured_variables,
            state_snapshots=context._state_snapshots,
            integration_calls=context._integration_calls
        )

    except WorkflowError as e:
        # Expected workflow error
        end_time = datetime.utcnow()
        duration_ms = int((end_time - start_time).total_seconds() * 1000)

        return ExecutionResult(
            execution_id=request.execution_id,
            status=ExecutionStatus.FAILED,
            result=None,
            duration_ms=duration_ms,
            logs=logger_output,
            variables=None,
            state_snapshots=context._state_snapshots,
            integration_calls=context._integration_calls,
            error_message=str(e),
            error_type=type(e).__name__
        )

    except Exception as e:
        # Unexpected error
        end_time = datetime.utcnow()
        duration_ms = int((end_time - start_time).total_seconds() * 1000)

        logger.error(
            f"Execution error: {request.name or 'script'}",
            extra={
                "execution_id": request.execution_id,
                "error": str(e),
                "error_type": type(e).__name__
            },
            exc_info=True
        )

        return ExecutionResult(
            execution_id=request.execution_id,
            status=ExecutionStatus.FAILED,
            result=None,
            duration_ms=duration_ms,
            logs=logger_output,
            variables=None,
            state_snapshots=context._state_snapshots,
            integration_calls=context._integration_calls,
            error_message=str(e),
            error_type=type(e).__name__
        )

    finally:
        # Clear bifrost SDK context
        if BIFROST_CONTEXT_AVAILABLE:
            clear_execution_context()
            logger.debug(
                f"Cleared bifrost execution context for execution {request.execution_id}")


async def _execute_script(code: str, context: ExecutionContext, name: str) -> tuple[Any, dict[str, Any], list[str]]:
    """
    Execute inline Python script.

    Args:
        code: Base64-encoded Python code
        context: ExecutionContext
        name: Script name for logging

    Returns:
        Tuple of (result, captured_variables, logs)
    """
    import base64

    # Decode base64 code
    script_code = base64.b64decode(code).decode('utf-8')

    # Compile script
    compiled_code = compile(script_code, f'<script:{name}>', 'exec')

    # Set up logging capture for the script
    # We pre-configure logging.basicConfig so logging.info() etc work
    script_logs: list[str] = []

    class ScriptLogHandler(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            # Format: [LEVEL] message
            script_logs.append(f"[{record.levelname}] {record.getMessage()}")

    # Configure logging for scripts
    handler = ScriptLogHandler()
    handler.setLevel(logging.INFO)

    # Get or create a logger for this script
    script_logger = logging.getLogger('__main__')
    script_logger.addHandler(handler)
    script_logger.setLevel(logging.INFO)
    script_logger.propagate = False  # Don't propagate to root

    try:
        # Create execution namespace with bifrost SDK access
        exec_globals = {
            '__name__': '__main__',
            '__file__': f'<script:{name}>',
            'context': context,
            'logging': logging  # Provide logging module
        }

        # Execute script
        exec(compiled_code, exec_globals)

        # Capture all variables from script (exclude functions, modules, built-ins, loggers)
        captured_variables = {
            k: v for k, v in exec_globals.items()
            if not k.startswith('__')
            and not callable(v)
            and not isinstance(v, type(sys))
            and not isinstance(v, logging.Logger)
            and k not in ['context', 'logging']
        }

        # Script result is success unless exception thrown
        result = {"status": "completed",
                  "message": "Script executed successfully"}
        return result, captured_variables, script_logs
    finally:
        # Clean up the logger
        script_logger.removeHandler(handler)
        script_logger.setLevel(logging.NOTSET)


async def _execute_workflow_with_trace(
    func: Any,
    context: ExecutionContext,
    parameters: dict[str, Any],
    execution_id: str | None = None,
    broadcaster: Any = None
) -> tuple[Any, dict[str, Any], list[str]]:
    """
    Execute a workflow function with variable capture using sys.settrace().

    This is the same approach used for scripts, ensuring consistency.
    Captures all local variables from the function as it executes.
    Streams logs in real-time via SignalR if broadcaster is provided.

    Args:
        func: Workflow function to execute
        context: ExecutionContext
        parameters: Function parameters
        execution_id: Execution ID for Web PubSub broadcasts
        broadcaster: WebPubSubBroadcaster for real-time log streaming

    Returns:
        Tuple of (result, captured_variables, logs)
    """
    captured_vars: dict[str, Any] = {}
    workflow_logs: list[str] = []
    func_name = func.__name__
    log_buffer: list[dict[str, Any]] = []  # Buffer for SignalR broadcasts

    # Get the workflow's module file path for filtering
    workflow_module_file = func.__code__.co_filename

    # Set up logging capture for the workflow
    class WorkflowLogHandler(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            # Only capture logs that originate from the workflow's file or workspace
            # This prevents capturing Azure SDK, aiohttp, and infrastructure logs
            # Use basename comparison since dynamically loaded modules may have different path formats
            import os
            workflow_basename = os.path.basename(workflow_module_file)
            record_basename = os.path.basename(record.pathname)

            # Also check if it's from workspace directory (for user workflows)
            is_workspace_log = 'workspace' in record.pathname or '/repo/' in record.pathname
            is_workflow_file = record_basename == workflow_basename

            # Don't log from inside the handler to avoid infinite recursion
            # Just filter and process

            if not (is_workflow_file or is_workspace_log):
                return

            # Format: [LEVEL] message
            log_entry = f"[{record.levelname}] {record.getMessage()}"
            workflow_logs.append(log_entry)

            # Real-time log processing (if broadcaster enabled)
            if broadcaster and execution_id:
                import uuid
                log_id = str(uuid.uuid4())
                timestamp = datetime.utcnow().isoformat() + "Z"

                log_dict = {
                    "executionLogId": log_id,
                    "level": record.levelname,
                    "message": record.getMessage(),
                    "timestamp": timestamp
                }
                log_buffer.append(log_dict)

                # Persist and broadcast immediately - direct synchronous calls
                # This ensures real-time log streaming (not buffered until end)
                try:
                    logs_repo = get_execution_logs_repository()

                    # Direct synchronous calls - no async/await
                    # Synchronous execution is critical for real-time streaming
                    logs_repo.append_log(
                        execution_id=execution_id,
                        level=record.levelname,
                        message=record.getMessage(),
                        source="workflow"
                    )

                    broadcaster.broadcast_execution_update(
                        execution_id=execution_id,
                        status="Running",
                        executed_by=context.user_id,
                        scope=context.org_id or "GLOBAL",
                        latest_logs=[log_dict],
                        is_complete=False
                    )
                except Exception as e:
                    # Log errors but don't fail workflow execution
                    # Real-time updates are non-critical
                    logger.error(
                        f"Failed to persist/broadcast log (non-fatal): {str(e)}",
                        exc_info=True,
                        extra={"execution_id": execution_id}
                    )

    # Configure logging for workflows
    handler = WorkflowLogHandler()
    handler.setLevel(logging.DEBUG)  # Capture all levels

    # Attach to root logger since workflows use logging.info() which goes to root
    root_logger = logging.getLogger()
    root_logger.addHandler(handler)

    def remove_circular_refs(obj, seen=None):
        """
        Remove circular references from objects to make them JSON serializable.

        Recursively walks through dicts/lists/tuples and replaces circular references
        with a string marker. Non-serializable objects are converted to string repr.
        """
        if seen is None:
            seen = set()

        obj_id = id(obj)
        if obj_id in seen:
            return "[Circular Reference]"

        seen = seen.copy()  # Copy seen set for this branch
        seen.add(obj_id)

        try:
            if isinstance(obj, dict):
                return {k: remove_circular_refs(v, seen) for k, v in obj.items()}
            elif isinstance(obj, (list, tuple)):
                cleaned = [remove_circular_refs(item, seen) for item in obj]
                return cleaned if isinstance(obj, list) else tuple(cleaned)
            elif isinstance(obj, set):
                return [remove_circular_refs(item, seen) for item in obj]
            else:
                # Test if primitive type is JSON serializable
                import json
                json.dumps(obj)
                return obj
        except (TypeError, ValueError):
            # Not serializable - return type name
            return f"<{type(obj).__name__}>"

    # Wrapper to capture local variables after execution using sys.settrace briefly
    async def execute_and_capture():
        import inspect

        # Track if we've entered the workflow function
        entered_workflow = [False]

        # Minimal trace function that only captures on workflow return
        def trace_workflow(frame, event, arg):
            # Check if we're entering the workflow function
            if event == 'call' and frame.f_code.co_name == func_name:
                entered_workflow[0] = True
                return trace_workflow  # Continue tracing this function

            # If we're in the workflow and it's returning, capture variables
            if entered_workflow[0] and event == 'return' and frame.f_code.co_name == func_name:
                # Capture variables from the workflow frame at return time
                param_names = set(parameters.keys()) | {'context', 'self'}

                for k, v in frame.f_locals.items():
                    # Skip parameters, private vars, callables, and modules
                    if (not k.startswith('_')
                        and k not in param_names
                        and not callable(v)
                        and not isinstance(v, type(sys))):
                        # Remove circular references to make JSON serializable
                        cleaned_value = remove_circular_refs(v)
                        captured_vars[k] = cleaned_value

            return trace_workflow  # Keep tracing active

        # Enable trace only for the workflow execution
        old_trace = sys.gettrace()
        sys.settrace(trace_workflow)

        try:
            result = await func(context, **parameters)
            return result
        finally:
            sys.settrace(old_trace)

    try:
        result = await execute_and_capture()
        return result, captured_vars, workflow_logs
    finally:
        # Clean up the logging handler
        root_logger.removeHandler(handler)


def _compute_cache_key(name: str, parameters: dict[str, Any], org_id: str | None) -> str:
    """
    Compute cache key for data provider.

    Args:
        name: Function name
        parameters: Input parameters
        org_id: Organization ID (optional)

    Returns:
        Cache key string
    """
    import hashlib
    import json

    if not parameters:
        return f"{org_id}:{name}" if org_id else name

    # Sort keys for deterministic hash
    param_str = json.dumps(parameters, sort_keys=True)
    param_hash = hashlib.sha256(param_str.encode()).hexdigest()[:16]

    if org_id:
        return f"{org_id}:{name}:{param_hash}"
    else:
        return f"{name}:{param_hash}"


def _check_cache(cache_key: str) -> Any | None:
    """
    Check if cached result exists and is still valid.

    Args:
        cache_key: Cache key to check

    Returns:
        Cached result if valid, None otherwise
    """
    if cache_key not in _cache:
        return None

    cached_entry = _cache[cache_key]
    expires_at = cached_entry['expires_at']

    # Check if cache is still valid
    if datetime.utcnow() < expires_at:
        logger.info(f"Cache hit for key: {cache_key}")
        return cached_entry
    else:
        # Cache expired, remove it
        del _cache[cache_key]
        return None


def _cache_result(cache_key: str, result: Any, ttl_seconds: int) -> None:
    """
    Cache execution result.

    Args:
        cache_key: Cache key
        result: Result to cache
        ttl_seconds: Time to live in seconds
    """
    expires_at = datetime.utcnow() + timedelta(seconds=ttl_seconds)
    _cache[cache_key] = {
        'data': result,
        'expires_at': expires_at
    }
    logger.info(f"Cached result for key: {cache_key} (TTL: {ttl_seconds}s)")


def _build_cached_result(
    execution_id: str,
    cached_entry: dict[str, Any],
    start_time: datetime
) -> ExecutionResult:
    """
    Build ExecutionResult from cached data provider result.

    Args:
        execution_id: Execution ID
        cached_entry: Cached entry with data and expires_at
        start_time: Execution start time

    Returns:
        ExecutionResult with cached data
    """
    end_time = datetime.utcnow()
    duration_ms = int((end_time - start_time).total_seconds() * 1000)

    return ExecutionResult(
        execution_id=execution_id,
        status=ExecutionStatus.SUCCESS,
        result=cached_entry['data'],
        duration_ms=duration_ms,
        logs=[],
        variables=None,
        state_snapshots=[],
        integration_calls=[],
        cached=True,
        cache_expires_at=cached_entry['expires_at'].isoformat() + "Z"
    )
