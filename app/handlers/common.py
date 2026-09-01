"""
Common Handlers: /start, /help, Main Menu navigation, and settings.
"""
from aiogram import Router, types
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import User
from app.keyboards.main import (
    get_main_menu_inline_keyboard,
    get_main_menu_reply_keyboard,
)

router = Router(name="common_router")


@router.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext, user_id: int, db_user: User):
    """
    Handles /start command.
    Checks if start parameter contains deep-link (e.g. quiz_123).
    """
    await state.clear()
    args = message.text.split()[1:] if message.text else []

    if args and args[0].startswith("quiz_"):
        # Let quiz_start router handle this or pass through
        from app.handlers.quiz_start import handle_quiz_deep_link
        await handle_quiz_deep_link(message, args[0], user_id, db_user)
        return

    name = db_user.first_name or "عزيزي المستخدم"
    welcome_text = (
        f"👋 أهلاً بك يا <b>{name}</b> في <b>بوت الاختبارات (QuizBot Arabic)</b> 🎓\n\n"
        "منصة متكاملة لإنشاء وإدارة ونشر الاختبارات التفاعلية على تيليجرام بسهولة وسرعة فائقة.\n\n"
        "⚡ <b>الإنشاء السريع:</b> أرسل عشرات الأسئلة دفعة واحدة وسيتم تجهيز الاختبار فوراً.\n"
        "📢 <b>النشر:</b> انشر اختبارك في قنواتك ومجموعاتك بنقرة زر.\n"
        "📊 <b>النتائج والترتيب:</b> تصحيح فوري وحساب دقيق للدرجات."
    )

    await message.answer(
        welcome_text,
        parse_mode="HTML",
        reply_markup=get_main_menu_reply_keyboard(),
    )


@router.message(Command("help"))
@router.message(lambda msg: msg.text == "❓ المساعدة")
async def cmd_help(message: types.Message):
    """Provides help instructions for using the bot and format guide."""
    help_text = (
        "📖 <b>دليل استخدام بوت الاختبارات:</b>\n\n"
        "1️⃣ <b>إنشاء اختبار جديد:</b> اضغط على '⚡ إنشاء سريع' ثم اكتب عنوان الاختبار.\n"
        "2️⃣ <b>صيغة الأسئلة المدعومة:</b>\n\n"
        "<code>س: ما هي عاصمة المملكة العربية السعودية؟\n"
        "أ: جدة\n"
        "ب: الرياض\n"
        "ج: الدمام\n"
        "ص: ب\n"
        "ش: الرياض هي العاصمة الرسمية والمركز المالي للمملكة.</code>\n\n"
        "3️⃣ <b>صيغة صح أو خطأ:</b>\n"
        "<code>س: الأرض كوكب كروي الشكل؟\n"
        "ص: صح</code>\n\n"
        "4️⃣ يمكنك إرسال عشرات الأسئلة دفعة واحدة وسيتم فحصها بالكامل تلقائياً!"
    )
    await message.answer(help_text, parse_mode="HTML")


@router.message(lambda msg: msg.text == "⚙️ الإعدادات")
async def cmd_settings(message: types.Message, db_user: User):
    """Displays user settings and status."""
    settings_text = (
        "⚙️ <b>إعدادات الحساب:</b>\n\n"
        f"👤 <b>الاسم:</b> {db_user.first_name or 'غير محدد'}\n"
        f"🆔 <b>المعرف الداخلي:</b> <code>{db_user.id}</code>\n"
        f"📱 <b>معرف تيليجرام:</b> <code>{db_user.telegram_id}</code>\n"
        f"🟢 <b>الحالة:</b> نشط"
    )
    await message.answer(settings_text, parse_mode="HTML")
