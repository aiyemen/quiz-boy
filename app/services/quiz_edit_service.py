"""
Quiz Management and Edit Service.
Enforces ownership validation and ACTIVE FREEZE rules on quizzes.
"""
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database.models import Option, Question, Quiz, QuizState


class QuizNotFoundError(Exception):
    pass


class QuizOwnershipError(Exception):
    pass


class QuizFrozenError(Exception):
    pass


class QuizEditService:
    @staticmethod
    async def get_user_quiz(
        session: AsyncSession,
        quiz_id: int,
        user_id: int,
        load_questions: bool = True,
    ) -> Quiz:
        """Retrieves a quiz and strictly verifies user ownership."""
        stmt = select(Quiz).where(Quiz.id == quiz_id)
        if load_questions:
            stmt = stmt.options(
                selectinload(Quiz.questions).selectinload(Question.options)
            )

        result = await session.execute(stmt)
        quiz = result.scalar_one_or_none()

        if quiz is None:
            raise QuizNotFoundError("الاختبار غير موجود.")
        if quiz.creator_id != user_id:
            raise QuizOwnershipError("ليس لديك صلاحية الوصول إلى هذا الاختبار.")

        return quiz

    @staticmethod
    async def get_user_quizzes(
        session: AsyncSession,
        user_id: int,
    ) -> List[Quiz]:
        """Lists all quizzes created by user."""
        stmt = (
            select(Quiz)
            .where(Quiz.creator_id == user_id)
            .options(selectinload(Quiz.questions))
            .order_by(Quiz.created_at.desc())
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def update_quiz_title(
        session: AsyncSession,
        quiz_id: int,
        user_id: int,
        new_title: str,
    ) -> Quiz:
        """Updates quiz title. BLOCKED if quiz is ACTIVE / frozen."""
        quiz = await QuizEditService.get_user_quiz(session, quiz_id, user_id, load_questions=False)
        if quiz.state == QuizState.ACTIVE or quiz.is_frozen:
            raise QuizFrozenError("لا يمكن تعديل عنوان الاختبار لأنه قيد التشغيل (نشط) ومجمّد.")
        quiz.title = new_title.strip()
        await session.commit()
        await session.refresh(quiz)
        return quiz

    @staticmethod
    async def edit_question_text(
        session: AsyncSession,
        quiz_id: int,
        question_id: int,
        user_id: int,
        new_text: str,
        new_explanation: Optional[str] = None,
    ) -> Question:
        """
        Edits question text.
        BLOCKED if quiz is ACTIVE / frozen.
        """
        quiz = await QuizEditService.get_user_quiz(session, quiz_id, user_id, load_questions=True)
        if quiz.state == QuizState.ACTIVE or quiz.is_frozen:
            raise QuizFrozenError("لا يمكن تعديل السؤال لأن الاختبار قيد التشغيل (نشط) ومجمّد.")

        # Find question in quiz
        target_q: Optional[Question] = None
        for q in quiz.questions:
            if q.id == question_id:
                target_q = q
                break

        if not target_q:
            raise QuizNotFoundError("السؤال غير موجود في هذا الاختبار.")

        target_q.text = new_text.strip()
        if new_explanation is not None:
            target_q.explanation = new_explanation.strip() if new_explanation.strip() else None

        quiz.version += 1
        await session.commit()
        await session.refresh(target_q)
        return target_q

    @staticmethod
    async def delete_question(
        session: AsyncSession,
        quiz_id: int,
        question_id: int,
        user_id: int,
    ) -> bool:
        """
        Deletes a question from a quiz.
        BLOCKED if quiz is ACTIVE / frozen.
        """
        quiz = await QuizEditService.get_user_quiz(session, quiz_id, user_id, load_questions=True)
        if quiz.state == QuizState.ACTIVE or quiz.is_frozen:
            raise QuizFrozenError("لا يمكن حذف السؤال لأن الاختبار قيد التشغيل (نشط) ومجمّد.")

        target_q = None
        for q in quiz.questions:
            if q.id == question_id:
                target_q = q
                break

        if not target_q:
            raise QuizNotFoundError("السؤال غير موجود في هذا الاختبار.")

        if len(quiz.questions) <= 1:
            raise ValueError("لا يمكن حذف السؤال الوحيد المتبقي في الاختبار.")

        await session.delete(target_q)
        quiz.version += 1
        await session.commit()
        return True

    @staticmethod
    async def set_quiz_state(
        session: AsyncSession,
        quiz_id: int,
        user_id: int,
        new_state: QuizState,
    ) -> Quiz:
        """Updates quiz lifecycle state (READY -> PUBLISHED -> ACTIVE -> ARCHIVED)."""
        quiz = await QuizEditService.get_user_quiz(session, quiz_id, user_id, load_questions=False)
        quiz.state = new_state
        if new_state == QuizState.ACTIVE:
            quiz.is_frozen = True
        elif new_state in (QuizState.DRAFT, QuizState.READY):
            quiz.is_frozen = False
        await session.commit()
        await session.refresh(quiz)
        return quiz

    @staticmethod
    async def delete_quiz(
        session: AsyncSession,
        quiz_id: int,
        user_id: int,
    ) -> bool:
        """Deletes a quiz and cascades to all related entities. BLOCKED if ACTIVE / frozen."""
        quiz = await QuizEditService.get_user_quiz(session, quiz_id, user_id, load_questions=False)
        if quiz.state == QuizState.ACTIVE or quiz.is_frozen:
            raise QuizFrozenError("لا يمكن حذف الاختبار لأنه قيد التشغيل (نشط) ومجمّد.")
        await session.delete(quiz)
        await session.commit()
        return True
