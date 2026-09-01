"""
Quiz Engine Service.
Manages interactive quiz sessions, snapshot creation, version locking, and tamper-proof answer recording.
"""
from datetime import datetime
from typing import Any, Dict, List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database.models import (
    Option,
    Question,
    Quiz,
    QuizAnswer,
    QuizSession,
    QuizState,
    SessionStatus,
)


class SessionError(Exception):
    pass


class SessionOwnershipError(SessionError):
    pass


class SessionInvalidStateError(SessionError):
    pass


class AnswerError(Exception):
    pass


class AnswerAlreadySubmittedError(AnswerError):
    pass


class QuizEngineService:
    @staticmethod
    async def start_quiz_session(
        session: AsyncSession,
        quiz_id: int,
        user_id: int,
    ) -> QuizSession:
        """
        Starts or resumes a quiz session for a user.
        Takes a snapshot of questions and options at start time to preserve versioning immutability.
        """
        # Fetch Quiz with questions and options
        stmt = (
            select(Quiz)
            .where(Quiz.id == quiz_id)
            .options(selectinload(Quiz.questions).selectinload(Question.options))
        )
        result = await session.execute(stmt)
        quiz = result.scalar_one_or_none()

        if quiz is None:
            raise SessionError("الاختبار غير موجود.")
        if not quiz.questions:
            raise SessionError("هذا الاختبار لا يحتوي على أي أسئلة.")

        # Check for existing ACTIVE session
        active_stmt = (
            select(QuizSession)
            .where(
                QuizSession.quiz_id == quiz_id,
                QuizSession.participant_id == user_id,
                QuizSession.status == SessionStatus.ACTIVE,
            )
            .options(selectinload(QuizSession.answers))
        )
        active_res = await session.execute(active_stmt)
        existing_session = active_res.scalar_one_or_none()

        if existing_session is not None:
            return existing_session

        # Build snapshot of questions & options
        snapshot = []
        for q in quiz.questions:
            q_snap = {
                "id": q.id,
                "text": q.text,
                "order_num": q.order_num,
                "explanation": q.explanation,
                "options": [
                    {
                        "id": opt.id,
                        "text": opt.text,
                        "is_correct": opt.is_correct,
                        "order_num": opt.order_num,
                    }
                    for opt in q.options
                ],
            }
            snapshot.append(q_snap)

        quiz_session = QuizSession(
            quiz_id=quiz.id,
            participant_id=user_id,
            quiz_version=quiz.version,
            status=SessionStatus.ACTIVE,
            current_question_index=0,
            snapshot_data=snapshot,
            started_at=datetime.utcnow(),
        )
        session.add(quiz_session)

        # Mark quiz as ACTIVE and frozen
        if quiz.state != QuizState.ACTIVE:
            quiz.state = QuizState.ACTIVE
            quiz.is_frozen = True

        await session.commit()
        await session.refresh(quiz_session)
        return quiz_session

    @staticmethod
    async def get_session_by_id(
        session: AsyncSession,
        session_id: int,
        user_id: int,
    ) -> QuizSession:
        """Retrieves session with strict ownership check."""
        stmt = (
            select(QuizSession)
            .where(QuizSession.id == session_id)
            .options(
                selectinload(QuizSession.answers),
                selectinload(QuizSession.quiz),
            )
        )
        result = await session.execute(stmt)
        quiz_session = result.scalar_one_or_none()

        if quiz_session is None:
            raise SessionError("جلسة الاختبار غير موجودة.")
        if quiz_session.participant_id != user_id:
            raise SessionOwnershipError("ليس لديك صلاحية الوصول إلى هذه الجلسة.")

        return quiz_session

    @staticmethod
    async def record_answer(
        session: AsyncSession,
        session_id: int,
        user_id: int,
        question_id: int,
        option_id: int,
    ) -> Dict[str, Any]:
        """
        Records an answer for a question in an active session.
        Enforces:
        - Server-side ownership verification
        - Active session state check
        - Anti-cheat idempotency (rejects duplicate answer for same question)
        - Correctness check from question snapshot
        """
        quiz_session = await QuizEngineService.get_session_by_id(session, session_id, user_id)

        if quiz_session.status != SessionStatus.ACTIVE:
            raise SessionInvalidStateError("جلسة الاختبار مكتملة أو غير نشطة.")

        # Check if question was already answered in this session
        existing_ans_stmt = select(QuizAnswer).where(
            QuizAnswer.session_id == session_id,
            QuizAnswer.question_id == question_id,
        )
        existing_ans_res = await session.execute(existing_ans_stmt)
        if existing_ans_res.scalar_one_or_none() is not None:
            raise AnswerAlreadySubmittedError("تمت الإجابة على هذا السؤال مسبقًا.")

        # Find question and option in snapshot
        snapshot = quiz_session.snapshot_data or []
        target_q = None
        target_opt = None

        for q in snapshot:
            if q["id"] == question_id:
                target_q = q
                for opt in q["options"]:
                    if opt["id"] == option_id:
                        target_opt = opt
                        break
                break

        if not target_q:
            raise AnswerError("السؤال المحدد غير موجود في هذه الجلسة.")
        if not target_opt:
            raise AnswerError("الخيار المحدد غير صالح لهذا السؤال.")

        is_correct = bool(target_opt["is_correct"])

        # Insert answer
        answer = QuizAnswer(
            session_id=session_id,
            question_id=question_id,
            option_id=option_id,
            is_correct=is_correct,
            answered_at=datetime.utcnow(),
        )
        session.add(answer)

        # Update current index
        quiz_session.current_question_index += 1

        # Check if all questions are answered
        total_q = len(snapshot)
        answered_stmt = select(QuizAnswer).where(QuizAnswer.session_id == session_id)
        ans_res = await session.execute(answered_stmt)
        total_answered = len(ans_res.scalars().all()) + 1  # including the new one

        is_finished = total_answered >= total_q

        await session.commit()
        await session.refresh(quiz_session)

        return {
            "answer_id": answer.id,
            "is_correct": is_correct,
            "explanation": target_q.get("explanation"),
            "question_index": quiz_session.current_question_index,
            "total_questions": total_q,
            "is_finished": is_finished,
        }
