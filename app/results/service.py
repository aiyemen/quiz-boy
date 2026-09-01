"""
Result Service and Ranking Service for Stage 7.
Handles idempotent session completion, result calculation, ownership checks, and Arabic output.
"""
from datetime import datetime
from typing import Any, Dict, List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database.models import (
    Quiz,
    QuizAnswer,
    QuizResult,
    QuizSession,
    SessionStatus,
)
from app.results.exceptions import (
    IncompleteSessionError,
    ResultNotFoundError,
    ResultOwnershipError,
)
from app.results.strategies import RankingStrategy


class ResultService:
    @staticmethod
    async def finish_session(
        session: AsyncSession,
        session_id: int,
        user_id: int,
    ) -> QuizResult:
        """
        Completes a quiz session and generates a QuizResult in an atomic transaction.
        Enforces idempotency: if result already exists, returns it safely without duplication.
        """
        # Check if result already exists for this session (idempotency)
        res_stmt = (
            select(QuizResult)
            .where(QuizResult.session_id == session_id)
            .options(selectinload(QuizResult.quiz))
        )
        res_exec = await session.execute(res_stmt)
        existing_result = res_exec.scalar_one_or_none()

        if existing_result is not None:
            if existing_result.participant_id != user_id:
                raise ResultOwnershipError("ليس لديك صلاحية الوصول إلى هذه النتيجة.")
            return existing_result

        # Fetch session with answers
        sess_stmt = (
            select(QuizSession)
            .where(QuizSession.id == session_id)
            .options(
                selectinload(QuizSession.answers),
                selectinload(QuizSession.quiz),
            )
        )
        sess_exec = await session.execute(sess_stmt)
        quiz_session = sess_exec.scalar_one_or_none()

        if quiz_session is None:
            raise ResultNotFoundError("جلسة الاختبار غير موجودة.")
        if quiz_session.participant_id != user_id:
            raise ResultOwnershipError("ليس لديك صلاحية الوصول إلى هذه الجلسة.")

        snapshot = quiz_session.snapshot_data or []
        total_questions = len(snapshot)
        answers = quiz_session.answers or []
        answered_count = len(answers)

        correct_count = sum(1 for a in answers if a.is_correct)
        wrong_count = answered_count - correct_count
        percentage = round((correct_count / total_questions * 100), 1) if total_questions > 0 else 0.0

        now = datetime.utcnow()
        quiz_session.status = SessionStatus.COMPLETED
        quiz_session.completed_at = now

        result = QuizResult(
            session_id=quiz_session.id,
            participant_id=user_id,
            quiz_id=quiz_session.quiz_id,
            quiz_version=quiz_session.quiz_version,
            total_questions=total_questions,
            answered_questions=answered_count,
            correct_answers=correct_count,
            wrong_answers=wrong_count,
            percentage=percentage,
            status="completed",
            started_at=quiz_session.started_at,
            completed_at=now,
            created_at=now,
            updated_at=now,
        )
        session.add(result)
        await session.commit()
        await session.refresh(result)
        return result

    @staticmethod
    async def get_result_by_id(
        session: AsyncSession,
        result_id: int,
        user_id: int,
    ) -> QuizResult:
        """Retrieves a result verifying participant or creator ownership."""
        stmt = (
            select(QuizResult)
            .where(QuizResult.id == result_id)
            .options(selectinload(QuizResult.quiz))
        )
        res_exec = await session.execute(stmt)
        result = res_exec.scalar_one_or_none()

        if result is None:
            raise ResultNotFoundError("النتيجة غير موجودة.")
        if result.participant_id != user_id and (result.quiz and result.quiz.creator_id != user_id):
            raise ResultOwnershipError("ليس لديك صلاحية عرض هذه النتيجة.")

        return result

    @staticmethod
    async def get_user_results(
        session: AsyncSession,
        user_id: int,
    ) -> List[QuizResult]:
        """Lists all quiz results for a participant."""
        stmt = (
            select(QuizResult)
            .where(QuizResult.participant_id == user_id)
            .options(selectinload(QuizResult.quiz))
            .order_by(QuizResult.completed_at.desc())
        )
        res_exec = await session.execute(stmt)
        return list(res_exec.scalars().all())

    @staticmethod
    async def get_quiz_results(
        session: AsyncSession,
        quiz_id: int,
        creator_id: int,
    ) -> List[QuizResult]:
        """Lists all participant results for a quiz (creator access)."""
        # Verify quiz ownership
        quiz_stmt = select(Quiz).where(Quiz.id == quiz_id)
        quiz_exec = await session.execute(quiz_stmt)
        quiz = quiz_exec.scalar_one_or_none()

        if quiz is None:
            raise ResultNotFoundError("الاختبار غير موجود.")
        if quiz.creator_id != creator_id:
            raise ResultOwnershipError("ليس لديك صلاحية عرض نتائج هذا الاختبار.")

        stmt = (
            select(QuizResult)
            .where(QuizResult.quiz_id == quiz_id)
            .options(selectinload(QuizResult.participant))
            .order_by(QuizResult.completed_at.desc())
        )
        res_exec = await session.execute(stmt)
        return list(res_exec.scalars().all())

    @staticmethod
    def format_result_arabic(result: QuizResult, quiz_title: str) -> str:
        """Formats the quiz completion summary message in clear Arabic."""
        return (
            "🏁 <b>انتهى الاختبار!</b>\n\n"
            f"📚 <b>{quiz_title}</b>\n\n"
            f"✅ <b>صحيحة:</b> {result.correct_answers}\n"
            f"❌ <b>خاطئة:</b> {result.wrong_answers}\n\n"
            f"📊 <b>النتيجة:</b> {result.percentage:.1f}%"
        )


class RankingService:
    """
    Ranking Service Abstraction.
    Operates strictly as an interface wrapper around RankingStrategy.
    Does not execute any invented or unapproved ranking formula.
    """

    def __init__(self, strategy: Optional[RankingStrategy] = None) -> None:
        self.strategy: Optional[RankingStrategy] = strategy

    async def get_quiz_rankings(
        self,
        session: AsyncSession,
        quiz_id: int,
        requester_id: int,
    ) -> List[Dict[str, Any]]:
        """
        Retrieves rankings using the configured strategy abstraction if provided.
        Returns empty list if no approved ranking strategy is configured.
        """
        if self.strategy is None:
            return []
        results = await ResultService.get_quiz_results(session, quiz_id, requester_id)
        return self.strategy.calculate_rankings(results)
