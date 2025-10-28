"""
Package Management API
Handles installation and management of Python packages for the platform workspace
"""

import json
import logging
import os
import uuid
from pathlib import Path

import azure.functions as func
from azure.storage.queue import QueueClient, TextBase64EncodePolicy

from shared.decorators import require_platform_admin, with_request_context
from shared.models import (
    InstallPackageRequest,
    InstalledPackagesResponse,
    PackageInstallResponse,
    PackageUpdatesResponse,
)
from shared.openapi_decorators import openapi_endpoint
from shared.package_manager import WorkspacePackageManager

# Create blueprint for package management endpoints
bp = func.Blueprint()

logger = logging.getLogger(__name__)


def get_workspace_path() -> Path:
    """
    Get the platform workspace path.

    Returns:
        Path to workspace directory
    """
    workspace_location = os.environ.get('BIFROST_WORKSPACE_LOCATION', '/mounts/workspace')
    return Path(workspace_location)


@bp.route(route="packages", methods=["GET"])
@bp.function_name("list_packages")
@openapi_endpoint(
    path="/packages",
    method="GET",
    summary="List installed packages",
    description="List all installed Python packages in the workspace",
    tags=["Package Management"],
    response_model=InstalledPackagesResponse,
)
@with_request_context
@require_platform_admin
async def list_packages(req: func.HttpRequest) -> func.HttpResponse:
    """List all installed packages in workspace"""
    try:
        workspace_path = get_workspace_path()

        pkg_manager = WorkspacePackageManager(workspace_path)
        packages = await pkg_manager.list_installed_packages()

        return func.HttpResponse(
            body=json.dumps({"packages": packages}),
            mimetype="application/json",
            status_code=200
        )
    except Exception as e:
        logger.error(f"Failed to list packages: {e}", exc_info=True)
        return func.HttpResponse(
            body=json.dumps({"error": "internal_error", "message": str(e)}),
            mimetype="application/json",
            status_code=500
        )


@bp.route(route="packages/updates", methods=["GET"])
@bp.function_name("check_package_updates")
@openapi_endpoint(
    path="/packages/updates",
    method="GET",
    summary="Check for package updates",
    description="Check for available updates to installed packages",
    tags=["Package Management"],
    response_model=PackageUpdatesResponse,
)
@with_request_context
@require_platform_admin
async def check_package_updates(req: func.HttpRequest) -> func.HttpResponse:
    """Check for available updates to installed packages"""
    try:
        workspace_path = get_workspace_path()

        pkg_manager = WorkspacePackageManager(workspace_path)
        updates = await pkg_manager.check_for_updates()

        return func.HttpResponse(
            body=json.dumps({"updates": updates}),
            mimetype="application/json",
            status_code=200
        )
    except Exception as e:
        logger.error(f"Failed to check package updates: {e}", exc_info=True)
        return func.HttpResponse(
            body=json.dumps({"error": "internal_error", "message": str(e)}),
            mimetype="application/json",
            status_code=500
        )


@bp.route(route="packages/install", methods=["POST"])
@bp.function_name("install_package")
@openapi_endpoint(
    path="/packages/install",
    method="POST",
    summary="Install a package or requirements.txt",
    description="Install a specific package or all packages from requirements.txt",
    tags=["Package Management"],
    request_model=InstallPackageRequest,
    response_model=PackageInstallResponse,
)
@with_request_context
@require_platform_admin
async def install_package(req: func.HttpRequest) -> func.HttpResponse:
    """Install a specific package or all packages from requirements.txt"""
    try:
        connection_id = req.headers.get("X-PubSub-ConnectionId")

        # Parse request body
        try:
            body = req.get_json()
        except ValueError:
            body = {}

        package = body.get("package") if body else None
        version = body.get("version") if body else None

        # Generate job ID
        job_id = str(uuid.uuid4())

        # Queue installation job
        connection_string = os.environ.get("AzureWebJobsStorage", "UseDevelopmentStorage=true")
        queue_client = QueueClient.from_connection_string(
            connection_string,
            queue_name="package-installations",
            message_encode_policy=TextBase64EncodePolicy()
        )

        try:
            message = {
                "type": "package_install",
                "job_id": job_id,
                "package": package,
                "version": version,
                "connection_id": connection_id,
                "user_id": getattr(req, "ctx", None).user_id if hasattr(req, "ctx") else "",  # type: ignore
                "user_email": getattr(req, "ctx", None).email if hasattr(req, "ctx") else ""  # type: ignore
            }

            queue_client.send_message(json.dumps(message))
            logger.info(f"Queued package installation job {job_id}")
        finally:
            queue_client.close()

        return func.HttpResponse(
            body=json.dumps({
                "job_id": job_id,
                "status": "queued"
            }),
            mimetype="application/json",
            status_code=202
        )

    except Exception as e:
        logger.error(f"Failed to queue package installation: {e}", exc_info=True)
        return func.HttpResponse(
            body=json.dumps({"error": "internal_error", "message": str(e)}),
            mimetype="application/json",
            status_code=500
        )
