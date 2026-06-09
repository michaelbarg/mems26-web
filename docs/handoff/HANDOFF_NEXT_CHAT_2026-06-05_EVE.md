# Cowork Handoff — Next Chat (2026-06-05 eve) — SHADOW רץ מ-0, day_type עובד, 2 CC בעבודה

**אתה (Cowork הבא):** orchestrator + verifier בלתי-תלוי של MEMS26. CC מבצע על ה-Mac;
אתה כותב פרומפטים, מצליב (**Rule 5: פקודה+פלט גולמי**), מעדכן בורדים. **לא** שולט
ב-backend/launchctl/Sierra מה-sandbox — אבל **כן** קורא קוד/git, שולף דאטה-חיה דרך
**Chrome→`http://localhost:8000`**, ומריץ scheduled-agents.

## 0 · מקור-אמת + פרוטוקולים (קרא קודם)
`CLAUDE.md` — כולל **§Codebase Index Protocol חדש** (קרא SYSTEM_INDEX קודם, לא grep עיוור) ·
§DB=Postgres · §Bridge Local-Only · §Pre-LIVE · §Source-of-Truth · §Sierra.
`CC_HANDOFF_CONTRACT.md` · `CC_VERIFICATION_PROTOCOL.md` (CC כותב `VERIFY_*` file, אתה מצליב).
**בורדים:** `STATUS_BOARD.md` (source-of-record) · `ROADMAP_TO_LIVE.html` (צ'קליסט נקי today→LIVE,
המערכת מסמנת) · **`docs/reports/MEMS26_ISSUES_REGISTER.md` (I-1…I-16 — רשימת-חשודים חיה, העיקרית).**

## 1 · מצב חי (2026-06-05 eve)
- **SHADOW רץ מ-0** אחרי חיתוך B-13: staleness-guard (`bars.py`) + session 08:30–15:00 שיקגו +
  G1 columns + S3 mute — **אומתו ע"י Cowork** (`VERIFY_CUTOVER_2026-06-05.md`). uncommitted.
- **day_type עובד** (Normal, IB 7552.75/7505.75 מ-Sierra TPO, `backend/main.py:405`). CC הוסיף
  re-eval רציף (C3→B2, בלי lock) לפי אפיון Michael. **לקח:** האבחון הקודם של Cowork "S1 dark"
  היה **שגוי** — נקרא מ-endpoint מת (`/day_type/state`→wrapper) + greptי `v9/main.py` הלא-נכון.
- **2 CC בעבודה:** (א) עיצוב Trades/Build-Status + **B-11** (`bridge_inspector.py` משתנה); (ב)
  פרומפט day_type-endpoint+choppiness.

## 2 · חוסמים פתוחים (פירוט מלא ברשימה — I-#)
- **I-5 · B-11** 🔴 — `bridge_inspector` rowid→ts_col; מקריס את כל ה-Build Status (BLOCKED/dead
  שקרי, הגשר משדר). **בתהליך** (CC עיצוב).
- **I-16 · choppiness_ok** 🔴 — `choppiness_score` מחושב רק ב-FIRST_HOUR_TACTICAL → תקוע →
  חוסם **8/10 תבניות-S2**. פרומפט מוכן: `CC_PROMPT_DAYTYPE_ENDPOINT_CHOPPINESS`.
- **day_type endpoint/wrapper/Woodies-A4** — `/state` קורא instance מת; להסיר dead-wrapper;
  propagation ל-Woodies A4. (אותו פרומפט.)
- **I-11 · S3 footprint 0-ברים** — **parked** (S3 muted פר-Michael; לבדוק כשמבטלים-השתקה).
- **I-13/I-14** — sizing=reject (aux<2) מפספס תבניות · opening→entry chain.
- **I-2/I-3/I-15** — A5 display (תוקן) · ZLR conservative · trend_state engine↔board.

## 3 · פרומפטים מוכנים (ב-`docs/handoff/`)
`CC_PROMPT_DAYTYPE_ENDPOINT_CHOPPINESS_2026-06-05` · `CC_PROMPT_BUILD_STATUS_DESIGN_P0_2026-06-05`
(כולל B-11+P0+stale) · `CC_PROMPT_FRONTEND_PHASE1_TRADES_REDESIGN_2026-06-04` ·
`CC_PROMPT_B14_CHART_5MIN_DUP` · `CC_PROMPT_REGEN_INDEX_2026-06-05`.
**OBSOLETE — אל תשלח:** `CC_PROMPT_DAYTYPE_FIX_2026-06-05` (שורש שגוי).

## 4 · סוכנים מתוזמנים (Cowork)
`pattern-diag-30min` (בדיקה עמוקה כל 30 דק' ב-RTH, 5-שאלות פר-תבנית + צילום-טבלה, מעדכן את
הרשימה) · `mems26-eod-issues-designs` (EOD: דוח מאוחד + counterfactual + עיצובים). **I-9:** ה-EOD
רץ בבוקר ולא אחרי-סגירה — לתקן trigger/guard.

## 5 · לקחים מחייבים (שלא יחזרו)
1. **אינדקס קודם** (CLAUDE.md §Index Protocol). `backend/main.py` ≠ `backend/v9/main.py`.
2. **אל תאבחן מ-endpoint יחיד** — הצלב מול הנתיב-האמיתי + DB.
3. **הצלב כל טענת-CC** (Rule 5, raw output). CC השחית `state_machine.py` עם תו "לך" → Cowork תיקן.
4. כשטועה — **הוֹדֵה ותקן** (קרה היום ב-day_type ובסעיף-4 של פרומפט).

## 6 · הצעד הראשון בצ'אט הבא
1. כש-CC מחזיר `VERIFY_*` — **הצלב** (Chrome→API + קוד/git): `/state`=Normal · 8 תבניות-S2 נפתחו ·
   B-11 הלוח חי · day_type ל-Woodies A4.
2. סנכרן register↔STATUS_BOARD; עדכן ROADMAP פר-שלב.
3. שלח `CC_PROMPT_REGEN_INDEX` אם האינדקס עדיין stale.
