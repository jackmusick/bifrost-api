"""
OAuth Repository
Wraps OAuthStorageService to provide consistent interface

Note: OAuth connections are already managed by OAuthStorageService which uses Config table.
This repository provides a clean interface following repository pattern.
"""

import logging
from datetime import datetime
from typing import TYPE_CHECKING

from shared.services.oauth_storage_service import OAuthStorageService

if TYPE_CHECKING:
    from shared.models import CreateOAuthConnectionRequest, OAuthConnection, UpdateOAuthConnectionRequest
    from shared.context import ExecutionContext

logger = logging.getLogger(__name__)


class OAuthRepository:
    """
    Repository for OAuth connections

    Wraps OAuthStorageService to provide consistent repository interface.
    OAuth connections are stored in Config table with workflow indexes.
    """

    def __init__(self, context: 'ExecutionContext | None' = None):
        self.context = context
        self._service = OAuthStorageService()

    async def create_connection(
        self,
        request: 'CreateOAuthConnectionRequest',
        org_id: str,
        created_by: str
    ) -> 'OAuthConnection':
        """
        Create new OAuth connection

        Args:
            request: OAuth connection creation request
            org_id: Organization ID or "GLOBAL"
            created_by: User ID creating the connection

        Returns:
            Created OAuthConnection model
        """
        return await self._service.create_connection(org_id, request, created_by)

    async def get_connection(
        self,
        connection_name: str,
        org_id: str
    ) -> 'OAuthConnection | None':
        """
        Get OAuth connection with org → GLOBAL fallback

        Args:
            connection_name: Connection name
            org_id: Organization ID

        Returns:
            OAuthConnection model or None if not found
        """
        return await self._service.get_connection(org_id, connection_name)

    async def list_connections(
        self,
        org_id: str,
        include_global: bool = True
    ) -> list['OAuthConnection']:
        """
        List OAuth connections for an organization

        Args:
            org_id: Organization ID
            include_global: Include GLOBAL connections

        Returns:
            List of OAuthConnection models
        """
        return await self._service.list_connections(org_id, include_global)

    async def update_connection(
        self,
        connection_name: str,
        org_id: str,
        request: 'UpdateOAuthConnectionRequest',
        updated_by: str
    ) -> 'OAuthConnection | None':
        """
        Update OAuth connection

        Args:
            connection_name: Connection name
            org_id: Organization ID
            request: Update request
            updated_by: User ID making the update

        Returns:
            Updated OAuthConnection or None if not found
        """
        return await self._service.update_connection(org_id, connection_name, request, updated_by)

    async def delete_connection(
        self,
        connection_name: str,
        org_id: str
    ) -> bool:
        """
        Delete OAuth connection

        Args:
            connection_name: Connection name
            org_id: Organization ID

        Returns:
            True if deleted successfully
        """
        return await self._service.delete_connection(org_id, connection_name)

    async def store_tokens(
        self,
        connection_name: str,
        org_id: str,
        access_token: str,
        refresh_token: str | None,
        expires_at: 'datetime',
        token_type: str = "Bearer",
        updated_by: str = "system"
    ) -> bool:
        """
        Store OAuth tokens

        Args:
            connection_name: Connection name
            org_id: Organization ID
            access_token: Access token
            refresh_token: Refresh token (optional)
            expires_at: Token expiration datetime
            token_type: Token type (default "Bearer")
            updated_by: User ID storing tokens

        Returns:
            True if stored successfully
        """
        return await self._service.store_tokens(
            org_id, connection_name, access_token, refresh_token,
            expires_at, token_type, updated_by
        )

    async def update_status(
        self,
        connection_name: str,
        org_id: str,
        status: str,
        status_message: str | None = None
    ) -> bool:
        """
        Update OAuth connection status

        Args:
            connection_name: Connection name
            org_id: Organization ID
            status: New status
            status_message: Optional status message

        Returns:
            True if updated successfully
        """
        return await self._service.update_connection_status(
            org_id, connection_name, status, status_message
        )

    async def refresh_token(
        self,
        connection_name: str,
        org_id: str
    ) -> bool:
        """
        Refresh OAuth access token

        Args:
            connection_name: Connection name
            org_id: Organization ID

        Returns:
            True if refreshed successfully
        """
        return await self._service.refresh_token(org_id, connection_name)

    async def run_refresh_job(
        self,
        trigger_type: str = "automatic",
        trigger_user: str | None = None,
        refresh_threshold_minutes: int | None = None
    ) -> dict:
        """
        Run OAuth token refresh job

        Args:
            trigger_type: Type of trigger ("automatic" or "manual")
            trigger_user: Email of user who triggered (for manual)
            refresh_threshold_minutes: Override threshold in minutes

        Returns:
            Dictionary with job results
        """
        return await self._service.run_refresh_job(
            trigger_type=trigger_type,
            trigger_user=trigger_user,
            refresh_threshold_minutes=refresh_threshold_minutes
        )
