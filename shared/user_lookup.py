"""
User Lookup - Pure business logic for user existence and organization lookup

This module contains pure business logic that can be unit tested with mocked repositories.
It's separated from request_context.py (which handles HTTP concerns).
"""

import logging
from datetime import datetime, timedelta

from shared.models import User, UserType
from shared.repositories.users import UserRepository

logger = logging.getLogger(__name__)

# In-memory cache for user lookups to reduce database calls
# Cache key: email, Value: (User, timestamp)
_user_cache: dict[str, tuple[User, datetime]] = {}
# Cache key: email, Value: (org_id | None, timestamp)
_org_cache: dict[str, tuple[str | None, datetime]] = {}
_cache_ttl = timedelta(seconds=30)  # Cache user lookups for 30 seconds


def _get_cached_user(email: str) -> User | None:
    """
    Get user from cache if present and not expired.

    Args:
        email: User email

    Returns:
        Cached User model or None if not cached or expired
    """
    if email in _user_cache:
        user, cached_at = _user_cache[email]
        age = datetime.utcnow() - cached_at

        if age < _cache_ttl:
            logger.debug(f"User cache hit for {email} (age: {age.total_seconds():.1f}s)")
            return user
        else:
            # Expired - remove from cache
            del _user_cache[email]
            logger.debug(f"User cache expired for {email}")

    return None


def _cache_user(email: str, user: User) -> None:
    """
    Cache user model with current timestamp.

    Args:
        email: User email
        user: User model to cache
    """
    _user_cache[email] = (user, datetime.utcnow())
    logger.debug(f"Cached user {email}")


def ensure_user_exists_in_db(email: str, is_platform_admin: bool) -> None:
    """
    Ensure user exists in Users table, creating if necessary.

    This is pure business logic - takes email and admin status, ensures user record exists.
    Used by request_context during authentication to handle development scenarios
    where GetRoles endpoint isn't called (e.g., local dev with direct headers).

    Uses in-memory cache to reduce database calls for repeated requests from the same user.

    Args:
        email: User's email address
        is_platform_admin: Whether user has PlatformAdmin role (from SWA/GetRoles)

    Note:
        The user's role (PlatformAdmin vs OrgUser) comes from SWA/GetRoles,
        so we trust that as the source of truth.
    """
    # Check cache first
    cached_user = _get_cached_user(email)
    if cached_user:
        # User exists in cache - no need to hit database
        # We don't update last_login on every request anymore (too chatty)
        return

    user_repo = UserRepository()

    # Check if user exists in database
    user = user_repo.get_user(email)

    if user:
        # User exists - cache it
        _cache_user(email, user)

        # Update last login only once per cache TTL (30 seconds)
        # This reduces database calls from every request to once per 30s
        try:
            user_repo.update_last_login(email)
        except Exception as e:
            logger.warning(f"Failed to update last login for {email}: {e}")
        return

    # User doesn't exist - create based on their role
    logger.info(f"Auto-creating user {email} (PlatformAdmin={is_platform_admin})")

    user_type = UserType.PLATFORM if is_platform_admin else UserType.ORG
    user = user_repo.create_user(
        email=email,
        display_name=email.split("@")[0],
        user_type=user_type,
        is_platform_admin=is_platform_admin
    )

    # Cache the newly created user
    _cache_user(email, user)

    logger.info(f"Created user {email} in database")

    # If ORG user, try to auto-provision org relationship by domain
    if not is_platform_admin:
        try:
            from shared.user_provisioning import _provision_org_relationship_by_domain
            org_id = _provision_org_relationship_by_domain(email)
            if org_id:
                logger.info(f"Auto-provisioned org relationship for {email} -> {org_id}")
        except ValueError as e:
            logger.warning(f"Could not auto-provision org relationship: {e}")
            # Don't raise - user will get proper error when we try to get org_id


def get_user_organization(email: str) -> str | None:
    """
    Look up user's organization ID from database.

    Pure business logic - takes email, queries repository, returns org_id or None.
    Uses in-memory cache to reduce database calls.

    Args:
        email: User's email address

    Returns:
        Organization ID if user has org assignment, None otherwise
    """
    # Check cache first
    if email in _org_cache:
        org_id, cached_at = _org_cache[email]
        age = datetime.utcnow() - cached_at

        if age < _cache_ttl:
            logger.debug(f"Org cache hit for {email}: {org_id} (age: {age.total_seconds():.1f}s)")
            return org_id
        else:
            # Expired - remove from cache
            del _org_cache[email]
            logger.debug(f"Org cache expired for {email}")

    try:
        user_repo = UserRepository()
        org_id = user_repo.get_user_org_id(email)

        # Cache the result (even if None)
        _org_cache[email] = (org_id, datetime.utcnow())

        if org_id:
            logger.debug(f"User {email} belongs to org: {org_id}")
        else:
            logger.warning(f"User {email} has no org assignments")

        return org_id

    except Exception as e:
        logger.error(f"Error looking up user org: {e}")
        return None
