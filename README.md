# 🎓 QuizBot Arabic — Production Ready

منصة متطورة واحترافية لإدارة ونشر الاختبارات التفاعلية عبر تيليجرام باللغة العربية، مصممة بأعلى معايير هندسة البرمجيات والأمان وقابلية التوسع.

---

## 🧭 جدول المحتويات (Table of Contents)

1. [نظرة عامة على المشروع (Project Overview)](#1-نظرة-عامة-على-المشروع)
2. [المعمارية والهيكلية (Architecture & Directory Structure)](#2-المعمارية-والهيكلية)
3. [المتطلبات الأساسية (Requirements)](#3-المتطلبات-الأساسية)
4. [التثبيت والإعداد (Installation & Setup)](#4-التثبيت-والإعداد)
5. [المتغيرات البيئية (Environment Variables)](#5-المتغيرات-البيئية)
6. [قاعدة البيانات والترحيل (Database & Alembic Migrations)](#6-قاعدة-البيانات-والترحيل)
7. [تشغيل البوت (Running the Bot)](#7-تشغيل-البوت)
8. [تشغيل الاختبارات (Running Tests)](#8-تشغيل-الاختبارات)
9. [الحاويات والنشر عبر Docker (Docker & Production Deployment)](#9-الحاويات-والنشر-عبر-docker)
10. [الأمان والحماية المتقدمة (Security Architecture)](#10-الأمان-والحماية-المتقدمة)

---

## 1. نظرة عامة على المشروع

**QuizBot Arabic** يتيح للمعلمين والمشرفين إنشاء اختبارات مؤتمتة بسرعة فائقة عبر ميزة **الإنشاء السريع (Quick Create)**، مع فحص ذري (Atomic All-or-Nothing Validation) للأسئلة بدون أخطاء جزئية، ونشرها على القنوات والمجموعات، وتشغيل جلسات الاختبار للمشاركين مع توثيق الإصدارات وتوليد بطاقات النتائج الفورية.

### أبرز الميزات:
- ⚡ **الإنشاء السريع الذري (Quick Create)**: إرسال عشرات الأسئلة دفعة واحدة وفحصها بالكامل.
- 🧊 **تجميد الاختبارات النشطة (Active Freeze)**: حماية الاختبارات قيد التشغيل من التعديل العشوائي.
- 🔒 **حماية التلاعب وحل مشكلة المعرفات (P0 User Resolution Fix)**: الفصل التام بين Telegram ID و Internal DB `users.id`.
- 📊 **محرك النتائج وترتيب المتسابقين (Results & Ranking Abstraction)**: حفظ غير متكرر (Idempotent Results) مع واجهة بروتوكول مرنة للترتيب `RankingStrategy`.
- 📢 **إدارة أماكن النشر والتحقق من الصلاحيات (Permission & Target Management)**: بدون أي معرفات ثابتة (No Hardcoded IDs).

---

## 2. المعمارية والهيكلية

```
.
├── app/
│   ├── bot.py                     # تهيئة البوت والموجهات و Middleware
│   ├── main.py                    # نقطة الدخول الرئيسية مع Graceful Shutdown
│   ├── config/                    # الإعدادات والمتغيرات البيئية
│   │   └── settings.py
│   ├── database/                  # نماذج SQLAlchemy واتصال قاعدة البيانات
│   │   ├── models.py
│   │   ├── schema.py
│   │   └── session.py
│   ├── handlers/                  # معالجات رسائل وأزرار تيليجرام
│   │   ├── common.py
│   │   ├── preview_edit.py
│   │   ├── publishing.py
│   │   ├── quick_create.py
│   │   ├── quiz_engine.py
│   │   ├── quiz_start.py
│   │   └── results.py
│   ├── keyboards/                 # لوحات المفاتيح والأزرار التفاعلية
│   │   ├── edit.py
│   │   ├── engine.py
│   │   ├── main.py
│   │   └── publishing.py
│   ├── middlewares/               # وسيط مطابقة وتوثيق المستخدمين
│   │   └── user_resolution.py
│   ├── permissions/               # فحص وإدارة صلاحيات القنوات والمجموعات
│   │   └── service.py
│   ├── publishing/                # خدمة نشر الاختبارات
│   │   └── service.py
│   ├── quick_create/              # محلل ونموذج الإنشاء السريع
│   │   ├── models.py
│   │   └── parser.py
│   ├── quiz_engine/               # محرك إدارة الجلسات وتسجيل الإجابات
│   │   └── service.py
│   ├── results/                   # محرك النتائج وبروتوكول الترتيب
│   │   ├── exceptions.py
│   │   ├── service.py
│   │   └── strategies.py
│   └── services/                  # خدمات المسودات وتعديل الاختبارات
│       ├── draft_service.py
│       └── quiz_edit_service.py
├── alembic/                       # ترحيلات قاعدة البيانات
│   ├── env.py
│   └── versions/001_initial_schema.py
├── tests/                         # مصفوفة الاختبارات الشاملة (Stages 1-8)
│   ├── conftest.py
│   ├── test_stage1.py
│   ├── test_stage2.py
│   ├── test_stage3.py
│   ├── test_stage4.py
│   ├── test_stage5.py
│   ├── test_stage6.py
│   ├── test_stage7.py
│   └── test_stage8.py
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── pyproject.toml
├── .env.example
└── README.md
```

---

## 3. المتطلبات الأساسية

- **Python**: 3.10 أو 3.11 أو أحدث
- **PostgreSQL**: 14+ (للإنتاج) أو SQLite (للتطوير المحلي)
- **Telegram Bot Token**: من [@BotFather](https://t.me/botfather)

---

## 4. التثبيت والإعداد

1. استنساخ المستودع:
```bash
git clone <repo_url>
cd quizbot-arabic
```

2. إنشاء وتفعيل البيئة الافتراضية:
```bash
python3 -m venv venv
source venv/bin/activate  # على Linux/macOS
# أو venv\Scripts\activate على Windows
```

3. تثبيت الاعتماديات:
```bash
pip install -r requirements.txt
```

4. نسخ ملف الإعدادات:
```bash
cp .env.example .env
# ثم عدل BOT_TOKEN في ملف .env
```

---

## 5. المتغيرات البيئية

| المتغير | الوصف | القيمة الافتراضية |
|---|---|---|
| `BOT_TOKEN` | توكن البوت الصادر من BotFather | `إلزامي` |
| `DATABASE_URL` | رابط الاتصال بقاعدة البيانات | `sqlite+aiosqlite:///./quizbot.db` |
| `ENVIRONMENT` | بيئة التشغيل (`development` أو `production`) | `development` |
| `LOG_LEVEL` | مستوى السجلات (`DEBUG`, `INFO`, `WARNING`, `ERROR`) | `INFO` |
| `MAX_BATCH_QUESTIONS` | الحد الأقصى للأسئلة في الدفعة الواحدة | `100` |
| `WEBHOOK_URL` | رابط الويب هوك في حال الرغبة باستخدامه | `فارغ (Long Polling)` |

---

## 6. قاعدة البيانات والترحيل

تطبيق ترحيلات Alembic:
```bash
alembic upgrade head
```

إنشاء ترحيل جديد بعد أي تعديل على النماذج:
```bash
alembic revision --autogenerate -m "وصف التعديل"
```

---

## 7. تشغيل البوت

### الوضع الافتراضي (Long Polling):
```bash
python3 -m app.main
```

### وضع Webhook:
اضبط `WEBHOOK_URL=https://your-domain.com` في ملف `.env` ثم شغّل:
```bash
python3 -m app.main
```

---

## 8. تشغيل الاختبارات

تشغيل كامل مصفوفة الاختبارات (Stages 1-8):
```bash
pytest -v
```

تشغيل مرحلة محددة (مثل Stage 7 للنتائج أو Stage 8 للأمان):
```bash
pytest tests/test_stage7.py -v
pytest tests/test_stage8.py -v
```

---

## 9. الحاويات والنشر عبر Docker

تشغيل البوت وقاعدة بيانات PostgreSQL باستخدام Docker Compose:
```bash
docker-compose up -d --build
```

فحص السجلات:
```bash
docker-compose logs -f bot
```

---

## 10. الأمان والحماية المتقدمة

1. **User Resolution Integrity (P0 Fix)**:
   يتم حل Telegram ID وتحويله إلى `users.id` الداخلي في طبقة Middleware، مع حظر تمرير معرف تيليجرام الخام إلى أي علاقة قاعدة بيانات.
2. **Anti-Tampering Callbacks**:
   التحقق الخادمي الصارم من تطابق هوية صاحب الجلسة والسؤال والخيار عند النقر على أي زر لمنع التلاعب.
3. **Idempotency & Race Protection**:
   استخدام قيد فريد `UNIQUE(session_id)` في جدول `quiz_results` وقيد `UNIQUE(session_id, question_id)` في جدول `quiz_answers` لمنع ازدواجية الحساب عند نقرات الأزرار المتكررة.
4. **Active Quiz Freeze**:
   منع حذف أو تعديل الأسئلة والخيارات والإجابات لأي اختبار حالته `ACTIVE` لحماية الجلسات الجارية.
5. **No Hardcoded Secrets / Chat IDs**:
   جميع الأسرار ومواقع النشر تُدار ديناميكياً وعبر المتغيرات البيئية فقط.
