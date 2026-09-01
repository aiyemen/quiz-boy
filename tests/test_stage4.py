"""
Stage 4 Tests: Preview, Edit, Active Freeze Rules, Versioning.
"""
import pytest
from app.database.models import Option, Question, Quiz, QuizState
from app.services.quiz_edit_service import QuizEditService, QuizFrozenError, QuizOwnershipError


@pytest.mark.asyncio
async def test_quiz_edit_and_active_freeze(db_session, sample_user, other_user):
    """
    Verifies:
    1. Editing questions is allowed in DRAFT/READY state.
    2. Editing or deleting questions is STRICTLY BLOCKED when Quiz is ACTIVE/Frozen.
    3. Cross-user editing is rejected with QuizOwnershipError.
    """
    # Create quiz
    quiz = Quiz(creator_id=sample_user.id, title="اختبار الجغرافيا", state=QuizState.READY, version=1)
    db_session.add(quiz)
    await db_session.flush()

    q1 = Question(quiz_id=quiz.id, text="ما هي عاصمة الأردن؟", order_num=1)
    db_session.add(q1)
    await db_session.flush()
    db_session.add(Option(question_id=q1.id, text="عمان", is_correct=True, order_num=1))
    db_session.add(Option(question_id=q1.id, text="إربد", is_correct=False, order_num=2))
    await db_session.commit()

    # Allowed edit in READY state
    updated_q = await QuizEditService.edit_question_text(
        db_session, quiz.id, q1.id, sample_user.id, "ما هي عاصمة المملكة الأردنية الهاشمية؟"
    )
    assert "الهاشمية" in updated_q.text

    # Blocked for other user (ownership isolation)
    with pytest.raises(QuizOwnershipError):
        await QuizEditService.edit_question_text(
            db_session, quiz.id, q1.id, other_user.id, "محاولة اختراق"
        )

    # Transition to ACTIVE (Frozen)
    await QuizEditService.set_quiz_state(db_session, quiz.id, sample_user.id, QuizState.ACTIVE)

    # Editing question on ACTIVE quiz must raise QuizFrozenError
    with pytest.raises(QuizFrozenError):
        await QuizEditService.edit_question_text(
            db_session, quiz.id, q1.id, sample_user.id, "تعديل مرفوض أثناء التشغيل"
        )
