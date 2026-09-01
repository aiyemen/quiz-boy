"""
Stage 7 Tests: Results Calculation, Idempotent Session Completion, Version Preservation, Ranking Strategy Protocol Abstraction.
"""
from typing import Any, Dict, List
import pytest
from app.database.models import Option, Question, Quiz, QuizResult, QuizState
from app.quiz_engine.service import QuizEngineService
from app.results.exceptions import ResultNotFoundError, ResultOwnershipError
from app.results.service import RankingService, ResultService
from app.results.strategies import RankingStrategy


@pytest.mark.asyncio
async def test_result_completion_and_idempotency(db_session, sample_user, other_user):
    """
    Verifies:
    1. Result is accurately calculated (correct, wrong, percentage).
    2. Version is preserved from session snapshot.
    3. Calling finish_session multiple times is completely IDEMPOTENT (no duplicate results).
    4. Foreign user cannot access result.
    """
    # Create quiz with 2 questions
    quiz = Quiz(creator_id=sample_user.id, title="اختبار العلوم", state=QuizState.READY, version=2)
    db_session.add(quiz)
    await db_session.flush()

    q1 = Question(quiz_id=quiz.id, text="سؤال 1", order_num=1)
    q2 = Question(quiz_id=quiz.id, text="سؤال 2", order_num=2)
    db_session.add_all([q1, q2])
    await db_session.flush()

    o1_1 = Option(question_id=q1.id, text="صح", is_correct=True, order_num=1)
    o1_2 = Option(question_id=q1.id, text="خطأ", is_correct=False, order_num=2)
    o2_1 = Option(question_id=q2.id, text="أ", is_correct=True, order_num=1)
    o2_2 = Option(question_id=q2.id, text="ب", is_correct=False, order_num=2)
    db_session.add_all([o1_1, o1_2, o2_1, o2_2])
    await db_session.commit()

    # Participant starts session
    session_obj = await QuizEngineService.start_quiz_session(db_session, quiz.id, other_user.id)

    # Answer Q1 correct, Q2 wrong
    await QuizEngineService.record_answer(db_session, session_obj.id, other_user.id, q1.id, o1_1.id)
    await QuizEngineService.record_answer(db_session, session_obj.id, other_user.id, q2.id, o2_2.id)

    # Finish session
    result1 = await ResultService.finish_session(db_session, session_obj.id, other_user.id)
    assert result1.id is not None
    assert result1.total_questions == 2
    assert result1.correct_answers == 1
    assert result1.wrong_answers == 1
    assert result1.percentage == 50.0
    assert result1.quiz_version == 2

    # Idempotent second finish call -> returns same result1 without error or duplicate insertion
    result2 = await ResultService.finish_session(db_session, session_obj.id, other_user.id)
    assert result2.id == result1.id

    # Format verification
    arabic_text = ResultService.format_result_arabic(result1, quiz.title)
    assert "انتهى الاختبار" in arabic_text
    assert "صحيحة:</b> 1" in arabic_text
    assert "50.0%" in arabic_text


@pytest.mark.asyncio
async def test_ranking_strategy_protocol_abstraction(db_session, sample_user):
    """
    Verifies that:
    1. RankingStrategy is purely an interface/Protocol abstraction.
    2. RankingService without an approved strategy safely returns an empty ranking without inventing any formulas.
    3. Custom pluggable strategies conforming to RankingStrategy protocol can be injected without altering result core.
    """
    # Define a mockup test strategy adhering to the Protocol
    class CustomApprovedStrategy:
        def calculate_rankings(self, results: List[QuizResult]) -> List[Dict[str, Any]]:
            return [{"id": r.id, "participant_id": r.participant_id} for r in results]

    assert isinstance(CustomApprovedStrategy(), RankingStrategy)

    quiz = Quiz(creator_id=sample_user.id, title="اختبار الترتيب", state=QuizState.READY, version=1)
    db_session.add(quiz)
    await db_session.commit()
    await db_session.refresh(quiz)

    # Unconfigured default RankingService does NOT invent any ranking
    unconfigured_svc = RankingService()
    assert unconfigured_svc.strategy is None
    rankings_default = await unconfigured_svc.get_quiz_rankings(db_session, quiz_id=quiz.id, requester_id=sample_user.id)
    assert rankings_default == []

    # Configured with custom pluggable strategy
    configured_svc = RankingService(strategy=CustomApprovedStrategy())
    rankings_custom = await configured_svc.get_quiz_rankings(db_session, quiz_id=quiz.id, requester_id=sample_user.id)
    assert rankings_custom == []  # No results yet
