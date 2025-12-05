"""
OAuth SDK for Bifrost.

Provides Python API for OAuth token retrieval.

All methods are synchronous and can be called directly (no await needed).
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from cryptography.fernet import Fernet
from sqlalchemy import select, or_

from src.models.orm import OAuthProvider, OAuthToken

from ._db import get_sync_session
from ._internal import get_context

logger = logging.getLogger(__name__)


def _get_encryption_key() -> bytes:
    """Get encryption key from settings."""
    from src.config import get_settings
    import base64
    settings = get_settings()
    key_bytes = settings.secret_key.encode()[:32].ljust(32, b'0')
    return base64.urlsafe_b64encode(key_bytes)


def _decrypt(value: bytes) -> str:
    """Decrypt bytes to string."""
    f = Fernet(_get_encryption_key())
    return f.decrypt(value).decode()


class oauth:
    """
    OAuth token management operations.

    Allows workflows to retrieve OAuth tokens for external integrations.

    All methods are synchronous - no await needed.
    """

    @staticmethod
    def get(provider: str, org_id: str | None = None) -> dict[str, Any] | None:
        """
        Get OAuth connection configuration and tokens for a provider.

        Returns the full OAuth configuration including decrypted credentials
        and tokens needed for API calls or custom token operations.

        Args:
            provider: OAuth provider/connection name (e.g., "microsoft", "partner_center")
            org_id: Organization ID (defaults to current org from context)

        Returns:
            dict | None: OAuth connection config with keys:
                - connection_name: str
                - client_id: str
                - client_secret: str (decrypted)
                - authorization_url: str | None
                - token_url: str | None
                - scopes: list[str]
                - access_token: str | None (decrypted, if available)
                - refresh_token: str | None (decrypted, if available)
                - expires_at: str | None (ISO format, if available)
            Returns None if connection not found.

        Raises:
            RuntimeError: If no execution context

        Example:
            >>> from bifrost import oauth
            >>> conn = oauth.get("partner_center")
            >>> if conn:
            ...     client_id = conn["client_id"]
            ...     client_secret = conn["client_secret"]
            ...     refresh_token = conn["refresh_token"]
        """
        context = get_context()
        target_org = org_id or getattr(context, 'org_id', None) or getattr(context, 'scope', None)

        org_uuid = None
        if target_org and target_org != "GLOBAL":
            try:
                org_uuid = UUID(target_org)
            except ValueError:
                pass

        with get_sync_session() as db:
            # Get OAuth provider with org→GLOBAL fallback
            if org_uuid:
                query = (
                    select(OAuthProvider)
                    .where(OAuthProvider.provider_name == provider)
                    .where(or_(
                        OAuthProvider.organization_id == org_uuid,
                        OAuthProvider.organization_id.is_(None)
                    ))
                    .order_by(OAuthProvider.organization_id.desc().nulls_last())
                    .limit(1)
                )
            else:
                query = (
                    select(OAuthProvider)
                    .where(OAuthProvider.provider_name == provider)
                    .where(OAuthProvider.organization_id.is_(None))
                    .limit(1)
                )

            result = db.execute(query)
            provider_row = result.scalars().first()

            if not provider_row:
                logger.warning(f"OAuth connection '{provider}' not found for org '{target_org}'")
                return None

            # Decrypt client secret
            client_secret = None
            if provider_row.encrypted_client_secret:
                try:
                    client_secret = _decrypt(bytes(provider_row.encrypted_client_secret))
                except Exception as e:
                    logger.warning(f"Could not decrypt client_secret for '{provider}': {e}")

            metadata = provider_row.provider_metadata or {}

            # Build result
            oauth_result: dict[str, Any] = {
                "connection_name": provider_row.provider_name,
                "client_id": provider_row.client_id,
                "client_secret": client_secret,
                "authorization_url": metadata.get("authorization_url"),
                "token_url": metadata.get("token_url"),
                "scopes": provider_row.scopes or [],
                "access_token": None,
                "refresh_token": None,
                "expires_at": None,
            }

            # Get tokens for this provider
            token_query = (
                select(OAuthToken)
                .where(OAuthToken.provider_id == provider_row.id)
                .where(OAuthToken.user_id.is_(None))
                .limit(1)
            )
            token_result = db.execute(token_query)
            token_row = token_result.scalars().first()

            if token_row:
                # Decrypt tokens
                if token_row.encrypted_access_token:
                    try:
                        oauth_result["access_token"] = _decrypt(bytes(token_row.encrypted_access_token))
                    except Exception as e:
                        logger.warning(f"Could not decrypt access_token for '{provider}': {e}")

                if token_row.encrypted_refresh_token:
                    try:
                        oauth_result["refresh_token"] = _decrypt(bytes(token_row.encrypted_refresh_token))
                    except Exception as e:
                        logger.warning(f"Could not decrypt refresh_token for '{provider}': {e}")

                if token_row.expires_at:
                    oauth_result["expires_at"] = token_row.expires_at.isoformat()

            return oauth_result
