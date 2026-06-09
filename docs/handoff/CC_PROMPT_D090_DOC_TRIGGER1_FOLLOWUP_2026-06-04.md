# CC PROMPT — תיעוד D-090 + פריט-המשך trigger#1 (קטן, לסגירה) · 2026-06-04

**פעל לפי `CC_HANDOFF_CONTRACT.md`.** סגירת חוב-תיעוד מ-`5343755`/`d785b2c`. **לא משנה לוגיקה** (פרט לפריט 2 שהוא מתועד-בלבד עכשיו).

## פריט 1 — מסמך החלטה D-090 (תיעוד בלבד)
צור `docs/decisions/D-090_S1_OBSERVER_ENFORCED.md` שמתעד את ההחלטה שכבר מומשה ב-`d785b2c`:
- **ההחלטה (Michael 2026-06-04):** S1 (Day-Type) = **OBSERVER** — אוכף ע"י `return None` ב-`backend/v9/systems/wrappers.py:88` אחרי `process_bar()`.
- **למה:** הרישום (`MEMS26_..._REGISTRY`) מסווג S1=OBSERVER/output=NEVER, אבל הקוד הדליף `Signal(system_id=1)` ב-LOCKED_LOW_CONF (22 signals ב-PG). אומת ע"י Cowork.
- **מה נשמר:** הסיווג (day_type/confidence/lock_state) ממשיך לרוץ ולהיכתב — רק יצירת ה-Signal נחסמה.
- **איך להפוך (אם תוחלט firing בעתיד):** הסר את ה-`return None` — דורש D-decision חדש.
- קשר: `state_machine.py` (classification), `wrappers.py:88` (guard).

## פריט 2 — פריט-המשך trigger#1 (extreme move) — OPEN, לא לתקן עכשיו
תעד ב-STATUS_BOARD (ובמסמך קצר אם נדרש) שב-`state_machine.py:_check_reeval` re-eval **trigger#1 (extreme move >3 ATR) עדיין חלקי**:
`move_30 = None` קשיח (`:783`) כי דורש חלון bar-history. ה-fallback של `_last_atr_daily` (`9cac12f`) החייה את **trigger#3 (range_exceeded)** וסיווגי-ה-ATR — אבל ה-move-component של trigger#1 לא מחושב.
- **אל תתקן עכשיו** — זה דורש העברת bar-history window ל-state-machine (scope נפרד). רשום כ-OPEN עם הפתרון המוצע (להזין חלון 30-דק' של ברים ל-`_check_reeval`).

## Acceptance
- [ ] `docs/decisions/D-090_S1_OBSERVER_ENFORCED.md` קיים ומדויק (מצביע ל-`wrappers.py:88`).
- [ ] STATUS_BOARD: שורת-OPEN ל-trigger#1 move-window עם הפתרון המוצע.
- [ ] 0 שינויי-לוגיקה (תיעוד בלבד) · commit · `git log`.

## Invariants
תיעוד-בלבד · אל תיגע בקוד-לוגיקה · localhost-PG · Cowork מאמת. (זה משלים את חבילת ה-firing-fixes; אחריו P1 = bring-up + אימות S2 ב-RTH.)
