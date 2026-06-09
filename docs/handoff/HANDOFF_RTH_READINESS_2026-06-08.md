# Handoff — מצב מוכנות-ירי RTH 2026-06-08 (~14:05 UTC / 17:05 IL)

## TL;DR — ❌ לא מוכן לירי. verdict=BLOCKED · 0 תבניות armed.
‏V2 מודלק והמערכת בריאה, אבל **אין ברי-RTH טריים** מ-Sierra → day_type=UNKNOWN →
שום תבנית לא דורכת. חוסם = **Sierra Chart 5 לא מייצר ברים להיום** (פעולת-Michael).

## מה מודלק/בריא (אומת Cowork חי + CC)
- `STOP_ANCHORS_V2=1` · `S4_EXTREME_TREND_RELABEL=true` · `MEMS26_MODE=shadow` — פעילים בתהליך.
- backend health ok · 0 שגיאות sqlite · DATABASE_URL=Postgres.
- גשר **חי** (PID 593, push #5843, 11 streams/3s, 0 FAILED) — "מת" היה false (באג-שמות).

## החוסמים (verdict=BLOCKED)
1. **🔴 אין ברי-RTH** — `v9_bars_5min` latest = שישי 23:55 IL. Sierra `5min.json` last bar =
   08:50 UTC (Globex). ברי-RTH של היום (09:30 ET+) **לא ביצוא**. ⇒ Chart 5 לא מייצר.
2. **day_type=UNKNOWN** (נגזר מ-#1) → S2/S4 לא דורכים (0/10 + 0/9 armed).
3. **🟡 באג-שמות build inspector** → verdict שקרי "dead: tick_reversal":
   `STREAM_CHECKS` ב-`bridge_inspector.py` משתמש ב: `5min_bars`(אמת `bars_5min`),
   `tpo_bars`(אמת `tpo`), `tick_reversal`(אמת `tick_reversal_12`/`_15`). → streams=0 שקרי.

## פעולות
### A · 🔴 Michael — Sierra (החוסם האמיתי)
1. הבא את **Chart 5** (MES RTH 5-min) לפוקוס בסיירה.
2. ודא שהוא מציג ברים אחרי 09:30 ET של היום.
3. אם ריק/תקוע: Chart → Recalculate · ודא DLL study על ה-chart הנכון.
4. אחרי שיצוא ברי-RTH טרי → גשר דוחף → day_type מסווג → תבניות דורכות (אוטומטי).

### B · 🟡 CC — תיקון-קוד build inspector (מהיר)
תקן את שמות-הטבלאות ב-`backend/v9/systems/build_status/bridge_inspector.py`
`STREAM_CHECKS`: `5min_bars`→`bars_5min` · `tpo_bars`→`tpo` ·
`tick_reversal`→`tick_reversal_15` (ה-stream הפעיל). + טסט שמאמת שכל table_name
ב-STREAM_CHECKS קיים ב-DB. מסיר את ה-BLOCKED השקרי.

### C · Cowork — אימות אחרי A
ברגע שברים זורמים: לאמת day_type≠UNKNOWN · תבניות armed>0 · ושעם V2 הסטופים/
חוזים/T1 של עסקאות-SHADOW חדשות תואמים ל-SPEC (הצלבה מול MASTER_TRADE_SPEC).

## מצב הדגלים (לתזכורת)
7 דגלי-כיול ON · STOP_ANCHORS_V2 ON · S4_EXTREME_TREND_RELABEL ON ·
2 דגלי-reclass = קוד-מת (no-op).
