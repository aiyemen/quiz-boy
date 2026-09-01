"""
Bot factory and dispatcher setup for QuizBot Arabic.
Registers all routers, middleware, and handlers.
"""
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from app.config.settings import settings
from app.handlers import (
    common_router,
    preview_edit_router,
    publishing_router,
    quick_create_router,
    quiz_engine_router,
    quiz_start_router,
    results_router,
)
from app.middlewares.user_resolution import UserResolutionMiddleware


def create_bot() -> Bot:
    """Creates and configures the aiogram Bot instance."""
    return Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )


def create_dispatcher() -> Dispatcher:
    """Creates and configures the aiogram Dispatcher instance with all middlewares and routers."""
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    # Register User Resolution Middleware on both messages and callback queries
    user_middleware = UserResolutionMiddleware()
    dp.message.middleware(user_middleware)
    dp.callback_query.middleware(user_middleware)

    # Register all feature routers
    dp.include_router(common_router)
    dp.include_router(quick_create_router)
    dp.include_router(preview_edit_router)
    dp.include_router(publishing_router)
    dp.include_router(quiz_start_router)
    dp.include_router(quiz_engine_router)
    dp.include_router(results_router)

    return dp
