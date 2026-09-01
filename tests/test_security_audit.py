"""
Deep Security Audit Test Suite: User Resolution, Ownership Isolation Matrix, and Callback Tampering.
"""
import pytest
from app.database.models import User, Quiz, Question, Option, QuizState, SessionStatus
from app.quiz_engine.service import QuizEngineService, SessionOwnershipError, SessionInvalidStateError
from app.results.service import ResultService
from app.results.exceptions import ResultOwnershipError
from app.services.draft_service import DraftService, DraftOwnershipError
from app.services.quiz_edit_service import QuizEditService, QuizOwnershipError
from app.permissions.service import PermissionService, TargetOwnershipError
from app.middlewares.user_resolution import resolve_or_create_user


@pytest.mark.asyncio
async def test_user_resolution_identity_divergence(db_session):
    """
    Proves that Telegram ID can differ drastically from internal DB users.id
    and the entire application works without any foreign key issues.
    """
    # Telegram ID is 9988776655443322
    tg_id_1 = 9988776655443322
    user1 = await resolve_or_create_user(db_session, tg_id_1, username="scholar", first_name="محمود")
    assert user1.id is not None
    assert user1.id != tg_id_1  # Internal auto-increment ID is different integer

    # Telegram ID 1122334455667788
    tg_id_2 = 1122334455667788
    user2 = await resolve_or_create_user(db_session, tg_id_2, username="student", first_name="طارق")
    assert user2.id is not None
    assert user2.id != tg_id_2
    assert user2.id != user1.id

    # Create quiz with user1
    quiz = Quiz(creator_id=user1.id, title="اختبار التاريخ الإسلامي", state=QuizState.READY, version=1)
    db_session.add(quiz)
    await db_session.flush()

    q1 = Question(quiz_id=quiz.id, text="متى وقعت معركة بدر؟", order_num=1)
    db_session.add(q1)
    await db_session.flush()
    opt1 = Option(question_id=q1.id, text="2 هـ", is_correct=True, order_num=1)
    opt2 = Option(question_id=q1.id, text="3 هـ", is_correct=False, order_num=2)
    db_session.add_all([opt1, opt2])
    await db_session.commit()

    # User2 starts session
    sess = await QuizEngineService.start_quiz_session(db_session, quiz.id, user2.id)
    assert sess.participant_id == user2.id

    # User2 answers
    await QuizEngineService.record_answer(db_session, sess.id, user2.id, q1.id, opt1.id)

    # Finish session
    res = await ResultService.finish_session(db_session, sess.id, user2.id)
    assert res.participant_id == user2.id
    assert res.correct_answers == 1
    assert res.percentage == 100.0


@pytest.mark.asyncio
async def test_full_cross_user_isolation_matrix(db_session, sample_user, other_user):
    """
    Exhaustive matrix: User A must never access or modify User B's entities:
    - Quiz
    - Draft
    - Publishing Target
    - Session
    - Result
    """
    # 1. Draft Isolation
    draft_b = await DraftService.get_or_create_draft(db_session, other_user.id, "مسودة المستخدم ب")
    with pytest.raises(DraftOwnershipError):
        await DraftService.convert_draft_to_quiz(db_session, draft_b.id, sample_user.id)
    with pytest.raises(DraftOwnershipError):
        await DraftService.delete_draft(db_session, draft_b.id, sample_user.id)

    # 2. Quiz Isolation
    quiz_b = Quiz(creator_id=other_user.id, title="اختبار المستخدم ب", state=QuizState.READY, version=1)
    db_session.add(quiz_b)
    await db_session.flush()

    q_b = Question(quiz_id=quiz_b.id, text="سؤال اختباري", order_num=1)
    db_session.add(q_b)
    await db_session.flush()

    opt_b = Option(question_id=q_b.id, text="خيار", is_correct=True, order_num=1)
    db_session.add(opt_b)
    await db_session.commit()

    with pytest.raises(QuizOwnershipError):
        await QuizEditService.update_quiz_title(db_session, quiz_b.id, sample_user.id, "محاولة تعديل")
    with pytest.raises(QuizOwnershipError):
        await QuizEditService.delete_quiz(db_session, quiz_b.id, sample_user.id)

    # 3. Publishing Target Isolation
    target_b = await PermissionService.register_target(
        db_session,
        user_id=other_user.id,
        chat_id=-100987654321,
        chat_type="channel",
        chat_title="قناة المستخدم ب",
    )
    with pytest.raises(TargetOwnershipError):
        await PermissionService.delete_target(db_session, target_b.id, sample_user.id)

    # 4. Session & Answer Hijacking Isolation
    sess_b = await QuizEngineService.start_quiz_session(db_session, quiz_b.id, other_user.id)
    with pytest.raises(SessionOwnershipError):
        await QuizEngineService.record_answer(
            db_session, session_id=sess_b.id, user_id=sample_user.id, question_id=1, option_id=1
        )
    with pytest.raises(ResultOwnershipError):
        await ResultService.finish_session(db_session, session_id=sess_b.id, user_id=sample_user.id)
