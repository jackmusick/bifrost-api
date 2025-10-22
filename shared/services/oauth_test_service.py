"""
OAuth Test Service
Tests OAuth connections by calling provider-specific test endpoints
"""

import logging

import aiohttp

logger = logging.getLogger(__name__)


class OAuthTestService:
    """
    Service for testing OAuth connections

    Tests connections by making authenticated requests to provider-specific
    test endpoints (e.g., Microsoft Graph /me, Google /userinfo)
    """

    # Provider-specific test endpoints
    TEST_ENDPOINTS = {
        "microsoft": "https://graph.microsoft.com/v1.0/me",
        "google": "https://www.googleapis.com/oauth2/v1/userinfo",
        "github": "https://api.github.com/user",
        "azure": "https://graph.microsoft.com/v1.0/me"
    }

    def __init__(self, timeout: int = 5):
        """
        Initialize OAuth test service

        Args:
            timeout: Request timeout in seconds (default: 5)
        """
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        logger.debug(f"OAuthTestService initialized (timeout={timeout}s)")

    async def test_connection(
        self,
        access_token: str,
        authorization_url: str,
        token_url: str
    ) -> tuple[bool, str]:
        """
        Test OAuth connection by making authenticated request to provider

        Args:
            access_token: OAuth access token to test
            authorization_url: OAuth authorization URL (used to detect provider)
            token_url: OAuth token URL (used to detect provider)

        Returns:
            Tuple of (success, message)
        """
        # Detect provider from URLs
        provider = self.detect_provider(authorization_url, token_url)
        logger.info(f"Testing OAuth connection for provider: {provider}")

        # Get test endpoint for provider
        test_url = self.TEST_ENDPOINTS.get(provider)

        if not test_url:
            logger.info(f"No test endpoint configured for provider '{provider}', marking as successful")
            return (True, "Connection completed successfully")

        # Make authenticated request to test endpoint
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                headers = {
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/json"
                }

                async with session.get(test_url, headers=headers) as response:
                    if response.status == 200:
                        logger.info(f"OAuth connection test successful for {provider}")
                        return (True, "Connection test successful")

                    elif response.status == 401:
                        error_msg = "Connection test failed: Invalid or expired token"
                        logger.warning(error_msg)
                        return (False, error_msg)

                    elif response.status == 403:
                        error_msg = "Connection test failed: Insufficient permissions"
                        logger.warning(error_msg)
                        return (False, error_msg)

                    else:
                        error_msg = f"Connection test failed: HTTP {response.status}"
                        logger.warning(error_msg)
                        return (False, error_msg)

        except aiohttp.ClientError as e:
            error_msg = f"Connection test failed: Network error - {str(e)}"
            logger.error(error_msg)
            return (False, error_msg)

        except Exception as e:
            error_msg = f"Connection test failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return (False, error_msg)

    def detect_provider(self, authorization_url: str, token_url: str) -> str:
        """
        Detect OAuth provider from URLs

        Args:
            authorization_url: OAuth authorization endpoint URL
            token_url: OAuth token endpoint URL

        Returns:
            Provider identifier (microsoft, google, github, azure, or generic)
        """
        combined = f"{authorization_url} {token_url}".lower()

        if "microsoft" in combined or "microsoftonline" in combined:
            return "microsoft"
        elif "login.microsoftonline.com" in combined:
            return "azure"
        elif "google" in combined or "googleapis" in combined:
            return "google"
        elif "github" in combined:
            return "github"
        else:
            return "generic"
