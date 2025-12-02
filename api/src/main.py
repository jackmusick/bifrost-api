"""
Bifrost API - FastAPI Application

Main entry point for the FastAPI application.
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI

from src.config import get_settings
from src.core.database import close_db, init_db
from src.core.pubsub import manager as pubsub_manager
from src.routers import (
    auth_router,
    mfa_router,
    oauth_router,
    health_router,
    organizations_router,
    users_router,
    roles_router,
    executions_router,
    workflows_router,
    forms_router,
    config_router,
    data_providers_router,
    websocket_router,
    branding_router,
    editor_files_router,
    schedules_router,
    workflow_keys_router,
    logs_router,
    metrics_router,
    packages_router,
    github_router,
    oauth_connections_router,
    endpoints_router,
    file_uploads_router,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan manager.

    Handles startup and shutdown events.
    """
    # Startup
    logger.info("Starting Bifrost API...")
    settings = get_settings()

    # Initialize database
    logger.info("Initializing database connection...")
    await init_db()
    logger.info("Database connection established")

    # Initialize discovery watcher for hot reload
    logger.info("Initializing workspace file watcher...")
    try:
        from shared.discovery import get_workspace_paths
        from shared.discovery_watcher import (
            build_initial_index,
            start_watcher,
            stop_watcher,
            get_index_stats,
        )

        workspace_paths = get_workspace_paths()
        if workspace_paths:
            build_initial_index(workspace_paths)
            start_watcher(workspace_paths)
            stats = get_index_stats()
            logger.info(
                f"Workspace watcher started: {stats['workflows']} workflows, "
                f"{stats['providers']} providers, {stats['forms']} forms indexed"
            )
        else:
            logger.warning("No workspace paths configured - watcher not started")
    except Exception as e:
        logger.warning(f"Failed to initialize workspace watcher: {e}")
        stop_watcher = None  # Ensure we don't try to stop on shutdown

    # Create default admin user if configured via environment variables
    if settings.default_user_email and settings.default_user_password:
        await create_default_user()

    logger.info(f"Bifrost API started in {settings.environment} mode")

    yield

    # Shutdown
    logger.info("Shutting down Bifrost API...")

    # Stop workspace watcher
    try:
        from shared.discovery_watcher import stop_watcher
        stop_watcher()
    except Exception as e:
        logger.warning(f"Error stopping workspace watcher: {e}")

    await pubsub_manager.close()
    await close_db()
    logger.info("Bifrost API shutdown complete")


async def create_default_user() -> None:
    """
    Create default admin user if it doesn't exist.

    Only runs if BIFROST_DEFAULT_USER_EMAIL and BIFROST_DEFAULT_USER_PASSWORD
    environment variables are set. This is useful for automated deployments
    where you want to pre-configure an admin account.

    If not configured, users will go through the setup wizard on first access.
    """
    from src.core.database import get_db_context
    from src.core.security import get_password_hash
    from src.repositories.users import UserRepository

    settings = get_settings()

    if not settings.default_user_email or not settings.default_user_password:
        return

    async with get_db_context() as db:
        user_repo = UserRepository(db)

        # Check if default user exists
        existing = await user_repo.get_by_email(settings.default_user_email)
        if existing:
            logger.info(f"Default user already exists: {settings.default_user_email}")
            return

        # Create default admin user
        hashed_password = get_password_hash(settings.default_user_password)
        user = await user_repo.create_user(
            email=settings.default_user_email,
            hashed_password=hashed_password,
            name="Admin",
            is_superuser=True,
        )
        logger.info(f"Created default admin user: {user.email} (id: {user.id})")


def create_app() -> FastAPI:
    """
    Create and configure FastAPI application.

    Returns:
        Configured FastAPI application instance
    """
    settings = get_settings()

    app = FastAPI(
        title="Bifrost API",
        description="MSP automation platform API",
        version="2.0.0",
        docs_url="/docs" if settings.is_development else None,
        redoc_url="/redoc" if settings.is_development else None,
        openapi_url="/openapi.json" if settings.is_development else None,
        lifespan=lifespan,
    )

    # Note: CORS middleware not needed - frontend proxies all /api requests
    # through Vite dev server (dev) or nginx (prod), making them same-origin.

    # Register routers
    app.include_router(health_router)
    app.include_router(auth_router)
    app.include_router(mfa_router)
    app.include_router(oauth_router)
    app.include_router(organizations_router)
    app.include_router(users_router)
    app.include_router(roles_router)
    app.include_router(executions_router)
    app.include_router(workflows_router)
    app.include_router(forms_router)
    app.include_router(config_router)
    app.include_router(data_providers_router)
    app.include_router(websocket_router)
    app.include_router(branding_router)
    app.include_router(editor_files_router)
    app.include_router(schedules_router)
    app.include_router(workflow_keys_router)
    app.include_router(logs_router)
    app.include_router(metrics_router)
    app.include_router(packages_router)
    app.include_router(github_router)
    app.include_router(oauth_connections_router)
    app.include_router(endpoints_router)
    app.include_router(file_uploads_router)

    # Root endpoint
    @app.get("/")
    async def root():
        return {
            "name": "Bifrost API",
            "version": "2.0.0",
            "docs": "/docs" if settings.is_development else "disabled",
        }

    return app


# Create app instance
app = create_app()


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "src.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.is_development,
    )
