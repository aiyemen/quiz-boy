"""
Keyboards for Publishing targets selection.
"""
from typing import List
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.database.models import PublishingTarget


def get_targets_selection_keyboard(
    quiz_id: int,
    targets: List[PublishingTarget],
) -> InlineKeyboardMarkup:
    """Keyboard listing available channels/groups for publishing."""
    buttons = []
    for t in targets:
        icon = "📢" if t.chat_type == "channel" else "👥"
        buttons.append([
            InlineKeyboardButton(
                text=f"{icon} {t.chat_title}",
                callback_data=f"target_sel_{quiz_id}_{t.id}",
            )
        ])

    buttons.append([
        InlineKeyboardButton(text="➕ تسجيل قناة / مجموعة جديدة", callback_data="add_new_target"),
    ])
    buttons.append([
        InlineKeyboardButton(text="🔙 إلغاء", callback_data=f"manage_quiz_{quiz_id}"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)
