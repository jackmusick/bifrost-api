"""
Pytest configuration for integration tests.

Integration tests use real PostgreSQL, RabbitMQ, and Redis services
provided by docker-compose.test.yml.
"""

import os

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.fixture(scope="session", autouse=True)
def setup_integration_environment():
    """
    Configure environment for integration tests.

    Uses docker-compose.test.yml services:
    - PostgreSQL on port 15432
    - RabbitMQ on port 15672
    - Redis on port 16379
    """
    # Environment variables are set in docker-compose.test.yml
    # These defaults are for running outside of Docker (local development)
    if "BIFROST_DATABASE_URL" not in os.environ:
        os.environ["BIFROST_DATABASE_URL"] = (
            "postgresql+asyncpg://bifrost:bifrost_test@localhost:15432/bifrost_test"
        )
    if "BIFROST_DATABASE_URL_SYNC" not in os.environ:
        os.environ["BIFROST_DATABASE_URL_SYNC"] = (
            "postgresql://bifrost:bifrost_test@localhost:15432/bifrost_test"
        )
    if "BIFROST_RABBITMQ_URL" not in os.environ:
        os.environ["BIFROST_RABBITMQ_URL"] = "amqp://bifrost:bifrost_test@localhost:15672/"
    if "BIFROST_REDIS_URL" not in os.environ:
        os.environ["BIFROST_REDIS_URL"] = "redis://localhost:16379/0"

    yield


@pytest_asyncio.fixture
async def integration_db_session(db_session: AsyncSession) -> AsyncSession:
    """
    Provide a database session for integration tests.

    Wraps the base db_session fixture with integration-specific setup.
    """
    yield db_session


@pytest.fixture(scope="module")
def api_base_url():
    """
    Base URL for API integration tests.

    Default: http://localhost:18000 (docker-compose.test.yml offset port)
    Can be overridden with TEST_API_URL environment variable.
    """
    return os.getenv("TEST_API_URL", "http://localhost:18000")
