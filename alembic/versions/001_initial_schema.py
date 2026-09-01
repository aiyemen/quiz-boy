"""Initial Schema with Users, Quizzes, Questions, Options, Drafts, Targets, Sessions, Answers, Results

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-09-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Users table
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('telegram_id', sa.BigInteger(), nullable=False),
        sa.Column('username', sa.String(length=255), nullable=True),
        sa.Column('first_name', sa.String(length=255), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_telegram_id'), 'users', ['telegram_id'], unique=True)

    # 2. Quizzes table
    op.create_table(
        'quizzes',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('creator_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('state', sa.Enum('DRAFT', 'READY', 'PUBLISHED', 'ACTIVE', 'ARCHIVED', name='quizstate', native_enum=False, length=50), nullable=False, server_default='DRAFT'),
        sa.Column('is_frozen', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['creator_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_quizzes_creator_id'), 'quizzes', ['creator_id'], unique=False)
    op.create_index(op.f('ix_quizzes_state'), 'quizzes', ['state'], unique=False)

    # 3. Questions table
    op.create_table(
        'questions',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('quiz_id', sa.Integer(), nullable=False),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('order_num', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('explanation', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['quiz_id'], ['quizzes.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_questions_quiz_id'), 'questions', ['quiz_id'], unique=False)

    # 4. Options table
    op.create_table(
        'options',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('question_id', sa.Integer(), nullable=False),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('is_correct', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('order_num', sa.Integer(), nullable=False, server_default='1'),
        sa.ForeignKeyConstraint(['question_id'], ['questions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_options_question_id'), 'options', ['question_id'], unique=False)

    # 5. Drafts table
    op.create_table(
        'drafts',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=True),
        sa.Column('questions_data', sa.JSON(), nullable=False),
        sa.Column('step', sa.String(length=50), nullable=False, server_default='WAITING_QUESTIONS'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_drafts_user_id'), 'drafts', ['user_id'], unique=False)

    # 6. Publishing Targets table
    op.create_table(
        'publishing_targets',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('chat_id', sa.BigInteger(), nullable=False),
        sa.Column('chat_type', sa.String(length=50), nullable=False),
        sa.Column('chat_title', sa.String(length=255), nullable=False),
        sa.Column('can_post_messages', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('can_edit_messages', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('verified_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'chat_id', name='uq_user_target_chat')
    )
    op.create_index(op.f('ix_publishing_targets_user_id'), 'publishing_targets', ['user_id'], unique=False)
    op.create_index(op.f('ix_publishing_targets_chat_id'), 'publishing_targets', ['chat_id'], unique=False)

    # 7. Quiz Sessions table
    op.create_table(
        'quiz_sessions',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('quiz_id', sa.Integer(), nullable=False),
        sa.Column('participant_id', sa.Integer(), nullable=False),
        sa.Column('quiz_version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('status', sa.Enum('ACTIVE', 'COMPLETED', 'EXPIRED', 'CANCELLED', name='sessionstatus', native_enum=False, length=50), nullable=False, server_default='ACTIVE'),
        sa.Column('current_question_index', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('snapshot_data', sa.JSON(), nullable=False),
        sa.Column('started_at', sa.DateTime(), nullable=False),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['participant_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['quiz_id'], ['quizzes.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_quiz_sessions_participant_id'), 'quiz_sessions', ['participant_id'], unique=False)
    op.create_index(op.f('ix_quiz_sessions_quiz_id'), 'quiz_sessions', ['quiz_id'], unique=False)
    op.create_index(op.f('ix_quiz_sessions_status'), 'quiz_sessions', ['status'], unique=False)

    # 8. Quiz Answers table
    op.create_table(
        'quiz_answers',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('session_id', sa.Integer(), nullable=False),
        sa.Column('question_id', sa.Integer(), nullable=False),
        sa.Column('option_id', sa.Integer(), nullable=False),
        sa.Column('is_correct', sa.Boolean(), nullable=False),
        sa.Column('answered_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['session_id'], ['quiz_sessions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('session_id', 'question_id', name='uq_session_question_answer')
    )
    op.create_index(op.f('ix_quiz_answers_session_id'), 'quiz_answers', ['session_id'], unique=False)
    op.create_index(op.f('ix_quiz_answers_question_id'), 'quiz_answers', ['question_id'], unique=False)

    # 9. Quiz Results table (Stage 7 with UNIQUE(session_id))
    op.create_table(
        'quiz_results',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('session_id', sa.Integer(), nullable=False),
        sa.Column('participant_id', sa.Integer(), nullable=False),
        sa.Column('quiz_id', sa.Integer(), nullable=False),
        sa.Column('quiz_version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('total_questions', sa.Integer(), nullable=False),
        sa.Column('answered_questions', sa.Integer(), nullable=False),
        sa.Column('correct_answers', sa.Integer(), nullable=False),
        sa.Column('wrong_answers', sa.Integer(), nullable=False),
        sa.Column('percentage', sa.Float(), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='completed'),
        sa.Column('started_at', sa.DateTime(), nullable=False),
        sa.Column('completed_at', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['participant_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['quiz_id'], ['quizzes.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['session_id'], ['quiz_sessions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('session_id', name='uq_quiz_result_session')
    )
    op.create_index(op.f('ix_quiz_results_session_id'), 'quiz_results', ['session_id'], unique=True)
    op.create_index(op.f('ix_quiz_results_participant_id'), 'quiz_results', ['participant_id'], unique=False)
    op.create_index(op.f('ix_quiz_results_quiz_id'), 'quiz_results', ['quiz_id'], unique=False)


def downgrade() -> None:
    op.drop_table('quiz_results')
    op.drop_table('quiz_answers')
    op.drop_table('quiz_sessions')
    op.drop_table('publishing_targets')
    op.drop_table('drafts')
    op.drop_table('options')
    op.drop_table('questions')
    op.drop_table('quizzes')
    op.drop_table('users')
