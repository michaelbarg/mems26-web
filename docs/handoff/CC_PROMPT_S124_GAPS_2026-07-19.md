# CC Prompt — S124 GAPS (G1–G8) — מופעל רק אחרי פסיקת-מייקל לפער

**מבצע:** cc-macbook · **מפרט/אימות:** cowork-dev · **מעקב:** cursor-agent  
**לוח:** `docs/handoff/LIVE_CHANNEL.md` §🔴 S124 GAPS  
**ביקורת:** `docs/handoff/S1_SOURCE_AND_DAYTYPE_AUDIT_2026-07-19.md`

## חוק הפעלה
1. `git pull`. קרא את שורת-הלוח לפער הפעיל.
2. **אל תתחיל קוד** אלא אם ב-LOG יש פסיקת-מייקל מפורשת: `G#: לתקן` (או `לשנות-כך: …`).
3. דגל חדש = default OFF. לא לגעת ב-`.env` ON בלי פסיקת-הדלקה נפרדת + RULED.
4. אחרי מימוש: טסטים + פלט גולמי ב-LOG. cowork מאמת (חוק-5). cursor מסמן ✅.
5. פער אחד בכל פעם. אחרי סגירה — עצור עד הפער הבא.

---

## G1 — B1 paint / `current_bar` (ראשון אחרי פסיקה)

**בעיה:** `bars.py` מחיל `_trend_from_cci` על history (~1087) אבל ה-override של `current_bar` (~1153) מעביר `trend_state` גולמי → S4 רואה GRAY בזמן ש-DB/UI מתוקנים.

**תיקון מוצע:**
- אחרי בניית `last_flat` מ-`current_bar`, החל:
  `last_flat["trend_state"] = _trend_from_cci(last_flat.get("trend_state"), last_flat.get("cci_14"))`
- עדיף תחת אותו `TREND_CCI_DIRECT_V1` (כבר קיים) — בלי דגל חדש אם ההתנהגות זהה ל-history.
- טסט רגרסיה: current_bar עם CCI>|thr| + GRAY raw → routed trend RED/BLUE; flag OFF → raw נשמר.

**קריטריון-סיום:** טסט ירוק + cowork מדביק פקודה+פלט + לוח G1→✅.

---

## G2 — S2 A2/A4 detection day-type

**בעיה:** Nontrend skip + `chart_patterns_allowed` על `self.current_day_type` (`five_min_system.py` ~1138–1195), לא `get_live_day_type`.

**תיקון מוצע (דגל `S2_DETECTION_LIVE_DAYTYPE_V1` default OFF):**
- כש-ON: `_det_dt = get_live_day_type() or self.current_day_type`
- השתמש ב-`_det_dt` ל-NT skip + chart gates
- אם live=None ו-current=None: warning קיים (לא skip שקט בלי לוג)

**טסטים:** override Variation + hydrate Nontrend → עם דגל ON detection לא עושה NT skip; OFF = byte-identical.

---

## G3 — Flag T2

**בעיה:** `dt = self.current_day_type` ב-~1551 בעוד emit כבר live.

**תיקון:** אותו מקור כמו `_emit_day_type` / live. יכול להתמזג עם G2 באותו PR אם מייקל אישר את שניהם.

---

## G4 — Honest prelock

**אין קוד חדש אם הדגל קיים.** אחרי פסיקת-הדלקה: `.env` + RULED + ריסטארט + `flag_guard`. cowork מוביל.

---

## G5 — UI SoT

**בעיה:** TopBar/DayTypeLens → `classify_replay` בלי override/antiflap.

**תיקון מוצע:** צרכן FE קורא endpoint/שדה שכבר חושף את `get_live_day_type` (KEEP API קיים אם יש; אחרת הוסף שדה ל-status/systems — לא לשכפל מנוע). טסט/ snaphot: עם override, UI == gate.

---

## G6 — Fallbacks מתים

**בעיה:** S4 נסיגה ל-`v9_day_type_state` / `"Normal"` (`woodies_system.py:672-688`); S2 hydrate מאותה טבלה.

**תיקון (דגל OFF):** כש-ON, אחרי כשל live — `None` / log, **לא** `"Normal"` ולא קריאת הטבלה-המתה. צרכנים מסרבים לירות / fail-open מפורש לפי פסיקה.

---

## G7 — FIXED_4 × REDUCED

**אסור קוד בלי פסיקה מפורשת** (להשאיר / לכבד REDUCED / כלל אחר). אם `לתקן=לכבד REDUCED`: FIXED_4 לא דורס כש-playbook=REDUCED (או מחשב 2). טסטים אנטי-טאוטולוגיים.

---

## G8 — דוקטרינה

תוצר = מפרט-דוקטרינה ב-LOG/מסמך קצר. **אין קוד מסווג** בלי עצירה-אסטרטגית + חתימת-מייקל.
