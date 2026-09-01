"""
Permission Service for Telegram Channels and Groups.
Checks bot permissions in target chats and manages registered targets per user.
No hardcoded IDs.
"""
from typing import List, Optional
from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import PublishingTarget


class PermissionDeniedError(Exception):
    pass


class TargetNotFoundError(Exception):
    pass


class TargetOwnershipError(TargetNotFoundError):
    pass


class PermissionService:
    @staticmethod
    async def check_bot_chat_permissions(bot: Bot, chat_id: int) -> dict:
        """
        Queries Telegram API for bot member permissions in target chat.
        Returns dict with status and permission booleans.
        """
        try:
            bot_member = await bot.get_chat_member(chat_id=chat_id, user_id=bot.id)
            status = getattr(bot_member, "status", "unknown")
            can_post = getattr(bot_member, "can_post_messages", True)
            can_edit = getattr(bot_member, "can_edit_messages", True)

            # In supergroups/channels, administrator status is required
            is_admin = status in ("administrator", "creator")

            return {
                "is_admin": is_admin,
                "can_post_messages": can_post or is_admin,
                "can_edit_messages": can_edit or is_admin,
                "status": status,
            }
        except TelegramAPIError as e:
            raise PermissionDeniedError(
                f"⚠️ تعذر التحقق من صلاحيات البوت في المحادثة ({chat_id}): تأكد من إضافة البوت كمسؤول."
            ) from e

    @staticmethod
    async def register_or_update_target(
        session: AsyncSession,
        user_id: int,
        chat_id: int,
        chat_type: str,
        chat_title: str,
        can_post_messages: bool = True,
        can_edit_messages: bool = True,
    ) -> PublishingTarget:
        """
        Registers or updates a publishing target for user_id.
        """
        stmt = select(PublishingTarget).where(
            PublishingTarget.user_id == user_id,
            PublishingTarget.chat_id == chat_id,
        )
        result = await session.execute(stmt)
        target = result.scalar_one_or_none()

        if target is None:
            target = PublishingTarget(
                user_id=user_id,
                chat_id=chat_id,
                chat_type=chat_type,
                chat_title=chat_title,
                can_post_messages=can_post_messages,
                can_edit_messages=can_edit_messages,
                is_active=True,
            )
            session.add(target)
        else:
            target.chat_title = chat_title
            target.chat_type = chat_type
            target.can_post_messages = can_post_messages
            target.can_edit_messages = can_edit_messages
            target.is_active = True

        await session.commit()
        await session.refresh(target)
        return target

    register_target = register_or_update_target

    @staticmethod
    async def get_user_targets(
        session: AsyncSession,
        user_id: int,
    ) -> List[PublishingTarget]:
        """Lists active publishing targets registered by user."""
        stmt = (
            select(PublishingTarget)
            .where(
                PublishingTarget.user_id == user_id,
                PublishingTarget.is_active == True,
            )
            .order_by(PublishingTarget.verified_at.desc())
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def get_target_by_id(
        session: AsyncSession,
        target_id: int,
        user_id: int,
    ) -> PublishingTarget:
        """Retrieves target with ownership check."""
        stmt = select(PublishingTarget).where(
            PublishingTarget.id == target_id,
            PublishingTarget.user_id == user_id,
        )
        result = await session.execute(stmt)
        target = result.scalar_one_or_none()

        if target is None:
            raise TargetNotFoundError("مكان النشر غير مسجل أو ليس لديك صلاحية الوصول إليه.")
        return target

    @staticmethod
    async def delete_target(
        session: AsyncSession,
        target_id: int,
        user_id: int,
    ) -> bool:
        """Deletes a publishing target after enforcing ownership."""
        stmt = select(PublishingTarget).where(PublishingTarget.id == target_id)
        result = await session.execute(stmt)
        target = result.scalar_one_or_none()

        if target is None:
            raise TargetNotFoundError("مكان النشر غير موجود.")
        if target.user_id != user_id:
            raise TargetOwnershipError("ليس لديك صلاحية حذف هذا الهدف.")

        await session.delete(target)
        await session.commit()
        return True
