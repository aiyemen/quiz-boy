"""
Main menu keyboards for QuizBot Arabic.
"""
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)


def get_main_menu_reply_keyboard() -> ReplyKeyboardMarkup:
    """Standard bottom reply keyboard for the main menu."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="⚡ إنشاء سريع"), KeyboardButton(text="📝 اختباراتي")],
            [KeyboardButton(text="📢 أماكن النشر"), KeyboardButton(text="📊 النتائج")],
            [KeyboardButton(text="⚙️ الإعدادات"), KeyboardButton(text="❓ المساعدة")],
        ],
        resize_keyboard=True,
    )


def get_main_menu_inline_keyboard() -> InlineKeyboardMarkup:
    """Inline keyboard for main navigation."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="⚡ إنشاء سريع", callback_data="menu_quick_create"),
                InlineKeyboardButton(text="📝 اختباراتي", callback_data="menu_my_quizzes"),
            ],
            [
                InlineKeyboardButton(text="📢 أماكن النشر", callback_data="menu_targets"),
                InlineKeyboardButton(text="📊 النتائج", callback_data="menu_results"),
            ],
            [
                InlineKeyboardButton(text="⚙️ الإعدادات", callback_data="menu_settings"),
                InlineKeyboardButton(text="❓ المساعدة", callback_data="menu_help"),
            ],
        ]
    )
