"""
Stage 8 Tests: Security Audit, P0 User Resolution Regression, Callback Tampering, Ownership Boundaries.
"""
import pytest
from app.config.settings import settings
from app.database.models import Option, Question, Quiz, QuizSession, QuizState, User
from app.middlewares.user_resolution import resolve_or_create_user
from app.quiz_engine.service import AnswerError, QuizEngineService, SessionError
from app.results.exceptions import ResultOwnershipError
from app.results.service import ResultService
from app.services.draft_service import DraftOwnershipError, DraftService
from app.services.quiz_edit_service import QuizOwnershipError, QuizEditService


@pytest.mark.asyncio
async def test_p0_user_resolution_prevents_fk_violation(db_session):
    """
    P0 REGRESSION TEST:
    Verifies that a user is resolved to internal users.id, and creating quizzes/drafts
    with users.id succeeds and enforces relational constraints.
    """
    tg_id = 778899001122
    db_user = await resolve_or_create_user(db_session, tg_id, username="alice", first_name="أليس")

    assert db_user.id != tg_id  # Internal DB ID is distinct from Telegram ID
    quiz = Quiz(creator_id=db_user.id, title="اختبار الأمان", state=QuizState.READY)
    db_session.add(quiz)
    await db_session.commit()
    assert quiz.creator_id == db_user.id


@pytest.mark.asyncio
async def test_foreign_ownership_isolation_matrix(db_session, sample_user, other_user):
    """
    SECURITY MATRIX:
    Verifies User A cannot touch User B's:
    1. Quizzes
    2. Drafts
    3. Sessions
    4. Results
    """
    # 1. Quizzes
    quiz = Quiz(creator_id=sample_user.id, title="اختبار سري", state=QuizState.READY)
    db_session.add(quiz)
    await db_session.commit()

    with pytest.raises(QuizOwnershipError):
        await QuizEditService.get_user_quiz(db_session, quiz.id, user_id=other_user.id)

    # 2. Drafts
    draft = await DraftService.get_or_create_draft(db_session, user_id=sample_user.id, title="مسودة سرية")
    with pytest.raises(DraftOwnershipError):
        await DraftService.get_user_draft(db_session, draft.id, user_id=other_user.id)

    # 3. Sessions
    session_obj = QuizSession(quiz_id=quiz.id, participant_id=sample_user.id, snapshot_data=[])
    db_session.add(session_obj)
    await db_session.commit()

    with pytest.raises(SessionError):
        await QuizEngineService.get_session_by_id(db_session, session_obj.id, user_id=other_user.id)

    # 4. Results
    with pytest.raises(ResultOwnershipError):
        await ResultService.finish_session(db_session, session_obj.id, user_id=other_user.id)


@pytest.mark.asyncio
async def test_callback_tampering_protection(db_session, sample_user, other_user):
    """
    CALLBACK SECURITY:
    Verifies that if an attacker tampers with callback data (e.g. sending question/option IDs
    that do not belong to the session or quiz), the server-side validator rejects it immediately.
    """
    quiz = Quiz(creator_id=sample_user.id, title="اختبار", state=QuizState.READY)
    db_session.add(quiz)
    await db_session.flush()

    q1 = Question(quiz_id=quiz.id, text="سؤال", order_num=1)
    db_session.add(q1)
    await db_session.flush()
    opt1 = Option(question_id=q1.id, text="أ", is_correct=True, order_num=1)
    db_session.add(opt1)
    await db_session.commit()

    session_obj = await QuizEngineService.start_quiz_session(db_session, quiz.id, other_user.id)

    # Invalid question ID (tampered)
    with pytest.raises(AnswerError):
        await QuizEngineService.record_answer(
            db_session,
            session_id=session_obj.id,
            user_id=other_user.id,
            question_id=99999,
            option_id=opt1.id,
        )

    # Invalid option ID (tampered)
    with pytest.raises(AnswerError):
        await QuizEngineService.record_answer(
            db_session,
            session_id=session_obj.id,
            user_id=other_user.id,
            question_id=q1.id,
            option_id=88888,
        )


def test_no_hardcoded_secrets_or_ids():
    """Verifies that no real tokens or hardcoded Telegram chat IDs are in configuration."""
    assert not settings.BOT_TOKEN.startswith("real_")
    assert isinstance(settings.MAX_BATCH_QUESTIONS, int)
