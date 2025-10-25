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

logger = logging.getLogger(__name__)

# Import bifrost context management for SDK support
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

try:
    from bifrost._context import set_execution_context, clear_execution_context
    BIFROST_CONTEXT_AVAILABLE = True
except ImportError:
    logger.warning("Bifrost SDK not available - user workflows cannot use bifrost SDK")
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
        raise ValueError("Cannot provide both code and name - they are mutually exclusive")

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
            raise ValueError(f"Function '{request.name}' not found in registry")
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
        logger.debug(f"Set bifrost execution context for execution {request.execution_id}")

    # Set up stdout/stderr capture
    # Python's logging writes to stderr by default, so we'll capture it naturally
    logger_output: list[dict[str, Any]] = []
    stdout_capture = StringIO()
    stderr_capture = StringIO()
    captured_logs: list[str] = []  # For captured logging (scripts and workflows)

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

                # For platform admins, use sys.settrace() to capture variables and logs
                # For regular users, execute function directly (no variable/log capture)
                if context.is_platform_admin:
                    result, captured_variables, captured_logs = await _execute_workflow_with_trace(
                        func,
                        context,
                        request.parameters
                    )
                else:
                    result = await func(context, **request.parameters)
                    captured_variables = None

                # Cache if data provider
                if metadata and "data_provider" in metadata.tags:
                    cache_key = _compute_cache_key(
                        request.name or "",
                        request.parameters,
                        request.organization.id if request.organization else None
                    )
                    _cache_result(cache_key, result, metadata.cache_ttl_seconds)

        # Process captured logs (from scripts or workflows with platform admin)
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
            logger.debug(f"Cleared bifrost execution context for execution {request.execution_id}")


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
        result = {"status": "completed", "message": "Script executed successfully"}
        return result, captured_variables, script_logs
    finally:
        # Clean up the logger
        script_logger.removeHandler(handler)
        script_logger.setLevel(logging.NOTSET)


async def _execute_workflow_with_trace(
    func: Any,
    context: ExecutionContext,
    parameters: dict[str, Any]
) -> tuple[Any, dict[str, Any], list[str]]:
    """
    Execute a workflow function with variable capture using sys.settrace().

    This is the same approach used for scripts, ensuring consistency.
    Captures all local variables from the function as it executes.

    Only used for platform admins to enable variable capture.

    Args:
        func: Workflow function to execute
        context: ExecutionContext
        parameters: Function parameters

    Returns:
        Tuple of (result, captured_variables, logs)
    """
    captured_vars: dict[str, Any] = {}
    workflow_logs: list[str] = []
    func_name = func.__name__

    # Set up logging capture for the workflow
    class WorkflowLogHandler(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            # Format: [LEVEL] message
            workflow_logs.append(f"[{record.levelname}] {record.getMessage()}")

    # Configure logging for workflows
    handler = WorkflowLogHandler()
    handler.setLevel(logging.DEBUG)  # Capture all levels

    # Attach to root logger (workflows use logging.info(), etc.)
    root_logger = logging.getLogger()
    root_logger.addHandler(handler)

    def trace_calls(frame, event, arg):
        # Track when we enter the workflow function
        if event == 'call' and frame.f_code.co_name == func_name:
            return trace_lines
        return trace_calls

    def trace_lines(frame, event, arg):
        # Capture variables on every line execution within the function
        if event == 'line' or event == 'return':
            # Skip parameter names and internal variables
            param_names = set(parameters.keys()) | {'context', 'self'}
            for k, v in frame.f_locals.items():
                if (not k.startswith('_')
                    and k not in param_names
                    and not callable(v)
                    and not isinstance(v, type(sys))):
                    try:
                        # Only capture JSON-serializable values
                        import json
                        json.dumps(v)
                        captured_vars[k] = v
                    except (TypeError, ValueError):
                        pass
        return trace_lines

    old_trace = sys.gettrace()
    sys.settrace(trace_calls)

    try:
        # Execute the workflow function
        result = await func(context, **parameters)
        return result, captured_vars, workflow_logs
    finally:
        sys.settrace(old_trace)
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
