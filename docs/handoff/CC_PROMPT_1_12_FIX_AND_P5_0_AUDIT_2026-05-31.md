# פרומפט CC — שני צעדים בטוחים: תיקון 1.12 + P5-0 audit

> להדבקה ב‑Claude Code עם גישה ל‑repo `mems26_web_git`. **קרא קודם `CLAUDE.md`
> ו‑`.cursor/rules/mems26-pre-live-protocol.mdc`.**
>
> ⚠️ שני הצעדים האלה הם **לפני** כל נגיעה בנתיב ההזמנה. צעד 1 = קוד טסטים בלבד.
> צעד 2 = read‑only. **אסור** לגעת ב‑order routing / gateway logic / risk / sizing /
> sc_study / polling. כתוב דוח אוטומטי לכל צעד (פורמט קבוע, פלט גולמי).

---

## צעד 1 · תיקון 1.12 — pytest נקי (קוד טסטים בלבד)

**מצב:** ב‑E2E 1/2 דווחו **4 כשלים קיימים מלפני** השינויים: `tests/v9/api/test_trades_exit.py`
נכשל בגלל fixture `setup_db` חסר ב‑scope של `tests/v9/api/` (אומת עם `git stash`).

**משימה:**
1. אבחן: רוץ `python3 -m pytest tests/v9/api/test_trades_exit.py -v` והדבק את ה‑traceback
   הגולמי שמראה את ה‑fixture החסר.
2. תקן: הוסף/חבר את fixture `setup_db` ל‑`tests/v9/api/conftest.py` (או scope מתאים),
   באותו דפוס כמו ה‑conftest הקיים ב‑gateway/. **קוד טסטים בלבד** — אסור לגעת בקוד
   פרודקשן.
3. אמת: רוץ את הסוויטה המלאה והדבק את השורה הסופית (`X passed, Y failed`). היעד:
   **0 failed**. אם נשארו כשלים אחרים — תעד אותם בנפרד, אל תסתיר.

**Forbidden:** שינוי קוד פרודקשן · שינוי לוגיקת טסט שמסווה כשל אמיתי.

**דוח:** `docs/reports/PYTEST_GREEN_1_12_2026-05-31.md` — traceback לפני, תיקון, פלט נקי אחרי.

---

## צעד 2 · P5-0 — Gateway audit (READ‑ONLY · אפס שינוי קוד)

**מטרה:** דוח המלצה ל‑D‑093.Q1 (gateway קנוני) — לא נעילה, רק המלצה מבוססת.

**קרא במלואם:**
- `backend/v9/gateway/trading_gateway.py` (Legacy · מחובר ב‑`main.py`)
- `backend/v9/services/trading_gateway/gateway.py` + `executors/{shadow,demo,live}.py` (New · לא מחובר)
- `backend/v9/services/sierra_command.py` (shared)
- `bridge/trade_commands.py` (handler · לא מחובר)
- `backend/main.py` סביב `:344` (gateway init)
- `docs/research/SIERRA_ORDER_ROUTING_RESEARCH_2026-05-24.md` §3.3
- `docs/decisions/D-093_SIERRA_ORDER_ROUTING.md`

**ממצאי Cowork מקדימים (לאמת/להפריך ב‑audit, לא לקבל כמובן מאליו):**
- Legacy מחבר cooldown / SSV (D‑049) / cluster_guard (D‑037) / chop gate /
  strict_checks — **כולם בפעולה**. כותב פקודת DEMO אבל מקודד חשבון **Apex מת**
  (`PA-APEX-125218-01`). LIVE = stub (`_execute_live` לא שולח).
- New: מבנה נקי (executors + thread‑safe) + RiskValidator (W14), אבל **חסרים** בו
  cooldown/SSV/cluster/chop. לא כותב פקודה לסיירה. docstring מפנה ל‑Apex מת.
- מסקנה מקדימה: cutover ישיר ל‑New = **רגרסיה במסנני סיכון** → נוטה ל‑**Merge**.

**בצע:**
1. סיווג **KEEP/ADAPT/REPLACE/DEFER** לכל קובץ, עם ציטוט קוד verbatim ונימוק.
2. המלצה ל‑D‑093.Q1: `RECOMMENDATION: [Legacy/New/Merge]` · `RATIONALE` (3 נק') ·
   `RISK IF WRONG` · `MIGRATION PATH`. התייחס מפורשות ל‑gap מסנני הסיכון.
3. **Dead‑code map:** אשר ש‑3 ה‑executor stubs (`gateway/{live,demo,shadow}_executor.py`)
   ללא imports בפרודקשן (`rg`).
4. **Apex map:** כל מופעי `PA-APEX-125218-01` בקוד → רשימה למחיקה/החלפה ל‑IronBeam
   `37138283` (ב‑P5 בלבד, לא עכשיו).
5. נגיעה ב‑3 ההחלטות הנוספות אם רלוונטי מהקוד: Re‑lock 1 (BuyEntry+Attached),
   Re‑lock 2 (ModifyOrder), heartbeat ladder.

**Output:** `docs/reports/P5_0_GATEWAY_AUDIT.md` (≥300 שורות · 5 צעדים · excerpts verbatim).

**Forbidden (P5-0):** אין מחיקת קוד · אין שינוי wiring · audit בלבד.

---

## סדר + שער
צעד 1 → צעד 2. אחרי שניהם: עצור ודווח. **אל תתחיל שום מימוש של Pipeline 5** (P5-0c
ומעלה) — זה ממתין לנעילת ההחלטות של Michael על בסיס דוח ה‑audit.
