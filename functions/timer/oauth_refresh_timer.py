"""
OAuth Token Refresh Timer
Scheduled job that automatically refreshes expiring OAuth tokens
"""

import logging

import azure.functions as func

from shared.services.oauth_storage_service import OAuthStorageService

logger = logging.getLogger(__name__)

# Create blueprint for timer function
bp = func.Blueprint()


@bp.function_name("oauth_refresh_timer")
@bp.timer_trigger(schedule="0 */15 * * * *", arg_name="timer", run_on_startup=False)
async def oauth_refresh_timer(timer: func.TimerRequest) -> None:
    """
    Timer trigger that runs every 15 minutes to refresh expiring OAuth tokens

    Schedule: "0 */15 * * * *" = Every 15 minutes at minute 0, 15, 30, 45

    Process:
    1. Query all OAuth connections
    2. Find tokens expiring within next 30 minutes
    3. Refresh tokens using refresh_token or client_credentials
    4. Update stored tokens and connection status
    5. Log results for monitoring
    """
    logger.info("OAuth token refresh timer triggered")

    # Initialize service and run refresh job
    oauth_service = OAuthStorageService()
    async with oauth_service.config_table:
        await oauth_service.run_refresh_job(trigger_type="automatic")
