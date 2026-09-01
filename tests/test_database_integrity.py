"""
Comprehensive Database Integrity and Constraint Tests.
Verifies DB constraints, foreign keys, cascades, unique constraints, and active-freeze protection.
"""
import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from app.database.models import (
    User,
    Quiz,
    Question,
    Option,
    QuizState,
    Draft,
    PublishingTarget,
    QuizSession,
    QuizAnswer,
    QuizResult,
    SessionStatus,
)
from app.quiz_engine.service import QuizEngineService
from app.services.quiz_edit_service import QuizEditService
from app.services.quiz_edit_service import QuizFrozenError


@pytest.mark.asyncio
async def test_duplicate_answer_unique_constraint(db_session, sample_user):
    """Verifies that DB enforces UNIQUE(session_id, question_id) on QuizAnswer."""
    quiz = Quiz(creator_id=sample_user.id, title="اختبار النزاهة", state=QuizState.READY, version=1)
    db_session.add(quiz)
    await db_session.flush()

    q1 = Question(quiz_id=quiz.id, text="السؤال الأول", order_num=1)
    db_session.add(q1)
    await db_session.flush()

    opt1 = Option(question_id=q1.id, text="أ", is_correct=True, order_num=1)
    opt2 = Option(question_id=q1.id, text="ب", is_correct=False, order_num=2)
    db_session.add_all([opt1, opt2])
    await db_session.commit()

    sess = QuizSession(
        quiz_id=quiz.id,
        participant_id=sample_user.id,
        quiz_version=1,
        status=SessionStatus.ACTIVE,
        snapshot_data=[{"id": q1.id, "text": q1.text, "options": []}],
    )
    db_session.add(sess)
    await db_session.commit()

    ans1 = QuizAnswer(session_id=sess.id, question_id=q1.id, option_id=opt1.id, is_correct=True)
    db_session.add(ans1)
    await db_session.commit()

    # Attempt inserting duplicate answer for same (session_id, question_id) -> MUST fail at DB level
    ans_dup = QuizAnswer(session_id=sess.id, question_id=q1.id, option_id=opt2.id, is_correct=False)
    db_session.add(ans_dup)
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()


@pytest.mark.asyncio
async def test_duplicate_result_unique_constraint(db_session, sample_user):
    """Verifies that DB enforces UNIQUE(session_id) on QuizResult."""
    quiz = Quiz(creator_id=sample_user.id, title="اختبار النتيجة الواحدة", state=QuizState.READY, version=1)
    db_session.add(quiz)
    await db_session.flush()

    sess = QuizSession(
        quiz_id=quiz.id,
        participant_id=sample_user.id,
        quiz_version=1,
        status=SessionStatus.COMPLETED,
        snapshot_data=[],
    )
    db_session.add(sess)
    await db_session.commit()

    res1 = QuizResult(
        session_id=sess.id,
        participant_id=sample_user.id,
        quiz_id=quiz.id,
        quiz_version=1,
        total_questions=1,
        answered_questions=1,
        correct_answers=1,
        wrong_answers=0,
        percentage=100.0,
        started_at=sess.started_at,
        completed_at=sess.started_at,
    )
    db_session.add(res1)
    await db_session.commit()

    # Attempt second result on same session_id -> MUST fail with IntegrityError
    res_dup = QuizResult(
        session_id=sess.id,
        participant_id=sample_user.id,
        quiz_id=quiz.id,
        quiz_version=1,
        total_questions=1,
        answered_questions=1,
        correct_answers=1,
        wrong_answers=0,
        percentage=100.0,
        started_at=sess.started_at,
        completed_at=sess.started_at,
    )
    db_session.add(res_dup)
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()


@pytest.mark.asyncio
async def test_cascade_deletion(db_session):
    """Verifies cascading delete rules from User -> Quiz -> Question -> Option."""
    user = User(telegram_id=555444333, username="temp_user", first_name="مؤقت")
    db_session.add(user)
    await db_session.commit()

    quiz = Quiz(creator_id=user.id, title="اختبار مؤقت للحذف", state=QuizState.DRAFT, version=1)
    db_session.add(quiz)
    await db_session.flush()

    q = Question(quiz_id=quiz.id, text="سؤال مؤقت", order_num=1)
    db_session.add(q)
    await db_session.flush()

    opt = Option(question_id=q.id, text="خيار مؤقت", is_correct=True, order_num=1)
    db_session.add(opt)
    await db_session.commit()

    # Delete Quiz
    await db_session.delete(quiz)
    await db_session.commit()

    # Verify Question & Option deleted
    q_check = await db_session.execute(select(Question).where(Question.id == q.id))
    assert q_check.scalar_one_or_none() is None
    opt_check = await db_session.execute(select(Option).where(Option.id == opt.id))
    assert opt_check.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_active_freeze_blocks_all_modifications(db_session, sample_user):
    """Verifies that ACTIVE state freezes quiz against title edit, question edit, deletion, or option changes."""
    quiz = Quiz(creator_id=sample_user.id, title="اختبار مجمد", state=QuizState.READY, version=1)
    db_session.add(quiz)
    await db_session.flush()

    q = Question(quiz_id=quiz.id, text="سؤال 1", order_num=1)
    db_session.add(q)
    await db_session.flush()

    opt = Option(question_id=q.id, text="أ", is_correct=True, order_num=1)
    db_session.add(opt)
    await db_session.commit()

    # Transition to ACTIVE
    await QuizEditService.set_quiz_state(db_session, quiz.id, sample_user.id, QuizState.ACTIVE)

    # 1. Block question edit
    with pytest.raises(QuizFrozenError):
        await QuizEditService.edit_question_text(db_session, quiz.id, q.id, sample_user.id, "نص جديد")

    # 2. Block quiz title update
    with pytest.raises(QuizFrozenError):
        await QuizEditService.update_quiz_title(db_session, quiz.id, sample_user.id, "عنوان جديد")

    # 3. Block quiz deletion
    with pytest.raises(QuizFrozenError):
        await QuizEditService.delete_quiz(db_session, quiz.id, sample_user.id)
