# CC PROMPT — אבחון S1/S2 מחדש על **Postgres** (מתקן ריצה קודמת על SQLite + ממצא S2 שגוי) · 2026-06-04

**פעל לפי `CC_HANDOFF_CONTRACT.md`.** **read-only / diagnostic — אל תתקן.** אישור Michael 2026-06-04.

## למה ריצה-מחדש (Cowork אימת 2 בעיות בריצה הקודמת)
1. **🔴 הריצה הקודמת רצה על SQLite הישן, לא על PG.** הדוח השתמש ב-`PRAGMA table_info` (תחביר SQLite) ו-`mems26_local.db`,
   והספירות ענקיות (374 עסקאות S3, ~492 שורות day_type_state) = דאטה מצטבר ישן. אנחנו על **Postgres** (`postgresql://localhost/mems26`),
   שהתחיל נקי. **כל ממצאי-הנתונים הקודמים פסולים.** הרץ הכל מול PG: `information_schema` / `db.read` / `psql`, **לא** PRAGMA, **לא** קובץ SQLite.
2. **🔴 ממצא ה-S2 הקודם שגוי עובדתית.** נטען "VSA/RVOL לא קיימים, הדגל S2_VSA_VOLUME לא קיים (grep zero)". **זה לא נכון** —
   הקוד מכיל 3 וריאציות מיושמות:
   - `S2_VSA_VOLUME` ב-`backend/v9/shared/atr.py:103` + `five_min_system.py:499,513,537,632`.
   - `_vsa_pass`/`_rvol_pass`/`_strict_pass` ב-`five_min_system.py:504-511`; `_variants_long/short = {"A_VSA","B_RVOL","C_STRICT"}` (544/568).
   השאלה היא **לא** "לבנות" אלא: איזו וריאציה פעילה (מצב-דגל) ומה ה-pass-rate שלה על דאטה אמיתי.

## אבחון נדרש (raw, מול PG בלבד)
### S1 day-type
1. סכמת `v9_bars_5min` ב-PG (`information_schema.columns`) — אשר אם יש/אין עמודת `atr`. (המודל ב-`db/models` בלי atr → צפוי אין.)
2. נתיב ה-ATR: `wrappers.py:75` `atr=bar.get("atr")` — אם אין עמודה → None. אשר ש-`state_machine.py:617` נופל ל-range fallback (`atr = bar.atr if ... else current_range`) → **הסיווג עובד**, אבל re-eval trigger #1 (extreme >3 ATR, `detector.py:503-539`) **מת** (קורא atr בלי fallback). הפרד בבירור: "סיווג חי" מול "trigger #1 מת".
3. **על PG:** התפלגות `lock_state` ב-`v9_day_type_state` + האם הגיע אי-פעם ל-`LOCKED` high-conf (≥0.85) או רק `LOCKED_LOW_CONF`. ספירות PG בלבד.
4. signal-leak: אשר `wrappers.py:86` מייצר Signal ב-LOCKED_LOW_CONF למרות S1=OBSERVER → קלט להחלטת D-090 (לא לתקן).

### S2 reactive
5. מצב הדגל `S2_VSA_VOLUME` בזמן-ריצה (env בפועל). אם OFF → הגייט הפעיל הוא legacy (90% drop); אם ON → A_VSA.
6. הרץ את 3 הווריאציות (`_vsa_pass`/`_rvol_pass`/`_strict_pass` + legacy) על ברי-RTH אמיתיים מ-**PG** (replay אם RTH סגור) → לכל וריאציה **כמה ברים עוברים מתוך N**.
7. ספירות **PG**: `v9_five_min_setups` count · `v9_trades WHERE firing_system=2`. אם ה-stop=0.25pt חוזר — אשר אם זה ב-PG או היה רק ב-SQLite הישן.

## תוצר (raw, ל-Cowork)
- S1: עמודת atr קיימת? · סיווג חי מול trigger#1 מת · lock_state התפלגות **ב-PG** · signal-leak (D-090).
- S2: מצב-דגל · pass-rate פר-וריאציה (4) על ברי-PG · setups/fires **ב-PG** · אישור/הפרכה של stop-anomaly ב-PG.
- המלצה: תיקון S1 atr (היכן בצינור) + איזו וריאציה ל-S2 (קלט ל-D-RVX). **אל תתקן.**

## Invariants
read-only · **PG בלבד — לא PRAGMA/SQLite** · localhost · ❌ לא Render/Upstash/prod-PG · אל תיגע risk-logic/sc_study · Cowork מאמת בלתי-תלוי. כל פלט = raw + ציון אם מקורו PG.
