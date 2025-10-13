"""
Authentication helpers for Azure Static Web Apps + Azure Functions
Works in both production (Azure Easy Auth) and local development (mock)
"""

import os
import logging
import base64
import json
from typing import Optional, Dict, Any
from functools import wraps
import azure.functions as func

logger = logging.getLogger(__name__)


class AuthenticatedUser:
    """Represents an authenticated user from Azure AD"""

    def __init__(self, user_id: str, email: str, display_name: str = None):
        self.user_id = user_id
        self.email = email
        self.display_name = display_name or email.split('@')[0]

    def to_dict(self) -> Dict[str, str]:
        return {
            "user_id": self.user_id,
            "email": self.email,
            "display_name": self.display_name
        }


def get_authenticated_user(req: func.HttpRequest) -> Optional[AuthenticatedUser]:
    """
    Extract authenticated user from Azure Static Web Apps headers

    Works in both production and local development:
    - Production: Azure SWA injects X-MS-CLIENT-PRINCIPAL-* headers
    - Local dev: Accepts X-Test-User-* headers for testing

    Args:
        req: Azure Functions HttpRequest

    Returns:
        AuthenticatedUser if authenticated, None otherwise
    """

    # Production: Check for Azure SWA headers
    client_principal_id = req.headers.get("X-MS-CLIENT-PRINCIPAL-ID")
    client_principal_name = req.headers.get("X-MS-CLIENT-PRINCIPAL-NAME")

    if client_principal_id and client_principal_name:
        # Parse full principal if available (contains display name)
        client_principal_b64 = req.headers.get("X-MS-CLIENT-PRINCIPAL")
        display_name = None

        if client_principal_b64:
            try:
                principal_json = base64.b64decode(client_principal_b64).decode('utf-8')
                principal = json.loads(principal_json)
                display_name = principal.get("claims", {}).get("name")
            except Exception as e:
                logger.warning(f"Failed to parse X-MS-CLIENT-PRINCIPAL: {e}")

        logger.info(f"Authenticated user from Azure SWA: {client_principal_name}")
        return AuthenticatedUser(
            user_id=client_principal_id,
            email=client_principal_name,
            display_name=display_name
        )

    # Local development: Check for test headers
    is_local = os.getenv("AZURE_FUNCTIONS_ENVIRONMENT") == "Development"
    if is_local:
        test_user_id = req.headers.get("X-Test-User-Id")
        test_email = req.headers.get("X-Test-User-Email")
        test_name = req.headers.get("X-Test-User-Name")

        if test_user_id or test_email or test_name:
            logger.info(f"Authenticated test user (local dev): {test_email or 'jack@gocovi.com'}")
            return AuthenticatedUser(
                user_id=test_user_id or "jack@gocovi.com",  # Default to platform admin email
                email=test_email or "jack@gocovi.com",
                display_name=test_name or "Jack Musick"
            )

        # Default test user for local development (platform admin)
        logger.info("Using default test user for local development (platform admin)")
        return AuthenticatedUser(
            user_id="jack@gocovi.com",  # Using email as user ID for consistency
            email="jack@gocovi.com",
            display_name="Jack Musick"
        )

    # No authentication found
    logger.warning("No authentication headers found in request")
    return None


def require_auth(func_to_wrap):
    """
    Decorator to require authentication on Azure Function endpoints

    Usage:
        @require_auth
        async def my_function(req: func.HttpRequest) -> func.HttpResponse:
            user = req.user  # AuthenticatedUser object
            return func.HttpResponse(f"Hello {user.display_name}")
    """
    import asyncio
    import inspect

    @wraps(func_to_wrap)
    async def async_wrapper(req: func.HttpRequest) -> func.HttpResponse:
        user = get_authenticated_user(req)

        if not user:
            logger.warning(f"Unauthorized request to {req.url}")
            return func.HttpResponse(
                json.dumps({
                    "error": "Unauthorized",
                    "message": "Authentication required. Please login."
                }),
                status_code=401,
                mimetype="application/json"
            )

        # Inject user into request for downstream use
        req.user = user

        # Call the actual function
        return await func_to_wrap(req)

    @wraps(func_to_wrap)
    def sync_wrapper(req: func.HttpRequest) -> func.HttpResponse:
        user = get_authenticated_user(req)

        if not user:
            logger.warning(f"Unauthorized request to {req.url}")
            return func.HttpResponse(
                json.dumps({
                    "error": "Unauthorized",
                    "message": "Authentication required. Please login."
                }),
                status_code=401,
                mimetype="application/json"
            )

        # Inject user into request for downstream use
        req.user = user

        # Call the actual function
        return func_to_wrap(req)

    # Return async wrapper if function is async, otherwise sync wrapper
    if inspect.iscoroutinefunction(func_to_wrap):
        return async_wrapper
    else:
        return sync_wrapper


def is_platform_admin(user_id: str) -> bool:
    """
    Check if a user is a platform admin by looking up their record

    Args:
        user_id: User ID

    Returns:
        True if user is platform admin, False otherwise
    """
    from shared.storage import TableStorageService

    try:
        users_service = TableStorageService("Users")
        user_entity = users_service.get_entity("USER", user_id)

        if user_entity:
            return user_entity.get("IsPlatformAdmin", False) and user_entity.get("UserType") == "PLATFORM"

        return False
    except Exception as e:
        logger.warning(f"Failed to check platform admin status for {user_id}: {e}")
        return False


def has_form_access(user_id: str, form_id: str) -> bool:
    """
    Check if a user has access to execute a specific form

    Access is granted if:
    1. User is a platform admin, OR
    2. Form is public (isPublic=true), OR
    3. User is in a group that has been assigned to the form

    Args:
        user_id: User ID
        form_id: Form ID

    Returns:
        True if user can access the form, False otherwise
    """
    from shared.storage import TableStorageService

    try:
        # Check if user is platform admin (bypass all checks)
        if is_platform_admin(user_id):
            logger.debug(f"User {user_id} is platform admin - granting form access")
            return True

        # Get form to check if it's public
        forms_service = TableStorageService("Forms")
        # Try to find form in any partition (we don't know the partition key here)
        # This is a limitation - we'll need to query by form ID
        form_entities = list(forms_service.query_entities(filter=f"RowKey eq '{form_id}'"))

        if not form_entities:
            logger.warning(f"Form {form_id} not found")
            return False

        form_entity = form_entities[0]

        # Check if form is public
        if form_entity.get("IsPublic", False):
            logger.debug(f"Form {form_id} is public - granting access")
            return True

        # Check if user is in any group assigned to this form
        # 1. Get user's groups from UserRoles table
        user_roles_service = TableStorageService("UserRoles")
        user_role_entities = list(user_roles_service.query_entities(
            filter=f"UserId eq '{user_id}'"
        ))

        if not user_role_entities:
            logger.debug(f"User {user_id} has no group assignments")
            return False

        user_group_ids = [entity["RoleId"] for entity in user_role_entities]
        logger.debug(f"User {user_id} is in groups: {user_group_ids}")

        # 2. Check if form is assigned to any of these groups via FormRoles table
        form_roles_service = TableStorageService("FormRoles")
        for group_id in user_group_ids:
            form_role_entity = form_roles_service.get_entity(form_id, f"role:{group_id}")
            if form_role_entity:
                logger.debug(f"User {user_id} has access to form {form_id} via group {group_id}")
                return True

        logger.debug(f"User {user_id} has no group-based access to form {form_id}")
        return False

    except Exception as e:
        logger.error(f"Error checking form access for user {user_id}, form {form_id}: {e}", exc_info=True)
        return False


def get_org_id(req: func.HttpRequest) -> Optional[str]:
    """
    Extract organization ID from X-Organization-Id header

    Args:
        req: Azure Functions HttpRequest

    Returns:
        Organization ID if present, None otherwise
    """
    org_id = req.headers.get("X-Organization-Id")

    if not org_id:
        logger.debug("No X-Organization-Id header found in request")

    return org_id


def require_org_header(func_to_wrap):
    """
    Decorator to require X-Organization-Id header
    Must be used AFTER @require_auth

    Usage:
        @require_auth
        @require_org_header
        async def my_function(req: func.HttpRequest) -> func.HttpResponse:
            user = req.user
            org_id = req.org_id
            return func.HttpResponse(f"User {user.email} accessing org {org_id}")
    """
    import inspect

    @wraps(func_to_wrap)
    async def async_wrapper(req: func.HttpRequest) -> func.HttpResponse:
        org_id = get_org_id(req)

        if not org_id:
            logger.warning(f"Missing X-Organization-Id header on {req.url}")
            return func.HttpResponse(
                json.dumps({
                    "error": "BadRequest",
                    "message": "X-Organization-Id header is required"
                }),
                status_code=400,
                mimetype="application/json"
            )

        # Inject org_id into request
        req.org_id = org_id

        return await func_to_wrap(req)

    @wraps(func_to_wrap)
    def sync_wrapper(req: func.HttpRequest) -> func.HttpResponse:
        org_id = get_org_id(req)

        if not org_id:
            logger.warning(f"Missing X-Organization-Id header on {req.url}")
            return func.HttpResponse(
                json.dumps({
                    "error": "BadRequest",
                    "message": "X-Organization-Id header is required"
                }),
                status_code=400,
                mimetype="application/json"
            )

        # Inject org_id into request
        req.org_id = org_id

        return func_to_wrap(req)

    # Return async wrapper if function is async, otherwise sync wrapper
    if inspect.iscoroutinefunction(func_to_wrap):
        return async_wrapper
    else:
        return sync_wrapper
