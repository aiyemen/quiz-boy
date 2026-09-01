"""
Results and Ranking Handlers.
Displays participant scores, personal quiz history, and creator leaderboards.
"""
from aiogram import F, Router, types
from sqlalchemy.ext.asyncio import AsyncSession

from app.results.service import RankingService, ResultService

router = Router(name="results_router")


@router.message(F.text == "📊 النتائج")
@router.callback_query(F.data == "menu_results")
async def show_my_results(
    event: types.Message | types.CallbackQuery,
    user_id: int,
    db_session: AsyncSession,
):
    """Lists completed quiz results for current user."""
    results = await ResultService.get_user_results(db_session, user_id)

    if not results:
        text = "📊 <b>سجل نتائجك:</b>\n\nلم تكمل أي اختبار حتى الآن."
    else:
        lines = ["📊 <b>سجل نتائج اختباراتك:</b>\n"]
        for r in results:
            quiz_name = r.quiz.title if r.quiz else "اختبار"
            lines.append(
                f"• <b>{quiz_name}</b>\n"
                f"   الدرجة: {r.correct_answers}/{r.total_questions} ({r.percentage:.1f}%)\n"
                f"   التاريخ: {r.completed_at.strftime('%Y-%m-%d %H:%M')}\n"
            )
        text = "\n".join(lines)

    if isinstance(event, types.CallbackQuery):
        await event.message.answer(text, parse_mode="HTML")
        await event.answer()
    else:
        await event.answer(text, parse_mode="HTML")


@router.callback_query(F.data.startswith("leaderboard_"))
async def show_quiz_leaderboard(
    callback: types.CallbackQuery,
    user_id: int,
    db_session: AsyncSession,
):
    """Displays rankings for a quiz using the RankingService abstraction."""
    quiz_id = int(callback.data.split("_")[1])

    try:
        ranking_svc = RankingService()
        rankings = await ranking_svc.get_quiz_rankings(db_session, quiz_id, requester_id=user_id)

        if not rankings:
            await callback.message.answer("📊 لم يتم اعتماد صيغة لترتيب المتصدرين بعد أو لا توجد نتائج.")
            await callback.answer()
            return

        lines = ["🏆 <b>لوحة المتصدرين للاختبار:</b>\n"]
        for item in rankings:
            lines.append(f"• <b>المتسابق ({item.get('participant_id')}):</b> {item.get('display_text', '')}")

        await callback.message.answer("\n".join(lines), parse_mode="HTML")
    except Exception as e:
        await callback.message.answer(f"⚠️ خطأ: {str(e)}")
    finally:
        await callback.answer()
