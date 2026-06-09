# CC PROMPT — Verify Extreme-CCI Trend Relabel · REAL test + shadow proof (V2) · 2026-06-02

**פעל לפי `docs/handoff/CC_HANDOFF_CONTRACT.md`.**
**תווית:** `D-WDIAG` · **מאת:** Michael → **אל:** Claude Code
**מחליף:** `CC_PROMPT_VERIFY_TREND_RELABEL_2026-06-02.md` — הטסט הקודם (`c9f3883`) **נפסל**: הוא העתיק את לוגיקת ה-relabel לתוך הטסט ובדק את ההעתק, **לא קרא ל-`process_bar`/`decision_tree`** (טאוטולוגי, חוזה §B1). **אל תשנה לוגיקה — רק אימות אמיתי.**

**רקע:** `b2be53c` מימם relabel ב-`studies["trend_state"]` (woodies_system.py ~278, לפני detect_all_patterns ו-WoodiesDecisionContext), מאחורי `S4_EXTREME_TREND_RELABEL` (default OFF).

---

## Phase 1 · טסט אינטגרציה דרך הקוד האמיתי (חוזה §B1)
מחק/החלף את `tests/v9/regression/test_d_wdiag_extreme_trend.py` הטאוטולוגי. כתוב טסט ש**קורא לקוד הייצור**:
- בנה `WoodiesSystem`, הזרם בר עם `trend_state="GRAY"` + `cci_14=331` דרך **`process_bar`** (לא להעתיק את ה-if).
- **דגל OFF:** ה-bar שנשמר/`decision_tree` רואה `trend_state="GRAY"`.
- **דגל ON:** אותו בר → ה-`WoodiesDecisionContext.studies["trend_state"]` שמגיע ל-`decision_tree._a1_trend_gate` = **BLUE**, וה-HFE מגיע ל-`ready_to_route=True`.
- **בר רגיל** (CCI=80, GRAY, דגל ON) → נשאר GRAY, אין שינוי routing.

**Acceptance (חוזה §B1 ליטמוס):** בכל טסט כתוב את השורה *"if reverted → RED because ___"*, והוכח אותה: הרץ את הטסט, ואז **הפוך זמנית את התיקון** (`git stash`/הערה) והראה שהטסט הופך **אדום**. הדבק את שני הריצות (Rule 5).

## Phase 2 · הוכחת shadow חיה (חוזה §B2)
הדלק `S4_EXTREME_TREND_RELABEL=1` ב-SHADOW. הדבק פלט גולמי:
- בר ±200 שנחסם בעבר → עכשיו `ready_to_route=True` וה-HFE נותב (לוג/DB).
- ברים רגילים (לא ±200) → **אפס** fires חדשים/שגויים.
אם רעש → דווח, אל תשאיר דלוק.

## Phase 3 · עצור לאישור (חוזה §B5)
לפני השארת הדגל ON קבוע ב-live — עצור ושאל את Michael.

## דוח (חוזה §C)
טבלת phases (DONE/PARTIAL/NOT-DONE + evidence) · שורת "if reverted → RED" לכל טסט · סעיף **NOT DONE / DEVIATIONS** (גם אם "none") · open. עדכן `STATUS_BOARD.md` + `DECISION_LEDGER.md` עם הפלט.

---
### עיגון קוד
`woodies_system.py`: relabel ~278, `process_bar`, `WoodiesDecisionContext(studies=studies)` ~413 · `decision_tree.py:176` `_a1_trend_gate` (קורא `ctx.studies`) · `atr.py:89` הדגל · `tests/v9/regression/test_d_wdiag_extreme_trend.py`.
