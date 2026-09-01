"""
Stage 2 Tests: Quick Create Parser, Arabic Prefixes, Atomic All-or-Nothing Validation, Draft Service.
"""
import pytest
from app.quick_create.parser import parse_quiz_text
from app.services.draft_service import DraftService


def test_single_question_parsing():
    raw = """
    س: ما هي عاصمة جمهورية مصر العربية؟
    أ: الإسكندرية
    ب: القاهرة
    ج: الجيزة
    د: أسوان
    ص: ب
    ش: القاهرة هي العاصمة وأكبر مدن مصر.
    """
    res = parse_quiz_text(raw)
    assert res.is_valid is True
    assert len(res.questions) == 1
    q = res.questions[0]
    assert "القاهرة" in q.text or "عاصمة" in q.text
    assert len(q.options) == 4
    assert q.options[1].is_correct is True
    assert q.explanation is not None


def test_true_false_question_parsing():
    raw = """
    سؤال: الشمس تدور حول الأرض؟
    الإجابة: خطأ
    """
    res = parse_quiz_text(raw)
    assert res.is_valid is True
    assert len(res.questions) == 1
    q = res.questions[0]
    assert len(q.options) == 2
    # 'خطأ' is second option and correct
    assert q.options[1].is_correct is True


def test_atomic_batch_all_or_nothing():
    """
    Verifies that if 1 question in a batch of multiple questions is invalid,
    the entire batch is marked invalid with NO partial acceptance.
    """
    batch = """
    س: ما هي عاصمة فرنسا؟
    أ: باريس
    ب: روما
    ص: أ

    س: سؤال خاطئ بدون خيارات كافية؟
    أ: خيار وحيد
    ص: أ

    س: ما هي عاصمة ألمانيا؟
    أ: برلين
    ب: ميونخ
    ص: أ
    """
    res = parse_quiz_text(batch)
    assert res.is_valid is False
    assert len(res.questions) == 0
    assert len(res.errors) >= 1
    assert "خياران" in res.errors[0].message


@pytest.mark.asyncio
async def test_draft_lifecycle(db_session, sample_user):
    """Tests draft creation, appending questions atomically, and converting to Quiz."""
    draft = await DraftService.get_or_create_draft(db_session, sample_user.id, "اختبار الأحياء")
    assert draft.id is not None
    assert draft.title == "اختبار الأحياء"

    raw = """
    س: ما هو العضو المسؤول عن ضخ الدم؟
    أ: الكبد
    ب: القلب
    ص: ب
    """
    parsed = parse_quiz_text(raw)
    draft = await DraftService.append_questions_atomic(
        db_session, draft.id, sample_user.id, parsed.questions
    )
    assert len(draft.questions_data) == 1

    # Convert to quiz
    quiz = await DraftService.convert_draft_to_quiz(db_session, draft.id, sample_user.id)
    assert quiz.id is not None
    assert len(quiz.questions) == 1
    assert quiz.creator_id == sample_user.id
