"""
Data models for Quick Create parsing and validation.
"""
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class ParsedOption:
    text: str
    is_correct: bool
    order_num: int
    label: str = ""  # e.g., "أ", "ب", "ج", "د"


@dataclass
class ParsedQuestion:
    text: str
    options: List[ParsedOption] = field(default_factory=list)
    explanation: Optional[str] = None
    order_num: int = 1
    raw_lines: List[str] = field(default_factory=list)


@dataclass
class ParseError:
    question_index: int  # 1-indexed question in batch
    line_number: Optional[int]
    message: str
    raw_text: str = ""


@dataclass
class ParseResult:
    is_valid: bool
    questions: List[ParsedQuestion] = field(default_factory=list)
    errors: List[ParseError] = field(default_factory=list)

    @property
    def total_questions(self) -> int:
        return len(self.questions)

    @property
    def error_summary_arabic(self) -> str:
        if not self.errors:
            return ""
        lines = ["⚠️ تم العثور على أخطاء في الأسئلة المرسلة (لم يتم حفظ أي سؤال):"]
        for err in self.errors:
            loc = f"السؤال #{err.question_index}"
            if err.line_number:
                loc += f" (السطر {err.line_number})"
            lines.append(f"• {loc}: {err.message}")
        return "\n".join(lines)
