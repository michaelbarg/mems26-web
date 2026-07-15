# שאילתת-ערב ל-cc-imac — פריסת תיקון-R:R כדי שהמערכת תסחר הערב · 2026-07-15

**מודל מומלץ לסשן הזה: Sonnet** (‏`/model sonnet`) — משימת-ביצוע-לפי-צ'קליסט; אל תשתמש ב-Opus.
כללי-חיסכון: קרא רק קבצים שמופיעים כאן · אל תדביק קבצים שלמים לדוח · ראיות = פקודה + ≤5 שורות פלט.

## הקשר (אל תחקור מחדש — זה כבר מאובחן)
ממצא-18:20 שלך אומת ותוקן: שער-R:R × רצפת-סטופ-0.8×ATR חסם את ה-ZLR SHORT המנצח של 18:15
(‏R:R 0.65). התיקון: **`RR_MIN_ROTATION`** — מינימום-R:R מדורג **בימי-רוטציה בלבד**
(‏Variation/Normal/Neutral): ‏`T1_dist ≥ stop_dist × ערך` במקום ‏≥1.0. ימי-Trend נשארים 1.0;
שגיאת-סוג-יום → 1.0 (שמרני). קוד: ‏`trading_gateway.py` בלוק ‏RR_ENTRY_GATE_V1;
טסטים: ‏`tests/v9/regression/test_rr_graded_rotation.py` (5, משחזרים את 18:15 במדויק).

## שער-GO
בצע **רק אם** ב-AGENT_SYNC מופיעה רשומת cowork-dev עם **"מייקל אישר RR_MIN_ROTATION=<ערך>"**.
אין רשומה → עצור, אל תשנה כלום, דווח שאתה ממתין.

## צעדים (בסדר הזה, עצור בכל כשל)
1. **טריות:** ‏`git pull --ff-only` → ‏behind=0. חייב לכלול את קומיט-הפאנל (44d6648) + קומיט-ה-R:R.
2. **FLAT-בלבד:** ‏`sierra_state.json` ‏position_qty=0 + ‏`/api/v9/trades/active`=null. פוזיציה פתוחה →
   המתן לסגירתה (T/סטופ). **אין ריסטארט עם עסקה חיה.**
3. **טסטים מקומיים (בלי שירותים):**
   `BRIDGE_TOKEN=test python3 -m pytest tests/v9/regression/test_rr_graded_rotation.py tests/v9/regression/test_gateway_decisions_feed.py -q` → ‏10 passed.
4. **‏.env:** הוסף ‏`RR_MIN_ROTATION=<הערך המאושר>` (+ ודא שאין כפילות). ‏`python3 scripts/sync_env_from_ruled.py --apply` → "already matches" או יישום נקי.
5. **באותו חלון-ריסטארט — גם S-8 (מוניטור-הנייד של מייקל):**
   ‏(א) ‏snapshot: ‏`scripts/mems26_snapshot.sh imac-bind-0000-rrmin` ‏(ב) בפליסט-הבקאנד שלך: ‏`--host 0.0.0.0`
   ‏(ג) דווח ‏IP: ‏`ipconfig getifaddr en0`.
6. **ריסטארט-בקאנד** (‏bootout/bootstrap או kickstart) → המתן ל-health.
7. **אימות (Rule 5 — הדבק פלט):**
   - ‏boot-line ‏env_loader מציג ‏RR_MIN_ROTATION.
   - ‏`python3 scripts/flag_guard.py` → ‏PASS (המספר יעלה אחרי עדכון-RULED של cowork-dev).
   - ‏`curl -s localhost:8000/api/v9/gateway/decisions | head -c 300` → עונה (הפיד חי).
   - ‏fire_drill → ‏GO, ‏effective=4.
8. **חזרה למסחר:** ודא חימוש (‏Input 22=1, ‏armed=true) + פיד טרי. מעכשיו ZLR-רוטציה עם ‏R:R≥הערך יעבור.
9. **דיווח:** רשומת-SYNC חתומה + סעיף ב-EXECUTION_REPORT: מה-בוצע · ראיות · **NOT-DONE מפורש**.
   בשורה הראשונה: שעת-החזרה-לחימוש. חסימת-rr הבאה שתעבור/תיחסם — צטט אותה מהפיד החדש.

## אסור
שינוי ערך-הדגל מעבר למאושר · נגיעה בשערים אחרים · ריסטארט עם פוזיציה · מסחר לפני צעד-7 ירוק.
