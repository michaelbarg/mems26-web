# מק-2 → LIVE מקבילי + סנכרון-שוטף (פסיקת-מייקל 2026-08-13)

**אל:** הסוכן על מק-2 (cc-imac / cc-mac2) · **מאת:** cowork-dev (מק-ראשי) · **פעל לפי** `CC_HANDOFF_CONTRACT.md`
**פסיקת-מייקל 08-13 (קבועה):** שני המחשבים רשאים לעבוד LIVE במקביל. **אין חסם-בטיחות-חשבון, ולא מעלים את זה שוב.**
**הדבר היחיד שחשוב: ששני המחשבים יהיו מעודכנים ומסונכרנים** — אותו קוד, אותם דגלים, אותו DLL.

---

## רצף LIVE + סנכרון (על מק-2)
1. **קוד:** `git pull` — כל הקוד+הדגלים החדשים (RESPONSIVE_WITH_DAY_TREND, EXTREME_CHASE_GUARD, OPENING_*, NEVERFADE_TREND_ONLY, SCALE_IN_V1, וכו').
2. **דגלים (מקור-אמת = `config/RULED_FLAGS.yaml`, ב-git):** יישר את `.env` של מק-2 → `python3 scripts/flag_guard.py` חייב **PASS 169/169**.
   זה מנגנון-הסנכרון: flag_guard נכשל אם מק-2 סוטה ממק-1. אל תמציא ערכים — RULED_FLAGS הוא המקור.
3. **גשר Local-Only:** `CLOUD_URL=http://localhost:8000` · LaunchAgent bridge `KeepAlive/SuccessfulExit=false` + `V9_DISABLE_WATCHDOG=1`.
4. **DLL:** `./scripts/build_monolithic_cpp.sh --deploy` → Sierra ACS_Source → Remote Build → reload study.
   Input-4 = `/Users/<mac2-user>/SierraChart_Data/v9_export/`; ודא אקספורטים חיים.
5. **snapshot:** `scripts/mems26_snapshot.sh "mac2-go-live-0813"`.
6. **LIVE:** `.env` `MEMS26_MODE=live` · `LIVE_TRADING_ARMED=1` · `SIERRA_LIVE_ACCOUNT=<חשבון מק-2>` · restart backend.
7. **אימות (Rule-5, raw):** `/api/v9/status.mode=live` · flag_guard 169/169 · `sierra_state.position_qty` נקרא נכון · Sierra `is_sim=0` · `scripts/fire_drill.py`=GO.
8. **דווח** שורה ב-`LIVE_CHANNEL.md`.

## סנכרון-שוטף (כדי ששתי המכונות לא יסטו — העיקר)
- **בתחילת כל סשן על שתי המכונות:** `git pull` + `flag_guard` (PASS = מסונכרן; FAIL = יישר לפני מסחר).
- **אחרי כל שינוי-דגל במק-אחת:** commit RULED_FLAGS+push → המכונה-השנייה `git pull`+יישור `.env`+flag_guard.
- **אחרי כל deploy-DLL:** `mems26_verify.sh` על שתי המכונות (DLL-deployed↔repo-monolith).
- **בדיקת-דריפט מהירה:** `scripts/mems26_verify.sh` (services · DLL↔repo · index · feed · DB-lag).

## מה כבר קיים (אל תבנה מחדש) — המעבר הוא תצורה+אימות, לא בנייה
`install_mems26.sh` · `build_monolithic_cpp.sh --deploy` · `start_all.sh` · `mems26_verify.sh` · `SECOND_MAC_SETUP.md` · כל ה-LaunchAgents · `MAC2_SIM_PARALLEL_2026-08-07.md` (מק-2 כבר רץ SIM-parallel מ-08-07).

## NOT-DONE (cowork)
לא ביצעתי על מק-2 (אין גישה מהמק-הראשי) — הרצף מבוצע שם (מייקל/סוכן-מק-2). SCALE_IN_V1 עדיין OFF (ממתין ל-Sierra-sim drill של child-PLACE); כשיודלק על מק-1, מק-2 יקבל אותו ב-pull+flag-sync.
