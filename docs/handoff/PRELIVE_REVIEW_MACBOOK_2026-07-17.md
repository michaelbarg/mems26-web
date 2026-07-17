# ביקורת פרה-לייב — מסחר-אמת מהמחשב-הפיתוח (MacBook) · 2026-07-17
**ביקורת-בלבד (בלי תיקונים), בקשת-מייקל.** 3 סוכני-קריאה + בדיקת-אינדקס. כל פריט = ממצא + ראיה (file:line) + בדיקה.
פרומפט-הפעולה ל-cc-imac: `CC_PROMPT_PRELIVE_REVIEW_2026-07-17.md`. **אף קובץ-קוד לא נגע.**

## מצב-רקע שהביקורת חשפה (חשוב)
- **המחשב כבר מחומש-לגמרי לאמת עכשיו:** `.env` — `MEMS26_MODE=live` · `LIVE_TRADING_V1=1` · `LIVE_EXECUTION_V1=1` · **`LIVE_TRADING_ARMED=1`** (הודלק 14:11, OPS_LOG) · `SIERRA_LIVE_ACCOUNT=37138283` · `FIXED_CONTRACTS_4=1`. זה כבר לא "לפני-חימוש" — זה "מחומש, לאמת מה שנשאר לפני הפתיחה".
- **אינדקס:** קיים ועדכני — SYSTEM_INDEX + FLAG_INDEX מ-07-17, 117 קובצי _INDEX, 0 drift בעץ. מינורי: `gen_flag_index --check` מסמן ~4 דגלים לא-מתועדים ב-FLAG_REGISTRY (`TELEGRAM_BOT_TOKEN/CHAT_ID`, `V9_CHART_TZ`, `T0_TARGET_PTS`) — להשלים ל-registry.

---

## 🔴 קריטי — לבדוק לפני העסקה הראשונה (יכול לעלות כסף-אמת)

**C1 — כניסה-עירומה + הגלאי עיוור לזה (S-13, החשיפה #1).** כניסה+סטופ = ברקט-אחד מוצמד בסיירה; ה-DLL מדווח הצלחה על קבלת-ההורה בלבד (`sc_study/MES_AI_DataExport.cpp:1103-1122`), בלי לוודא שילד-הסטופ נעשה working. הגלאי סומך על האות-הלא-נכון: `reconcile.py:41-44` מכליל `"ORDER_SUBMITTED"` ב-`_STOP_OK_STATUSES` → כניסה-עירומה מסווגת `IN_POSITION_OK`; אמת-הקרקע `working_orders` (מ-`sierra_state.json`) לא-נקראת. תיקון=alert-בלבד, לעולם לא מציב-סטופ אוטומטית (`sierra_position_reconciler.py:79-83`). **בדיקה:** אחרי כל ירי — `cat ~/SierraChart_Data/v9_export/sierra_state.json | python3 -c "import json,sys;d=json.load(sys.stdin);print('qty',d['position_qty'],'working',d['working_orders'])"` — אם `|qty|>working` יש ברקט חלקי/עירום בזמן שהרקונסיילר אומר OK.

**C2 — `LIVE_TRADING_ARMED` לא-חוסם את הנתיב-האוטומטי (פירוק-שקר).** שער-ה-armed/is_sim קיים רק ב-endpoint-הידני (`trade_commands.py:75-96`) שהבוט לא-משתמש בו. הנתיב-האוטומטי כותב `op=PLACE` ישירות (`sierra_command.py:60`), ושעריו הם `LIVE_TRADING_V1` + `LIVE_EXECUTION_V1` + Sierra Input 22 — **לא** `LIVE_TRADING_ARMED`. משמעות: `LIVE_TRADING_ARMED=0` לא-יעצור ירי-אוטונומי; ואין בדיקת-is_sim בנתיב-האוטומטי → אם סיירה בטעות live+Input22, הבוט יורה על אמת. **בדיקה:** `grep -rn "LIVE_TRADING_ARMED\|is_sim" backend/v9/gateway/ backend/v9/services/sierra_command.py` (צפוי 0). **החלט עם cc-imac איזה דגל באמת עוצר מסחר תוך-יומי** (kill_switch / `LIVE_EXECUTION_V1=0`+restart / Input22-off).

**C3 — רקונסיילר לעולם לא מיישר יתום-אמת (S-9).** phantom-heal מרפא רק את ההיפוך (backend-מחזיק/סיירה-שטוח) וגם-אז רק סוגר-slot, בלי הוראת-סיירה. יתום-עירום (סיירה-מחזיק/backend-לא) → ענף מדווח-בלבד (`sierra_position_reconciler.py:246-256`), וה-streak ננעל 0/3 (`:233-238` reset על כל `sierra_qty!=0`). מאומת-חי ב-`ALERTS_LIVE.md:230`. **בדיקה:** ‏`sierra_state.json` טרי (<10ש') ומכיל `working_orders`; ערוץ-הפוש (Pushover/Telegram) באמת מגיע — כל רשת-הבטיחות של היתומים = "אדם רואה התראה".

**C4 — ירי-כפול (S-15).** אותו חשבון 37138283 על שתי המכונות, וה-MacBook כבר מחומש. **חובה לאמת ה-iMac=Sim+disarmed+flat לפני שה-MacBook יורה.** בדיוק-חיבור-DTC-אחד ל-37138283. (לא-נגיש מהסנדבוקס שלי — אישור מ-cc-imac/בעין.)

---

## 🟠 גבוה — לבדוק לפני הפתיחה

**H1 — מוות-פיד באמצע-פוזיציה משאיר פוזיציה-חיה בלי-ניהול.** feed_watchdog חוסם רק ירי-חדש (`trading_gateway.py:523-526`); ניהול-הסטופ/טרייל/EOD יושב ב-`bar_level_detector.on_bar` (בר-מונע) → אם הפיד מת, אין ברים → אין ניהול ואין EOD-flatten. הברקט-הסיירתי המוצמד הוא ההגנה היחידה — וזה בדיוק C1. **בדיקה:** לוודא שכל כניסה מציבה ברקט-סיירה-נייטיב (סטופ+יעד OCO) בעת-המילוי, בלתי-תלוי בלולאת-הברים.

**H2 — סטופ-עירום מזוהה ב-3 מקומות אך לעולם לא-אוטומטי.** `reconcile.py:113-117` (log-בלבד) · System6 `naked_stop`=ALERT-לא-AUTO (`system6_supervisor.py:131-134`) · הרגל-ה-"סיירה" השלישי ב-reconcile מתפוגג ל-None (`getattr(tm,'position',...)`) → הבדיקה בלולאת-הבר היא slot-מול-DB בלבד. **בדיקה:** בזמן פוזיציה-חיה — לחפש `naked_stop ALERT`/`NAKED_STOP_SUSPECT` ולוודא נוהל-אדם-בלולאה.

**H3 — CONFLUENCE_RI_ZLR מנותב ל-לייב, לא-shadow.** `.env` — גם `CONFLUENCE_RI_ZLR_V1=1` וגם `CONFLUENCE_RI_ZLR_LIVE=1` → `trading_gateway.py:1631-1637` מסיר את חסם-ה-shadow. המפרט אמר n=5, EV-גולמי שלילי-עד-אפס, "STANDING-OFF עד n≥15 shadow". כלומר תבנית לא-מאומתת יכולה להציב הוראות-אמת (2 חוזים, סטופ ≤7pt). **בדיקה:** לאשר מול פסיקת-מייקל 07-17 שאישרת ניתוב-אמת ל-CONFLUENCE (ולא רק shadow); אם לא — `CONFLUENCE_RI_ZLR_LIVE=0`.

---

## 🟡 בינוני — לאמת/ליישב לפני הפתיחה

**M1 — עצירת-הפסד: מספר + התנהגות.** `RISK_HALT_V1=1` חוסם באמת op=PLACE בכל-המצבים (`trading_gateway.py:1546-1565`) — **אבל** על pnl-ממומש בלבד (פוזיציה-פתוחה יורדת מתחת-לתקרה לא-עוצרת), והתקרה `RISK_DAILY_LOSS_CAP=400` בעוד הערות-.env אומרות −$450 (ברירות-קוד סותרות: 250/450). **בדיקה:** לאשר ש-−$400 ממומש הוא המספר הנכון ליום-1.

**M2 — EOD_FLATTEN_V1=1 תלוי בבר בסגירה.** רץ ב-`on_bar` ב-15:59 ET (`b2_eod_check.py:13`) — אם הפיד מת בסגירה, אין auto-flatten → פוזיציה-לילה. **בדיקה:** בר זורם ל-`v9_bars_5min_woodies` ב-~14:59 CT; לשמור את ה-EOD-flatten הסיירתי-העצמאי כגיבוי.

**M3 — `V9_CHART_TZ=America/Chicago` הוא פין למחשב-הזה.** הגשר מפרש כל ts דרך ה-TZ הזה (`base_stream.py:80,309-329`). אם צ'ארט-הסיירה כאן בעצם Eastern (או יוחלף) — כל בר זז שעה → סוג-יום/רמות/EOD שגויים. **בדיקה:** לאשר שצ'ארט-הסיירה במחשב-הזה הוא Central.

**M4 — 4 חוזים חיים בעוד הערות-.env אומרות 2/3.** `FIXED_CONTRACTS_4=1` גובר; `le=4` בסכמה תקין (אין le=3 חוסם). **בדיקה:** לאשר ש-4 חוזים מכוון ליום-1-לייב-מפוקח (הכפול של "2").

**M5 — override-סוג-יום נקי עכשיו, אבל harness-הסים כותב override מתוארך-היום ל-.env.** `sim_matrix_e2e.py:89-91` כתב היום `DAY_TYPE_MANUAL_OVERRIDE=<היום>:<תווית>` (אחרון=Neutral_Extreme), פג-רק ב-ET-roll. עכשיו ריק (טוב). **בדיקה בפתיחה:** `grep DAY_TYPE_MANUAL_OVERRIDE .env` — ריק או תאריך≠היום.

**M6 — LaunchAgents-מותקנים לא-נגישים+לא-בגיט.** ה-plist של bridge/backend מותקנים אבל לא ב-`scripts/launchagents/` → אין מול-מה-לדַיֵּף מול חובת-CLAUDE.md (KeepAlive-מותנה, `V9_DISABLE_WATCHDOG=1`, CLOUD_URL=localhost, נתיב-המחשב-הזה). frontend.plist ברפו מכוון ל-iMac (`/Users/michael/mems26/...`) לא ל-`~/Downloads/...`. **בדיקה:** `plutil -p ~/Library/LaunchAgents/com.mems26.bridge.plist` — KeepAlive/SuccessfulExit=false, watchdog-off, נתיב-נכון; `lsof -ti tcp:3000|wc -l`=1, `:8000`=1 (לא screen+LaunchAgent שניהם).

**M7 — מוקש-.env: TODO "חזרה ל-onrender".** `.env:3` `# TODO: Revert to https://mems26-web.onrender.com` מעל `CLOUD_URL=http://localhost:8000`. השומר יסרב-להתניע (טוב) אבל ההערה מזמינה שינוי-שגוי בקאטאובר. **בדיקה:** להשאיר localhost; להתעלם מה-TODO.

**M8 — API `action=EXIT` לא-מגודר.** `trade_commands.py:107-118` מחוץ לשער-ה-BUY/SELL → POST-EXIT ידני כותב op=EXIT לקובץ-הלייב. שבור-r=-1 (נכשל-בטוח) אבל כותב-לייב-לא-מגודר. **בדיקה:** לא-לשלוח EXIT ידני; יציאות רק OCO/MODIFY_STOP/FLATTEN_ACCOUNT.

---

## 🟢 אומת-נקי (בשורה טובה — לא-דורש פעולה)
- **op=EXIT:** אין caller-אוטומטי-חי; `STALL_EXIT`/`OPPOSITE_EXIT_V1` OFF (`.env` נעדרים). ✓
- **Sizing:** `le=4`, אין le=3 חוסם; סב-4 רק חיתוכי-סטופ-רחב מכוונים. ✓
- **feed_watchdog:** קורא את ה-SoT הנכון `v9_bars_5min_woodies`, חוסם-כניסה על-סטייל. ✓
- **System6 protective:** רק MODIFY_STOP + DROP_TARGET, לעולם לא op=EXIT (executor דוחה כל op-אחר). ⚠ FLAG_INDEX מציג אותו OFF בטעות — הקוד ON.
- **Bridge local-only:** שומר-הקוד תקין; אין CLOUD_URL-ענן פעיל בשום מקום.
- **שערים-כבויים-סטנדינג** (chop×2, S2_REQUIRE_COT_AMT, T1_LADDER_V2, DAYTYPE_POSITION_GATE...) — כולם OFF; לא-להחזיר בקאטאובר/ריסטארט.
- **DEMO_EXECUTION_ENABLED=1** מיותר אך לא-ירי-כפול (main.py רושם live-בלבד).

---
**סיכום-על:** החשיפה-הגדולה-לכסף-אמת = **C1+H2 יחד** (ברקט-נכשל/יתום → המערכת *מזהה ומתריעה* אך *לעולם לא מגינה-עצמית* → פוזיציה-עירומה עד שאדם מתערב) **+ C2** (פירוק-שקר). לפני-לייב, 3 האימותים בעלי-הערך-הגבוה: (א) ברקט-סיירה-נייטיב נצמד בכל כניסה, (ב) ערוץ-הפוש באמת מגיע, (ג) ה-iMac=Sim+disarmed+flat על 37138283.
