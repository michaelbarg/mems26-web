# T15 — ביקורת פרוטוקול-הבוקר: GO-כוזב

**תאריך:** 2026-07-19 · cursor-agent · **קריאה+הצעה בלבד** (מימוש ≠ cursor)

## הבעיה (מייקל)
כל שבוע `fire_drill` / פרוטוקול החזירו GO — והמערכת לא סחרה כמו שצריך (0 עסקאות / חסימות-שער / paint-lag).  
GO ירוק בזמן מערכת שבורה = נחמה-כוזבת.

## מה כל שלב בודק היום (file:line)

### A · `scripts/flag_guard.py` (via `fire_drill.stage_a` :54-59)
- בודק: דגלים RULED לא זזו מול המפרט.
- **למה עובר עם 0 עסקאות:** אין בדיקת ירי / גייטים / תבניות. רק קונפיג.

### B · `scripts/fire_drill.py` `stage_b` :76-94
- בודק: `compute_stop_v2` + `validate_fire` על **entry סינתטי 7500** + עוגנים סינתטיים.
- **למה עובר עם 0 עסקאות:** plumbing של סטופ/וולידטור על setup מושלם — לא detector אמיתי, לא location/cont_trend/cutoff/entry_confirm על ברים חיים.

### C · `stage_c` :97-114
- בודק: `effective_contracts({"size":"full"})` == want (4 תחת FIXED_4) · `entry_confirmed` על בר סינתטי.
- **למה עובר עם 0 עסקאות:** ספירת-חוזים + בר-אישור מבודד — לא שרשרת גייטי-מסחר על setup אמיתי.

### D · `stage_d` :117-134
- בודק: health · live_price age · gateway slot · live_enabled=[2,4] · **`/day_type/state`** (מקור ישן/לא-gate).
- **למה עובר עם 0 עסקאות:** תשתיות חיות ≠ מוכנות-ירי. גם day_type כאן ≠ `get_live_day_type`.

### `scripts/morning_briefing.py`
- ATR / יום / מפלסים / תזכורת ש-fire_drill+flag_guard חייבים 🟢.
- **לא** מריץ setups אמיתיים דרך גייטים.

## הפער GO↔מציאות
| נבדק היום | לא נבדק (מה שחסם בשבוע שעבר) |
|---|---|
| flag RULED | playbook SKIP / position / location |
| validate_fire סינתטי | detection על live day-type (G2) |
| contracts==4 | paint GRAY על current_bar (G1 — תוקן חלקית) |
| feed age | CONT_TREND / LSMA veto / entry_not_confirmed |
| gateway slot | against-Dalton / VA side |
| day_type/state | UI≠gate (G5 — תוקן חלקית) |

## הצעה — בדיקת מוכנות-ירי-אמיתית (שלב חדש E / `fire_readiness_real`)

**GO רק אם** לפחות N setups אמיתיים (אתמול או חלון RTH אחרון) **היו עוברים** את שרשרת-השערים החיה — לא drill סינתטי.

1. **מקור setups:**  
   - `audit_pattern_miss` / `missed_trade_watch` על תאריך אתמול, **או**  
   - replay `/api/v9/chart/replay` + detectors S2/S4 על ברים אמיתיים.
2. **להריץ כל setup דרך אותם גייטים כמו gateway** (read-only / dry):  
   daytype_playbook · `get_live_day_type` · location/position (אם ON) · CONT_TREND / LSMA · entry_confirm · pre_fire · sizing.  
   **פלט:** `would_fire` / `blocked_by=<gate>` per setup.
3. **קריטריון GO:**  
   - אם היו ≥1 setups ש-`would_fire=true` תחת הדגלים החיים → GO (המערכת *יכולה* לירות).  
   - אם כל setups אמיתיים `blocked_by=…` ורק הסינתטי עובר → **NO-GO** עם סיבות.  
   - אם 0 setups זוהו בכלל (יום Nontrend / אין ברים) → **NO-GO / INDETERMINATE** עם סיבה מפורשת — לא GO שקט.
4. **שער עקביות מקורות (בוקר):**  
   paint UI == in-memory S4 · `direction_now` · `day_type/live` == מה שהשער רואה · `dir` vs `dir_sustained` מדווח.  
   אי-התאמה → WARNING/NO-GO לפי חומרה.

## מצב מימוש — 🟡 בנוי OFF, ממתין אימות+פסיקת-הדלקה

`scripts/fire_readiness_real.py` נבנה כשלב E עצמאי, read-only:
- מקור setups = עסקאות אמיתיות ולא-סינתטיות מ-`/api/v9/chart/replay` + העשרה מ-`/api/v9/trades`;
  מסנן RTH ומאחד shadow/live כפולים של אותו setup.
- גייטים טהורים: playbook · position (אם דלוק) · CONT/LSMA · entry-confirm · pre-fire · contracts-count.
- `get_live_day_type` של אתמול מסומן בכנות `NOT_EVALUATED` (הוא קורא `app.state` של היום);
  `day_type_at_entry` החתום משמש לשערים ההיסטוריים.
- `GO` רק עם `would_fire>=1`; כולם חסומים=`NO-GO`; אפס setups/שער-חובה חסר=`INDETERMINATE`.
- חיבור ל-`fire_drill.py` רק תחת `FIRE_DRILL_STAGE_E=1`; ברירת-מחדל OFF ופלט A–D ללא הדגל זהה.

ראיית 07-17: 7 setups ייחודיים ב-RTH · 1 `would_fire` (BEAR_FLAG_SHORT 14:10 ET) → GO.
ראיית 07-16: 0 setups → INDETERMINATE (exit 2). טסט: `5 passed`.

## המלצת-סדר
1. cowork מאמת diff + פלט גולמי.
2. פסיקת-מייקל נפרדת לפני `FIRE_DRILL_STAGE_E=1` (אין שינוי `.env` בקומיט הזה).
3. עדכון `morning_briefing` לציין E במפורש אחרי פסיקת-הדלקה.
