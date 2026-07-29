# CC — מערכת 0 "מנצח-ההקשר" + סגירת פערי-דלתון בסוג-הפתיחה (פסיקת-מייקל 07-24)

**פעל לפי `docs/handoff/CC_HANDOFF_CONTRACT.md`** (anti-tautological · Rule-5 · NOT-DONE חובה).
**תזמון:** אחרי סגירת CC_OVERNIGHT_3FIXES (Phases 0-7). לא מתחרה בדדליין-היום. הכל flag-gated OFF; cowork מאמת ומדליק לפי פסיקה.
**מקורות-חובה לקריאה לפני:** `docs/plans/OPENING_FIRE_SYSTEM_PLAN_2026-07-23.md` · `docs/reports/OPENING_TYPE_PRECISION_STUDY_2026-07-23.md` (35 סשנים: drive-chase 4/10, AUCTION_OUT מדורג-שגוי) · פרק-הפתיחות של דלתון (עמ' 63-77, הציטוטים במחקר).

## הרציונל (מייקל)
הבעיה אינה חוסר-אותות אלא **הקשר מפוצל**: ‏day_type, ‏opening_type, ‏dir_bias, ‏expansion חיים בנפרד, כל זרוע שואלת חתיכה אחרת ומקבלת תשובות סותרות (07-23: יום=UNKNOWN, פתיחה=NEUTRAL, ‏LSMA=RED באותו רגע). מערכת 0 = **שירות-איחוד אחד** שמפרסם חוזה-הקשר יחיד לכל המערכות. היא **מחליפה** את הגטרים המפוזרים — לא מוח חמישי נוסף.

## Phase A — `backend/v9/services/market_context.py` (המנצח)
דגל `MARKET_CONTEXT_V1` (default OFF). ‏dataclass ‏`MarketContext` + פונקציה `get_market_context()` יחידה:
```python
@dataclass
class MarketContext:
    balance_state: str      # in_value_accepted | out_value_in_range | out_of_range | UNKNOWN  (דלתון: פתיחה מול ערך/טווח-אתמול)
    balance_conviction: str # low | medium | high  (out_of_range=high risk/opportunity)
    opening_type: str       # OPEN_DRIVE / TEST_DRIVE / ORR / AUCTION_IN / AUCTION_OUT / UNKNOWN
    opening_dir: str        # UP / DOWN / NEUTRAL
    opening_conf: float     # מדורג-דלתון: Drive .85 > Test .75 > ORR .65 > Auction ≤.5
    acceptance: str         # pending | accepted | rejected  (קבלה-דרך-זמן, ר' Phase C)
    day_bias: str           # UP / DOWN / NONE  (זריעת-פתיחה → dir_bias-LSMA → expansion, בסדר-קדימות זה)
    day_type: str           # הקנוני מ-get_live_day_type (ללא שינוי)
    updated_ts: float
```
מקורות: קומפוזיציה של הקיים בלבד — `opening_detector_v2`, ‏`get_live_day_type`, ‏`get_live_dir_bias`, ‏`get_live_expansion`, זריעת-Phase-3, ולוגיקת-האיזון מ-Phase B. ‏**escalation-only**: שדה שנקבע לא מתדרדר (רק מתחזק/ננעל) עד סוף-סשן; חצייה-חדה (מחיר חוצה את כל ערך-אתמול) = האירוע היחיד שמתיר reclass, עם לוג.
**חיבור-צרכנים (Phase A2, זהיר):** הגייטוויי (playbook-kwargs) והפאנלים עוברים לקרוא מ-`get_market_context()`; הגטרים הישנים נשארים כ-fallback כשהדגל OFF. **אסור** לשנות התנהגות כשהדגל OFF (byte-identical).

## Phase B — פערי-דלתון בגלאי (opening_detector_v2)
דגל `OPENING_DALTON_GAPS_V1` (default OFF), ארבעה תיקונים:
1. **איזון = ציר-ראשי:** ‏`_loc()` מקודם מפלט-הערה ל-`balance_state` שנפלט מהבר-הראשון + טבלת-conviction (out_of_range→high).
2. **עיגון-Drive:** ‏OPEN_DRIVE רק כשהפתיחה בקצה-הסשן (הקיים) **וגם** אין-חזרה-דרך-טווח-הפתיחה; **חזרה דרך טווח-הפתיחה = ביטול-הייחוס** — הגלאי מוריד את ה-drive ופולט `invalidated=true` (וזה גם כלל-יציאה לעסקות-פתיחה ב-opening_entry: סטופ-ביטול).
3. **‏AUCTION_OUT = דריכות, לא ניטרלי:** כשנפתח מחוץ-לטווח והסיווג auction — ‏opening_conf=0.55, ‏reasons+="out-of-balance: double-distribution potential", ‏balance_conviction=high. הזרועות מקבלות "צפה הרחבת-טווח; ירי על range-extension עם קבלה" במקום כלום (הכשל של 07-23).
4. **טיימר-קבלה:** מדידת acceptance — המחיר בונה ≥‏60 דק' (12 ברי-5-דק', ‏≥70% מהזמן) בתוך/מחוץ לאזור-הייחוס → ‏accepted/rejected; לפני-כן pending. נכנס ל-MarketContext.acceptance.

## Phase C — טסטים + replay (חובה, Rule-5)
1. יחידה לכל תיקון + revert→RED לכל אחד.
2. **replay 07-23:** עם שני הדגלים ON — ‏ב-16:35: ‏balance_state=out_of_range (נפתח אחרי ‑74 לילי), ‏conviction=high, לא-NEUTRAL-שקט; ‏acceptance מתעדכן; ‏day_bias=DOWN עד 16:45. ‏MarketContext יציב (אפס-קרטוע) לאורך הסשן.
3. **replay 35 הסשנים** (השתמש בסקריפט-המחקר כבסיס): שיעור-ההיפוך של OPEN_DRIVE אחרי עיגון-מיקום חייב להשתפר מ-6/10 (דווח את המספר; אם לא משתפר — NOT-DONE כן עם הנתון).
4. רגרסיה מלאה ירוקה + flag_guard + FLAG_REGISTRY + gen_flag_index + דוח חלק-C → `docs/reports/CC_SYSTEM0_REPORT.md`.

## אסור לגעת
דגלי-הכיול (16T/1.5R/probe) · דגלים-פסוקים (RULED_FLAGS) · נתיב-הפקודות/DLL · ‏reconciler (Phase-7 נפרד) · אין הדלקה עצמית.

**סדר: A → B → C. אם היקף-A2 (חיבור-צרכנים) גדול — בנה A1+B+C ותשאיר A2 כ-NOT-DONE מפורט עם מפת-הצרכנים.**
