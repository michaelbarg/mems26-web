# CC Prompt — D-WDIAG · `trend_original` ל-A/B של ה-relabel

פעל לפי `docs/handoff/CC_HANDOFF_CONTRACT.md`.

**תווית:** D-WDIAG (✅ APPROVED 2026-06-02, Michael) — `docs/plans/DECISION_LEDGER.md`.
כל קוד נושא `# D-WDIAG`.

## מטרה (אחת)
לשמר את ה-trend **המקורי** (לפני ה-extreme-CCI relabel) ולהזרים אותו ל-`cross_context`
של העסקה, כדי שנוכל A/B: אילו fires נבעו מ-relabel (trend מקורי GRAY/YELLOW שהפך BLUE/RED)
מול trend טבעי. **observability בלבד — לא משנה לוגיקת ירי/gating.**

## רקע מאומת (Cowork 2026-06-02 — מכריע סתירה בין שני דוחות)
דוח `docs/reports/D_WDIAG_RELABEL_FLAG_AUDIT_2026-06-02.md` (CC) טען ש**שורה אחת מספיקה**
כי `studies` זורם דרך `current_state.update(studies)`. **זה שגוי** — אומת מול הקוד:
- `woodies_system.py:425-432` הוא **`current_state.update({מילון מפורש})`** עם רשימת-מפתחות
  קשיחה (`cci_14,...,trend_state,predictor_next_cci,signal,...`). זה **לא** `update(studies)`,
  לכן מפתח חדש ב-`studies` **לא** מועתק ל-`current_state`.
- `get_current()` (`:733-734`) מחזיר `dict(self.current_state)`; ה-gateway בונה את ה-cross_context
  מ-`get_current()` (`trading_gateway.py:405` `ctx[name]=sys_ref.get_current()`, נלכד ב-`:89`).
  → ה-woodies blob ב-cross_context = `current_state`, **לא** ה-WoodiesBar.
- מסקנה: `WoodiesBar(**studies)` (`:299`) הוא נתיב מנוע-התבניות בלבד; Pydantic מתעלם ממפתח עודף
  (לא קורס) — **אין צורך בשינוי schema**. `trade_context.py:342` הוא reader לתצוגה, לא אחסון.

**→ המינימום הנכון = 2 נגיעות** (לא 1, לא 4).

## Phases (אטומיים)
**P1 · שמירת המקור** — `backend/v9/systems/woodies/trend_relabel.py`: לפני הדריסה
`studies["trend_state"]=...`, הוסף `studies["trend_original"] = trend`. כדי שהשדה **תמיד קיים**
(גם no-op / דגל OFF / CCI<200), הצב `trend_original` = הערך הנוכחי בתחילת הפונקציה. `# D-WDIAG`.
- **AC1:** קריאה ישירה לפונקציה עם YELLOW+CCI=250 → `studies["trend_original"]=="YELLOW"` ו-`studies["trend_state"]=="BLUE"`.

**P2 · current_state (הנגיעה הקריטית)** — `woodies_system.py:425-432`: הוסף למילון ה-update
המפורש שורה `"trend_original": studies.get("trend_original"),`. **זה השלב שמכניס את השדה
ל-`get_current()` → cross_context JSON.**
- **AC2:** ראה טסט הליבה.

**P3 (אופציונלי, nice-to-have) · תצוגת סיכום** — `backend/v9/services/trade_context.py:342`,
ענף `sid==4`: הוסף `"trend_original"` ל-tuple כדי שיופיע גם בסיכום-התצוגה. לא נדרש ל-A/B גולמי.

## טסט אנטי-טאוטולוגי (B1) — הליבה
טסט שמייבא וקורא לקוד הייצור end-to-end (לא העתק): מזין בר `trend_state=YELLOW`+`cci_14>=200`
+`S4_EXTREME_TREND_RELABEL=1` דרך `WoodiesSystem.process_bar`, ואז קורא ל-`woodies_system.get_current()`
(או בונה את ה-cross_context דרך ה-gateway) → **assert ש-`get_current()["trend_original"]=="YELLOW"`
בעוד `["trend_state"]=="BLUE"`**. ה-assert על הצרכן האמיתי (get_current/cross_context), לא על studies.
שורת ליטמוס: *"if reverted P2 → RED because השדה לא מגיע ל-current_state ולכן לא ל-cross_context"* —
ודא שהסרת **P2 לבדה** (משאירים P1) הופכת אדום. זה מוכיח שהנתיב מלא ואינו dead-wired.

## אסור לגעת (risk surface)
- **אסור** לשנות לוגיקת gating/relabel או את `trend_state`. רק שדה צללי נוסף.
- אין שינוי schema ל-`WoodiesBar` (מיותר — אומת). הדגל `S4_EXTREME_TREND_RELABEL` נשאר; אין הדלקה ל-live (B5).

## Verify (Rule 5) + דוח חובה (C) + NOT-DONE + עדכון `STATUS_BOARD.md`+`ROADMAP_TO_LIVE.html`
- `grep -rn "trend_original" backend/` + פלט הטסט (revert P2 → RED) — raw.
