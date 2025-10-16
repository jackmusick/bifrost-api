"""
OAuth Storage Service
Handles CRUD operations for OAuth connections with Config table integration
"""

import json
import logging
from datetime import datetime

from azure.core.exceptions import ResourceNotFoundError

from models.oauth_connection import CreateOAuthConnectionRequest, OAuthConnection, UpdateOAuthConnectionRequest
from shared.keyvault import KeyVaultClient
from shared.storage import TableStorageService

logger = logging.getLogger(__name__)


class OAuthStorageService:
    """
    Service for managing OAuth connections in Table Storage and Config table

    Responsibilities:
    - CRUD operations for OAuthConnections table
    - Store client_secret in Config table with Type="secret_ref"
    - Store OAuth response tokens in Config table with Type="secret_ref"
    - Store metadata in Config table with Type="json"
    - Implement org→GLOBAL fallback pattern
    """

    def __init__(self, connection_string: str | None = None):
        """
        Initialize OAuth storage service

        Args:
            connection_string: Optional Azure Storage connection string override
        """
        self.oauth_table = TableStorageService("OAuthConnections", connection_string or None)
        self.config_table = TableStorageService("Config", connection_string or None)

        # Ensure OAuthConnections table exists
        self._ensure_table_exists()

        logger.debug("OAuthStorageService initialized")

    def _ensure_table_exists(self):
        """Ensure OAuthConnections table exists, create if it doesn't"""
        try:
            self.oauth_table.table_client.create_table()
            logger.info("Created OAuthConnections table")
        except Exception as e:
            # Table likely already exists, which is fine
            logger.debug(f"OAuthConnections table check: {e}")

    async def create_connection(
        self,
        org_id: str,
        request: CreateOAuthConnectionRequest,
        created_by: str
    ) -> OAuthConnection:
        """
        Create a new OAuth connection

        Process:
        1. Create OAuthConnection entity in OAuthConnections table
        2. Store client_secret in Config table (Type="secret_ref")
        3. Store metadata in Config table (Type="json")

        Args:
            org_id: Organization ID or "GLOBAL"
            request: OAuth connection creation request
            created_by: User ID creating the connection

        Returns:
            Created OAuthConnection

        Raises:
            ResourceExistsError: If connection with same name already exists
        """
        now = datetime.utcnow()

        # Generate config references
        client_secret_ref = f"oauth_{request.connection_name}_client_secret"
        oauth_response_ref = f"oauth_{request.connection_name}_oauth_response"

        # Create OAuth connection model
        # Note: redirect_uri should point to the UI callback page, not the API
        connection = OAuthConnection(
            org_id=org_id,
            connection_name=request.connection_name,
            description=request.description,
            oauth_flow_type=request.oauth_flow_type,
            client_id=request.client_id,
            client_secret_ref=client_secret_ref,
            oauth_response_ref=oauth_response_ref,
            authorization_url=request.authorization_url,
            token_url=request.token_url,
            scopes=request.scopes,
            redirect_uri=f"/oauth/callback/{request.connection_name}",  # UI route, not /api/
            status="not_connected",
            created_by=created_by,
            created_at=now,
            updated_at=now,
            expires_at=None
        )

        # Convert to Table Storage entity
        entity = connection.model_dump()
        entity["PartitionKey"] = org_id
        entity["RowKey"] = request.connection_name

        # Serialize datetime fields
        entity["created_at"] = entity["created_at"].isoformat()
        entity["updated_at"] = entity["updated_at"].isoformat()
        if entity.get("expires_at"):
            entity["expires_at"] = entity["expires_at"].isoformat()

        # Store in OAuthConnections table
        self.oauth_table.insert_entity(entity)
        logger.info(f"Created OAuth connection: {request.connection_name} for org {org_id}")

        # Store client_secret in Key Vault and Config table (Type="secret_ref") if provided
        # Value is the Key Vault secret name
        # Note: Client secret is optional for PKCE flow
        if request.client_secret:
            try:
                keyvault = KeyVaultClient()
                assert keyvault._client is not None, "KeyVault client is None"
                keyvault_secret_name = f"{org_id}--oauth-{request.connection_name}-client-secret"

                keyvault._client.set_secret(keyvault_secret_name, request.client_secret)
                logger.info(f"Stored client_secret in Key Vault: {keyvault_secret_name}")
            except ValueError as e:
                # KeyVault not configured (e.g., in test environment)
                logger.warning(f"KeyVault not available for client_secret storage: {e}")
                logger.warning("Client secret will not be persisted - OAuth connection may not work in production")
            except Exception as e:
                logger.error(f"Failed to store client_secret in Key Vault: {e}")
                raise

            client_secret_config = {
                "PartitionKey": org_id,
                "RowKey": f"config:oauth_{request.connection_name}_client_secret",
                "Value": keyvault_secret_name,
                "Type": "secret_ref",
                "Description": f"OAuth client secret for {request.connection_name}",
                "UpdatedAt": now.isoformat(),
                "UpdatedBy": created_by
            }
            self.config_table.insert_entity(client_secret_config)
            logger.info(f"Stored client_secret config reference for {request.connection_name}")
        else:
            logger.info(f"No client secret provided (PKCE flow) for {request.connection_name}")

        # Store metadata in Config table (Type="json")
        metadata = {
            "oauth_flow_type": request.oauth_flow_type,
            "client_id": request.client_id,
            "authorization_url": request.authorization_url,
            "token_url": request.token_url,
            "scopes": request.scopes,
            "redirect_uri": connection.redirect_uri,
            "status": connection.status
        }
        metadata_config = {
            "PartitionKey": org_id,
            "RowKey": f"config:oauth_{request.connection_name}_metadata",
            "Value": json.dumps(metadata),
            "Type": "json",
            "Description": f"OAuth metadata for {request.connection_name}",
            "UpdatedAt": now.isoformat(),
            "UpdatedBy": created_by
        }
        self.config_table.insert_entity(metadata_config)
        logger.info(f"Stored metadata config for {request.connection_name}")

        return connection

    async def get_connection(
        self,
        org_id: str,
        connection_name: str
    ) -> OAuthConnection | None:
        """
        Get OAuth connection with org→GLOBAL fallback

        Args:
            org_id: Organization ID
            connection_name: Connection name

        Returns:
            OAuthConnection or None if not found
        """
        # Try org-specific first
        entity = self.oauth_table.get_entity(org_id, connection_name)

        if entity:
            logger.debug(f"Found org-specific OAuth connection: {connection_name} for org {org_id}")
            return self._entity_to_connection(entity)

        # Fallback to GLOBAL
        entity = self.oauth_table.get_entity("GLOBAL", connection_name)

        if entity:
            logger.debug(f"Found GLOBAL OAuth connection: {connection_name}")
            return self._entity_to_connection(entity)

        logger.debug(f"OAuth connection not found: {connection_name} (org: {org_id})")
        return None

    async def list_connections(
        self,
        org_id: str,
        include_global: bool = True
    ) -> list[OAuthConnection]:
        """
        List OAuth connections for an organization

        Args:
            org_id: Organization ID
            include_global: Whether to include GLOBAL connections

        Returns:
            List of OAuthConnection
        """
        connections = []

        try:
            # Get org-specific connections
            org_entities = list(self.oauth_table.query_by_org(org_id))
            connections.extend([self._entity_to_connection(e) for e in org_entities])

            # Get GLOBAL connections if requested AND we're not already querying GLOBAL
            # (avoid duplicates when org_id is "GLOBAL")
            if include_global and org_id != "GLOBAL":
                global_entities = list(self.oauth_table.query_by_org("GLOBAL"))
                connections.extend([self._entity_to_connection(e) for e in global_entities])

            logger.info(f"Listed {len(connections)} OAuth connections for org {org_id} (include_global={include_global})")
        except ResourceNotFoundError:
            # Table doesn't exist yet - return empty list
            # Table will be created when first connection is added
            logger.info("OAuthConnections table does not exist yet - returning empty list")

        return connections

    async def update_connection(
        self,
        org_id: str,
        connection_name: str,
        request: UpdateOAuthConnectionRequest,
        updated_by: str
    ) -> OAuthConnection | None:
        """
        Update an existing OAuth connection

        Args:
            org_id: Organization ID
            connection_name: Connection name
            request: Update request with optional fields
            updated_by: User ID making the update

        Returns:
            Updated OAuthConnection or None if not found
        """
        # Get existing connection
        entity = self.oauth_table.get_entity(org_id, connection_name)

        if not entity:
            logger.warning(f"OAuth connection not found for update: {connection_name}")
            return None

        # Update fields if provided
        if request.client_id is not None:
            entity["client_id"] = request.client_id
        if request.authorization_url is not None:
            entity["authorization_url"] = request.authorization_url
        if request.token_url is not None:
            entity["token_url"] = request.token_url
        if request.scopes is not None:
            entity["scopes"] = request.scopes

        # Update timestamp
        entity["updated_at"] = datetime.utcnow().isoformat()

        # If credentials changed, mark as requiring reconnection
        if request.client_id or request.client_secret or request.authorization_url or request.token_url:
            entity["status"] = "not_connected"
            entity["status_message"] = "Connection requires re-authorization due to configuration update"

        # Update entity
        self.oauth_table.update_entity(entity)
        logger.info(f"Updated OAuth connection: {connection_name}")

        # Update metadata config if needed
        if request.client_id or request.authorization_url or request.token_url or request.scopes:
            await self._update_metadata_config(org_id, connection_name, entity, updated_by)

        return self._entity_to_connection(entity)

    async def delete_connection(
        self,
        org_id: str,
        connection_name: str
    ) -> bool:
        """
        Delete an OAuth connection and its associated configs

        Args:
            org_id: Organization ID
            connection_name: Connection name

        Returns:
            True if deleted, False if not found
        """
        # Delete from OAuthConnections table
        deleted = self.oauth_table.delete_entity(org_id, connection_name)

        if not deleted:
            logger.warning(f"OAuth connection not found for deletion: {connection_name}")
            return False

        # Delete secrets from Key Vault
        try:
            keyvault = KeyVaultClient()
            assert keyvault._client is not None, "KeyVault client is None"
            keyvault_secret_names = [
                f"{org_id}--oauth-{connection_name}-client-secret",
                f"{org_id}--oauth-{connection_name}-response"
            ]

            for secret_name in keyvault_secret_names:
                try:
                    keyvault._client.begin_delete_secret(secret_name).wait()
                    logger.debug(f"Deleted Key Vault secret: {secret_name}")
                except Exception as e:
                    # Secret might not exist (e.g., PKCE flow has no client_secret)
                    logger.debug(f"Could not delete Key Vault secret {secret_name}: {e}")
        except ValueError as e:
            # KeyVault not configured (e.g., in test environment)
            logger.warning(f"KeyVault not available for secret deletion: {e}")
            logger.debug("Skipping Key Vault secret cleanup")

        # Delete associated configs
        config_keys = [
            f"config:oauth_{connection_name}_client_secret",
            f"config:oauth_{connection_name}_oauth_response",
            f"config:oauth_{connection_name}_metadata"
        ]

        for config_key in config_keys:
            try:
                self.config_table.delete_entity(org_id, config_key)
                logger.debug(f"Deleted config: {config_key}")
            except Exception as e:
                logger.warning(f"Failed to delete config {config_key}: {e}")

        logger.info(f"Deleted OAuth connection and configs: {connection_name}")
        return True

    async def store_tokens(
        self,
        org_id: str,
        connection_name: str,
        access_token: str,
        refresh_token: str | None,
        expires_at: datetime,
        token_type: str = "Bearer",
        updated_by: str = "system"
    ) -> bool:
        """
        Store OAuth tokens in Config table

        Args:
            org_id: Organization ID
            connection_name: Connection name
            access_token: OAuth access token
            refresh_token: Optional refresh token
            expires_at: Token expiration datetime
            token_type: Token type (usually "Bearer")
            updated_by: User ID storing tokens

        Returns:
            True if stored successfully
        """
        # Prepare OAuth response JSON
        oauth_response = {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": token_type,
            "expires_at": expires_at.isoformat()
        }

        # Store OAuth response JSON in Key Vault
        try:
            keyvault = KeyVaultClient()
            assert keyvault._client is not None, "KeyVault client is None"
            keyvault_secret_name = f"{org_id}--oauth-{connection_name}-response"

            keyvault._client.set_secret(keyvault_secret_name, json.dumps(oauth_response))
            logger.info(f"Stored OAuth tokens in Key Vault: {keyvault_secret_name}")
        except ValueError as e:
            # KeyVault not configured (e.g., in test environment)
            logger.warning(f"KeyVault not available for OAuth token storage: {e}")
            logger.warning("OAuth tokens will not be persisted - this connection will not work in production")
        except Exception as e:
            logger.error(f"Failed to store OAuth tokens in Key Vault: {e}")
            raise

        # Store in Config table (Type="secret_ref")
        # Value is the Key Vault secret name
        oauth_response_config = {
            "PartitionKey": org_id,
            "RowKey": f"config:oauth_{connection_name}_oauth_response",
            "Value": keyvault_secret_name,
            "Type": "secret_ref",
            "Description": f"OAuth tokens for {connection_name}",
            "UpdatedAt": datetime.utcnow().isoformat(),
            "UpdatedBy": updated_by
        }

        # Upsert (create or update)
        self.config_table.upsert_entity(oauth_response_config)
        logger.info(f"Stored OAuth tokens config reference for {connection_name}")

        # Update expires_at in OAuthConnections table for quick checks
        await self.update_connection_status(
            org_id,
            connection_name,
            status="completed",
            expires_at=expires_at
        )

        return True

    async def update_connection_status(
        self,
        org_id: str,
        connection_name: str,
        status: str,
        status_message: str | None = None,
        expires_at: datetime | None = None,
        last_refresh_at: datetime | None = None
    ) -> bool:
        """
        Update OAuth connection status

        Args:
            org_id: Organization ID
            connection_name: Connection name
            status: New status
            status_message: Optional status message
            expires_at: Optional new expiration time
            last_refresh_at: Optional last refresh timestamp

        Returns:
            True if updated successfully
        """
        entity = self.oauth_table.get_entity(org_id, connection_name)

        if not entity:
            logger.warning(f"OAuth connection not found for status update: {connection_name}")
            return False

        # Update fields
        entity["status"] = status
        if status_message is not None:
            entity["status_message"] = status_message
        if expires_at is not None:
            entity["expires_at"] = expires_at.isoformat()
        if last_refresh_at is not None:
            entity["last_refresh_at"] = last_refresh_at.isoformat()
        entity["updated_at"] = datetime.utcnow().isoformat()

        self.oauth_table.update_entity(entity)
        logger.info(f"Updated OAuth connection status: {connection_name} -> {status}")

        return True

    async def _update_metadata_config(
        self,
        org_id: str,
        connection_name: str,
        entity: dict,
        updated_by: str
    ):
        """Update metadata config when connection details change"""
        metadata = {
            "oauth_flow_type": entity["oauth_flow_type"],
            "client_id": entity["client_id"],
            "authorization_url": entity["authorization_url"],
            "token_url": entity["token_url"],
            "scopes": entity["scopes"],
            "redirect_uri": entity["redirect_uri"],
            "status": entity["status"]
        }

        metadata_config = {
            "PartitionKey": org_id,
            "RowKey": f"config:oauth_{connection_name}_metadata",
            "Value": json.dumps(metadata),
            "Type": "json",
            "Description": f"OAuth metadata for {connection_name}",
            "UpdatedAt": datetime.utcnow().isoformat(),
            "UpdatedBy": updated_by
        }

        self.config_table.upsert_entity(metadata_config)

    def _entity_to_connection(self, entity: dict) -> OAuthConnection:
        """
        Convert Table Storage entity to OAuthConnection model

        Args:
            entity: Entity from Table Storage

        Returns:
            OAuthConnection model
        """
        # Parse datetime fields
        created_at = entity.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))

        updated_at = entity.get("updated_at")
        if isinstance(updated_at, str):
            updated_at = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
        elif updated_at is None:
            # Default to created_at if updated_at is missing
            updated_at = created_at if created_at else datetime.utcnow()

        expires_at = entity.get("expires_at")
        if expires_at and isinstance(expires_at, str):
            expires_at = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))

        last_refresh_at = entity.get("last_refresh_at")
        if last_refresh_at and isinstance(last_refresh_at, str):
            last_refresh_at = datetime.fromisoformat(last_refresh_at.replace("Z", "+00:00"))

        last_test_at = entity.get("last_test_at")
        if last_test_at and isinstance(last_test_at, str):
            last_test_at = datetime.fromisoformat(last_test_at.replace("Z", "+00:00"))

        # Parse required fields with assertions for type safety
        client_secret_ref = entity.get("client_secret_ref")
        assert client_secret_ref is not None, "client_secret_ref is required"
        oauth_response_ref = entity.get("oauth_response_ref")
        assert oauth_response_ref is not None, "oauth_response_ref is required"
        assert created_at is not None, "created_at is required"

        return OAuthConnection(
            org_id=entity["PartitionKey"],
            connection_name=entity["RowKey"],
            description=entity.get("description"),
            oauth_flow_type=entity["oauth_flow_type"],
            client_id=entity["client_id"],
            client_secret_ref=client_secret_ref,
            oauth_response_ref=oauth_response_ref,
            authorization_url=entity["authorization_url"],
            token_url=entity["token_url"],
            scopes=entity.get("scopes", ""),
            redirect_uri=entity["redirect_uri"],
            token_type=entity.get("token_type", "Bearer"),
            expires_at=expires_at,
            status=entity["status"],
            status_message=entity.get("status_message"),
            last_refresh_at=last_refresh_at,
            last_test_at=last_test_at,
            created_at=created_at,
            created_by=entity["created_by"],
            updated_at=updated_at
        )
