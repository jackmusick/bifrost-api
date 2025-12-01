"""
Application Configuration

Uses pydantic-settings for environment variable loading with validation.
All configuration is centralized here for easy management.
"""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    Environment variables can be set directly or via .env file.
    All secrets should be provided via environment variables in production.
    """

    model_config = SettingsConfigDict(
        env_prefix="BIFROST_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ==========================================================================
    # Environment
    # ==========================================================================
    environment: Literal["development", "testing", "production"] = Field(
        default="development",
        description="Runtime environment"
    )

    debug: bool = Field(
        default=False,
        description="Enable debug mode"
    )

    # ==========================================================================
    # Database (PostgreSQL)
    # ==========================================================================
    database_url: str = Field(
        default="postgresql+asyncpg://bifrost:bifrost_dev@localhost:5432/bifrost",
        description="Async PostgreSQL connection URL"
    )

    database_url_sync: str = Field(
        default="postgresql://bifrost:bifrost_dev@localhost:5432/bifrost",
        description="Sync PostgreSQL connection URL (for Alembic)"
    )

    database_pool_size: int = Field(
        default=5,
        description="Database connection pool size"
    )

    database_max_overflow: int = Field(
        default=10,
        description="Max overflow connections beyond pool size"
    )

    # ==========================================================================
    # RabbitMQ
    # ==========================================================================
    rabbitmq_url: str = Field(
        default="amqp://bifrost:bifrost_dev@localhost:5672/",
        description="RabbitMQ connection URL"
    )

    # ==========================================================================
    # Redis
    # ==========================================================================
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL"
    )

    # ==========================================================================
    # Security
    # ==========================================================================
    secret_key: str = Field(
        default="dev-secret-key-change-in-production-must-be-32-chars",
        description="Secret key for JWT signing and encryption",
        min_length=32
    )

    algorithm: str = Field(
        default="HS256",
        description="JWT signing algorithm"
    )

    access_token_expire_minutes: int = Field(
        default=30,
        description="Access token expiration time in minutes"
    )

    refresh_token_expire_days: int = Field(
        default=7,
        description="Refresh token expiration time in days"
    )

    # ==========================================================================
    # CORS
    # ==========================================================================
    cors_origins: str = Field(
        default="http://localhost:3000,http://localhost:8000",
        description="Comma-separated list of allowed CORS origins"
    )

    @computed_field
    @property
    def cors_origins_list(self) -> list[str]:
        """Parse CORS origins into a list."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    # ==========================================================================
    # File Storage
    # ==========================================================================
    workspace_path: str = Field(
        default="/workspace",
        description="Path to workspace directory for user workflows"
    )

    temp_path: str = Field(
        default="/tmp/bifrost",
        description="Path to temporary storage directory"
    )

    # ==========================================================================
    # Development User (for local development only)
    # ==========================================================================
    dev_user_email: str = Field(
        default="admin@localhost",
        description="Default dev user email"
    )

    dev_user_password: str = Field(
        default="admin",
        description="Default dev user password"
    )

    # ==========================================================================
    # Server
    # ==========================================================================
    host: str = Field(
        default="0.0.0.0",
        description="Server host"
    )

    port: int = Field(
        default=8000,
        description="Server port"
    )

    # ==========================================================================
    # Computed Properties
    # ==========================================================================
    @computed_field
    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.environment == "development"

    @computed_field
    @property
    def is_testing(self) -> bool:
        """Check if running in testing mode."""
        return self.environment == "testing"

    @computed_field
    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.environment == "production"

    def validate_paths(self) -> None:
        """
        Validate that required filesystem paths exist.

        Raises:
            ValueError: If workspace path doesn't exist
        """
        workspace = Path(self.workspace_path)
        if not workspace.exists():
            raise ValueError(
                f"Workspace path does not exist: {self.workspace_path}. "
                "Please create it or set WORKSPACE_PATH environment variable."
            )

        # Create temp path if it doesn't exist
        temp = Path(self.temp_path)
        temp.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    """
    Get cached settings instance.

    Uses lru_cache to ensure settings are only loaded once.
    """
    return Settings()
