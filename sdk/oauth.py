"""
OAuth SDK Module

Provides OAuth connection management.
Uses the current execution context to access org-scoped OAuth connections.

Usage:
    from bifrost import oauth
    
    # Get OAuth credentials for a connection
    creds = await oauth.get_connection("HaloPSA")
    
    # Use credentials in API request
    headers = {"Authorization": creds.get_auth_header()}
    response = requests.get("https://api.example.com/v1/data", headers=headers)
"""

from typing import TYPE_CHECKING
from ._context import _get_context

if TYPE_CHECKING:
    from shared.models import OAuthCredentials


class oauth:
    """OAuth connection management SDK."""
    
    @staticmethod
    async def get_connection(connection_name: str) -> 'OAuthCredentials':
        """
        Get OAuth credentials for a connection.
        
        Retrieves OAuth credentials from storage and Key Vault,
        resolving them to actual access tokens for workflow use.
        
        This method works with both org-scoped and GLOBAL contexts.
        OAuth connections follow org→GLOBAL fallback pattern.
        
        Args:
            connection_name: Name of the OAuth connection to retrieve
            
        Returns:
            OAuthCredentials object with access_token and metadata
            
        Raises:
            ValueError: If connection not found or not authorized
            KeyError: If credentials cannot be resolved from Key Vault
            RuntimeError: If no execution context is available
            
        Example:
            # Get OAuth connection
            creds = await oauth.get_connection("HaloPSA")
            
            # Use in API request
            headers = {"Authorization": creds.get_auth_header()}
            response = requests.get(
                "https://api.example.com/v1/data",
                headers=headers
            )
            
            # Check if token is expired
            if creds.is_expired():
                print("Token needs refresh!")
        """
        context = _get_context()
        return await context.get_oauth_connection(connection_name)
