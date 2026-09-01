"""
Keyboards for interactive Quiz Session execution.
"""
from typing import Any, Dict, List
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def get_question_options_keyboard(
    session_id: int,
    question_id: int,
    options: List[Dict[str, Any]],
) -> InlineKeyboardMarkup:
    """Builds inline buttons for each option in the active question."""
    buttons = []
    labels = ["أ", "ب", "ج", "د", "هـ", "و"]

    for idx, opt in enumerate(options):
        label = labels[idx] if idx < len(labels) else f"#{idx+1}"
        text = f"{label}) {opt['text']}"
        callback_data = f"ans_{session_id}_{question_id}_{opt['id']}"
        buttons.append([InlineKeyboardButton(text=text, callback_data=callback_data)])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_next_question_keyboard(session_id: int) -> InlineKeyboardMarkup:
    """Button to navigate to next question."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="السؤال التالي ➡️", callback_data=f"next_q_{session_id}")]
        ]
    )
