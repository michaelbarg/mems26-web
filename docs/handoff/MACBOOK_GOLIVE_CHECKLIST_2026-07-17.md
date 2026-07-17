# MacBook GO-LIVE — קאטאובר מסחר-אמת ל-cowork-dev/MacBook · 2026-07-17
**פסיקת-מייקל 07-17: המסחר עובר למחשב-הזה (MacBook), לייב כסף-אמת היום. ה-iMac יורד לסים.**
מהפך-פסיקה (07-11: מק-זה=פיתוח). כל צעד רץ **על ה-MacBook בידי מייקל** (הסנדבוקס של cowork-dev לא מגיע ל-backend/Sierra/DB).
cowork-dev מכין+מאמת דרך המאונט + computer-use; **לא מחמש — מייקל מחמש.**

## מצב-פתיחה שנמדד (.env של ה-MacBook, 07-17)
`MEMS26_MODE=live` · `SIERRA_LIVE_ACCOUNT=37138283` (=חשבון-הלייב של ה-iMac) · `LIVE_EXECUTION_V1=1` ·
`OPENING_WINDOW_FIRE_V1=1` · `RISK_HALT_V1=1` (−$450) · `EOD_FLATTEN_V1=1` · **`LIVE_TRADING_ARMED` חסר=OFF** (שער-בטיחות מחזיק) ·
`DAY_TYPE_MANUAL_OVERRIDE` לא-מוגדר (טוב). קוד-הלילה כבר בעץ (migration 022 קיים, S1_IB_SANITY בקוד) — אבל לא-live עד migrate+restart.

## 🔴 שער-0 — מניעת ירי-כפול (חובה ראשון, לא-מתפשר)
אותו חשבון 37138283 על שתי המכונות ⇒ הבטיחות כולה = **בדיוק מכונה-אחת חיה**.
- [ ] ה-iMac ב-**Trade Simulation Mode → ON** + disarmed + flat. אישור מ-cc-imac (SYNC S-15) או ממך בעין.
- [ ] **אל תחמש את ה-MacBook לפני האישור הזה.** (cowork לא יכול לאמת iMac — 403.)

## Phase A — לעדכן+להריץ את קוד-הלילה על ה-MacBook
- [ ] `cd ~/Downloads/mems26_web_git && git pull --no-rebase` — ודא HEAD כולל d79f1a48 (patterns-panel) + cdac81c2 (N1).
- [ ] migration 022: `env DATABASE_URL=postgresql://localhost/mems26 .venv/bin/python3 backend/v9/db/migrations/versions/022_day_type_state_n1_columns.py` (אידמפוטנטי; "already exists — skip" = תקין).
- [ ] ודא `le=4` בסכמת-S2: `grep -n "le=" backend/v9/**/output_schema.py` (תיקון-S-10; אם le=3 → לא-נמשך).

## Phase B — להרים שירותים על ה-MacBook
- [ ] `bash scripts/start_all.sh` (bridge+backend+frontend; hard-exports CLOUD_URL=localhost:8000).
- [ ] מאזינים: `lsof -iTCP:8000 -sTCP:LISTEN; lsof -iTCP:3000 -sTCP:LISTEN` — מופע-יחיד לכל אחד.
- [ ] `curl -s localhost:8000/api/v9/status` → `mode":"live"` + `sierra.writing` (אחרי Phase C).

## Phase C — לחבר-מחדש את סיירה של ה-MacBook (בוטל בכוונה 07-15)
- [ ] Sierra: **Input 22 = 1** (ייצוא-DLL חמוש) + **File → Connect** (פיד-נתונים + trade-service).
- [ ] Sierra: **Trade → Trade Simulation Mode → OFF** (חשבון-אמת 37138283).
- [ ] ודא-בעין: `is_sim=0` **וגם** מחיר-שפוי (~7595, לא 996150) **וגם** `qty=0` (flat).

## Phase D — שער-N6 (7 בדיקות, כולן ירוקות לפני העסקה הראשונה — ראה N6_MORNING_PROTOCOL_2026-07-17.md)
- [ ] `python3 scripts/bar_gap_monitor.py --window 60` — 0 פערים ב-`v9_bars_5min_woodies`.
- [ ] `bash scripts/post_restart_verify.sh` GREEN (false-RED ידוע: staleness על `v9_bars_5min` הישן — לא-חוסם אם woodies טרי; אמור זאת מפורש).
- [ ] S1 מפרסם day_type תוך 30 דק' מהפתיחה: `curl -s localhost:8000/api/v9/mobile/data | python3 -c "import sys,json;print(json.load(sys.stdin).get('day_type'))"` — לא-null בחלון המתאים (None לפני נעילת-IB אם DAYTYPE_HONEST_PRELOCK_V1 דלוק).
- [ ] S2-DL פעיל על בר-חי: `curl -s localhost:8000/api/v9/gateway/decisions | python3 -m json.tool | head -40` — חותמות-זמן עכשוויות.
- [ ] `python3 scripts/flag_guard.py` PASS · `python3 scripts/fire_drill.py` GO.
- [ ] `grep OPENING_WINDOW .env` → `OPENING_WINDOW_FIRE_V1=1`.
- [ ] `grep DAY_TYPE_MANUAL_OVERRIDE .env` → ריק, או תאריך=היום בלבד (override-ישן חל שקט על היום).
- [ ] `grep EOD_FLATTEN_V1 .env` → `=1` (נוטרל לחלון-סים; חובה חזרה ל-1 לפני-לייב + ריסטארט).

## Phase E — חימוש (רק אחרי כל השערים ירוקים + iMac=Sim מאושר)
- [ ] `.env`: `LIVE_EXECUTION_V1=1` (כבר) + הוסף **`LIVE_TRADING_ARMED=1`** (שער-הבטיחות — אחרון).
- [ ] snapshot לפני עריכת-.env: `scripts/mems26_snapshot.sh "macbook-golive-arm"`.
- [ ] ריסטארט → `flag_guard` PASS + `fire_drill` GO → מוכן-RTH.
- [ ] **שער:** is_sim=0 + מחיר-שפוי + 3 החימושים (Input22=1 · LIVE_EXECUTION_V1=1 · LIVE_TRADING_ARMED=1) + drill GO.

## 🔴 סיכונים-פתוחים לקבל-במודע או לפתור לפני לייב-אמת היום
- **S-13 — כניסה-עירומה לסירוגין (בטיחות-לייב!):** ב-N9-סים אמש, במחזורים-מהירים הברקט לא-נצמד → כניסה בלי סטופ עד FLATTEN (3/8). בלייב = הפסד-לא-חסום. **המלצה: לפתור ב-DLL קודם, או לקבל-במודע עם התראת-S6-naked + עין-אנושית.**
- **S-14 — פסיקת-S1:** 3 דגלי-S1 בנויים אך OFF ולא-אומתו-בסים-חי; פער-דוקטרינה נייטרלי-ערכי; שורש-IB פרה-אופן-תקוע (re-base DLL 17:30). לא-להדליק את הדגלים בלי pass-סים קודם.
- **פיד-חי בפתיחה:** וטו feed_watchdog חוסם RTH עד שהפיד חי-אמת (לא Replay).
- **S2 בגודל-4:** אתמול 0 עסקאות-S2; לאמת REACTIVE/INITIATIVE יורה עם le=4.

## GO/NO-GO
תעד פסק-דין + פלט-גולמי לכל שער ב-AGENT_SYNC (חוק-5). אין-לחמש ללא iMac=Sim מאושר + Phase D כולו ירוק.
