"""
Web PubSub connection endpoints

Provides connection negotiation for real-time updates via Azure Web PubSub.
"""

import json
import logging
import os

import azure.functions as func
from azure.messaging.webpubsubservice import WebPubSubServiceClient
from azure.identity import DefaultAzureCredential

from shared.decorators import with_request_context
from shared.openapi_decorators import openapi_endpoint

logger = logging.getLogger(__name__)

# Create blueprint
bp = func.Blueprint()


@bp.function_name("webpubsub_negotiate")
@bp.route(route="webpubsub/negotiate", methods=["POST"])
@openapi_endpoint(
    path="/webpubsub/negotiate",
    method="POST",
    summary="Negotiate Web PubSub connection",
    description="Returns Web PubSub connection information for real-time execution updates.",
    tags=["WebPubSub"],
    response_model=None  # Web PubSub connection info schema is standard
)
@with_request_context
async def negotiate(req: func.HttpRequest) -> func.HttpResponse:
    """
    POST /api/webpubsub/negotiate

    Returns Web PubSub connection info for real-time updates.

    After connecting, clients are automatically added to execution-specific groups
    when they subscribe to channels like "execution:abc-123".

    Returns:
        Web PubSub connection info (url, accessToken)
    """
    try:
        context = req.context  # type: ignore[attr-defined]
        user_id = context.user_id

        logger.info(f"Web PubSub negotiate for user {user_id}")

        # Get configuration
        hub_name = os.getenv('AZURE_WEBPUBSUB_HUB', 'bifrost')
        endpoint = os.getenv('AZURE_WEBPUBSUB_ENDPOINT')
        connection_string = os.getenv('WebPubSubConnectionString')

        # Check if Web PubSub is configured
        if not endpoint and not connection_string:
            return func.HttpResponse(
                json.dumps({
                    'error': 'ServiceUnavailable',
                    'message': 'Real-time updates not configured'
                }),
                status_code=503,
                mimetype='application/json'
            )

        # Create client
        if endpoint:
            # Use managed identity (production)
            logger.info(f"Creating Web PubSub client with managed identity: {endpoint}")
            credential = DefaultAzureCredential()
            service_client = WebPubSubServiceClient(
                endpoint=endpoint,
                hub=hub_name,
                credential=credential
            )
        elif connection_string:
            # Use connection string (local dev)
            logger.info("Creating Web PubSub client with connection string")
            service_client = WebPubSubServiceClient.from_connection_string(
                connection_string=connection_string,
                hub=hub_name
            )
        else:
            # Should not reach here due to earlier check, but satisfy type checker
            return func.HttpResponse(
                json.dumps({
                    'error': 'ServiceUnavailable',
                    'message': 'Real-time updates not configured'
                }),
                status_code=503,
                mimetype='application/json'
            )

        # Generate client access token with permissions to join groups
        token = service_client.get_client_access_token(
            user_id=user_id,
            roles=["webpubsub.joinLeaveGroup", "webpubsub.sendToGroup"]
        )

        # Return connection info
        return func.HttpResponse(
            json.dumps({
                'url': token['url']
            }),
            status_code=200,
            mimetype='application/json'
        )

    except Exception as e:
        logger.error(f"Web PubSub negotiate failed: {str(e)}", exc_info=True)
        return func.HttpResponse(
            json.dumps({
                'error': 'InternalServerError',
                'message': f'Failed to negotiate Web PubSub connection: {str(e)}'
            }),
            status_code=500,
            mimetype='application/json'
        )
