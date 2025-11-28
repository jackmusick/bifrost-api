"""
Bifrost Jobs - Background Worker Service

Main entry point for the background job worker.
Handles RabbitMQ message consumption and scheduled tasks.
"""

import asyncio
import logging
import signal
import sys
from typing import NoReturn

from src.config import get_settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class JobsWorker:
    """
    Background jobs worker.

    Manages:
    - RabbitMQ consumers for workflow execution, git sync, package installation
    - APScheduler for scheduled tasks (CRON jobs, cleanup, OAuth refresh)
    """

    def __init__(self):
        self.settings = get_settings()
        self.running = False
        self._shutdown_event = asyncio.Event()

    async def start(self) -> None:
        """Start the worker."""
        self.running = True
        logger.info("Starting Bifrost Jobs Worker...")
        logger.info(f"Environment: {self.settings.environment}")

        # TODO: Initialize RabbitMQ connection
        # TODO: Initialize APScheduler
        # TODO: Start consumers

        logger.info("Bifrost Jobs Worker started")
        logger.info("Waiting for messages... (Ctrl+C to stop)")

        # Keep running until shutdown
        await self._shutdown_event.wait()

    async def stop(self) -> None:
        """Stop the worker gracefully."""
        logger.info("Stopping Bifrost Jobs Worker...")
        self.running = False
        self._shutdown_event.set()

        # TODO: Close RabbitMQ connection
        # TODO: Stop APScheduler

        logger.info("Bifrost Jobs Worker stopped")

    def handle_signal(self, signum: int, frame) -> None:
        """Handle shutdown signals."""
        logger.info(f"Received signal {signum}, initiating shutdown...")
        asyncio.create_task(self.stop())


async def main() -> NoReturn:
    """Main entry point."""
    worker = JobsWorker()

    # Register signal handlers
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, lambda s=sig: worker.handle_signal(s, None))

    try:
        await worker.start()
    except Exception as e:
        logger.error(f"Worker error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
