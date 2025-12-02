"""
Packages Router

Python package management for the workflow runtime.
Allows listing, installing, and uninstalling Python packages.
"""

import logging
import subprocess
import json

from fastapi import APIRouter, HTTPException, status

from src.models.schemas import (
    InstallPackageRequest,
    InstalledPackage,
    InstalledPackagesResponse,
    PackageInstallResponse,
    PackageUpdate,
    PackageUpdatesResponse,
)
from src.core.auth import Context, CurrentActiveUser, CurrentSuperuser

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/packages", tags=["Packages"])


# =============================================================================
# Helper Functions
# =============================================================================


async def check_package_updates() -> list[PackageUpdate]:
    """
    Check for available package updates using pip.

    Returns:
        List of packages with available updates
    """
    try:
        result = subprocess.run(
            ["pip", "list", "--outdated", "--format=json"],
            capture_output=True,
            text=True,
            timeout=60,
        )

        if result.returncode != 0:
            logger.error(f"pip list --outdated failed: {result.stderr}")
            return []

        packages_data = json.loads(result.stdout)
        return [
            PackageUpdate(
                name=pkg["name"],
                current_version=pkg["version"],
                latest_version=pkg["latest_version"],
            )
            for pkg in packages_data
        ]

    except subprocess.TimeoutExpired:
        logger.error("pip list --outdated timed out")
        return []
    except json.JSONDecodeError:
        logger.error("Failed to parse pip outdated output")
        return []
    except Exception as e:
        logger.error(f"Error checking package updates: {str(e)}")
        return []


async def get_installed_packages() -> list[InstalledPackage]:
    """
    Get list of installed Python packages.

    Uses pip to query installed packages.
    """
    try:
        result = subprocess.run(
            ["pip", "list", "--format=json"],
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode != 0:
            logger.error(f"pip list failed: {result.stderr}")
            return []

        packages_data = json.loads(result.stdout)
        return [
            InstalledPackage(name=pkg["name"], version=pkg["version"])
            for pkg in packages_data
        ]

    except subprocess.TimeoutExpired:
        logger.error("pip list timed out")
        return []
    except json.JSONDecodeError:
        logger.error("Failed to parse pip output")
        return []
    except Exception as e:
        logger.error(f"Error getting installed packages: {str(e)}")
        return []


# =============================================================================
# HTTP Endpoints
# =============================================================================


@router.get(
    "",
    response_model=InstalledPackagesResponse,
    summary="List installed packages",
    description="List all installed Python packages",
)
async def list_packages(
    ctx: Context,
    user: CurrentActiveUser,
) -> InstalledPackagesResponse:
    """
    List all installed Python packages.

    Returns:
        List of installed packages with versions
    """
    try:
        packages = await get_installed_packages()
        logger.info(f"Listed {len(packages)} installed packages")
        return InstalledPackagesResponse(packages=packages)

    except Exception as e:
        logger.error(f"Error listing packages: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list packages",
        )


@router.get(
    "/updates",
    response_model=PackageUpdatesResponse,
    summary="Check for package updates",
    description="Check for available updates to installed packages",
)
async def check_updates(
    ctx: Context,
    user: CurrentActiveUser,
) -> PackageUpdatesResponse:
    """
    Check for available package updates.

    Returns:
        List of packages with available updates
    """
    try:
        updates = await check_package_updates()
        logger.info(f"Found {len(updates)} package updates available")
        return PackageUpdatesResponse(updates=updates)

    except Exception as e:
        logger.error(f"Error checking package updates: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to check for package updates",
        )


@router.post(
    "/install",
    response_model=PackageInstallResponse,
    summary="Install a Python package",
    description="Install a Python package (Platform admin only)",
)
async def install_package(
    request: InstallPackageRequest,
    ctx: Context,
    user: CurrentSuperuser,
) -> PackageInstallResponse:
    """
    Install a Python package.

    In production, this would queue a RabbitMQ job for background installation.
    For now, it attempts direct installation.

    Args:
        request: Package install request with name and optional version

    Returns:
        Installation response
    """
    try:
        package_spec = request.package
        if request.version:
            package_spec = f"{request.package}=={request.version}"

        logger.info(f"Installing package: {package_spec}")

        # In production, this would be queued as a job
        # For now, attempt direct installation
        result = subprocess.run(
            ["pip", "install", package_spec],
            capture_output=True,
            text=True,
            timeout=300,  # 5 minute timeout
        )

        if result.returncode != 0:
            logger.error(f"pip install failed: {result.stderr}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Package installation failed: {result.stderr}",
            )

        logger.info(f"Successfully installed package: {package_spec}")

        return PackageInstallResponse(
            job_id=request.package,
            status="queued",
        )

    except subprocess.TimeoutExpired:
        logger.error(f"Package installation timed out: {request.package}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Package installation timed out",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error installing package: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to install package",
        )


@router.delete(
    "/{package_name}",
    summary="Uninstall a Python package",
    description="Uninstall a Python package (Platform admin only)",
)
async def uninstall_package(
    package_name: str,
    ctx: Context,
    user: CurrentSuperuser,
) -> dict:
    """
    Uninstall a Python package.

    In production, this would queue a RabbitMQ job for background uninstall.
    For now, it attempts direct uninstallation.

    Args:
        package_name: Name of the package to uninstall

    Returns:
        Confirmation message
    """
    try:
        logger.info(f"Uninstalling package: {package_name}")

        # In production, this would be queued as a job
        # For now, attempt direct uninstallation
        result = subprocess.run(
            ["pip", "uninstall", "-y", package_name],
            capture_output=True,
            text=True,
            timeout=300,  # 5 minute timeout
        )

        if result.returncode != 0:
            logger.error(f"pip uninstall failed: {result.stderr}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Package uninstallation failed: {result.stderr}",
            )

        logger.info(f"Successfully uninstalled package: {package_name}")

        return {
            "message": f"Package '{package_name}' uninstalled successfully",
            "status": "uninstalled",
        }

    except subprocess.TimeoutExpired:
        logger.error(f"Package uninstallation timed out: {package_name}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Package uninstallation timed out",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uninstalling package: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to uninstall package",
        )
