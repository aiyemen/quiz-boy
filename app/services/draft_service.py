"""
Draft Service for managing quiz drafts during creation.
Handles atomic append, ownership enforcement, and conversion to Quiz.
"""
from typing import Any, Dict, List, Optional
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Draft, Option, Question, Quiz, QuizState
from app.quick_create.models import ParsedQuestion


class DraftNotFoundError(Exception):
    pass


class DraftOwnershipError(Exception):
    pass


class DraftService:
    @staticmethod
    async def get_or_create_draft(
        session: AsyncSession,
        user_id: int,
        title: Optional[str] = None,
    ) -> Draft:
        """Finds existing active draft or creates a new one for user_id."""
        stmt = select(Draft).where(Draft.user_id == user_id).order_by(Draft.updated_at.desc())
        result = await session.execute(stmt)
        draft = result.scalars().first()

        if draft is None:
            draft = Draft(
                user_id=user_id,
                title=title or "اختبار جديد",
                questions_data=[],
                step="WAITING_QUESTIONS",
            )
            session.add(draft)
            await session.commit()
            await session.refresh(draft)
        elif title and draft.title != title:
            draft.title = title
            await session.commit()
            await session.refresh(draft)

        return draft

    @staticmethod
    async def get_user_draft(
        session: AsyncSession,
        draft_id: int,
        user_id: int,
    ) -> Draft:
        """Retrieves draft verifying strict user ownership."""
        stmt = select(Draft).where(Draft.id == draft_id)
        result = await session.execute(stmt)
        draft = result.scalar_one_or_none()

        if draft is None:
            raise DraftNotFoundError("مسودة الاختبار غير موجودة.")
        if draft.user_id != user_id:
            raise DraftOwnershipError("ليس لديك صلاحية الوصول إلى هذه المسودة.")

        return draft

    @staticmethod
    async def append_questions_atomic(
        session: AsyncSession,
        draft_id: int,
        user_id: int,
        parsed_questions: List[ParsedQuestion],
    ) -> Draft:
        """
        Appends a validated batch of parsed questions to the draft atomically.
        """
        draft = await DraftService.get_user_draft(session, draft_id, user_id)

        # Convert ParsedQuestions into JSON-serializable structure
        new_q_data = list(draft.questions_data or [])
        start_idx = len(new_q_data) + 1

        for idx, pq in enumerate(parsed_questions):
            q_dict = {
                "order_num": start_idx + idx,
                "text": pq.text,
                "explanation": pq.explanation,
                "options": [
                    {
                        "order_num": opt.order_num,
                        "text": opt.text,
                        "is_correct": opt.is_correct,
                        "label": opt.label,
                    }
                    for opt in pq.options
                ],
            }
            new_q_data.append(q_dict)

        draft.questions_data = new_q_data
        draft.step = "REVIEW"
        await session.commit()
        await session.refresh(draft)
        return draft

    @staticmethod
    async def delete_draft(
        session: AsyncSession,
        draft_id: int,
        user_id: int,
    ) -> bool:
        """Deletes draft ensuring ownership."""
        draft = await DraftService.get_user_draft(session, draft_id, user_id)
        await session.delete(draft)
        await session.commit()
        return True

    @staticmethod
    async def convert_draft_to_quiz(
        session: AsyncSession,
        draft_id: int,
        user_id: int,
    ) -> Quiz:
        """
        Converts draft into a persistent Quiz in READY state with questions and options.
        Deletes draft atomically upon conversion.
        """
        draft = await DraftService.get_user_draft(session, draft_id, user_id)
        if not draft.questions_data:
            raise ValueError("لا يمكن نشر اختبار بدون أسئلة.")

        quiz = Quiz(
            creator_id=user_id,
            title=draft.title or "اختبار جديد",
            description=None,
            version=1,
            state=QuizState.READY,
            is_frozen=False,
        )
        session.add(quiz)
        await session.flush()  # populate quiz.id

        # Insert questions and options
        for q_dict in draft.questions_data:
            question = Question(
                quiz_id=quiz.id,
                text=q_dict["text"],
                order_num=q_dict.get("order_num", 1),
                explanation=q_dict.get("explanation"),
            )
            session.add(question)
            await session.flush()

            for opt_dict in q_dict.get("options", []):
                option = Option(
                    question_id=question.id,
                    text=opt_dict["text"],
                    is_correct=opt_dict["is_correct"],
                    order_num=opt_dict.get("order_num", 1),
                )
                session.add(option)

        # Remove draft
        await session.delete(draft)
        await session.commit()
        await session.refresh(quiz)
        return quiz
