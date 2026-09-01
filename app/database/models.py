"""
Database models and SQLAlchemy declarative schema for QuizBot Arabic.
All models strictly enforce:
- Foreign key relations to internal users.id (NEVER raw telegram_id)
- Unique constraints (UNIQUE session_id on results, UNIQUE(session_id, question_id) on answers)
- Indexes on foreign keys and lookup columns
- Quiz version preservation and frozen states
"""
from datetime import datetime
from enum import Enum as PyEnum
from typing import List, Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class QuizState(str, PyEnum):
    DRAFT = "DRAFT"
    READY = "READY"
    PUBLISHED = "PUBLISHED"
    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"


class SessionStatus(str, PyEnum):
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False, index=True)
    username = Column(String(255), nullable=True)
    first_name = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    quizzes = relationship("Quiz", back_populates="creator", cascade="all, delete-orphan", lazy="selectin")
    drafts = relationship("Draft", back_populates="user", cascade="all, delete-orphan", lazy="selectin")
    sessions = relationship("QuizSession", back_populates="participant", cascade="all, delete-orphan", lazy="selectin")
    results = relationship("QuizResult", back_populates="participant", cascade="all, delete-orphan", lazy="selectin")
    publishing_targets = relationship("PublishingTarget", back_populates="user", cascade="all, delete-orphan", lazy="selectin")

    def __repr__(self) -> str:
        return f"<User id={self.id} tg={self.telegram_id} username={self.username}>"


class Quiz(Base):
    __tablename__ = "quizzes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    creator_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    version = Column(Integer, default=1, nullable=False)
    state = Column(Enum(QuizState, native_enum=False, length=50), default=QuizState.DRAFT, nullable=False, index=True)
    is_frozen = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    creator = relationship("User", back_populates="quizzes", lazy="selectin")
    questions = relationship("Question", back_populates="quiz", cascade="all, delete-orphan", order_by="Question.order_num", lazy="selectin")
    sessions = relationship("QuizSession", back_populates="quiz", cascade="all, delete-orphan", lazy="selectin")
    results = relationship("QuizResult", back_populates="quiz", cascade="all, delete-orphan", lazy="selectin")

    def __repr__(self) -> str:
        return f"<Quiz id={self.id} title={self.title} state={self.state} v={self.version}>"


class Question(Base):
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    quiz_id = Column(Integer, ForeignKey("quizzes.id", ondelete="CASCADE"), nullable=False, index=True)
    text = Column(Text, nullable=False)
    order_num = Column(Integer, nullable=False, default=1)
    explanation = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    quiz = relationship("Quiz", back_populates="questions", lazy="selectin")
    options = relationship("Option", back_populates="question", cascade="all, delete-orphan", order_by="Option.order_num", lazy="selectin")

    def __repr__(self) -> str:
        return f"<Question id={self.id} quiz_id={self.quiz_id} order={self.order_num}>"


class Option(Base):
    __tablename__ = "options"

    id = Column(Integer, primary_key=True, autoincrement=True)
    question_id = Column(Integer, ForeignKey("questions.id", ondelete="CASCADE"), nullable=False, index=True)
    text = Column(Text, nullable=False)
    is_correct = Column(Boolean, default=False, nullable=False)
    order_num = Column(Integer, nullable=False, default=1)

    # Relationships
    question = relationship("Question", back_populates="options", lazy="selectin")

    def __repr__(self) -> str:
        return f"<Option id={self.id} question_id={self.question_id} is_correct={self.is_correct}>"


class Draft(Base):
    __tablename__ = "drafts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=True)
    questions_data = Column(JSON, default=list, nullable=False)
    step = Column(String(50), default="WAITING_QUESTIONS", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="drafts", lazy="selectin")

    def __repr__(self) -> str:
        return f"<Draft id={self.id} user_id={self.user_id} title={self.title}>"


class PublishingTarget(Base):
    __tablename__ = "publishing_targets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    chat_id = Column(BigInteger, nullable=False, index=True)
    chat_type = Column(String(50), nullable=False)  # channel, supergroup, group
    chat_title = Column(String(255), nullable=False)
    can_post_messages = Column(Boolean, default=True, nullable=False)
    can_edit_messages = Column(Boolean, default=True, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    verified_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="publishing_targets", lazy="selectin")

    __table_args__ = (
        UniqueConstraint("user_id", "chat_id", name="uq_user_target_chat"),
    )

    def __repr__(self) -> str:
        return f"<PublishingTarget id={self.id} user_id={self.user_id} chat={self.chat_title}>"


class QuizSession(Base):
    __tablename__ = "quiz_sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    quiz_id = Column(Integer, ForeignKey("quizzes.id", ondelete="CASCADE"), nullable=False, index=True)
    participant_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    quiz_version = Column(Integer, nullable=False, default=1)
    status = Column(Enum(SessionStatus, native_enum=False, length=50), default=SessionStatus.ACTIVE, nullable=False, index=True)
    current_question_index = Column(Integer, default=0, nullable=False)
    snapshot_data = Column(JSON, default=list, nullable=False)  # questions & options snapshot at session start
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    quiz = relationship("Quiz", back_populates="sessions", lazy="selectin")
    participant = relationship("User", back_populates="sessions", lazy="selectin")
    answers = relationship("QuizAnswer", back_populates="session", cascade="all, delete-orphan", lazy="selectin")
    result = relationship("QuizResult", back_populates="session", uselist=False, cascade="all, delete-orphan", lazy="selectin")

    def __repr__(self) -> str:
        return f"<QuizSession id={self.id} quiz_id={self.quiz_id} participant_id={self.participant_id} status={self.status}>"


class QuizAnswer(Base):
    __tablename__ = "quiz_answers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey("quiz_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    question_id = Column(Integer, nullable=False, index=True)
    option_id = Column(Integer, nullable=False)
    is_correct = Column(Boolean, nullable=False)
    answered_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    session = relationship("QuizSession", back_populates="answers", lazy="selectin")

    __table_args__ = (
        UniqueConstraint("session_id", "question_id", name="uq_session_question_answer"),
    )

    def __repr__(self) -> str:
        return f"<QuizAnswer id={self.id} session_id={self.session_id} q={self.question_id} correct={self.is_correct}>"


class QuizResult(Base):
    __tablename__ = "quiz_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey("quiz_sessions.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    participant_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    quiz_id = Column(Integer, ForeignKey("quizzes.id", ondelete="CASCADE"), nullable=False, index=True)
    quiz_version = Column(Integer, nullable=False, default=1)
    total_questions = Column(Integer, nullable=False)
    answered_questions = Column(Integer, nullable=False)
    correct_answers = Column(Integer, nullable=False)
    wrong_answers = Column(Integer, nullable=False)
    percentage = Column(Float, nullable=False)
    status = Column(String(50), default="completed", nullable=False)
    started_at = Column(DateTime, nullable=False)
    completed_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    session = relationship("QuizSession", back_populates="result", lazy="selectin")
    participant = relationship("User", back_populates="results", lazy="selectin")
    quiz = relationship("Quiz", back_populates="results", lazy="selectin")

    __table_args__ = (
        UniqueConstraint("session_id", name="uq_quiz_result_session"),
    )

    def __repr__(self) -> str:
        return f"<QuizResult id={self.id} session_id={self.session_id} score={self.correct_answers}/{self.total_questions} ({self.percentage}%)>"
