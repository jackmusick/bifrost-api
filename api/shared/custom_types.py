"""
Type definitions for HTTP requests with custom extensions
"""

from typing import TYPE_CHECKING, Any, Protocol, Union, cast

import azure.functions as func

if TYPE_CHECKING:
    from shared.auth import FunctionKeyPrincipal, UserPrincipal
    from shared.context import ExecutionContext


class HttpRequestWithContext(Protocol):
    """
    Extended HttpRequest with injected context attribute.

    Used by @with_request_context decorator to inject ExecutionContext.
    """
    context: "ExecutionContext"

    # Standard HttpRequest attributes
    method: str
    url: str
    headers: dict
    params: dict
    route_params: dict

    def get_body(self) -> bytes: ...
    def get_json(self) -> dict: ...


def get_context(req: func.HttpRequest) -> "ExecutionContext":
    """
    Type-safe helper to extract ExecutionContext from HttpRequest.

    Usage:
        @with_request_context
        async def handler(req: func.HttpRequest):
            context = get_context(req)
            # context is now properly typed as ExecutionContext
    """
    req_with_context = cast(HttpRequestWithContext, req)
    return req_with_context.context


def get_route_param(req: func.HttpRequest, param_name: str) -> str:
    """
    Type-safe helper to extract required route parameter from HttpRequest.

    Raises ValueError if parameter is missing.

    Usage:
        connection_name = get_route_param(req, "connection_name")
        # connection_name is guaranteed to be str (not None)
    """
    value = req.route_params.get(param_name)
    if value is None:
        raise ValueError(f"Missing required route parameter: {param_name}")
    return value


def get_org_context(req: func.HttpRequest) -> Any:
    """
    Type-safe helper to extract ExecutionContext from HttpRequest.

    Usage:
        @with_org_context
        async def handler(req: func.HttpRequest):
            context = get_org_context(req)
            # context is now properly typed as ExecutionContext
    """
    req_with_context = cast(HttpRequestWithOrgContext, req)
    return req_with_context.org_context


class HttpRequestWithPrincipal(Protocol):
    """
    Extended HttpRequest with injected principal attribute.

    Used by @require_auth decorator to inject UserPrincipal or FunctionKeyPrincipal.
    """
    principal: Union["UserPrincipal", "FunctionKeyPrincipal"]

    # Standard HttpRequest attributes
    method: str
    url: str
    headers: dict
    params: dict
    route_params: dict

    def get_body(self) -> bytes: ...
    def get_json(self) -> dict: ...


class HttpRequestWithUser(Protocol):
    """
    Extended HttpRequest with injected user attribute (legacy pattern).

    Used by old @require_auth decorator.
    """
    user: "UserPrincipal"

    # Standard HttpRequest attributes
    method: str
    url: str
    headers: dict
    params: dict
    route_params: dict

    def get_body(self) -> bytes: ...
    def get_json(self) -> dict: ...


class HttpRequestWithOrgContext(Protocol):
    """
    Extended HttpRequest with injected org_context attribute.

    Used by @with_org_context decorator to inject ExecutionContext.
    """
    org_context: "Any"  # ExecutionContext from shared.auth

    # Standard HttpRequest attributes
    method: str
    url: str
    headers: dict
    params: dict
    route_params: dict

    def get_body(self) -> bytes: ...
    def get_json(self) -> dict: ...
