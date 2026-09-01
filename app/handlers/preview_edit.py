"""
Preview and Edit Handlers.
Allows users to list their quizzes, preview questions, edit titles, and delete quizzes.
"""
from aiogram import F, Router, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession

from app.keyboards.edit import get_quiz_actions_keyboard
from app.services.quiz_edit_service import QuizEditService, QuizFrozenError

router = Router(name="preview_edit_router")


class EditTitleStates(StatesGroup):
    waiting_new_title = State()


@router.message(F.text == "📝 اختباراتي")
@router.callback_query(F.data == "menu_my_quizzes")
async def list_my_quizzes(
    event: types.Message | types.CallbackQuery,
    user_id: int,
    db_session: AsyncSession,
):
    """Lists all quizzes created by the current user."""
    quizzes = await QuizEditService.get_user_quizzes(db_session, user_id)

    if not quizzes:
        text = "📝 <b>ليس لديك أي اختبارات منشأة حالياً.</b>\n\nاضغط على ⚡ <b>إنشاء سريع</b> لإنشاء أول اختبار لك!"
        if isinstance(event, types.CallbackQuery):
            await event.message.answer(text, parse_mode="HTML")
            await event.answer()
        else:
            await event.answer(text, parse_mode="HTML")
        return

    buttons = []
    state_icons = {
        "DRAFT": "📝",
        "READY": "✅",
        "PUBLISHED": "📢",
        "ACTIVE": "🟢",
        "ARCHIVED": "📦",
    }

    for q in quizzes:
        icon = state_icons.get(q.state.value, "📚")
        buttons.append([
            types.InlineKeyboardButton(
                text=f"{icon} {q.title} ({len(q.questions)} أسئلة)",
                callback_data=f"manage_quiz_{q.id}",
            )
        ])

    keyboard = types.InlineKeyboardMarkup(inline_keyboard=buttons)
    text = "📋 <b>قائمة اختباراتك:</b>\nاختر اختباراً لعرض تفاصيله أو إدارته:"

    if isinstance(event, types.CallbackQuery):
        await event.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
        await event.answer()
    else:
        await event.answer(text, parse_mode="HTML", reply_markup=keyboard)


@router.callback_query(F.data.startswith("manage_quiz_"))
async def manage_quiz_callback(
    callback: types.CallbackQuery,
    user_id: int,
    db_session: AsyncSession,
):
    """Displays single quiz management actions."""
    quiz_id = int(callback.data.split("_")[2])
    try:
        quiz = await QuizEditService.get_user_quiz(db_session, quiz_id, user_id, load_questions=True)
        text = (
            f"📚 <b>{quiz.title}</b>\n\n"
            f"🏷️ <b>الحالة:</b> {quiz.state.value}\n"
            f"🔢 <b>الإصدار:</b> v{quiz.version}\n"
            f"❓ <b>عدد الأسئلة:</b> {len(quiz.questions)}\n"
            f"🔒 <b>مجمّد ضد التعديل:</b> {'نعم (نشط)' if quiz.is_frozen else 'لا'}"
        )
        await callback.message.edit_text(
            text,
            parse_mode="HTML",
            reply_markup=get_quiz_actions_keyboard(quiz.id, quiz.state.value),
        )
    except Exception as e:
        await callback.message.answer(f"⚠️ خطأ: {str(e)}")
    finally:
        await callback.answer()


@router.callback_query(F.data.startswith("preview_quiz_"))
async def preview_quiz_questions(
    callback: types.CallbackQuery,
    user_id: int,
    db_session: AsyncSession,
):
    """Previews all questions in the quiz."""
    quiz_id = int(callback.data.split("_")[2])
    try:
        quiz = await QuizEditService.get_user_quiz(db_session, quiz_id, user_id, load_questions=True)

        lines = [f"👁️ <b>معاينة أسئلة: {quiz.title}</b>\n"]
        labels = ["أ", "ب", "ج", "د", "هـ", "و"]

        for idx, q in enumerate(quiz.questions, start=1):
            lines.append(f"<b>س{idx}: {q.text}</b>")
            for opt_i, opt in enumerate(q.options):
                lbl = labels[opt_i] if opt_i < len(labels) else f"#{opt_i+1}"
                mark = " (✅)" if opt.is_correct else ""
                lines.append(f"   {lbl}) {opt.text}{mark}")
            if q.explanation:
                lines.append(f"   💡 <i>الشرح: {q.explanation}</i>")
            lines.append("")

        text = "\n".join(lines)
        if len(text) > 4000:
            text = text[:3950] + "\n... (تم تقليص النص لطوله)"

        back_kb = types.InlineKeyboardMarkup(
            inline_keyboard=[[types.InlineKeyboardButton(text="🔙 العودة", callback_data=f"manage_quiz_{quiz.id}")]]
        )
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=back_kb)
    except Exception as e:
        await callback.message.answer(f"⚠️ خطأ: {str(e)}")
    finally:
        await callback.answer()


@router.callback_query(F.data.startswith("edit_title_"))
async def prompt_edit_title(
    callback: types.CallbackQuery,
    state: FSMContext,
    user_id: int,
    db_session: AsyncSession,
):
    """Prompts for new quiz title."""
    quiz_id = int(callback.data.split("_")[2])
    await state.set_state(EditTitleStates.waiting_new_title)
    await state.update_data(edit_quiz_id=quiz_id)
    await callback.message.answer("✏️ يرجى إرسال العنوان الجديد للاختبار:")
    await callback.answer()


@router.message(EditTitleStates.waiting_new_title)
async def process_edit_title(
    message: types.Message,
    state: FSMContext,
    user_id: int,
    db_session: AsyncSession,
):
    """Saves new title."""
    data = await state.get_data()
    quiz_id = data.get("edit_quiz_id")
    new_title = message.text.strip()

    if not new_title:
        await message.answer("⚠️ يرجى إدخال عنوان صالح.")
        return

    try:
        quiz = await QuizEditService.update_quiz_title(db_session, quiz_id, user_id, new_title)
        await state.clear()
        await message.answer(
            f"✅ تم تحديث عنوان الاختبار إلى: <b>{quiz.title}</b>",
            parse_mode="HTML",
            reply_markup=get_quiz_actions_keyboard(quiz.id, quiz.state.value),
        )
    except Exception as e:
        await message.answer(f"⚠️ خطأ: {str(e)}")


@router.callback_query(F.data.startswith("delete_quiz_"))
async def delete_quiz_callback(
    callback: types.CallbackQuery,
    user_id: int,
    db_session: AsyncSession,
):
    """Deletes a quiz."""
    quiz_id = int(callback.data.split("_")[2])
    try:
        await QuizEditService.delete_quiz(db_session, quiz_id, user_id)
        await callback.message.edit_text("🗑️ تم حذف الاختبار بنجاح.")
    except Exception as e:
        await callback.message.answer(f"⚠️ خطأ: {str(e)}")
    finally:
        await callback.answer()
