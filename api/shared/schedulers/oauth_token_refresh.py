"""
OAuth Token Refresh Scheduler

Automatically refreshes OAuth tokens that are about to expire.
Runs every 15 minutes to check for tokens expiring within 30 minutes.
"""

import logging
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import select

from src.core.database import get_db_context
from src.models import OAuthToken, OAuthProvider

logger = logging.getLogger(__name__)


async def refresh_expiring_tokens() -> dict[str, Any]:
    """
    Refresh OAuth tokens that are about to expire.

    Finds all tokens expiring within 30 minutes and attempts to refresh them
    using their associated provider's configuration.

    Returns:
        Summary of refresh results
    """
    logger.info("OAuth token refresh job started")

    results = {
        "total_checked": 0,
        "refreshed": 0,
        "failed": 0,
        "errors": [],
    }

    try:
        # Find tokens expiring within 30 minutes
        expiry_threshold = datetime.utcnow() + timedelta(minutes=30)

        async with get_db_context() as db:
            # Query tokens that have refresh tokens and are expiring soon
            query = (
                select(OAuthToken)
                .where(OAuthToken.expires_at.isnot(None))
                .where(OAuthToken.expires_at <= expiry_threshold)
                .where(OAuthToken.encrypted_refresh_token.isnot(None))
            )
            result = await db.execute(query)
            expiring_tokens = result.scalars().all()

            results["total_checked"] = len(expiring_tokens)
            logger.info(f"Found {len(expiring_tokens)} tokens expiring within 30 minutes")

            for token in expiring_tokens:
                try:
                    # Get the provider configuration
                    provider_query = select(OAuthProvider).where(
                        OAuthProvider.id == token.provider_id
                    )
                    provider_result = await db.execute(provider_query)
                    provider = provider_result.scalar_one_or_none()

                    if not provider:
                        logger.warning(
                            f"Provider not found for token {token.id}"
                        )
                        results["errors"].append({
                            "token_id": str(token.id),
                            "error": "Provider not found",
                        })
                        results["failed"] += 1
                        continue

                    # Attempt to refresh the token
                    success = await _refresh_single_token(db, token, provider)

                    if success:
                        results["refreshed"] += 1
                        logger.info(
                            f"Refreshed token for provider '{provider.provider_name}'"
                        )
                    else:
                        results["failed"] += 1
                        results["errors"].append({
                            "token_id": str(token.id),
                            "provider": provider.provider_name,
                            "error": "Refresh failed",
                        })

                except Exception as e:
                    results["failed"] += 1
                    results["errors"].append({
                        "token_id": str(token.id),
                        "error": str(e),
                    })
                    logger.error(
                        f"Error refreshing token {token.id}: {e}",
                        exc_info=True,
                    )

            await db.commit()

        logger.info(
            f"OAuth token refresh completed: "
            f"Checked={results['total_checked']}, "
            f"Refreshed={results['refreshed']}, "
            f"Failed={results['failed']}"
        )

    except Exception as e:
        logger.error(f"OAuth token refresh job failed: {e}", exc_info=True)
        results["errors"].append({"error": str(e)})

    return results


async def _refresh_single_token(
    db,
    token: OAuthToken,
    provider: OAuthProvider,
) -> bool:
    """
    Refresh a single OAuth token.

    Args:
        db: Database session
        token: Token to refresh
        provider: OAuth provider configuration

    Returns:
        True if refresh succeeded, False otherwise
    """
    import httpx

    from src.core.security import decrypt_data, encrypt_data

    try:
        # Decrypt the refresh token
        refresh_token = decrypt_data(token.encrypted_refresh_token)
        client_secret = decrypt_data(provider.encrypted_client_secret)

        if not refresh_token or not client_secret:
            logger.warning(f"Missing refresh token or client secret for token {token.id}")
            return False

        # Build refresh request
        token_url = provider.token_url
        if not token_url:
            logger.warning(f"No token URL configured for provider {provider.provider_name}")
            return False

        data = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": provider.client_id,
            "client_secret": client_secret,
        }

        # Add scopes if available
        if token.scopes:
            data["scope"] = " ".join(token.scopes)

        # Make the refresh request
        async with httpx.AsyncClient() as client:
            response = await client.post(
                token_url,
                data=data,
                timeout=30.0,
            )

        if response.status_code != 200:
            logger.error(
                f"Token refresh failed for {provider.provider_name}: "
                f"Status {response.status_code}, Body: {response.text[:200]}"
            )
            return False

        token_data = response.json()

        # Update the token
        new_access_token = token_data.get("access_token")
        new_refresh_token = token_data.get("refresh_token", refresh_token)
        expires_in = token_data.get("expires_in")

        if not new_access_token:
            logger.error(f"No access token in refresh response for {provider.provider_name}")
            return False

        # Encrypt and store new tokens
        token.encrypted_access_token = encrypt_data(new_access_token)
        token.encrypted_refresh_token = encrypt_data(new_refresh_token)

        # Update expiration
        if expires_in:
            token.expires_at = datetime.utcnow() + timedelta(seconds=int(expires_in))
        else:
            # Default to 1 hour if not specified
            token.expires_at = datetime.utcnow() + timedelta(hours=1)

        # Update scopes if returned
        new_scopes = token_data.get("scope")
        if new_scopes:
            token.scopes = new_scopes.split(" ")

        # Update provider status
        provider.status = "connected"
        provider.last_token_refresh = datetime.utcnow()
        provider.status_message = None

        return True

    except Exception as e:
        logger.error(f"Error refreshing token: {e}", exc_info=True)
        # Update provider status to indicate error
        provider.status = "error"
        provider.status_message = f"Token refresh failed: {str(e)[:200]}"
        return False
