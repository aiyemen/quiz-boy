"""
Publishing Handlers for QuizBot Arabic.
Enables selecting registered channels/groups, checking permissions, and publishing tests.
"""
from aiogram import Bot, F, Router, types
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from app.keyboards.publishing import get_targets_selection_keyboard
from app.permissions.service import PermissionDeniedError, PermissionService
from app.publishing.service import PublishingError, PublishingService
from app.services.quiz_edit_service import QuizEditService

router = Router(name="publishing_router")


@router.message(F.text == "📢 أماكن النشر")
@router.callback_query(F.data == "menu_targets")
async def list_user_targets(
    event: types.Message | types.CallbackQuery,
    user_id: int,
    db_session: AsyncSession,
):
    """Lists registered channels and groups for user."""
    targets = await PermissionService.get_user_targets(db_session, user_id)

    if not targets:
        text = (
            "📢 <b>أماكن النشر (القنوات والمجموعات):</b>\n\n"
            "لم تقم بتسجيل أي قناة أو مجموعة بعد.\n\n"
            "📌 <b>طريقة إضافة مكان نشر:</b>\n"
            "1. أضف البوت إلى قناتك أو مجموعتك.\n"
            "2. امنح البوت صلاحيات الإشراف (إرسال الرسائل).\n"
            "3. قم بتوجيه (Forward) أي رسالة من القناة إلى البوت هنا لتسجيلها تلقائياً."
        )
    else:
        lines = ["📢 <b>أماكن النشر المسجلة لديك:</b>\n"]
        for t in targets:
            icon = "📢" if t.chat_type == "channel" else "👥"
            lines.append(f"• {icon} <b>{t.chat_title}</b> (<code>{t.chat_id}</code>)")
        text = "\n".join(lines)

    if isinstance(event, types.CallbackQuery):
        await event.message.answer(text, parse_mode="HTML")
        await event.answer()
    else:
        await event.answer(text, parse_mode="HTML")


@router.callback_query(F.data.startswith("publish_quiz_"))
async def prompt_publish_target(
    callback: types.CallbackQuery,
    user_id: int,
    db_session: AsyncSession,
):
    """Prompts user to choose publishing target for quiz."""
    quiz_id = int(callback.data.split("_")[2])
    try:
        quiz = await QuizEditService.get_user_quiz(db_session, quiz_id, user_id, load_questions=False)
        targets = await PermissionService.get_user_targets(db_session, user_id)

        if not targets:
            text = (
                f"📢 <b>نشر اختبار: {quiz.title}</b>\n\n"
                "⚠️ لم تسجل أي قناة أو مجموعة حتى الآن.\n"
                "أضف البوت إلى قناتك كمسؤول ثم وجّه أي رسالة منها هنا لتسجيلها."
            )
            await callback.message.edit_text(text, parse_mode="HTML")
            return

        text = f"📢 <b>نشر اختبار: {quiz.title}</b>\n\nاختر مكان النشر أدناه:"
        await callback.message.edit_text(
            text,
            parse_mode="HTML",
            reply_markup=get_targets_selection_keyboard(quiz.id, targets),
        )
    except Exception as e:
        await callback.message.answer(f"⚠️ خطأ: {str(e)}")
    finally:
        await callback.answer()


@router.callback_query(F.data.startswith("target_sel_"))
async def execute_publish_to_target(
    callback: types.CallbackQuery,
    bot: Bot,
    user_id: int,
    db_session: AsyncSession,
):
    """Executes publishing to chosen target."""
    parts = callback.data.split("_")
    quiz_id = int(parts[2])
    target_id = int(parts[3])

    try:
        result = await PublishingService.publish_quiz_to_target(
            bot=bot,
            session=db_session,
            quiz_id=quiz_id,
            target_id=target_id,
            user_id=user_id,
        )

        success_text = (
            f"🎉 <b>تم نشر الاختبار بنجاح!</b>\n\n"
            f"📢 <b>الجهة:</b> {result['target_title']}\n"
            f"🏷️ <b>الحالة:</b> منشور (PUBLISHED)\n\n"
            "أصبح بإمكان المشتركين البدء في حل الاختبار الآن."
        )
        await callback.message.edit_text(success_text, parse_mode="HTML")
    except (PermissionDeniedError, PublishingError) as e:
        await callback.message.answer(f"⚠️ {str(e)}", parse_mode="HTML")
    except Exception as e:
        await callback.message.answer(f"⚠️ حدث خطأ غير متوقع أثناء النشر: {str(e)}")
    finally:
        await callback.answer()


@router.message(F.forward_from_chat)
async def register_forwarded_chat(
    message: types.Message,
    bot: Bot,
    user_id: int,
    db_session: AsyncSession,
):
    """Auto-registers target chat when user forwards a message from channel/supergroup."""
    chat = message.forward_from_chat
    if not chat:
        return

    try:
        perms = await PermissionService.check_bot_chat_permissions(bot, chat.id)
        target = await PermissionService.register_or_update_target(
            session=db_session,
            user_id=user_id,
            chat_id=chat.id,
            chat_type=chat.type,
            chat_title=chat.title or "قناة/مجموعة بدون عنوان",
            can_post_messages=perms.get("can_post_messages", True),
            can_edit_messages=perms.get("can_edit_messages", True),
        )

        await message.answer(
            f"✅ <b>تم تسجيل مكان النشر بنجاح!</b>\n\n"
            f"📢 <b>الاسم:</b> {target.chat_title}\n"
            f"🆔 <b>المعرف:</b> <code>{target.chat_id}</code>\n"
            f"🏷️ <b>النوع:</b> {target.chat_type}\n\n"
            "يمكنك الآن اختيار هذه القناة/المجموعة عند نشر أي اختبار.",
            parse_mode="HTML",
        )
    except Exception as e:
        await message.answer(f"⚠️ تعذر تسجيل القناة: {str(e)}")
