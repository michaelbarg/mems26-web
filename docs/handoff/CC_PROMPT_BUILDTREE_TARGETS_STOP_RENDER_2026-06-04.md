# CC PROMPT — BuildTreeView: רינדור שלב TARGETS/STOP + הסרת de-trust מיושן (P0-2 כבר נחת) · 2026-06-04

**פעל לפי `docs/handoff/CC_HANDOFF_CONTRACT.md`.** אישור Michael 2026-06-04. **Frontend-only, read-only מול ה-backend** — אפס שינוי endpoint/inspector/risk.
מבוסס על הצלבת-Cowork (`STATUS_BOARD.md` 2026-06-04 eve): P0-2 (`8eb5747`) **כבר פולט** את שלב `targets_stop`, אך ה-UI לא מציג אותו כראוי וה-de-trust הישן התיישן.

## רקע — שני ממצאים שאומתו ע"י Cowork (נקודת-פתיחה לאודיט, לא להניח — לאמת מחדש)
1. **הדאטה כבר זורמת אך "קבורה":** `s2_inspector.py:382-432` + `woodies_inspector.py:374-430` כבר מוסיפים ל-`components[]` רכיבים עם `stage="targets_stop"`:
   - S2: `r_t1_gate` · `stop_price` · `targets` · `sizing_time_stop`.
   - S4: `r_t1_gate` · `stop_price` · `targets` · `day_type_matrix`.
   `BuildTreeView.ComponentTable` (`:359`) מרנדר את כל ה-`components[]` גנרית → השורות **כבר מופיעות** בתוך ה-drill-down, מעורבבות עם שאר השלבים. **חסר:** תצוגה **ייעודית ובולטת** של TARGETS/STOP (entry/stop/T1-T3/r_t1/sizing/time_stop ב-$ וב-R) כשלב-6 בעץ, לא שורות-טבלה אנונימיות.
2. **`isProxyGate` התיישן והפך למטעה:** `BuildTreeView.tsx:160` → `includes('confidence')`. ה-backend ב-P0-2 **החליף** את פרוקסי ה-`confidence>=0.5` בשער `r_t1` אמיתי (`woodies_inspector.py:344` → r_t1). לכן: (א) כנראה **שום** רכיב כבר לא נושא "confidence" → ה-branch ⧗ ב-`:385` ו-`:727` הוא **dead/מטעה**; (ב) ה-title "⧗ ממתין ל-backend (P0-2)" **שקרי** — P0-2 נחת.

## Phase 1 — אודיט (diagnose-first, הדבק ראיה)
1. הדבק `curl -s localhost:8000/api/v9/build/pattern-status | jq '.systems[] | {id, patterns:[.patterns[]?|{id, components:[.components[]?|select(.stage=="targets_stop")|{key,live,present,value}]}]}'` (או שווה-ערך) — **הראה את רכיבי targets_stop בפועל ל-S2 ו-S4**. אם השרת כבוי — הרץ unit/fixture שמדגים את ה-payload.
2. **grep:** האם נשאר רכיב כלשהו עם "confidence" ב-`key`/`spec` בכל ה-inspectors? (`grep -rn confidence backend/v9/systems/build_status`). הדבק → הכרע אם `isProxyGate` מת לחלוטין.
3. אתר את אתרי-הצריכה ב-`BuildTreeView.tsx`: `:385` (ComponentTable ⧗), `:727` (global_gates proxy), `:578` (schema סטטי "synced VERBATIM P0-2"), והיכן מצויר שלב-6/"projection".

## Phase 2 — רינדור שלב TARGETS/STOP (מהדאטה הקיימת, Rule 1)
- הוסף תצוגה ייעודית per-firing-pattern (S2/S4) ששואבת מ-`components[stage=="targets_stop"]` בתגובה: `stop_price`, `r_t1` (מול `>= min`), `targets` (t1/t2/t3), `sizing`, `time_stop`, ו-S4 `day_type_matrix verdict`.
- **הקרנת $/R (spec §6):** עכשיו ש-1R נחשף — הצג entry→stop→T1-T3 ב-$ ו-R. **Rule 1:** ערך `null`/חסר → "⧗ ממתין" (detection pending), **לא לסנתז**. אל תמיר את ה-schema הסטטי (`:578`) לערכים — קרא מהתגובה החיה.
- אל תיגע ב-`ComponentTable` הגנרי (יכול להישאר ל-drill-down מלא); זו הוספת view בולט מעל/לצד.

## Phase 3 — הסרת de-trust מיושן
- אם Phase-1.2 מאשר ש-0 רכיבים נושאים "confidence": **הסר** את `isProxyGate` ואת שני אתרי-הצריכה (⧗ ב-`:385`, proxy ב-`:727`), והצג את שער ה-`r_t1_gate` האמיתי כ-✓/✕ לפי `present` (כמו כל שער). הסר את ה-title "⧗ ממתין ל-backend (P0-2)".
- אם בכל-זאת נשאר רכיב confidence כלשהו → **לעצור ולדווח** (B6), לא להרחיב.

## Acceptance (✓/✗ + raw)
- [ ] Phase-1 payload של targets_stop ל-S2+S4 מודבק (raw jq/fixture) + תוצאת grep confidence.
- [ ] שלב TARGETS/STOP מוצג ייעודית עם entry/stop/T1-T3/r_t1/sizing/time_stop; חסר→"⧗ ממתין" (0 סינתזה). הדבק diff + screenshot/`/build`.
- [ ] **טסט/בדיקה אנטי-טאוטולוגי (B1):** רכיב-render שמוזן ב-payload מוקאפ עם `r_t1=null` → מציג "ממתין"; payload עם `stop_price=X, r_t1=1.4` → מציג את הערכים. *"if reverted (render מוסר) → RED because הערך לא יופיע / 'ממתין' לא יוצג."* assert על ה-DOM/הפלט, לא על משתנה-ביניים.
- [ ] de-trust הישן הוסר/עודכן: 0 ⧗-פרוקסי על r_t1; ה-title המטעה ירד. (raw: grep `isProxyGate`/"ממתין ל-backend (P0-2)" → 0 או מנומק.)
- [ ] `tsc --noEmit` נקי (raw) · `git log -1` · סעיף **NOT-DONE/DEVIATIONS** (גם "none").

## Invariants
Frontend-only · read-only מול backend (אפס שינוי inspector/endpoint/risk) · Rule 1 (חסר→"ממתין", לא סינתזה) ·
אל תיגע polling-floors/V9Dashboard/sc_study · single-source (קרא מהתגובה, לא מ-schema סטטי) · Cowork מאמת בלתי-תלוי (litmus render + grep confidence=0).
