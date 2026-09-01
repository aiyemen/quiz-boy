"""
Quiz Start Handlers.
Processes deep links (/start quiz_<id>) and begins interactive quiz sessions.
"""
from aiogram import Router, types
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import User
from app.keyboards.engine import get_question_options_keyboard
from app.quiz_engine.service import QuizEngineService, SessionError

router = Router(name="quiz_start_router")


async def render_question_message(
    message: types.Message,
    session_id: int,
    question_data: dict,
    current_num: int,
    total_num: int,
    quiz_title: str,
):
    """Renders a single quiz question with its inline option buttons."""
    text = (
        f"📚 <b>{quiz_title}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"❓ <b>السؤال ({current_num}/{total_num}):</b>\n\n"
        f"<b>{question_data['text']}</b>"
    )

    keyboard = get_question_options_keyboard(
        session_id=session_id,
        question_id=question_data["id"],
        options=question_data["options"],
    )

    await message.answer(text, parse_mode="HTML", reply_markup=keyboard)


async def handle_quiz_deep_link(
    message: types.Message,
    param: str,
    user_id: int,
    db_user: User,
):
    """Starts or resumes quiz session from deep link parameter (e.g. quiz_42)."""
    try:
        quiz_id = int(param.replace("quiz_", ""))
    except ValueError:
        await message.answer("⚠️ رابط الاختبار غير صالح.")
        return

    # Use database session
    from app.database.session import async_session_factory
    async with async_session_factory() as session:
        try:
            quiz_session = await QuizEngineService.start_quiz_session(
                session=session,
                quiz_id=quiz_id,
                user_id=user_id,
            )

            snapshot = quiz_session.snapshot_data or []
            total_q = len(snapshot)

            # Check if current index is valid
            curr_idx = quiz_session.current_question_index
            if curr_idx >= total_q:
                # Quiz already answered, finish and show result
                from app.results.service import ResultService
                res = await ResultService.finish_session(session, quiz_session.id, user_id)
                summary = ResultService.format_result_arabic(res, quiz_session.quiz.title if quiz_session.quiz else "الاختبار")
                await message.answer(summary, parse_mode="HTML")
                return

            current_q = snapshot[curr_idx]
            quiz_title = quiz_session.quiz.title if quiz_session.quiz else "اختبار"

            await message.answer(
                f"🚀 <b>بدء الاختبار: {quiz_title}</b>\n\n"
                f"يتكون هذا الاختبار من {total_q} أسئلة. بالتوفيق!",
                parse_mode="HTML",
            )

            await render_question_message(
                message=message,
                session_id=quiz_session.id,
                question_data=current_q,
                current_num=curr_idx + 1,
                total_num=total_q,
                quiz_title=quiz_title,
            )

        except SessionError as e:
            await message.answer(f"⚠️ {str(e)}")
        except Exception as e:
            await message.answer(f"⚠️ تعذر بدء الاختبار: {str(e)}")
