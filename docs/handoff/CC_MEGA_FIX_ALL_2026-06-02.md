# CC MEGA — תיקון כולל: יציבות DB + streams + S1/S2/S4 חי לפי האפיון · 2026-06-02

פעל לפי `docs/handoff/CC_HANDOFF_CONTRACT.md`.
**מחליף** את `CC_MEGA_FIX_DB_S1_S2_LIVE_2026-06-02.md` (מוסיף השבתת footprint + תיקון ה-streams).

## החלטות Michael (נעולות היום)
- **footprint מושבת זמנית** — `v9_footprint_journal` הוא מקור ה-corruption, ו-S1/S2/S4 לא תלויים בו.
  להשאיר מושבת עד שיהיו כמה ימים נקיים של 1/2/4. (footprint = thread נפרד אחר כך.)
- **S2 יורה חי** לפי האפיון (D-RVX).
- **S1 מסווג מחדש חי** לפי האפיון (Auth Table = strategic-stop, Michael מאשר בשער).

## אפיון — לעקוב, לא להמציא
- S2: `docs/reports/DECISION_BRIEF_REACTIVE_VOLUME_THRESHOLD_2026-06-01.md`
- S1: `docs/reports/DECISION_BRIEF_S1_DAYTYPE_RECLASSIFICATION_2026-06-01.md`
- חוקה/Auth Table: `docs/spec_authority/MEMS26_CONSTITUTION_V3_FINAL.txt` · `S2_AUTH_TABLE_V1*.md` · `MEMS26_Auth_Table_V2_*.csv`
- צינור as-built: `docs/reference/MEMS26_PIPELINE_DAYTYPE_TO_TRADE_MGMT_2026-05-31.md`

## 🚦 כלל שערים: כל phase עובר לפני הבא. Phase 1 (DB) חוסם הכל. כל דגל default-OFF · golden regression · טסט אנטי-טאוטולוגי (revert→RED) · אפס נגיעה ב-order/risk/sizing · דווח פר-phase.

---

## Phase 1 · יציבות DB (חוסם)
1. **השבת footprint לגמרי** מאחורי דגל `FOOTPRINT_DISABLED` (הפיך, אל תמחק קוד): לא subscribe, לא
   `_write_journal`/`_fire`/persist. (D-S3MUTE עצר רק ירי — כאן עוצרים גם כתיבה/עיבוד.)
2. ודא ש-S1/S2/S4 לא נשברים בלי footprint — S2 reactive: fallback ל-volume/מחיר אם נשען על footprint deltas.
3. שאר הכותבים דרך `safe_writer` בלבד — **אפס** `sqlite3.connect` שכותב (כולל `tpo_system.py:88` — אם כתיבה, העבר; אם קריאה, ציין).
4. שקם DB נקי פעם אחת → `integrity_check=ok` + `quick_check=ok` **עם backend כבוי** (זה האימות הקובע).
5. **SOAK ≥15 דק'** עם footprint כבוי, `integrity_check` כל 5 דק', **זמני wall-clock אמיתיים**.
   GATE: נשאר `ok` כל ה-15 דק' → ממשיכים. הדבק פלט גולמי מלא.

## Phase 2 · תיקון ה-streams התקועים (באגים אמיתיים — אומת ע"י Cowork ב-DB)
- `cumulative_delta` — max_ts ~04:30 (~8 שעות): אבחן למה ה-CVD לא נכתב → תקן נתיב הגשר/ingest.
- `imbalance` — ~04:40 (~8 שעות): אותו דבר.
- `tpo_bars` — **ריק (0 שורות)** בעוד `tpo_journal` טרי → **אי-התאמת wiring**: נתוני TPO נכתבים ל-journal ולא לטבלה שהמערכות/UI קוראים. תקן את היעד.
- `woodies_5min` "no_data" overnight = **תקין** (RTH-only) — רק ודא שנעשה fresh בפתיחה, אל תשנה.
- אימות: ב-Build Status ה-streams מראים fresh בפתיחה.

## Phase 3 · S2 Reactive — הפעלה חיה (לפי D-RVX)
- גייט VSA כבר קיים (`S2_VSA_VOLUME`, default OFF, `five_min_system.py:497`). יישם לפי ה-brief.
- 3 הווריאציות A=VSA / B=RVOL-TOD / C=Strict — **אחת חיה** (יורה), השתיים observers ב-Build Status.
- אמת: S2 **כן** מפיק setup (היה 0 all-time) + golden flag-OFF זהה.
- 🛑 **strategic-stop:** אילו וריאציה חיה — אישור Michael לפני הדלקה.

## Phase 4 · S1 Day-Type — סיווג-מחדש חי (לפי האפיון)
- כיום: reeval חי מת (`state_machine._check_reeval`: `move_30=None` + `atr=bar.atr=None`); `shadow_reclass.py`
  מחשב נכון Normal→Variation→Trend אך רק רושם.
- קדם את `shadow_reclass` לנהוג את ה-day_type **החי** (single-source), מאחורי דגל (`S1_DYNAMIC_RECLASS` חי),
  **או** תקן את קלט ה-reeval (ATR יומי אמיתי + bar-history ל-move_30) לפי ה-brief.
- ולידציה: live חייב להסכים עם ה-shadow-log לפני הדלקה.
- ⛔ **strategic-stop קשיח:** משנה Auth Table gating (SKIP→FULL). default-OFF; הדלקה רק באישור Michael מפורש
  אחרי הסכמת live-vs-shadow. (SHADOW mode כללי נשמר — אין הזמנות אמיתיות.)

## Phase 5 · S4 Woodies — אימות (כבר תוקן)
- ודא ש-S4 יורה נקי אחרי תיקון ה-DB; `trend_original` (A/B) נלכד על בר ±200 ב-RTH.

## Phase 6 · Backfill היסטוריה (task #17)
- אחרי DB יציב: backfill הברים שאבדו מ-Sierra exports (`~/SierraChart_Data/v9_export/`) — **לא** מהגיבוי הפגום.

## Phase 7 · אימות מוכנות
- באנר ה-readiness עובר ל-READY בפתיחה; צ'ק-ליסט Pre-Trade (PRE_TRADE_PROTOCOL) עובר.

---
## דוח חובה (חלק C) + NOT-DONE לכל phase + עדכון `STATUS_BOARD.md`+`ROADMAP_TO_LIVE.html`+`DECISION_LEDGER.md`.
טסט לכל תיקון עם שורת *"if reverted → RED because ___"*. strategic-stops: Phase 3 (וריאציה) + Phase 4 (S1 חי).
