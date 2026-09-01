"""
Deterministic Arabic Quiz Question Parser.
Parses batch text formatted in standard Arabic quiz notation into structured, validated questions.
Guarantees atomic all-or-nothing batch validation.
"""
import re
from typing import List, Optional, Tuple

from app.quick_create.models import (
    ParsedOption,
    ParsedQuestion,
    ParseError,
    ParseResult,
)

# Regex Patterns for Questions, Options, Answers, Explanations
QUESTION_PREFIXES = [
    r"^(?:س(?:ؤال)?\s*(?:\d+)?\s*[:\-]\s*|\d+[\.\-\)]\s*س(?:ؤال)?\s*[:\-]?\s*|\d+[\.\-\)]\s+)",
]

OPTION_PREFIX_PATTERN = re.compile(
    r"^(?:(هـ|[أ-يa-zA-Z]|\d+))[\s]*[:\-\.\)]\s*(.*)$",
    re.IGNORECASE,
)

ANSWER_PREFIX_PATTERN = re.compile(
    r"^(?:ص(?:حيح)?|ال[إا]جابة|الجواب|الصح)\s*[:\-]\s*(.*)$",
    re.IGNORECASE,
)

EXPLANATION_PREFIX_PATTERN = re.compile(
    r"^(?:ش(?:رح)?|تلميح|توضيح)\s*[:\-]\s*(.*)$",
    re.IGNORECASE,
)

ARABIC_OPTION_LETTERS = ["أ", "ب", "ج", "د", "هـ", "و", "ز"]
NORMALIZED_LETTERS_MAP = {
    "أ": "أ", "ا": "أ", "إ": "أ", "آ": "أ", "1": "أ", "A": "أ", "a": "أ",
    "ب": "ب", "2": "ب", "B": "ب", "b": "ب",
    "ج": "ج", "3": "ج", "C": "ج", "c": "ج",
    "د": "د", "4": "د", "D": "د", "d": "د",
    "هـ": "هـ", "ه": "هـ", "5": "هـ", "E": "هـ", "e": "هـ",
    "و": "و", "6": "و", "F": "و", "f": "و",
}


def normalize_arabic_text(text: str) -> str:
    """Strip diacritics and excessive whitespace."""
    if not text:
        return ""
    # Strip tatweel and common marks
    text = re.sub(r"[\u064B-\u0652\u0640]", "", text)
    return text.strip()


def parse_quiz_text(raw_text: str, max_batch: int = 100) -> ParseResult:
    """
    Parses a block of text containing one or multiple quiz questions.
    Returns ParseResult with parsed questions or structured errors.
    Enforces atomic batch validation: if any question is invalid, is_valid=False.
    """
    if not raw_text or not raw_text.strip():
        return ParseResult(
            is_valid=False,
            questions=[],
            errors=[ParseError(question_index=0, line_number=1, message="النص المدخل فارغ.")],
        )

    lines = raw_text.splitlines()
    raw_blocks: List[List[Tuple[int, str]]] = []
    current_block: List[Tuple[int, str]] = []

    # Helper to check if line starts a new question
    def is_question_start(line_str: str) -> bool:
        line_clean = line_str.strip()
        if not line_clean:
            return False
        # Check standard question prefixes
        for pat in QUESTION_PREFIXES:
            if re.match(pat, line_clean, re.IGNORECASE):
                return True
        return False

    for line_idx, line in enumerate(lines, start=1):
        line_stripped = line.strip()
        if not line_stripped:
            # Empty line could separate questions if block exists
            if current_block and len(current_block) >= 3:
                # Check if next non-empty line starts a question or if block is already full
                pass
            continue

        if is_question_start(line_stripped):
            if current_block:
                raw_blocks.append(current_block)
                current_block = []
            current_block.append((line_idx, line_stripped))
        else:
            if not current_block:
                # First line might not have question prefix (e.g. just question sentence)
                current_block.append((line_idx, line_stripped))
            else:
                current_block.append((line_idx, line_stripped))

    if current_block:
        raw_blocks.append(current_block)

    if not raw_blocks:
        return ParseResult(
            is_valid=False,
            questions=[],
            errors=[ParseError(question_index=0, line_number=1, message="لم يتم التعرف على أي أسئلة صالحة.")],
        )

    if len(raw_blocks) > max_batch:
        return ParseResult(
            is_valid=False,
            questions=[],
            errors=[
                ParseError(
                    question_index=0,
                    line_number=1,
                    message=f"عدد الأسئلة ({len(raw_blocks)}) يتجاوز الحد الأقصى للدفعة الواحدة ({max_batch}).",
                )
            ],
        )

    parsed_questions: List[ParsedQuestion] = []
    all_errors: List[ParseError] = []

    for q_idx, block in enumerate(raw_blocks, start=1):
        q_text = ""
        options_raw: List[Tuple[int, str, str]] = []  # (line_num, label, text)
        correct_answer_raw: Optional[Tuple[int, str]] = None
        explanation_raw: Optional[str] = None
        block_lines = [b[1] for b in block]

        # First line is usually question text
        q_line_num, first_line = block[0]
        # Clean prefix
        clean_q_text = first_line
        for pat in QUESTION_PREFIXES:
            clean_q_text = re.sub(pat, "", clean_q_text, flags=re.IGNORECASE).strip()
        q_text = clean_q_text

        # Process rest of lines in the block
        for line_num, line_str in block[1:]:
            ans_match = ANSWER_PREFIX_PATTERN.match(line_str)
            if ans_match:
                correct_answer_raw = (line_num, ans_match.group(1).strip())
                continue

            exp_match = EXPLANATION_PREFIX_PATTERN.match(line_str)
            if exp_match:
                explanation_raw = exp_match.group(1).strip()
                continue

            opt_match = OPTION_PREFIX_PATTERN.match(line_str)
            if opt_match:
                label = opt_match.group(1).strip()
                opt_text = opt_match.group(2).strip()
                options_raw.append((line_num, label, opt_text))
                continue

            # If line doesn't match option/answer/explanation, maybe continuation of question or explanation
            if not options_raw and not correct_answer_raw:
                q_text += " " + line_str
            elif explanation_raw is not None:
                explanation_raw += " " + line_str
            elif options_raw:
                # Append to last option
                last_line, last_label, last_text = options_raw[-1]
                options_raw[-1] = (last_line, last_label, last_text + " " + line_str)

        # Validation for this question
        q_errors: List[ParseError] = []

        if not q_text.strip():
            q_errors.append(
                ParseError(
                    question_index=q_idx,
                    line_number=q_line_num,
                    message="نص السؤال غير موجود أو فارغ.",
                )
            )

        # Handle True/False questions (صح / خطأ) if no explicit options were provided or answer is صح/خطأ
        if not options_raw and correct_answer_raw:
            ans_val = correct_answer_raw[1].strip()
            if ans_val in ("صح", "صحيح", "true", "True", "خطأ", "خطا", "false", "False"):
                is_true_correct = ans_val in ("صح", "صحيح", "true", "True")
                options_raw = [
                    (correct_answer_raw[0], "أ", "صح"),
                    (correct_answer_raw[0], "ب", "خطأ"),
                ]
                # mark answer
                correct_answer_raw = (correct_answer_raw[0], "أ" if is_true_correct else "ب")

        if len(options_raw) < 2:
            q_errors.append(
                ParseError(
                    question_index=q_idx,
                    line_number=q_line_num,
                    message=f"السؤال يحتوي على {len(options_raw)} خيارات فقط. الحد الأدنى هو خياران.",
                )
            )
        elif len(options_raw) > 6:
            q_errors.append(
                ParseError(
                    question_index=q_idx,
                    line_number=q_line_num,
                    message=f"السؤال يحتوي على {len(options_raw)} خيارات. الحد الأقصى هو 6 خيارات.",
                )
            )

        # Check for duplicate options
        seen_texts = set()
        for l_num, lbl, opt_t in options_raw:
            norm_opt = normalize_arabic_text(opt_t)
            if not norm_opt:
                q_errors.append(
                    ParseError(
                        question_index=q_idx,
                        line_number=l_num,
                        message=f"نص الخيار ({lbl}) فارغ.",
                    )
                )
            elif norm_opt in seen_texts:
                q_errors.append(
                    ParseError(
                        question_index=q_idx,
                        line_number=l_num,
                        message=f"الخيار ({opt_t}) مكرر في نفس السؤال.",
                    )
                )
            seen_texts.add(norm_opt)

        # Determine correct option
        if not correct_answer_raw:
            q_errors.append(
                ParseError(
                    question_index=q_idx,
                    line_number=q_line_num,
                    message="لم يتم تحديد الإجابة الصحيحة (استخدم 'ص: أ' أو 'الإجابة: ...').",
                )
            )

        parsed_opts: List[ParsedOption] = []
        if not q_errors and correct_answer_raw:
            ans_str = correct_answer_raw[1].strip()
            norm_ans_letter = NORMALIZED_LETTERS_MAP.get(ans_str, ans_str)
            correct_found = False

            for order_i, (l_num, lbl, opt_t) in enumerate(options_raw, start=1):
                norm_lbl = NORMALIZED_LETTERS_MAP.get(lbl, lbl)
                is_correct = False

                # Match by label (e.g. 'أ' == 'أ') or text matching (e.g. 'باريس' == 'باريس')
                if norm_lbl == norm_ans_letter or lbl.lower() == ans_str.lower():
                    is_correct = True
                    correct_found = True
                elif normalize_arabic_text(opt_t) == normalize_arabic_text(ans_str):
                    is_correct = True
                    correct_found = True
                elif ans_str.isdigit() and int(ans_str) == order_i:
                    is_correct = True
                    correct_found = True

                parsed_opts.append(
                    ParsedOption(
                        text=opt_t,
                        is_correct=is_correct,
                        order_num=order_i,
                        label=lbl,
                    )
                )

            if not correct_found:
                q_errors.append(
                    ParseError(
                        question_index=q_idx,
                        line_number=correct_answer_raw[0],
                        message=f"الإجابة الصحيحة المحددة '{ans_str}' لا تطابق أي خيار من الخيارات المتاحة.",
                    )
                )
            else:
                # Verify exactly one correct option
                correct_count = sum(1 for o in parsed_opts if o.is_correct)
                if correct_count != 1:
                    q_errors.append(
                        ParseError(
                            question_index=q_idx,
                            line_number=correct_answer_raw[0],
                            message=f"يجب أن تكون هناك إجابة صحيحة واحدة فقط، تم العثور على {correct_count}.",
                        )
                    )

        if q_errors:
            all_errors.extend(q_errors)
        else:
            parsed_questions.append(
                ParsedQuestion(
                    text=q_text,
                    options=parsed_opts,
                    explanation=explanation_raw,
                    order_num=q_idx,
                    raw_lines=block_lines,
                )
            )

    if all_errors:
        return ParseResult(
            is_valid=False,
            questions=[],
            errors=all_errors,
        )

    return ParseResult(
        is_valid=True,
        questions=parsed_questions,
        errors=[],
    )
