# T16 — S6 מודעת-היפוך: audit + הצעה

**תאריך:** 2026-07-19 · cursor-agent · **קריאה+הצעה בלבד** · מימוש = cc-macbook + סים + פסיקה

## דרישת-מייקל
בהיפוך-משמעותי נגד פוזיציה פתוחה — **לממש או לקרב יעדים** (לא להישאר עם יעד רחוק).

## מה S6 מזהה היום (`system6_supervisor.py`)

| קוד | שורות | פעולה | הערות |
|---|---|---|---|
| naked / wrong-side stop | 130-152 | ALERT (+ MODIFY_STOP הצעה ב-naked) | לא היפוך |
| stop_not_at_be (אחרי T1) | 156-161 | **AUTO** `MODIFY_STOP` → entry | עובד תחת protective |
| t1/t2/t3_wrong_side | 171-180 | **AUTO** `DROP_TARGET` | advisory/חלקי — ראה למטה |
| counter_signal_pre_t1 | ~190+ | ALERT | caller מעביר bool — לא מחשב היפוך בעצמו |
| stuck_trade | 214-222 | ALERT | "consider tightening" — אין קירוב-יעד |
| **runner_reversal** | **224-231** | **ALERT בלבד** | אחרי T1; אין MODIFY_TARGET / אין flatten חלקי |

**אין** זיהוי עצמאי של CVD-divergence / CCI-flip / היפוך-טרנד בתוך ה-supervisor — רק דגלים שה-caller מעביר.

## מה S6 מגיב בפועל

| נתיב | מצב | הערות |
|---|---|---|---|
| `MODIFY_STOP` | ✅ wired | `TradeManager._emit_modify_stop` · protective AUTO |
| `DROP_TARGET` | 🟡 חלקי | `manager._apply_drop_target` קיים; CLAUDE.md: advisory DROP_TARGET **לא מחווט לסיירה** ב-protective; `bar_level_detector._exec` מטפל ב-DROP_TARGET כש-AUTOCORRECT=1 |
| `MODIFY_TARGET` | ✅ קיים ב-TM | `manager._emit_modify_target` + `sierra_command.write_modify_target` — **S6 לא פולט אותו** על היפוך |
| `op=EXIT` | ❌ שבור | אסור עד EXIT-v2 · S6 לא אמור לפלוט |
| `FLATTEN_ACCOUNT` | ✅ מלא | יציאה מלאה בלבד — לא חלקי |

`SYSTEM6_AUTOCORRECT=protective` (חי): רק סט AUTO מצמצם-סיכון (stop→BE, DROP_TARGET advisory) — **לא** קירוב יעדים על היפוך.

## פער מול דרישת-מייקל
1. `runner_reversal` / stuck / counter-signal = ALERT בלבד → אין "לקרב יעדים".  
2. אין `MODIFY_TARGET` מ-S6.  
3. "לממש" חלקי דורש op=EXIT → **חסום**. Flatten מלא אפשרי אבל גס.

## הצעה (לפסיקה + סים)
**על היפוך-משמעותי (דגל חדש OFF, למשל `SYSTEM6_REVERSAL_TIGHTEN_V1`):**
1. `MODIFY_STOP` הידוק (BE או trail קרוב יותר) — כבר עובד.  
2. `MODIFY_TARGET` קירוב היעד הבא/ה-runner לכיוון המחיר הנוכחי (R-fraction או מבני קרוב) — להשתמש בנתיב הקיים ב-TM.  
3. **לא** op=EXIT. אם נדרשת יציאה מלאה → `FLATTEN_ACCOUNT` רק עם פסיקה מפורשת / סף חמור.  
4. caller חייב להגדיר "היפוך-משמעותי" (N closes adverse / CVD flip / LSMA cross) — לא לסנתז ב-supervisor.

**אנטי-טאוטולוגיה לטסט:** היפוך מדומה → חייב `MODIFY_TARGET` עם מחיר קרוב יותר לכניסה; בלי היפוך → byte-identical.
