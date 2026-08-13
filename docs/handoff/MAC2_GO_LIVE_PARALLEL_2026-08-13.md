# מק-2 → LIVE מקבילי + סנכרון-שוטף (פסיקת-מייקל 2026-08-13)

**אל:** הסוכן על מק-2 (cc-imac / cc-mac2) · **מאת:** cowork-dev (מק-ראשי) · **פעל לפי** `CC_HANDOFF_CONTRACT.md`
**פסיקת-מייקל 08-13 (קבועה):** שני המחשבים רשאים לעבוד LIVE במקביל. **אין חסם-בטיחות-חשבון, ולא מעלים את זה שוב.**
**הדבר היחיד שחשוב: ששני המחשבים יהיו מעודכנים ומסונכרנים** — אותו קוד, אותם דגלים, אותו DLL.

---

## רצף LIVE + סנכרון (על מק-2) — עודכן 13.08 10:00 (cowork)
1. **קוד:** `git pull` — כל הקוד+הדגלים החדשים (RESPONSIVE_WITH_DAY_TREND, EXTREME_CHASE_GUARD, OPENING_*, NEVERFADE_TREND_ONLY, SCALE_IN_V1=ON, F3-מיושר-לרחב, PHONE_ALERTS_V1, MACHINE_TAG).
2. **דגלים (מקור-אמת = `config/RULED_FLAGS.yaml`, ב-git):** יישר את `.env` של מק-2 → `python3 scripts/flag_guard.py` חייב **PASS 170/170**.
   זה מנגנון-הסנכרון: flag_guard נכשל אם מק-2 סוטה ממק-1. אל תמציא ערכים — RULED_FLAGS הוא המקור.
2ב. **התראות-נפרדות (פסיקת-מייקל 13.08):** ב-.env של מק-2: `MACHINE_TAG=מק-2` +
   `PHONE_ALERTS_V1=1` + `PUSHOVER_USER_KEY`/`PUSHOVER_API_TOKEN`/`NTFY_TOPIC` (זהים למק-1,
   מ-.env שם — לא ב-git). שלח פוש-בדיקה ואמת שמייקל רואה `[מק-2]` בכותרת. הדבק פלט (Rule-5).
2ג. **רנדר-נפרד למק-2 (פסיקת-מייקל 13.08 10:30; 11:00: חינם-בלבד):** אחרי שמייקל פורס
   את ה-blueprint (`render.yaml` → שירות `mems26-phone-mac2`, **plan: free**): ב-.env של מק-2:
   `RENDER_MOBILE_URL=https://mems26-phone-mac2.onrender.com` + `MOBILE_ACCESS_KEY`/
   `MOBILE_PUSH_KEY` (זהים למק-1) + **תקציב-שעות-החינם (חובה, אחרת השעיה באמצע-חודש):**
   `RELAY_WINDOW_IL=10:00-23:30` + `RELAY_DAYS_IL=Sun,Mon,Tue,Wed,Thu,Fri` →
   טען את ה-LaunchAgent `com.mems26.mobile_relay` (מ-`launchagents/`) → אמת:
   `curl -s https://mems26-phone-mac2.onrender.com/healthz` מחזיר `has_snapshot:true,
   age_s<10`, והדף מציג תג `מק-2` בכותרת. הדבק פלט.
   **אסור** להצביע על `mems26-mobile` (זה של מק-1) — כל מכונה והשירות שלה.
3. **גשר Local-Only:** `CLOUD_URL=http://localhost:8000` · LaunchAgent bridge `KeepAlive/SuccessfulExit=false` + `V9_DISABLE_WATCHDOG=1`.
4. **DLL:** `./scripts/build_monolithic_cpp.sh --deploy` → Sierra ACS_Source → Remote Build → reload study.
   Input-4 = `/Users/<mac2-user>/SierraChart_Data/v9_export/`; ודא אקספורטים חיים.
5. **snapshot:** `scripts/mems26_snapshot.sh "mac2-go-live-0813"`.
6. **LIVE:** `.env` `MEMS26_MODE=live` · `LIVE_TRADING_ARMED=1` · `SIERRA_LIVE_ACCOUNT=<חשבון מק-2>` · restart backend.
7. **אימות (Rule-5, raw):** `/api/v9/status.mode=live` · flag_guard 170/170 · `sierra_state.position_qty` נקרא נכון · Sierra `is_sim=0` · `scripts/fire_drill.py`=GO.
7ב. **DLL/סטאדי זהה (דרישת-מייקל 13.08 "זהה בדגלים וב-DLL"; 10:35: "אין לו סטאדי
   מעודכן" — הסטאדי במק-2 ישן ⇒ פריסה היא **חובה לפני חימוש**, לא אימות בלבד):**
   `git pull` → `./scripts/build_monolithic_cpp.sh --deploy` → הדבק את שתי שורות-ה-shasum
   של **מקור-המונוליט**: `shasum ~/SierraChart/ACS_Source/MES_AI_DataExport.cpp` מול
   ה-build מהריפו — חייבות להיות זהות (מקור-זהה = סטאדי-זהה). אחר-כך בתוך Sierra:
   Remote Build → reload study (אם אין לך גישת-UI — בקש ממייקל, זו פעולה במסך של מק-2),
   ואמת אקספורטים חיים: `sierra_state.json` מתעדכן (גיל <10ש) וכל קבצי `v9_export`
   מתקדמים. סטאדי ישן = op-codes/שדות לא-תואמים לבקנד החדש ⇒ אסור לחמש לפני.
8. **דווח** שורה חתומה ב-`LIVE_CHANNEL.md` + חובות-הפיקוח השוטפות (רשומת cowork 13.08 09:50):
   flag_guard-PASS כל סשן · shasum אחרי כל deploy · דוח-סים/לייב חתום כל סוף-סשן.
   cw מריץ ביקורת-יומית 15:05 ומתריע למייקל על שתיקה/סטייה.

## סנכרון-שוטף (כדי ששתי המכונות לא יסטו — העיקר)
- **בתחילת כל סשן על שתי המכונות:** `git pull` + `flag_guard` (PASS = מסונכרן; FAIL = יישר לפני מסחר).
- **אחרי כל שינוי-דגל במק-אחת:** commit RULED_FLAGS+push → המכונה-השנייה `git pull`+יישור `.env`+flag_guard.
- **אחרי כל deploy-DLL:** `mems26_verify.sh` על שתי המכונות (DLL-deployed↔repo-monolith).
- **בדיקת-דריפט מהירה:** `scripts/mems26_verify.sh` (services · DLL↔repo · index · feed · DB-lag).

## מה כבר קיים (אל תבנה מחדש) — המעבר הוא תצורה+אימות, לא בנייה
`install_mems26.sh` · `build_monolithic_cpp.sh --deploy` · `start_all.sh` · `mems26_verify.sh` · `SECOND_MAC_SETUP.md` · כל ה-LaunchAgents · `MAC2_SIM_PARALLEL_2026-08-07.md` (מק-2 כבר רץ SIM-parallel מ-08-07).

## NOT-DONE (cowork)
לא ביצעתי על מק-2 (אין גישה מהמק-הראשי) — הרצף מבוצע שם (מייקל/סוכן-מק-2). SCALE_IN_V1 עדיין OFF (ממתין ל-Sierra-sim drill של child-PLACE); כשיודלק על מק-1, מק-2 יקבל אותו ב-pull+flag-sync.
