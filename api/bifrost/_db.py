"""
Synchronous database access for Bifrost SDK.

Provides a thread-safe sync SQLAlchemy session factory using psycopg2.
This is used by SDK modules that run inside workflow threads (which have their own
event loop via asyncio.run()), where async database connections won't work due to
event loop affinity issues with asyncpg.

Uses the same ORM models as the async database layer for type safety.
"""

import logging
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Generator
from uuid import UUID

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

logger = logging.getLogger(__name__)

# Global sync engine and session factory - initialized lazily
_sync_engine = None
_sync_session_factory: sessionmaker[Session] | None = None


def _get_sync_database_url() -> str:
    """Get the sync database URL from settings."""
    from src.config import get_settings
    settings = get_settings()
    # Convert async URL to sync: postgresql+asyncpg:// -> postgresql+psycopg2://
    return settings.database_url.replace("+asyncpg", "+psycopg2")


def _get_sync_engine():
    """Get or create the sync SQLAlchemy engine."""
    global _sync_engine
    if _sync_engine is None:
        sync_url = _get_sync_database_url()
        logger.debug("Creating sync SQLAlchemy engine with psycopg2")
        _sync_engine = create_engine(
            sync_url,
            pool_size=5,
            max_overflow=5,
            pool_pre_ping=True,
        )
    return _sync_engine


def get_sync_session_factory() -> sessionmaker[Session]:
    """
    Get or create the sync session factory.

    Returns:
        sessionmaker instance for sync sessions
    """
    global _sync_session_factory
    if _sync_session_factory is None:
        engine = _get_sync_engine()
        _sync_session_factory = sessionmaker(
            bind=engine,
            expire_on_commit=False,
            autoflush=False,
        )
    return _sync_session_factory


@contextmanager
def get_sync_session() -> Generator[Session, None, None]:
    """
    Get a sync database session.

    Usage:
        with get_sync_session() as db:
            role = db.query(Role).filter(Role.id == role_id).first()

    Automatically commits on success, rolls back on exception.
    """
    session_factory = get_sync_session_factory()
    session = session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def close_sync_pool() -> None:
    """Close all connections in the sync pool. Call on shutdown."""
    global _sync_engine, _sync_session_factory
    if _sync_engine is not None:
        _sync_engine.dispose()
        _sync_engine = None
        _sync_session_factory = None
        logger.debug("Closed sync SQLAlchemy engine")


# =============================================================================
# Execution Log Helper (for real-time logging from workflow threads)
# =============================================================================


def append_log_sync(
    execution_id: str | UUID,
    level: str,
    message: str,
    metadata: dict[str, Any] | None = None,
    timestamp: datetime | None = None,
) -> None:
    """
    Append an execution log entry synchronously.

    This is used for real-time log streaming from workflow threads where
    async database access isn't possible due to event loop constraints.

    Args:
        execution_id: Execution UUID (string or UUID)
        level: Log level (INFO, WARNING, ERROR, DEBUG, CRITICAL)
        message: Log message text
        metadata: Optional JSON metadata
        timestamp: Optional timestamp (defaults to now)
    """
    from src.models.orm import ExecutionLog

    exec_uuid = UUID(execution_id) if isinstance(execution_id, str) else execution_id
    ts = timestamp or datetime.utcnow()

    with get_sync_session() as db:
        log_entry = ExecutionLog(
            execution_id=exec_uuid,
            level=level.upper(),
            message=message,
            log_metadata=metadata,
            timestamp=ts,
        )
        db.add(log_entry)
