# CC PROMPT — Verify Trend Relabel · REAL routing test (V3, final) · 2026-06-02

**פעל לפי `docs/handoff/CC_HANDOFF_CONTRACT.md`.**
**תווית:** `D-WDIAG` · **מאת:** Michael → **אל:** Claude Code
**מחליף:** V2. מבוסס על המלצתך בדוח (`_a1_trend_gate` ישיר) + שתי חידודים כדי שההוכחה תהיה חד-משמעית.

**רקע:** relabel ב-`woodies_system.py:278` (מקור יחיד, מאחורי `S4_EXTREME_TREND_RELABEL`, default OFF). הטסט הקיים (`c9f3883`) טאוטולוגי — נשאר ירוק גם אחרי revert. צריך טסט שקורא לקוד האמיתי.

---

## Phase 1 · טסט דרך החלטת הניתוב האמיתית (לא העתק)
החלף את `c9f3883`. כתוב טסט שקורא ל**קוד הייצור**:
- **חידוד 1 — בדוק את הניתוב הסופי, לא רק A1:** קרא ל-`decision_tree.evaluate_bar(ctx)` ובדוק **`ready_to_route`** (זה מה שקובע אם HFE יוצא). אם בודקים גם `_a1_trend_gate` ישירות — מצוין כשלב ביניים, אבל ה-assert המכריע הוא על `ready_to_route`. שתי הפונקציות סינכרוניות, בלי DB/async.
- **חידוד 2 — השתמש ב-YELLOW+קיצוני לניגוד נקי:** בר עם `cci_14=331` ו-trend גלמי **YELLOW** (YELLOW חוסם תמיד, אז הניגוד חד-משמעי; GRAY דו-משמעי כי עובר A1 ב-conf≥0.55).
  - דגל ON → studies עבר relabel ל-**BLUE** → `ready_to_route=True` (HFE עובר).
  - דגל OFF → studies נשאר **YELLOW** → `ready_to_route=False` (חסום).
  - בר רגיל (CCI=80, GRAY, דגל ON) → לא משתנה, לא מנותב.

**Acceptance (חוזה §B1):** הרץ את הטסט (ירוק). ואז **הפוך זמנית את ה-relabel** (revert/הערה) והראה שהטסט הופך **אדום**. הדבק את שתי הריצות (Rule 5). כתוב בטסט: *"if reverted → RED because evaluate_bar sees YELLOW → ready_to_route=False"*.

## Phase 2 · הוכחת shadow (deferred ל-RTH — מותר NOT-DONE עכשיו)
כשיגיע בר \|CCI\|≥200 ב-RTH עם הדגל ON: הדבק פלט שה-HFE נותב + אפס fires שגויים בברים רגילים. אם עוד לא קרה — רשום ב-NOT-DONE עם הסיבה ("אין בר ±200 ב-session").

## Phase 3 · עצור לאישור
לפני השארת הדגל ON קבוע ב-live — עצור ושאל את Michael.

## דוח (חוזה §C)
טבלת phases · שורת "if reverted → RED because ___" · סעיף NOT DONE / DEVIATIONS · open. עדכן `STATUS_BOARD.md` + `DECISION_LEDGER.md`. אל תכתוב "בוצע" בלי command+output.

---
### עיגון קוד
`backend/v9/systems/woodies/decision_tree.py` — `evaluate_bar(...)`, `_a1_trend_gate` (:176, קורא `ctx.studies["trend_state"]`), `WoodiesDecisionContext` · `woodies_system.py:278` relabel · `atr.py:89` דגל · `tests/v9/regression/test_d_wdiag_extreme_trend.py`.
