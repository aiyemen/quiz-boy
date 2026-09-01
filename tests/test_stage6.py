"""
Stage 6 Tests: Quiz Engine, Sessions, Version Snapshot, Answer Recording, Anti-cheat.
"""
import pytest
from app.database.models import Option, Question, Quiz, QuizState
from app.quiz_engine.service import (
    AnswerAlreadySubmittedError,
    QuizEngineService,
    SessionError,
)


@pytest.mark.asyncio
async def test_quiz_engine_session_and_answers(db_session, sample_user, other_user):
    """Verifies starting session, taking question snapshot, recording answer, and preventing duplicates."""
    # Create quiz
    quiz = Quiz(creator_id=sample_user.id, title="اختبار التاريخ", state=QuizState.READY, version=1)
    db_session.add(quiz)
    await db_session.flush()

    q1 = Question(quiz_id=quiz.id, text="في أي عام وقعت معركة حطين؟", order_num=1)
    db_session.add(q1)
    await db_session.flush()

    opt1 = Option(question_id=q1.id, text="1187 م", is_correct=True, order_num=1)
    opt2 = Option(question_id=q1.id, text="1192 م", is_correct=False, order_num=2)
    db_session.add_all([opt1, opt2])
    await db_session.commit()

    # Participant starts session
    session_obj = await QuizEngineService.start_quiz_session(db_session, quiz.id, other_user.id)
    assert session_obj.id is not None
    assert session_obj.participant_id == other_user.id
    assert session_obj.quiz_version == 1
    assert len(session_obj.snapshot_data) == 1

    # Record correct answer
    ans_res = await QuizEngineService.record_answer(
        session=db_session,
        session_id=session_obj.id,
        user_id=other_user.id,
        question_id=q1.id,
        option_id=opt1.id,
    )
    assert ans_res["is_correct"] is True
    assert ans_res["is_finished"] is True

    # Duplicate answer on same question must raise AnswerAlreadySubmittedError
    with pytest.raises(AnswerAlreadySubmittedError):
        await QuizEngineService.record_answer(
            session=db_session,
            session_id=session_obj.id,
            user_id=other_user.id,
            question_id=q1.id,
            option_id=opt2.id,
        )
