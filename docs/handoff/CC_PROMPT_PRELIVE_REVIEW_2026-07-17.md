# CC PROMPT — ביקורת פרה-לייב MacBook-cutover · אימות בלבד (2026-07-17)
**מאת cowork-dev · אל cc-imac (Sonnet). מייקל: ביקורת-בלבד — אל תבצע תיקונים בקוד ללא go-מפורש שלו (הכל risk-surface).**
המשימה שלך: **לאמת כל ממצא על המערכת-החיה, לדווח עם ראיה (חוק-5), ולהציע-תיקון בלי-להחיל.** ריפוט מלא: `PRELIVE_REVIEW_MACBOOK_2026-07-17.md`.

## הקשר
המסחר-החי עובר ל-MacBook (S-15), וה-.env שם כבר מחומש-לגמרי (`LIVE_TRADING_ARMED=1` מ-14:11 · `SIERRA_LIVE_ACCOUNT=37138283` · `FIXED_CONTRACTS_4=1` · `CONFLUENCE_RI_ZLR_LIVE=1`). ביקורת-קריאה של cowork (3 סוכנים) מצאה את הפריטים למטה. **אל תחליף קוד** — תאמת, תדווח, ותציע. שינוי-קוד רק אחרי פסיקת-מייקל פר-פריט.

## פרוטוקול-דיווח
לכל פריט → שורה ב-`OPS_LOG_2026-07-17.md` + רשומת-SYNC: `אומת/הופרך` + ראיה גולמית (פקודה+פלט) + `הצעת-תיקון (לא-הוחלה)`. סמן כל פריט KEEP / FIX-מוצע-ל-מייקל / RULING-נדרש. **אל תריץ ירי-לייב לצורך בדיקה — השתמש ב-sim/replay/state-files.**

## 🔴 קריטי — לאמת ראשון
**C1 — כניסה-עירומה + גלאי-עיוור (S-13).** אמת: `sed -n '37,120p' backend/v9/services/reconcile.py` — האם `"ORDER_SUBMITTED"` ב-`_STOP_OK_STATUSES` וה-`working_orders` לא-נקרא. הצעת-תיקון (אל-תחיל): הוסף בדיקת-`working_orders` מ-`sierra_state.json` הטרי כתנאי-אמת ל-`stop_ok` (במקום/בנוסף ל-status), והזרם דגל `naked_stop_suspect` כשה-`|qty|>working`. **אמת קודם על עסקת-סים** שהגלאי אכן מפספס היום.

**C2 — `LIVE_TRADING_ARMED` לא-חוסם נתיב-אוטומטי.** אמת: `grep -rn "LIVE_TRADING_ARMED\|is_sim" backend/v9/gateway/ backend/v9/services/sierra_command.py` (צפוי 0 בנתיב-האוטומטי). **פסיקת-מייקל נדרשת:** האם הנתיב-האוטומטי צריך לקרוא is_sim/armed לפני op=PLACE? ומהו דגל-העצירה-התוך-יומי הרשמי (kill_switch / `LIVE_EXECUTION_V1=0`+restart / Input22)? תעד את התשובה כ-runbook.

**C3 — יתום-אמת לא-מיושר (S-9).** אמת חי: `sierra_state.json` טרי (<10ש') ומכיל `working_orders`; grep `NAKED ORPHAN`/`streak 0/3` בלוג. אמת שערוץ-הפוש מגיע (שלח test-push). הצעה (אל-תחיל בלי go): `RECONCILER_AUTO_ADOPT_V1` — הצבת-סטופ-מגן אוטומטית ליתום, flag-OFF, sim-first.

**C4 — ירי-כפול (S-15).** **בצע עכשיו (בטוח, לא-קוד):** אשר ה-iMac ב-Sim-Mode+disarmed+flat על 37138283, והדבק `is_sim=1`+`qty=0` ל-SYNC. זה השער-0 לחימוש-ה-MacBook.

## 🟠 גבוה
**H1/H2 — פוזיציה-חיה בלי-ניהול במוות-פיד + סטופ-עירום לא-אוטומטי.** אמת: כל כניסה מציבה ברקט-סיירה-נייטיב (OCO סטופ+יעד) בעת-המילוי (בדוק `trade_result.json`/`PLACE_BRACKET_OK`). אמת שהרגל-ה-"סיירה" ב-reconcile מתפוגג ל-None (`getattr(tm,'position',...)`). דווח פער; הצעה גזורה מ-C1.

**H3 — CONFLUENCE_RI_ZLR ל-לייב.** אמת `.env`: `CONFLUENCE_RI_ZLR_LIVE=1`. **RULING:** אם מייקל לא-אישר ניתוב-אמת (רק shadow, n<15) → הצע `CONFLUENCE_RI_ZLR_LIVE=0`, אל-תחיל בלי go.

## 🟡 בינוני — לאמת/ליישב
- **M1** תקרת-הפסד: אשר `RISK_DAILY_LOSS_CAP=400` מכוון (מול הערת-450); הבהר ש-halt על pnl-ממומש-בלבד (פוזיציה-פתוחה-יורדת לא-עוצרת).
- **M2** EOD_FLATTEN תלוי-בר-בסגירה: אמת בר זורם ~14:59 CT; ודא EOD-סיירתי-עצמאי כגיבוי.
- **M3** `V9_CHART_TZ=America/Chicago`: אשר שצ'ארט-הסיירה במחשב-הזה באמת Central.
- **M4** 4-חוזים: אשר מכוון ליום-1-מפוקח.
- **M5** `grep DAY_TYPE_MANUAL_OVERRIDE .env` בפתיחה — ריק/תאריך≠היום (harness-הסים כותב אליו).
- **M6** `plutil -p` ל-bridge/backend/frontend plist: KeepAlive-מותנה, `V9_DISABLE_WATCHDOG=1`, CLOUD_URL=localhost, נתיב-`~/Downloads/...`, מופע-יחיד :8000/:3000. frontend.plist-ברפו מכוון-iMac — לתקן-נתיב (הצעה).
- **M7** `.env:3` TODO-onrender = מוקש; להשאיר localhost.
- **M8** לא-לשלוח `action=EXIT` ידני; יציאות רק OCO/MODIFY_STOP/FLATTEN_ACCOUNT.
- **אינדקס:** `gen_flag_index --check` מסמן ~4 דגלים לא-מתועדים (`TELEGRAM_*`,`V9_CHART_TZ`,`T0_TARGET_PTS`) — הוסף ל-`FLAG_REGISTRY.yaml` → regenerate.

## אומת-נקי (לא-לגעת)
op=EXIT אין-caller-חי · sizing le=4 תקין · feed_watchdog קורא woodies · System6 protective רק MODIFY_STOP · bridge local-only שומר תקין · שערים-כבויים-סטנדינג OFF. **אל-תחזיר/תדליק אף אחד מאלה.**

## גדרות
snapshot לפני כל שינוי out-of-git · אפס op=PLACE לצורך-בדיקה · שינוי risk-surface = flag-OFF + סים + פסיקת-מייקל · **בסבב-הזה: אימות+הצעה בלבד, בלי החלת-קוד.**
