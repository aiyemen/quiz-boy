"""
Main Application Entry Point for QuizBot Arabic.
Supports Long Polling and Webhook modes with graceful shutdown and structured logging.
"""
import asyncio
import logging
import signal
import sys

from app.bot import create_bot, create_dispatcher
from app.config.settings import settings
from app.database.session import close_db, init_db


def setup_logging() -> None:
    """Configures logging format without leaking tokens or sensitive info."""
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )
    # Suppress verbose HTTP logging
    logging.getLogger("aiogram.event").setLevel(logging.WARNING)


async def main() -> None:
    setup_logging()
    logger = logging.getLogger("quizbot")
    logger.info("Starting QuizBot Arabic (Environment: %s)...", settings.ENVIRONMENT)

    # Initialize Database Schema if in SQLite dev mode
    if settings.is_sqlite:
        logger.info("Initializing database tables...")
        await init_db()

    bot = create_bot()
    dp = create_dispatcher()

    stop_event = asyncio.Event()

    def signal_handler():
        logger.info("Shutdown signal received. Stopping bot gracefully...")
        stop_event.set()

    # Register signal handlers for SIGINT & SIGTERM
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, signal_handler)
        except NotImplementedError:
            pass

    try:
        if settings.WEBHOOK_URL:
            logger.info("Running in Webhook mode on %s%s", settings.WEBHOOK_URL, settings.WEBHOOK_PATH)
            await bot.set_webhook(f"{settings.WEBHOOK_URL}{settings.WEBHOOK_PATH}")
            # In a production webhook server (e.g. aiohttp/FastAPI), the app runner would start here.
            # For standard polling or webhook loop:
            await stop_event.wait()
        else:
            logger.info("Running in Long Polling mode...")
            await bot.delete_webhook(drop_pending_updates=True)
            polling_task = asyncio.create_task(dp.start_polling(bot))
            await stop_event.wait()
            polling_task.cancel()
    except asyncio.CancelledError:
        pass
    except Exception as e:
        logger.error("Fatal error during bot execution: %s", str(e), exc_info=False)
    finally:
        logger.info("Cleaning up resources and closing database connections...")
        await bot.session.close()
        await close_db()
        logger.info("QuizBot Arabic shutdown complete.")


if __name__ == "__main__":
    asyncio.run(main())
