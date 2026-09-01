"""
Quick Create Handlers.
Implements the core rapid creation workflow with atomic validation and FSM.
"""
from aiogram import F, Router, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import User
from app.keyboards.edit import get_draft_review_keyboard, get_quiz_actions_keyboard
from app.keyboards.main import get_main_menu_reply_keyboard
from app.quick_create.parser import parse_quiz_text
from app.services.draft_service import DraftService

router = Router(name="quick_create_router")


class QuickCreateStates(StatesGroup):
    waiting_title = State()
    waiting_questions = State()


@router.message(F.text == "⚡ إنشاء سريع")
@router.callback_query(F.data == "menu_quick_create")
async def start_quick_create(event: types.Message | types.CallbackQuery, state: FSMContext, user_id: int):
    """Starts the Quick Create flow."""
    await state.set_state(QuickCreateStates.waiting_title)
    text = (
        "⚡ <b>الإنشاء السريع للاختبارات</b>\n\n"
        "يرجى إرسال <b>عنوان أو اسم الاختبار</b> أولاً (مثال: اختبار الكيمياء - الوحدة الأولى):"
    )

    if isinstance(event, types.CallbackQuery):
        await event.message.answer(text, parse_mode="HTML")
        await event.answer()
    else:
        await event.answer(text, parse_mode="HTML")


@router.message(QuickCreateStates.waiting_title)
async def process_quiz_title(
    message: types.Message,
    state: FSMContext,
    user_id: int,
    db_session: AsyncSession,
):
    """Stores quiz title in draft and requests questions block."""
    title = message.text.strip()
    if not title:
        await message.answer("⚠️ يرجى إدخال عنوان صالح للاختبار.")
        return

    # Create draft
    draft = await DraftService.get_or_create_draft(db_session, user_id, title)
    await state.update_data(draft_id=draft.id)
    await state.set_state(QuickCreateStates.waiting_questions)

    prompt = (
        f"📝 تم ضبط عنوان الاختبار: <b>{title}</b>\n\n"
        "الآن، أرسل الأسئلة (سؤال واحد أو حتى 100 سؤال دفعة واحدة):\n\n"
        "<b>مثال:</b>\n"
        "<code>س: ما هي وحدة قياس القوة؟\n"
        "أ: الجول\n"
        "ب: النيوتن\n"
        "ج: الواط\n"
        "ص: ب\n"
        "ش: النيوتن هو وحدة القوة في النظام الدولي.</code>"
    )
    await message.answer(prompt, parse_mode="HTML")


@router.message(QuickCreateStates.waiting_questions)
async def process_questions_batch(
    message: types.Message,
    state: FSMContext,
    user_id: int,
    db_session: AsyncSession,
):
    """
    Parses questions with atomic all-or-nothing validation.
    """
    text = message.text or ""
    parse_result = parse_quiz_text(text)

    if not parse_result.is_valid:
        # Atomic failure - no questions stored
        err_msg = parse_result.error_summary_arabic
        await message.answer(
            f"{err_msg}\n\n"
            "💡 <i>يرجى تصحيح الأخطاء وإعادة إرسال الأسئلة مرة أخرى.</i>",
            parse_mode="HTML",
        )
        return

    # Success: append atomically to draft
    data = await state.get_data()
    draft_id = data.get("draft_id")

    if not draft_id:
        draft = await DraftService.get_or_create_draft(db_session, user_id)
        draft_id = draft.id
        await state.update_data(draft_id=draft_id)

    draft = await DraftService.append_questions_atomic(
        db_session,
        draft_id=draft_id,
        user_id=user_id,
        parsed_questions=parse_result.questions,
    )

    total_q = len(draft.questions_data or [])
    summary_text = (
        f"✅ <b>تم فحص وإضافة {len(parse_result.questions)} سؤال بنجاح!</b>\n\n"
        f"📚 <b>العنوان:</b> {draft.title}\n"
        f"🔢 <b>إجمالي الأسئلة في المسودة:</b> {total_q}\n\n"
        "يمكنك إرسال دفعة أسئلة أخرى لإضافتها، أو الضغط على اعتماد وحفظ الاختبار أدناه 👇"
    )

    await message.answer(
        summary_text,
        parse_mode="HTML",
        reply_markup=get_draft_review_keyboard(draft.id),
    )


@router.callback_query(F.data.startswith("draft_save_"))
async def save_draft_callback(
    callback: types.CallbackQuery,
    state: FSMContext,
    user_id: int,
    db_session: AsyncSession,
):
    """Converts draft into persistent Quiz and shows quiz actions."""
    draft_id = int(callback.data.split("_")[2])
    try:
        quiz = await DraftService.convert_draft_to_quiz(db_session, draft_id, user_id)
        await state.clear()

        text = (
            f"🎉 <b>تم إنشاء الاختبار بنجاح!</b>\n\n"
            f"📚 <b>العنوان:</b> {quiz.title}\n"
            f"❓ <b>عدد الأسئلة:</b> {len(quiz.questions)}\n"
            f"🏷️ <b>الحالة:</b> جاهز للنشر (READY)\n\n"
            "ماذا تود أن تفعل الآن؟"
        )
        await callback.message.edit_text(
            text,
            parse_mode="HTML",
            reply_markup=get_quiz_actions_keyboard(quiz.id, quiz.state.value),
        )
    except Exception as e:
        await callback.message.answer(f"⚠️ حدث خطأ أثناء حفظ الاختبار: {str(e)}")
    finally:
        await callback.answer()


@router.callback_query(F.data.startswith("draft_cancel_"))
async def cancel_draft_callback(
    callback: types.CallbackQuery,
    state: FSMContext,
    user_id: int,
    db_session: AsyncSession,
):
    """Cancels and deletes draft."""
    draft_id = int(callback.data.split("_")[2])
    await DraftService.delete_draft(db_session, draft_id, user_id)
    await state.clear()
    await callback.message.edit_text("❌ تم إلغاء المسودة بنجاح.")
    await callback.answer()
