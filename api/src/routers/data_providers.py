"""
Data Providers Router

Returns metadata for all registered data providers.
API-compatible with the existing Azure Functions implementation.
"""

import logging

from fastapi import APIRouter, HTTPException, status

# Import existing Pydantic models for API compatibility
from src.models.schemas import DataProviderMetadata

from src.core.auth import CurrentActiveUser

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/data-providers", tags=["Data Providers"])


@router.get(
    "",
    response_model=list[DataProviderMetadata],
    summary="List all data providers",
    description="Returns metadata for all registered data providers in the system",
)
async def list_data_providers(
    user: CurrentActiveUser,
) -> list[DataProviderMetadata]:
    """List all registered data providers."""
    from shared.discovery import scan_all_data_providers
    from shared.handlers.discovery_handlers import convert_data_provider_metadata_to_model

    try:
        providers = []
        for dp in scan_all_data_providers():
            try:
                provider_model = convert_data_provider_metadata_to_model(dp)
                providers.append(provider_model)
            except Exception as e:
                logger.error(f"Failed to convert data provider '{dp.name}': {e}")

        logger.info(f"Returning {len(providers)} data providers")
        return providers

    except Exception as e:
        logger.error(f"Error retrieving data providers: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve data providers",
        )
