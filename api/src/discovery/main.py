"""
Bifrost Discovery - File Watcher Service

Main entry point for the discovery service.
Watches workspace for file changes and syncs discovered metadata to database.

This container is responsible for:
- Watching workspace for file changes (Watchdog)
- Building initial index on startup
- Syncing discovered workflows/providers/forms to database
- Processing pending DB operations from file watcher events

IMPORTANT: This container MUST run as a single instance (replicas: 1)
because the file watcher needs exclusive control over DB sync to prevent
race conditions.
"""

import asyncio
import logging
import signal
import sys

from src.config import get_settings
from src.core.database import init_db, close_db

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# Suppress noisy third-party loggers
logging.getLogger("watchdog").setLevel(logging.WARNING)
logging.getLogger("watchdog.observers.inotify_buffer").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


class Discovery:
    """
    Discovery service.

    Manages:
    - File system watcher for workspace directories
    - Initial index building and DB sync on startup
    - Background task for processing pending DB operations
    """

    def __init__(self):
        self.settings = get_settings()
        self.running = False
        self._shutdown_event = asyncio.Event()
        self._db_sync_task: asyncio.Task | None = None

    async def start(self) -> None:
        """Start the discovery service."""
        self.running = True
        logger.info("Starting Bifrost Discovery...")
        logger.info(f"Environment: {self.settings.environment}")

        # Initialize database connection
        logger.info("Initializing database connection...")
        await init_db()
        logger.info("Database connection established")

        # Initialize workspace file watcher and sync to database
        logger.info("Initializing workspace file watcher...")
        await self._start_watcher_and_sync()

        # Start background task for processing pending DB operations
        self._db_sync_task = asyncio.create_task(self._db_sync_loop())

        logger.info("Bifrost Discovery started")
        logger.info("Watching for file changes... (Ctrl+C to stop)")

        # Keep running until shutdown
        await self._shutdown_event.wait()

    async def _start_watcher_and_sync(self) -> None:
        """Initialize file watcher and perform initial DB sync."""
        try:
            from shared.discovery import get_workspace_paths
            from shared.discovery_watcher import (
                build_initial_index,
                start_watcher,
                sync_to_database,
                get_index_stats,
            )

            workspace_paths = get_workspace_paths()
            if workspace_paths:
                # Build in-memory index
                build_initial_index(workspace_paths)

                # Sync to database (startup verification)
                logger.info("Syncing discovery index to database...")
                counts = await sync_to_database()
                logger.info(
                    f"Database sync complete: {counts['workflows']} workflows, "
                    f"{counts['providers']} providers, {counts['forms']} forms"
                )

                # Start file watcher
                start_watcher(workspace_paths)

                stats = get_index_stats()
                logger.info(
                    f"Workspace watcher started: {stats['workflows']} workflows, "
                    f"{stats['providers']} providers, {stats['forms']} forms indexed"
                )
            else:
                logger.warning("No workspace paths configured - watcher not started")

        except Exception as e:
            logger.error(f"Failed to initialize workspace watcher: {e}", exc_info=True)
            raise

    async def _db_sync_loop(self) -> None:
        """
        Background task to process file watcher events and sync to database.

        Event-driven: waits for file change events instead of polling.
        - For form changes: processes pending operations (fast)
        - For Python file changes: does full import-based scan (needed for parameters)
        """
        from shared.discovery_watcher import (
            wait_for_db_ops,
            process_pending_db_ops,
            has_pending_db_ops,
            python_files_need_sync,
            sync_to_database,
        )

        logger.info("Starting event-driven DB sync loop...")

        while self.running:
            try:
                # Wait for file change events (blocks until event or timeout)
                # Timeout allows periodic check of self.running for graceful shutdown
                event_triggered = await asyncio.get_event_loop().run_in_executor(
                    None, wait_for_db_ops, 30.0  # 30 second timeout
                )

                if not self.running:
                    break

                if event_triggered or has_pending_db_ops():
                    # Check if Python files changed - need full import scan
                    if python_files_need_sync():
                        logger.info("Python files changed, running full sync...")
                        counts = await sync_to_database()
                        logger.info(
                            f"Full sync complete: {counts['workflows']} workflows, "
                            f"{counts['providers']} providers, {counts['forms']} forms"
                        )
                    else:
                        # Just process pending form operations (fast)
                        processed = await process_pending_db_ops()
                        if processed > 0:
                            logger.info(f"Processed {processed} file change events")

            except Exception as e:
                logger.error(f"Error in DB sync loop: {e}", exc_info=True)
                await asyncio.sleep(5)  # Back off on error

    async def stop(self) -> None:
        """Stop the discovery service gracefully."""
        logger.info("Stopping Bifrost Discovery...")
        self.running = False

        # Cancel DB sync task
        if self._db_sync_task:
            self._db_sync_task.cancel()
            try:
                await self._db_sync_task
            except asyncio.CancelledError:
                pass

        # Stop file watcher
        try:
            from shared.discovery_watcher import stop_watcher
            stop_watcher()
            logger.info("File watcher stopped")
        except Exception as e:
            logger.error(f"Error stopping file watcher: {e}")

        # Close database connections
        await close_db()
        logger.info("Database connections closed")

        self._shutdown_event.set()
        logger.info("Bifrost Discovery stopped")

    def handle_signal(self, signum: int, frame) -> None:
        """Handle shutdown signals."""
        logger.info(f"Received signal {signum}, initiating shutdown...")
        asyncio.create_task(self.stop())


async def main() -> None:
    """Main entry point."""
    discovery = Discovery()

    # Register signal handlers
    def make_handler(s: signal.Signals) -> None:
        discovery.handle_signal(int(s), None)

    loop = asyncio.get_running_loop()
    loop.add_signal_handler(signal.SIGINT, make_handler, signal.SIGINT)
    loop.add_signal_handler(signal.SIGTERM, make_handler, signal.SIGTERM)

    try:
        await discovery.start()
    except Exception as e:
        logger.error(f"Discovery error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
