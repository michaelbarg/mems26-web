# מק-2 → LIVE מקבילי (פסיקת-מייקל 2026-08-13)

**אל:** הסוכן על מק-2 (cc-imac / cc-mac2) · **מאת:** cowork-dev (מק-ראשי) · **פעל לפי** `CC_HANDOFF_CONTRACT.md`
**פסיקה:** מייקל 08-13 — "הכן את המק-השני להיות פרלל LIVE מלא, עם כל הדגלים, הגשר וה-DLL שמתחבר לסיארה שם."
**מצב-נוכחי:** מק-2 רץ SIM-parallel מאז 08-07 (`MAC2_SIM_PARALLEL_2026-08-07.md`). המעבר ל-LIVE = דלתא קטנה + בטיחות-חשבון.
**אני לא יכול לבצע על מק-2 מכאן** — הרצף הזה מבוצע על מק-2 עצמו (או ע"י מייקל). הסנכרון דרך git.

---

## 🔴 בטיחות-חשבון — לחסום לפני הדלקה (החלטת-מייקל נדרשת)
**שתי מכונות LIVE על אותו חשבון Sierra = כפל-הזמנות ופוזיציה-כפולה.** ה-reconciler מודע-בעלות
(`RECONCILER_OWNERSHIP_AWARE_V1`) יגרום לכל מכונה להתעלם מהזמנות-השנייה — אבל **שתיהן עדיין יִרו במקביל**,
כלומר סיכון/גודל כפול. לפני LIVE על מק-2, אחת משתיים:
- **(א) חשבון-Sierra נפרד למק-2** (`SIERRA_LIVE_ACCOUNT` שונה) — הפתרון הנקי. **מומלץ.**
- **(ב) אותו חשבון + חלוקת-אחריות מפורשת** (למשל מק-1=S2/S4, מק-2=עסקאות-פתיחה בלבד) כדי שלא יִרו כפול על אותו setup.
**ללא הכרעה זו — אל תדליק LIVE על מק-2.** ברירת-מחדל בטוחה: מק-2 נשאר SIM עד שמייקל קובע חשבון/חלוקה.

## רצף המעבר SIM→LIVE (על מק-2)
1. **`git pull`** — משוך את כל הקוד+הדגלים החדשים (RESPONSIVE_WITH_DAY_TREND, EXTREME_CHASE_GUARD, OPENING_*, SCALE_IN_V1, וכו').
2. **פריטי-דגלים (מקור-אמת = `config/RULED_FLAGS.yaml`, כבר ב-git):** ודא `.env` של מק-2 תואם את כל 169 הדגלים הפסוקים.
   הרץ `python3 scripts/flag_guard.py` → חייב **PASS 169/169**. אם יש drift — יישר את `.env` לפי RULED_FLAGS
   (הדגלים הם code-default, אז רובם לא צריכים env; רק הפסוקים=1/param). **אל תמציא ערכים — RULED_FLAGS הוא המקור.**
3. **גשר (Local-Only):** ודא `CLOUD_URL=http://localhost:8000` (הגשר מסרב לעלות אחרת). LaunchAgent
   `com.mems26.bridge.plist` עם `KeepAlive/SuccessfulExit=false` + `V9_DISABLE_WATCHDOG=1`. אל תכוון ל-render.
4. **DLL:** `./scripts/build_monolithic_cpp.sh --deploy` (auto-snapshot) → Sierra ACS_Source → Remote Build → reload study.
   ודא Input-4 (V9 Export Directory) = `/Users/<mac2-user>/SierraChart_Data/v9_export/` והאקספורטים חיים שם.
5. **snapshot לפני שינוי-.env:** `scripts/mems26_snapshot.sh "mac2-go-live-0813"`.
6. **הדלקת-לייב (רק אחרי הכרעת-החשבון §למעלה):** `.env`: `MEMS26_MODE=sim→live` · `LIVE_TRADING_ARMED=1` ·
   `SIERRA_LIVE_ACCOUNT=<החשבון שנקבע>` · restart backend (`launchctl kickstart -k gui/$UID/com.mems26.backend`).
7. **אימות-runtime (Rule-5, הדבק raw):** `/api/v9/status.mode=live` · health ok · flag_guard 169/169 ·
   feeder חי על החשבון · `sierra_state.position_qty` נקרא נכון (המפתח `position_qty`, לא position_quantity) ·
   Sierra `is_sim=0`. הרץ `scripts/fire_drill.py` → GO.
8. **דווח** שורה חתומה ב-`LIVE_CHANNEL.md` + עדכן `MAC2_SIM_PARALLEL...`→LIVE.

## מה כבר קיים (אל תבנה מחדש)
`install_mems26.sh` · `build_monolithic_cpp.sh --deploy` · `start_all.sh` · SECOND_MAC_SETUP.md · כל ה-LaunchAgents.
המעבר הוא **תצורה+אימות**, לא בנייה.

## NOT-DONE (cowork)
לא ביצעתי על מק-2 (אין לי גישה מכאן). לא הכרעתי חשבון-נפרד-מול-משותף — זו פסיקת-מייקל שחוסמת §בטיחות.
SCALE_IN_V1 עדיין OFF (ממתין ל-Sierra-sim drill של child-PLACE) — כשיודלק על מק-1, מק-2 יקבל אותו ב-pull.
