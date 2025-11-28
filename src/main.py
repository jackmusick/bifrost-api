"""
Bifrost API - FastAPI Application

Main entry point for the FastAPI application.
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.config import get_settings
from src.core.database import close_db, init_db
from src.routers import auth_router, health_router

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

    # Create default dev user if in development mode
    if settings.is_development:
        await create_dev_user()

    logger.info(f"Bifrost API started in {settings.environment} mode")

    yield

    # Shutdown
    logger.info("Shutting down Bifrost API...")
    await close_db()
    logger.info("Bifrost API shutdown complete")


async def create_dev_user() -> None:
    """
    Create default development user if it doesn't exist.

    Only runs in development mode.
    """
    from src.core.database import get_db_context
    from src.core.security import get_password_hash
    from src.repositories.users import UserRepository

    settings = get_settings()

    async with get_db_context() as db:
        user_repo = UserRepository(db)

        # Check if dev user exists
        existing = await user_repo.get_by_email(settings.dev_user_email)
        if existing:
            logger.info(f"Dev user already exists: {settings.dev_user_email}")
            return

        # Create dev user
        hashed_password = get_password_hash(settings.dev_user_password)
        user = await user_repo.create_user(
            email=settings.dev_user_email,
            hashed_password=hashed_password,
            name="Dev Admin",
            is_superuser=True,
        )
        logger.info(f"Created dev user: {user.email} (id: {user.id})")


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

    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register routers
    app.include_router(health_router)
    app.include_router(auth_router)

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
