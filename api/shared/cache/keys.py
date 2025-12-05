"""
Redis key generation functions for Bifrost cache.

All Redis keys follow the pattern: bifrost:{scope}:{entity}:{id}
Where scope is either "global" or "org:{org_uuid}"

These functions are the SINGLE SOURCE OF TRUTH for key generation.
Used by both SDK (reads) and API routes (invalidation).
"""

from __future__ import annotations


def _get_scope(org_id: str | None) -> str:
    """Get the scope prefix for a key."""
    if org_id and org_id != "GLOBAL":
        return f"org:{org_id}"
    return "global"


# =============================================================================
# Config Keys
# =============================================================================


def config_hash_key(org_id: str | None) -> str:
    """
    Key for the hash containing all config values for an org.

    Structure: HASH where field = config key, value = JSON config data
    """
    scope = _get_scope(org_id)
    return f"bifrost:{scope}:config"


def config_key(org_id: str | None, key: str) -> str:
    """
    Key for an individual config value (used for targeted invalidation).

    Note: We primarily use the hash (config_hash_key), but this is useful
    for invalidating specific keys.
    """
    scope = _get_scope(org_id)
    return f"bifrost:{scope}:config:{key}"


# =============================================================================
# OAuth Keys
# =============================================================================


def oauth_hash_key(org_id: str | None) -> str:
    """
    Key for the hash containing all OAuth providers for an org.

    Structure: HASH where field = provider name, value = JSON provider data
    """
    scope = _get_scope(org_id)
    return f"bifrost:{scope}:oauth"


def oauth_provider_key(org_id: str | None, provider: str) -> str:
    """Key for a specific OAuth provider (for targeted invalidation)."""
    scope = _get_scope(org_id)
    return f"bifrost:{scope}:oauth:{provider}"


# =============================================================================
# Form Keys
# =============================================================================


def forms_hash_key(org_id: str | None) -> str:
    """
    Key for the hash containing all forms for an org.

    Structure: HASH where field = form_id, value = JSON form data
    """
    scope = _get_scope(org_id)
    return f"bifrost:{scope}:forms"


def form_key(org_id: str | None, form_id: str) -> str:
    """Key for a specific form (for targeted invalidation)."""
    scope = _get_scope(org_id)
    return f"bifrost:{scope}:forms:{form_id}"


def user_forms_key(org_id: str | None, user_id: str) -> str:
    """
    Key for the set of form IDs accessible by a specific user.

    Structure: SET of form UUIDs
    """
    scope = _get_scope(org_id)
    return f"bifrost:{scope}:user_forms:{user_id}"


# =============================================================================
# Role Keys
# =============================================================================


def roles_hash_key(org_id: str | None) -> str:
    """
    Key for the hash containing all roles for an org.

    Structure: HASH where field = role_id, value = JSON role data
    """
    scope = _get_scope(org_id)
    return f"bifrost:{scope}:roles"


def role_key(org_id: str | None, role_id: str) -> str:
    """Key for a specific role (for targeted invalidation)."""
    scope = _get_scope(org_id)
    return f"bifrost:{scope}:roles:{role_id}"


def role_users_key(org_id: str | None, role_id: str) -> str:
    """
    Key for the set of user IDs assigned to a role.

    Structure: SET of user UUIDs
    """
    scope = _get_scope(org_id)
    return f"bifrost:{scope}:roles:{role_id}:users"


def role_forms_key(org_id: str | None, role_id: str) -> str:
    """
    Key for the set of form IDs assigned to a role.

    Structure: SET of form UUIDs
    """
    scope = _get_scope(org_id)
    return f"bifrost:{scope}:roles:{role_id}:forms"


# =============================================================================
# Organization Keys
# =============================================================================


def org_key(org_id: str) -> str:
    """Key for a specific organization."""
    return f"bifrost:global:orgs:{org_id}"


def orgs_list_key() -> str:
    """Key for the list of all organizations."""
    return "bifrost:global:orgs:_list"


# =============================================================================
# Execution-Scoped Keys (Write Buffer)
# =============================================================================


def pending_changes_key(execution_id: str) -> str:
    """
    Key for the hash containing pending changes for an execution.

    Structure: HASH where field = change identifier, value = JSON change record
    Used by write buffer, cleared after flush.
    """
    return f"bifrost:pending:{execution_id}"


def execution_logs_stream_key(execution_id: str) -> str:
    """
    Key for the Redis Stream containing logs for an execution.

    Structure: STREAM with log entries
    """
    return f"bifrost:logs:{execution_id}"


# =============================================================================
# TTL Constants
# =============================================================================


# TTLs in seconds
TTL_CONFIG = 300  # 5 minutes
TTL_OAUTH = 60  # 1 minute (tokens can be refreshed)
TTL_FORMS = 600  # 10 minutes
TTL_ROLES = 600  # 10 minutes
TTL_ORGS = 3600  # 1 hour
TTL_PENDING = 3600  # 1 hour (safety for orphaned changes)
