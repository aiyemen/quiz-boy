"""
User Resolution Middleware for Telegram Bot (Aiogram 3.x / Handler Data).
Resolves Telegram from_user.id -> internal users.id in the database.
Guarantees that all handlers and domain services receive the internal database User model.
"""
from typing import Any, Awaitable, Callable, Dict, Optional
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, User as TgUser
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import User
from app.database.session import async_session_factory


async def resolve_or_create_user(
    session: AsyncSession,
    telegram_id: int,
    username: Optional[str] = None,
    first_name: Optional[str] = None,
) -> User:
    """
    Looks up user by telegram_id. If not exists, creates user in DB atomically.
    Returns the internal User entity with valid users.id.
    """
    stmt = select(User).where(User.telegram_id == telegram_id)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()

    if user is None:
        user = User(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
            is_active=True,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
    else:
        # Update profile fields if changed
        updated = False
        if username and user.username != username:
            user.username = username
            updated = True
        if first_name and user.first_name != first_name:
            user.first_name = first_name
            updated = True
        if updated:
            await session.commit()
            await session.refresh(user)

    return user


class UserResolutionMiddleware(BaseMiddleware):
    """
    Aiogram middleware that injects `db_user` and `db_session` into handler data.
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        tg_user: Optional[TgUser] = data.get("event_from_user")
        if not tg_user:
            return await handler(event, data)

        async with async_session_factory() as session:
            db_user = await resolve_or_create_user(
                session=session,
                telegram_id=tg_user.id,
                username=tg_user.username,
                first_name=tg_user.first_name,
            )
            data["db_user"] = db_user
            data["user_id"] = db_user.id  # Internal users.id
            data["db_session"] = session
            return await handler(event, data)
