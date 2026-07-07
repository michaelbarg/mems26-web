# פערים פתוחים לפני LIVE — ל-Cowork (2026-07-07)

SIM proof ירוק (ORDER_SUBMITTED + Sierra sim fill @7578.50, קומיט 7d84325).
DLL מתוקן (error_text + account + SendOrdersToTradeService auto-match).
הבקאנד מטפל ב-ORDER_FAILED (cancel + release slot).

## מה חסר — לפי סדר עדיפות

### 1. Orphan detection — פוזיציה בסיארה בלי TM trade
כש-fill חוזר מסיארה ואין TM trade תואם (order_id לא ממופה + אין עסקה
demo/live פעילה) — ה-fill נזרק (`fill dropped`). זה קרה ב-SIM test ידני
(צפוי) אבל יכול לקרות גם ב-LIVE אם הבקאנד רסטרט באמצע עסקה.
**צריך:** fill שנזרק → התראה + ניסיון ליצור TM trade מהפיל, או לפחות
לוג WARNING ברמת CRITICAL שמיכאל רואה.

### 2. Auto-flatten — סגירה אוטומטית ב-22:15 IL / EOD
`EOD_RISK_WINDOW_V1=1` חוסם כניסות חדשות ב-45 דקות האחרונות אבל **לא
סוגר פוזיציות פתוחות**. מיכאל ביקש flatten ב-22:15 IL (= 14:15 CT
בקיץ). **צריך:** scheduled flatten שכותב CANCEL ל-trade_command.json +
מסמן TM trade כ-CLOSED(FLATTEN_EOD). הדגל קיים, הפעולה לא מחווטת.

### 3. Reconcile ל-LIVE (item-20)
מודול reconcile קיים (21ae344) אבל בודק רק demo/shadow. **צריך:** להוסיף
mode=live ל-reconcile pass + להריץ אותו בלולאה (כל 30 שניות?) כשיש
live_slot פעיל. מזהה: orphan / naked-stop / slot↔DB mismatch.

### 4. A7 fire_setup — אימות על ירי חי
התיקון בקוד (V2SizingResult.stop_price + risk_points fallback, קומיט
90567fb). עדיין לא אומת על ירי אוטומטי של ZLR בזמן RTH. **צריך:** לוודא
שב-RTH הבא ZLR/GHOST מגיעים ל-gateway (לא A7 FAIL). אם עדיין נכשל —
להוסיף לוג ספציפי של `best.stop` + `_effective_stop` ברגע הכשל.

### 5. fill dropped → יצירת TM trade
כרגע fill שלא ממופה ל-TM trade → `fill dropped`. ב-DEMO זה עובד כי I-58
fallback מוצא את ה-demo trade האחרון. ב-LIVE **צריך אותו fallback** — כי
אם הבקאנד רסטרט, ה-order_map נמחק, וה-fill של הפוזיציה החיה ייזרק.
**בדוק:** שה-I-58 fallback עובד גם ל-mode=live (הקוד מסנן
`demo/live/SIM`).

### 6. contracts=2 עם Sim Mode OFF
`FIXED_CONTRACTS_2=1` קיים בקוד ובenv. **צריך לוודא:** כשנעבור ל-Sim Mode
OFF (LIVE אמיתי), ה-trade_command.json מוציא contracts=2 (לא 3). בדוק
ב-`command_from_setup` שה-FIXED_CONTRACTS_2 עוקף את _3.

### 7. Frontend (:3000)
כבוי. צריך להעלות לפני מסחר כדי שמיכאל יראה דשבורד + יומן + פאנל-עסקה.

## מה עובד (SIM-proven)
- DLL: BuyEntry/SellEntry → ORDER_SUBMITTED + fill + error_text
- DLL: account field applied (o.TradeAccount)
- DLL: SendOrdersToTradeService auto-match Sim Mode
- DLL: CANCEL/FlattenAndCancelAllOrders → CANCEL_OK
- Backend: FillPoller._check_result() → ORDER_FAILED → CANCELLED + release slot
- Backend: P&L from Sierra fill price (not trade.stop)
- Backend: item-11 sizing consolidation (SIZING_CONSOLIDATION_V1)
- Gateway: _execute_live mirrors _execute_demo (LIVE_EXECUTION_V1)
