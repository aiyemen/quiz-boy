"""
Quiz Engine Interactive Handlers.
Processes answer clicks, advances questions, enforces anti-tampering callback security, and finalizes results.
"""
from aiogram import F, Router, types
from sqlalchemy.ext.asyncio import AsyncSession

from app.keyboards.engine import get_next_question_keyboard
from app.quiz_engine.service import (
    AnswerAlreadySubmittedError,
    AnswerError,
    QuizEngineService,
    SessionError,
)
from app.results.service import ResultService

router = Router(name="quiz_engine_router")


@router.callback_query(F.data.startswith("ans_"))
async def process_answer_callback(
    callback: types.CallbackQuery,
    user_id: int,
    db_session: AsyncSession,
):
    """
    Handles user clicking on an answer option.
    Data format: ans_{session_id}_{question_id}_{option_id}
    """
    parts = callback.data.split("_")
    if len(parts) != 4:
        await callback.answer("⚠️ بيانات غير صالحة.", show_alert=True)
        return

    try:
        session_id = int(parts[1])
        question_id = int(parts[2])
        option_id = int(parts[3])
    except ValueError:
        await callback.answer("⚠️ بيانات غير صالحة.", show_alert=True)
        return

    try:
        ans_result = await QuizEngineService.record_answer(
            session=db_session,
            session_id=session_id,
            user_id=user_id,
            question_id=question_id,
            option_id=option_id,
        )

        is_correct = ans_result["is_correct"]
        status_text = "✅ إجابة صحيحة!" if is_correct else "❌ إجابة خاطئة!"
        await callback.answer(status_text, show_alert=False)

        # Update message with feedback
        explanation = ans_result.get("explanation")
        feedback_lines = [
            callback.message.text or "",
            "\n━━━━━━━━━━━━━━━━━━━━",
            f"<b>{status_text}</b>",
        ]
        if explanation:
            feedback_lines.append(f"💡 <i>الشرح: {explanation}</i>")

        if ans_result["is_finished"]:
            # All questions answered -> Finalize session
            result_obj = await ResultService.finish_session(db_session, session_id, user_id)
            quiz_title = result_obj.quiz.title if result_obj.quiz else "الاختبار"
            summary = ResultService.format_result_arabic(result_obj, quiz_title)

            feedback_lines.append("\n" + summary)
            await callback.message.edit_text(
                "\n".join(feedback_lines),
                parse_mode="HTML",
                reply_markup=None,
            )
        else:
            feedback_lines.append("\nاضغط على الزر أدناه للانتقال للسؤال التالي 👇")
            await callback.message.edit_text(
                "\n".join(feedback_lines),
                parse_mode="HTML",
                reply_markup=get_next_question_keyboard(session_id),
            )

    except AnswerAlreadySubmittedError:
        await callback.answer("⚠️ لقد قمت بالإجابة على هذا السؤال مسبقاً.", show_alert=True)
    except (SessionError, AnswerError) as e:
        await callback.answer(f"⚠️ {str(e)}", show_alert=True)
    except Exception as e:
        await callback.answer("⚠️ حدث خطأ أثناء تسجيل الإجابة.", show_alert=True)


@router.callback_query(F.data.startswith("next_q_"))
async def next_question_callback(
    callback: types.CallbackQuery,
    user_id: int,
    db_session: AsyncSession,
):
    """Fetches and displays the next question in the active session."""
    session_id = int(callback.data.split("_")[2])

    try:
        quiz_session = await QuizEngineService.get_session_by_id(db_session, session_id, user_id)
        snapshot = quiz_session.snapshot_data or []
        total_q = len(snapshot)
        curr_idx = quiz_session.current_question_index

        if curr_idx >= total_q:
            # All answered, show result
            res = await ResultService.finish_session(db_session, session_id, user_id)
            summary = ResultService.format_result_arabic(res, quiz_session.quiz.title if quiz_session.quiz else "الاختبار")
            await callback.message.edit_text(summary, parse_mode="HTML")
            await callback.answer()
            return

        from app.handlers.quiz_start import render_question_message
        current_q = snapshot[curr_idx]
        quiz_title = quiz_session.quiz.title if quiz_session.quiz else "الاختبار"

        # Edit current message or delete and send new
        await callback.message.delete()
        await render_question_message(
            message=callback.message,
            session_id=session_id,
            question_data=current_q,
            current_num=curr_idx + 1,
            total_num=total_q,
            quiz_title=quiz_title,
        )
        await callback.answer()

    except Exception as e:
        await callback.answer(f"⚠️ تعذر تحميل السؤال التالي: {str(e)}", show_alert=True)
