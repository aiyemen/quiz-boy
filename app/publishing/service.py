"""
Publishing Service for dispatching quizzes to Telegram channels / groups.
Validates ownership, rechecks permissions, and transitions quiz to PUBLISHED / ACTIVE.
"""
from typing import Optional
from aiogram import Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Quiz, QuizState
from app.permissions.service import PermissionDeniedError, PermissionService
from app.services.quiz_edit_service import QuizEditService


class PublishingError(Exception):
    pass


class PublishingService:
    @staticmethod
    async def publish_quiz_to_target(
        bot: Bot,
        session: AsyncSession,
        quiz_id: int,
        target_id: int,
        user_id: int,
    ) -> dict:
        """
        Publishes a quiz to a channel/group target.
        - Verifies quiz ownership
        - Verifies target ownership
        - Rechecks bot permissions in the target chat
        - Sends start post to target chat with inline button
        - Updates quiz state to PUBLISHED and freezes it
        """
        quiz = await QuizEditService.get_user_quiz(session, quiz_id, user_id, load_questions=True)
        if not quiz.questions:
            raise PublishingError("لا يمكن نشر اختبار فارغ بدون أسئلة.")

        target = await PermissionService.get_target_by_id(session, target_id, user_id)

        # Re-check bot permissions in chat
        perms = await PermissionService.check_bot_chat_permissions(bot, target.chat_id)
        if not perms.get("can_post_messages"):
            raise PermissionDeniedError(
                f"⚠️ البوت لا يملك صلاحية إرسال الرسائل في {target.chat_title}. يرجى ترقيته إلى مسؤول."
            )

        # Format start announcement
        bot_info = await bot.get_me()
        bot_username = bot_info.username

        text = (
            f"📚 <b>{quiz.title}</b>\n\n"
            f"❓ عدد الأسئلة: {len(quiz.questions)}\n"
            f"⏱️ اضغط على الزر أدناه لبدء الاختبار في المحادثة الخاصة مع البوت 👇"
        )

        start_url = f"https://t.me/{bot_username}?start=quiz_{quiz.id}"
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="🚀 ابدأ الاختبار الآن",
                        url=start_url,
                    )
                ]
            ]
        )

        try:
            sent_msg = await bot.send_message(
                chat_id=target.chat_id,
                text=text,
                parse_mode="HTML",
                reply_markup=keyboard,
            )
        except Exception as e:
            raise PublishingError(f"تعذر إرسال الاختبار إلى المحادثة: {str(e)}") from e

        # Update quiz state
        quiz.state = QuizState.PUBLISHED
        quiz.is_frozen = True
        await session.commit()
        await session.refresh(quiz)

        return {
            "success": True,
            "message_id": sent_msg.message_id,
            "target_title": target.chat_title,
            "quiz_id": quiz.id,
            "state": quiz.state.value,
        }
