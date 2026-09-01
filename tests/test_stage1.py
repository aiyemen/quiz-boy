"""
Stage 1 Tests: Database Foundation, Models, Foreign Keys, Schema Integrity.
"""
import pytest
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.database.models import User, Quiz, Question, Option, QuizState, Draft


@pytest.mark.asyncio
async def test_user_creation_and_fields(db_session):
    """Verifies User creation with telegram_id and internal id."""
    user = User(telegram_id=11223344, username="teacher1", first_name="علي")
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    assert user.id is not None
    assert user.telegram_id == 11223344
    assert user.is_active is True


@pytest.mark.asyncio
async def test_quiz_and_question_hierarchy(db_session, sample_user):
    """Verifies Quiz -> Question -> Option cascading relationships using internal user.id."""
    quiz = Quiz(
        creator_id=sample_user.id,
        title="اختبار الرياضيات",
        state=QuizState.DRAFT,
        version=1,
    )
    db_session.add(quiz)
    await db_session.flush()

    q1 = Question(quiz_id=quiz.id, text="ما هو ناتج 5 * 5 ؟", order_num=1)
    db_session.add(q1)
    await db_session.flush()

    opt1 = Option(question_id=q1.id, text="20", is_correct=False, order_num=1)
    opt2 = Option(question_id=q1.id, text="25", is_correct=True, order_num=2)
    db_session.add_all([opt1, opt2])
    await db_session.commit()

    stmt = (
        select(Quiz)
        .where(Quiz.id == quiz.id)
        .options(selectinload(Quiz.questions).selectinload(Question.options))
    )
    res = await db_session.execute(stmt)
    loaded_quiz = res.scalar_one()

    assert len(loaded_quiz.questions) == 1
    assert len(loaded_quiz.questions[0].options) == 2
    assert loaded_quiz.questions[0].options[1].is_correct is True
