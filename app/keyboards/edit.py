"""
Keyboards for Quiz preview, edit, and management.
"""
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def get_quiz_actions_keyboard(quiz_id: int, state_str: str) -> InlineKeyboardMarkup:
    """Action buttons for a created quiz."""
    buttons = [
        [
            InlineKeyboardButton(text="👁️ معاينة الأسئلة", callback_data=f"preview_quiz_{quiz_id}"),
            InlineKeyboardButton(text="🚀 نشر الاختبار", callback_data=f"publish_quiz_{quiz_id}"),
        ],
        [
            InlineKeyboardButton(text="✏️ تعديل العنوان", callback_data=f"edit_title_{quiz_id}"),
            InlineKeyboardButton(text="🗑️ حذف الاختبار", callback_data=f"delete_quiz_{quiz_id}"),
        ],
        [
            InlineKeyboardButton(text="🔙 العودة للاختبارات", callback_data="menu_my_quizzes"),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_draft_review_keyboard(draft_id: int) -> InlineKeyboardMarkup:
    """Action buttons when reviewing a draft."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="➕ إضافة المزيد من الأسئلة", callback_data=f"draft_append_{draft_id}"),
                InlineKeyboardButton(text="✅ اعتماد وحفظ الاختبار", callback_data=f"draft_save_{draft_id}"),
            ],
            [
                InlineKeyboardButton(text="❌ إلغاء المسودة", callback_data=f"draft_cancel_{draft_id}"),
            ],
        ]
    )
