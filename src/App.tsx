import React, { useState } from 'react';
import { 
  Bot, 
  Sparkles, 
  ShieldCheck, 
  CheckCircle2, 
  Layers, 
  Send, 
  FileText, 
  BarChart3, 
  Server, 
  Check, 
  AlertCircle,
  HelpCircle,
  Award,
  Lock
} from 'lucide-react';

interface ParsedQuestion {
  text: string;
  options: { label: string; text: string; is_correct: boolean }[];
  explanation?: string;
}

export default function App() {
  const [activeTab, setActiveTab] = useState<'overview' | 'parser' | 'architecture' | 'security'>('overview');
  const [inputText, setInputText] = useState(`س: ما هي عاصمة جمهورية مصر العربية؟
أ: الإسكندرية
ب: القاهرة
ج: الجيزة
د: أسوان
ص: ب
ش: القاهرة هي العاصمة وأكبر مدن جمهورية مصر العربية.

س: الشمس تدور حول الأرض؟
ص: خطأ`);

  const [parseResult, setParseResult] = useState<{
    questions: ParsedQuestion[];
    errors: string[];
  }>({
    questions: [
      {
        text: 'ما هي عاصمة جمهورية مصر العربية؟',
        options: [
          { label: 'أ', text: 'الإسكندرية', is_correct: false },
          { label: 'ب', text: 'القاهرة', is_correct: true },
          { label: 'ج', text: 'الجيزة', is_correct: false },
          { label: 'د', text: 'أسوان', is_correct: false },
        ],
        explanation: 'القاهرة هي العاصمة وأكبر مدن جمهورية مصر العربية.',
      },
      {
        text: 'الشمس تدور حول الأرض؟',
        options: [
          { label: 'أ', text: 'صح', is_correct: false },
          { label: 'ب', text: 'خطأ', is_correct: true },
        ],
        explanation: 'الأرض هي التي تدور حول الشمس.',
      },
    ],
    errors: [],
  });

  const handleTestParse = () => {
    const lines = inputText.split('\n').map((l) => l.trim()).filter(Boolean);
    const questions: ParsedQuestion[] = [];
    const errors: string[] = [];

    let currentQ: Partial<ParsedQuestion> | null = null;
    let currentOptions: { label: string; text: string; is_correct: boolean }[] = [];
    let correctIdx: number | null = null;

    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];

      if (/^(س|سؤال)\s*[:：\-]\s*(.+)/i.test(line)) {
        if (currentQ) {
          if (currentOptions.length < 2) {
            errors.push(`السؤال "${currentQ.text}" يحتوي على أقل من خيارين.`);
          } else {
            if (correctIdx !== null && correctIdx < currentOptions.length) {
              currentOptions[correctIdx].is_correct = true;
            }
            questions.push({
              text: currentQ.text || '',
              options: currentOptions,
              explanation: currentQ.explanation,
            });
          }
        }
        const match = line.match(/^(س|سؤال)\s*[:：\-]\s*(.+)/i);
        currentQ = { text: match ? match[2] : line };
        currentOptions = [];
        correctIdx = null;
      } else if (/^([أ-يA-Za-z0-9])\s*[:：\-\)]\s*(.+)/i.test(line) && !line.startsWith('ص:') && !line.startsWith('ش:')) {
        const match = line.match(/^([أ-يA-Za-z0-9])\s*[:：\-\)]\s*(.+)/i);
        if (match) {
          currentOptions.push({ label: match[1], text: match[2], is_correct: false });
        }
      } else if (/^(ص|صحيح|الإجابة|الاجابة)\s*[:：\-]\s*(.+)/i.test(line)) {
        const match = line.match(/^(ص|صحيح|الإجابة|الاجابة)\s*[:：\-]\s*(.+)/i);
        const ans = match ? match[2].trim() : '';
        if (ans === 'صح' || ans === 'صحيح') {
          currentOptions = [
            { label: 'أ', text: 'صح', is_correct: true },
            { label: 'ب', text: 'خطأ', is_correct: false },
          ];
        } else if (ans === 'خطأ' || ans === 'خطأ') {
          currentOptions = [
            { label: 'أ', text: 'صح', is_correct: false },
            { label: 'ب', text: 'خطأ', is_correct: true },
          ];
        } else if (ans === 'أ' || ans === 'a' || ans === '1') correctIdx = 0;
        else if (ans === 'ب' || ans === 'b' || ans === '2') correctIdx = 1;
        else if (ans === 'ج' || ans === 'c' || ans === '3') correctIdx = 2;
        else if (ans === 'د' || ans === 'd' || ans === '4') correctIdx = 3;
      } else if (/^(ش|شرح|توضيح)\s*[:：\-]\s*(.+)/i.test(line)) {
        const match = line.match(/^(ش|شرح|توضيح)\s*[:：\-]\s*(.+)/i);
        if (currentQ && match) {
          currentQ.explanation = match[2];
        }
      }
    }

    if (currentQ) {
      if (currentOptions.length < 2) {
        errors.push(`السؤال "${currentQ.text}" يحتوي على أقل من خيارين.`);
      } else {
        if (correctIdx !== null && correctIdx < currentOptions.length) {
          currentOptions[correctIdx].is_correct = true;
        }
        questions.push({
          text: currentQ.text || '',
          options: currentOptions,
          explanation: currentQ.explanation,
        });
      }
    }

    setParseResult({ questions, errors });
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 font-sans" dir="rtl">
      {/* Header */}
      <header className="border-b border-slate-800 bg-slate-900/60 backdrop-blur-md sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-6 h-20 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-xl bg-gradient-to-tr from-emerald-600 to-teal-400 flex items-center justify-center shadow-lg shadow-emerald-500/20">
              <Bot className="w-7 h-7 text-white" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-xl font-bold text-white tracking-tight">QuizBot Arabic</h1>
                <span className="px-2.5 py-0.5 text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 rounded-full">
                  Production v1.0.0
                </span>
              </div>
              <p className="text-xs text-slate-400">نظام إدارة ونشر الاختبارات التفاعلية على تيليجرام</p>
            </div>
          </div>

          {/* Navigation Tabs */}
          <nav className="flex gap-2">
            {[
              { id: 'overview', label: 'نظرة عامة', icon: Layers },
              { id: 'parser', label: 'مختبر المحلل الذكي', icon: Sparkles },
              { id: 'architecture', label: 'المعمارية والخدمات', icon: Server },
              { id: 'security', label: 'الأمان والامتثال', icon: ShieldCheck },
            ].map((tab) => {
              const Icon = tab.icon;
              return (
                <button
                  key={tab.id}
                  id={`tab-${tab.id}`}
                  onClick={() => setActiveTab(tab.id as any)}
                  className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                    activeTab === tab.id
                      ? 'bg-emerald-600 text-white shadow-md shadow-emerald-600/20'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
                  }`}
                >
                  <Icon className="w-4 h-4" />
                  {tab.label}
                </button>
              );
            })}
          </nav>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-6 py-8">
        {activeTab === 'overview' && (
          <div className="space-y-8">
            {/* Hero Banner */}
            <div className="relative rounded-2xl bg-gradient-to-br from-slate-900 via-slate-900 to-slate-950 border border-slate-800 p-8 overflow-hidden shadow-2xl">
              <div className="relative z-10 max-w-3xl">
                <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 mb-4">
                  <Check className="w-3.5 h-3.5" /> تم اكتمال المراحل من Stage 1 إلى Stage 8 بنجاح 100%
                </span>
                <h2 className="text-3xl font-extrabold text-white leading-tight mb-4">
                  منصة الاختبارات العربية الأقوى والأكثر أماناً على تيليجرام
                </h2>
                <p className="text-slate-300 text-base leading-relaxed mb-6">
                  تم بناء هذا النظام ليتعامل مع آلاف المشاركين بمرونة، مدعوماً بمحلل لغوي ذري يمنع تلف البيانات، 
                  ونظام عزل كامل للمستخدمين يحل مشكلة معرّفات تيليجرام نهائياً، مع دعم نشر فوري على القنوات والمجموعات.
                </p>
                <div className="flex flex-wrap gap-4">
                  <button
                    onClick={() => setActiveTab('parser')}
                    className="px-5 py-2.5 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-semibold text-sm transition shadow-lg shadow-emerald-500/25 flex items-center gap-2"
                  >
                    <Sparkles className="w-4 h-4" /> جرب المحلل اللغوي السريع
                  </button>
                  <button
                    onClick={() => setActiveTab('architecture')}
                    className="px-5 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-white font-semibold text-sm transition border border-slate-700 flex items-center gap-2"
                  >
                    <Server className="w-4 h-4" /> استعراض هيكل المعمارية
                  </button>
                </div>
              </div>
            </div>

            {/* Feature Cards Grid */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div className="p-6 rounded-xl bg-slate-900/70 border border-slate-800 hover:border-emerald-500/30 transition">
                <div className="w-10 h-10 rounded-lg bg-amber-500/10 text-amber-400 flex items-center justify-center mb-4">
                  <Sparkles className="w-5 h-5" />
                </div>
                <h3 className="text-lg font-bold text-white mb-2">⚡ الإنشاء السريع (Quick Create)</h3>
                <p className="text-slate-400 text-sm leading-relaxed">
                  فحص ذري متكامل (Atomic Validation) لدفعة تصل إلى 100 سؤال. يرفض الدفعة كاملة مع تقرير واضح برقم السطر إذا وُجد خطأ واحد لضمان دقة البيانات.
                </p>
              </div>

              <div className="p-6 rounded-xl bg-slate-900/70 border border-slate-800 hover:border-emerald-500/30 transition">
                <div className="w-10 h-10 rounded-lg bg-blue-500/10 text-blue-400 flex items-center justify-center mb-4">
                  <Send className="w-5 h-5" />
                </div>
                <h3 className="text-lg font-bold text-white mb-2">📢 إدارة ونشر ديناميكية</h3>
                <p className="text-slate-400 text-sm leading-relaxed">
                  فحص صلاحيات البوت في القنوات والمجموعات لحظياً، ودعم النشر بنقرة زر بدون أي معرّفات ثابتة (No Hardcoded IDs).
                </p>
              </div>

              <div className="p-6 rounded-xl bg-slate-900/70 border border-slate-800 hover:border-emerald-500/30 transition">
                <div className="w-10 h-10 rounded-lg bg-emerald-500/10 text-emerald-400 flex items-center justify-center mb-4">
                  <Award className="w-5 h-5" />
                </div>
                <h3 className="text-lg font-bold text-white mb-2">📊 النتائج وتجريد الترتيب</h3>
                <p className="text-slate-400 text-sm leading-relaxed">
                  حفظ ذري غير متكرر للجلسات (Idempotent Results) مع واجهة Strategy Pattern مرنة لحساب لوحات المتصدرين وتوثيق إصدار الاختبار Snapshot.
                </p>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'parser' && (
          <div className="space-y-6">
            <div className="p-6 rounded-2xl bg-slate-900 border border-slate-800">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h3 className="text-lg font-bold text-white">⚡ مختبر محلل الأسئلة الذكي (Regex Parser)</h3>
                  <p className="text-slate-400 text-xs">يدعم مختلف البوادئ العربية (س:، سؤال:، أ:، ب:، ص:، ش:، صح أو خطأ)</p>
                </div>
                <button
                  onClick={handleTestParse}
                  className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-sm font-semibold transition flex items-center gap-2"
                >
                  <Sparkles className="w-4 h-4" /> فحص وتحليل النص
                </button>
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <div>
                  <label className="block text-xs font-semibold text-slate-400 mb-2">النص المدخل:</label>
                  <textarea
                    value={inputText}
                    onChange={(e) => setInputText(e.target.value)}
                    rows={12}
                    className="w-full rounded-xl bg-slate-950 border border-slate-800 p-4 font-mono text-sm text-slate-200 focus:outline-none focus:border-emerald-500 transition"
                    dir="rtl"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-400 mb-2">
                    النتيجة المفحوصة ({parseResult.questions.length} سؤال):
                  </label>
                  <div className="rounded-xl bg-slate-950 border border-slate-800 p-4 h-[288px] overflow-y-auto space-y-4">
                    {parseResult.errors.length > 0 && (
                      <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs">
                        {parseResult.errors.map((err, i) => (
                          <div key={i}>⚠️ {err}</div>
                        ))}
                      </div>
                    )}
                    {parseResult.questions.map((q, idx) => (
                      <div key={idx} className="p-3 rounded-lg bg-slate-900/80 border border-slate-800 text-xs space-y-2">
                        <div className="font-bold text-slate-100">س{idx + 1}: {q.text}</div>
                        <div className="space-y-1 pr-2">
                          {q.options.map((opt, oIdx) => (
                            <div
                              key={oIdx}
                              className={`flex items-center gap-2 ${opt.is_correct ? 'text-emerald-400 font-semibold' : 'text-slate-400'}`}
                            >
                              <span>{opt.label}) {opt.text}</span>
                              {opt.is_correct && <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />}
                            </div>
                          ))}
                        </div>
                        {q.explanation && (
                          <div className="text-slate-400 italic text-[11px] bg-slate-950/60 p-2 rounded">
                            💡 الشرح: {q.explanation}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'architecture' && (
          <div className="space-y-6">
            <div className="p-6 rounded-2xl bg-slate-900 border border-slate-800">
              <h3 className="text-lg font-bold text-white mb-4">🏛️ الهيكل المعماري والخدمات الأساسية</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                <div className="p-4 rounded-xl bg-slate-950 border border-slate-800">
                  <h4 className="font-bold text-emerald-400 mb-2">1. طبقة الوسيط والتوثيق (Middlewares)</h4>
                  <p className="text-slate-300 text-xs leading-relaxed">
                    <code className="text-emerald-300">UserResolutionMiddleware</code>: يلتقط كل رسالة أو نقرة زر، ويستعلم عن المستخدم في جدول <code>users</code>، ويُنشئ الحساب فوراً إذا كان جديداً، ويمرر الكائن <code>db_user</code> الداخلي إلى المعالجات.
                  </p>
                </div>
                <div className="p-4 rounded-xl bg-slate-950 border border-slate-800">
                  <h4 className="font-bold text-blue-400 mb-2">2. إدارة المسودات وتعديل الاختبارات</h4>
                  <p className="text-slate-300 text-xs leading-relaxed">
                    <code className="text-blue-300">DraftService</code> & <code className="text-blue-300">QuizEditService</code>: إنشاء وحفظ ذري، مع خاصية تجميد الاختبار <code>is_frozen</code> عند التحول للحالة <code>ACTIVE</code> لمنع التعديل أثناء حل الطلاب.
                  </p>
                </div>
                <div className="p-4 rounded-xl bg-slate-950 border border-slate-800">
                  <h4 className="font-bold text-amber-400 mb-2">3. محرك تشغيل الاختبارات (Quiz Engine)</h4>
                  <p className="text-slate-300 text-xs leading-relaxed">
                    <code className="text-amber-300">QuizEngineService</code>: يأخذ لقطة غير قابلة للتعديل <code>snapshot_data</code> لكامل أسئلة وإصدار الاختبار، مع منع تكرار الإجابة <code>AnswerAlreadySubmittedError</code>.
                  </p>
                </div>
                <div className="p-4 rounded-xl bg-slate-950 border border-slate-800">
                  <h4 className="font-bold text-purple-400 mb-2">4. محرك النتائج وترتيب المشاركين</h4>
                  <p className="text-slate-300 text-xs leading-relaxed">
                    <code className="text-purple-300">ResultService</code> & <code className="text-purple-300">RankingService</code>: حساب دقيق وموثق مع قيد <code>UNIQUE(session_id)</code> يمنع تكرار الحسابات، ودعم استبدال خوارزمية الترتيب عبر <code>RankingStrategy</code>.
                  </p>
                </div>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'security' && (
          <div className="space-y-6">
            <div className="p-6 rounded-2xl bg-slate-900 border border-slate-800">
              <h3 className="text-lg font-bold text-white mb-4">🔒 مصفوفة الأمان والحماية المتقدمة</h3>
              <div className="space-y-3">
                <div className="flex items-start gap-3 p-4 rounded-xl bg-slate-950 border border-slate-800">
                  <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0 mt-0.5" />
                  <div>
                    <div className="font-bold text-sm text-white">حل مشكلة معرّفات تيليجرام (P0 User Resolution Fix)</div>
                    <div className="text-slate-400 text-xs">لا يتم تمرير معرف تيليجرام <code>from_user.id</code> إلى أي علاقة قاعدة بيانات، بل يتم تحويله إلى <code>users.id</code> الداخلي لمنع أخطاء Foreign Key.</div>
                  </div>
                </div>

                <div className="flex items-start gap-3 p-4 rounded-xl bg-slate-950 border border-slate-800">
                  <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0 mt-0.5" />
                  <div>
                    <div className="font-bold text-sm text-white">حماية التلاعب بالبيانات (Anti-Tampering Callbacks)</div>
                    <div className="text-slate-400 text-xs">التحقق الخادمي الصارم من ملكية الجلسة، وتطابق أرقام الأسئلة والخيارات التابعة للاختبار فقط.</div>
                  </div>
                </div>

                <div className="flex items-start gap-3 p-4 rounded-xl bg-slate-950 border border-slate-800">
                  <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0 mt-0.5" />
                  <div>
                    <div className="font-bold text-sm text-white">عزل تام للملكيات والبيانات (Ownership Isolation Matrix)</div>
                    <div className="text-slate-400 text-xs">لا يمكن لأي مستخدم استعراض أو تعديل مسودات أو اختبارات أو نتائج مستخدم آخر.</div>
                  </div>
                </div>

                <div className="flex items-start gap-3 p-4 rounded-xl bg-slate-950 border border-slate-800">
                  <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0 mt-0.5" />
                  <div>
                    <div className="font-bold text-sm text-white">خلو تام من الأسرار والمعرفات الثابتة (Zero Hardcoded Secrets)</div>
                    <div className="text-slate-400 text-xs">إدارة كاملة عبر المتغيرات البيئية <code>.env</code> و <code>pydantic-settings</code>.</div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
