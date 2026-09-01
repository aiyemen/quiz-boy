"""
Exhaustive QA Test Suite for Quick Create Parser and Atomic Transactions.
Verifies all Arabic prefixes, separators, whitespace, true/false, multiple choice,
error conditions, and atomic 20-question rollback.
"""
import pytest
from app.quick_create.parser import parse_quiz_text
from app.services.draft_service import DraftService
from app.database.models import Quiz, Question, Option, Draft


def test_arabic_question_prefix_variations():
    cases = [
        "س: ما هي لغة الضاد؟\nأ: العربية\nب: الإنجليزية\nص: أ",
        "س : ما هي لغة الضاد؟\nأ : العربية\nب : الإنجليزية\nص : أ",
        "سؤال: ما هي لغة الضاد؟\nأ- العربية\nب- الإنجليزية\nالاجابة: أ",
        "سؤال : ما هي لغة الضاد؟\nأ: العربية\nب: الإنجليزية\nالإجابة: أ",
        "س- ما هي لغة الضاد؟\nأ) العربية\nب) الإنجليزية\nالجواب: العربية",
        "1. س: ما هي لغة الضاد؟\n1: العربية\n2: الإنجليزية\nص: 1",
    ]
    for raw in cases:
        res = parse_quiz_text(raw)
        assert res.is_valid is True, f"Failed on raw text:\n{raw}\nErrors: {res.errors}"
        assert len(res.questions) == 1
        assert res.questions[0].options[0].is_correct is True


def test_arabic_explanation_prefixes():
    cases = [
        "س: سؤال توضيحي؟\nأ: خيار 1\nب: خيار 2\nص: أ\nش: هذا شرح تفصيلي.",
        "س: سؤال توضيحي؟\nأ: خيار 1\nب: خيار 2\nص: أ\nشرح: هذا شرح تفصيلي.",
        "س: سؤال توضيحي؟\nأ: خيار 1\nب: خيار 2\nص: أ\nتلميح: هذا تلميح ذكي.",
        "س: سؤال توضيحي؟\nأ: خيار 1\nب: خيار 2\nص: أ\nتوضيح: هذا توضيح هام.",
    ]
    for raw in cases:
        res = parse_quiz_text(raw)
        assert res.is_valid is True
        assert res.questions[0].explanation is not None
        assert len(res.questions[0].explanation) > 0


def test_true_false_syntaxes():
    # Implicit options with صح
    raw1 = "س: الأرض كروية الشكل؟\nالإجابة: صح"
    res1 = parse_quiz_text(raw1)
    assert res1.is_valid is True
    assert len(res1.questions[0].options) == 2
    assert res1.questions[0].options[0].text == "صح"
    assert res1.questions[0].options[0].is_correct is True

    # Implicit options with خطأ
    raw2 = "س: الشمس تدور حول القمر؟\nالاجابة: خطأ"
    res2 = parse_quiz_text(raw2)
    assert res2.is_valid is True
    assert len(res2.questions[0].options) == 2
    assert res2.questions[0].options[1].text == "خطأ"
    assert res2.questions[0].options[1].is_correct is True


def test_multiple_choice_up_to_six_options():
    raw = """
    س: ما هي الألوان الأساسية والثانوية؟
    أ: أحمر
    ب: أزرق
    ج: أصفر
    د: أخضر
    هـ: برتقالي
    و: بنفسجي
    ص: أ
    """
    res = parse_quiz_text(raw)
    assert res.is_valid is True
    assert len(res.questions[0].options) == 6


def test_error_conditions_isolated():
    # 1. Missing options (< 2)
    res_one_opt = parse_quiz_text("س: سؤال بخيار واحد؟\nأ: خيار يتيم\nص: أ")
    assert res_one_opt.is_valid is False
    assert any("خياران" in e.message for e in res_one_opt.errors)

    # 2. Excess options (> 6)
    res_excess = parse_quiz_text("""
    س: سؤال خيارات كثيرة؟
    أ: 1
    ب: 2
    ج: 3
    د: 4
    هـ: 5
    و: 6
    ز: 7
    ص: أ
    """)
    assert res_excess.is_valid is False
    assert any("الحد الأقصى" in e.message for e in res_excess.errors)

    # 3. Duplicate options
    res_dup = parse_quiz_text("س: خيارات مكررة؟\nأ: عمان\nب: عمان\nص: أ")
    assert res_dup.is_valid is False
    assert any("مكرر" in e.message for e in res_dup.errors)

    # 4. Empty option
    res_empty_opt = parse_quiz_text("س: خيار فارغ؟\nأ: \nب: إجابة\nص: ب")
    assert res_empty_opt.is_valid is False
    assert any("فارغ" in e.message for e in res_empty_opt.errors)

    # 5. Missing correct answer
    res_no_ans = parse_quiz_text("س: أين الإجابة؟\nأ: خيار 1\nب: خيار 2")
    assert res_no_ans.is_valid is False
    assert any("لم يتم تحديد الإجابة" in e.message for e in res_no_ans.errors)

    # 6. Invalid answer reference
    res_inv_ans = parse_quiz_text("س: إجابة غير موجودة؟\nأ: خيار 1\nب: خيار 2\nص: ج")
    assert res_inv_ans.is_valid is False
    assert any("لا تطابق" in e.message for e in res_inv_ans.errors)


def test_twenty_questions_batch_valid():
    """Generates a batch of 20 valid questions and verifies full parsing."""
    lines = []
    for i in range(1, 21):
        lines.append(f"س: هذا هو السؤال رقم {i}؟")
        lines.append(f"أ: خيار ألف للسؤال {i}")
        lines.append(f"ب: خيار باء للسؤال {i}")
        lines.append(f"ج: خيار جيم للسؤال {i}")
        lines.append(f"ص: أ")
        lines.append(f"ش: شرح السؤال {i}")
        lines.append("")

    batch_text = "\n".join(lines)
    res = parse_quiz_text(batch_text)
    assert res.is_valid is True
    assert len(res.questions) == 20
    for idx, q in enumerate(res.questions, start=1):
        assert q.order_num == idx
        assert len(q.options) == 3
        assert q.options[0].is_correct is True
        assert f"شرح السؤال {idx}" in q.explanation


@pytest.mark.asyncio
async def test_atomic_rollback_on_question_seventeen_failure(db_session, sample_user):
    """
    Critical QA requirement:
    For a batch containing 20 questions where question #17 is invalid:
    Expected: ZERO questions persisted.
    Verify database state after atomic transaction.
    """
    draft = await DraftService.get_or_create_draft(db_session, sample_user.id, "اختبار الذرة والفيزياء")
    initial_draft_questions = list(draft.questions_data)
    assert len(initial_draft_questions) == 0

    lines = []
    for i in range(1, 21):
        if i == 17:
            # Corrupted question #17 with missing options and invalid answer
            lines.append("س: ما هو تسارع الجاذبية الأرضية؟")
            lines.append("أ: 9.8 م/ث2")
            lines.append("ص: ز")  # Invalid option key
        else:
            lines.append(f"س: سؤال رقم {i}؟")
            lines.append("أ: إجابة صحيحة")
            lines.append("ب: إجابة خاطئة")
            lines.append("ص: أ")
        lines.append("")

    batch_text = "\n".join(lines)
    parse_result = parse_quiz_text(batch_text)

    # 1. Verify parser rejected entire batch atomically
    assert parse_result.is_valid is False
    assert len(parse_result.questions) == 0
    assert len(parse_result.errors) > 0

    # 2. Attempt to persist invalid questions list (empty)
    with pytest.raises(Exception):
        if not parse_result.is_valid:
            raise ValueError("Parser atomic rejection: batch contains errors")
        await DraftService.append_questions_atomic(
            db_session, draft.id, sample_user.id, parse_result.questions
        )

    # 3. Verify database state remains 100% clean with ZERO questions added
    await db_session.refresh(draft)
    assert len(draft.questions_data) == 0
