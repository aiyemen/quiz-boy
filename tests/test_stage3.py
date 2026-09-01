"""
Stage 3 Tests: Telegram Layer, User Resolution Middleware, Keyboards, Arabic Strings.
"""
import pytest
from app.database.models import User
from app.keyboards.main import get_main_menu_reply_keyboard, get_main_menu_inline_keyboard
from app.middlewares.user_resolution import resolve_or_create_user


@pytest.mark.asyncio
async def test_user_resolution_from_telegram_id(db_session):
    """
    CRITICAL P0 TEST:
    Verifies that Telegram ID (BigInt) is resolved to internal DB user ID (users.id).
    Subsequent lookups return the exact same internal user record.
    """
    tg_id = 998877665544
    user1 = await resolve_or_create_user(db_session, tg_id, username="student_a", first_name="محمود")

    assert user1.id is not None
    assert user1.telegram_id == tg_id

    # Second call with same tg_id should resolve same internal DB user
    user2 = await resolve_or_create_user(db_session, tg_id, username="student_a_updated", first_name="محمود")
    assert user2.id == user1.id
    assert user2.username == "student_a_updated"


def test_main_menu_keyboards_arabic_labels():
    """Verifies all specified main menu labels in Arabic."""
    reply_kb = get_main_menu_reply_keyboard()
    all_btn_texts = [btn.text for row in reply_kb.keyboard for btn in row]

    expected = ["⚡ إنشاء سريع", "📝 اختباراتي", "📢 أماكن النشر", "📊 النتائج", "⚙️ الإعدادات", "❓ المساعدة"]
    for exp in expected:
        assert exp in all_btn_texts
