# צ'קליסט-ביצוע ערב 2026-07-02 — המסמך המחייב (מחליף את CC_WORK_QUEUE_2026-07-01)

_כלל: שום פריט לא "בוצע" בלי ראיה גולמית (Rule 5). כל סטייה נרשמת כ-NOT-DONE עם סיבה._
_בקרה אוטומטית: משימה מתוזמנת 23:20 IL תסרוק ותתריע על מה שחסר._

## שלב 0 · לפני-הכל (Michael)
- [ ] הצ'אט-המקביל מסיים את הליכת-התבניות (נותרו: HTLB עוגן+סולם · TLB Stage-2+חלון · DBDT/HNS אשרור-סולם · ZLR/GB100 אשרור-מדרגה-יחידה) → הפסיקות נרשמות ב-PATTERN_RECONCILIATION + טבלת-פריט-4.
- [ ] Michael מדביק ל-CC את: `CC_PATTERN_ECONOMICS_PACKAGE_2026-07-02.md` (**16 פריטים** — נוספו במהלך היום: 14=A7/Mechanism-C · 15=בתוך-11 · 16=VOL_REGIME+מדיניות-יום-אלים; ופריטי-הרזולבר קיבלו ראיות-חיות 277/278: רצפת-C1, t1≠t2, עיגול-גריד).

## שלב 1 · בניית-CC (אחרי סגירה 23:00 IL; סדר מחייב)
- [ ] פריט-2 רזולבר (מונוטוניות+קאפים+ATR-חי+swing-לכל-הימים) — טסט-HTLB-הפוך עובר
- [ ] פריט-1 תאי-playbook (8 פסקים + באג-aliases-דאבלים #9) — טסט decide() נכשל-על-הישן
- [ ] פריט-3 `RR_ENTRY_GATE_V1` · פריט-4 `STOP_RESOLVER_V1` (+חישוב-אחורה גולמי מ-06-20) · פריט-5 `S2_B4_VOL_V1`
- [ ] פריט-6 `S4_ENTRY_CONFIRM_V1` · פריט-12 `TT_SPEC_V2` (ספק-המקור המלא) · פריט-13 `PB_SHAPE_FILTER_V1`
- [ ] פריט-11 השלמה: ריכוז-notify ב-TradeManager (ה-hotfix כבר חי מהיום) + תיקון fallback-FillPoller המסוכן
- [ ] פריט-10 `OPENING_WINDOW_FIRE_V1` + תיקון-I-53 (ts::timestamptz) באותו קומיט — **מטרה: מוכן להפתחה של מחר**
- [ ] פריטים 7-8 (מחקר בלבד): פרוטוטייפ חלון-דינמי + ספק-פולבק — דוחות, לא קוד-חי
- [ ] כל דגל חדש → `docs/FLAG_REGISTRY.yaml` (+ השלמת FIXED_CONTRACTS_3/DAYTYPE_CONFIRM_BARS/OPPOSITE_EXIT_THRESHOLD החסרים) → `python3 scripts/gen_flag_index.py`

## שלב 2 · קומיטים ותיעוד (Cowork/CC)
- [ ] קומיט UI (סבבי 1+2 שכבר חיים: 15 קבצי-פרונט) + `python3 scripts/gen_index.py` + קומיט אינדקסים
- [ ] טסט-Mechanism-C **התנהגותי** מחליף את הטאוטולוגי (ממצא ביקורת-14:45)
- [ ] STATUS_BOARD + ROADMAP: רשומת-EOD מלאה (finding+fix+verified)

## שלב 3 · ריסטארט-ערב + אימות (אחרי שהכל קומט)
- [ ] `launchctl kickstart -k gui/$(id -u)/com.mems26.backend` (שוק סגור, 0 פתוחות)
- [ ] boot-line: כל הדגלים החדשים OFF כברירת-מחדל ✓ · hydration ✓ · אין tracebacks
- [ ] הפעלות לפי פסק-Michael בלבד (מועמדים למחר: `OPENING_WINDOW_FIRE_V1`)

## שלב 4 · מחר בבוקר (מתוזמן אוטומטית)
- [ ] 16:05 IL בדיקת-קדם-פתיחה (כבר מתוזמנת ל-03-07) — כולל ready_to_route + הדגלים החדשים
- [ ] פתיחה: אימות ירי-בחלון-הפתיחה אם הדגל הופעל · המשך-walkthrough על מה שנותר

## תלויים-ועומדים שאסור לאבד (מקור: סשן 07-02)
watch סיווג-Variation על שבירת-ה-IB (אם המחיר מחזיק מטה וה-S1 לא מתהפך → ראיה חיה לפריט-2 ב-workstream) · תחקור 2-3 הבוטים הלא-מיוזמים (~16:00-17:35, bind-collisions) · `S1_MOM_DETECTORS_WORKSTREAM` (double-print → VA-rule → NONCONVICTION) · דוח מיקומי-מימוש — רענון עם עסקאות-היום · פסיקות-D6..D-9 שטרם יושמו (docs: תיקון ACCESS_MAP/DEFINITIONS_INDEX/TableA-close/כרטיסי-VEGAS-GHOST-TT-INITIATIVE בפלייבוק).
