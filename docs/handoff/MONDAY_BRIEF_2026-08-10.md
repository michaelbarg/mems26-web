# בריף-בוקר יום שני · 2026-08-10 07:00 IDT

**סוכן:** cowork-dev (משימה מתוזמנת, דרך Desktop Commander על ה-MacBook — מכונת-המסחר)
**ענף:** `stabilize/mems26-local-truth-2026-05-16` @ `5fb15b9c`
**שינוי-תוכנית (מייקל 08-09 ערב):** ה-**MacBook עצמו סוחר לייב היום**; מעבר ל-Mac2 נדחה.

## ⚖️ פסק: **GO** — כל שערי-הפתיחה ירוקים

תנאי-החימוש של מייקל (מבחן-סיירה לתור-הפקודות) **מולא בלילה**. אין חוסם.
שני פריטי-מעקב לא-חוסמים למטה (§5).

---

## 1. מבחן-הלילה — ✅ PASS

`docs/reports/QUEUE_SIM_TEST_2026-08-10.md` · night-sim-agent · 01:20–01:25 IDT.

ה-drainer נבדק מול ה-DLL האמיתי בפתיחת Globex, **על חשבון-אמת אך באופן חסין-בהוכחה**
(`MODIFY_STOP` עם `stop_ids:[999999]` → ה-fallback לסלוטים לא רץ → `mod_count=0`).
לפני ואחרי: `position_qty=0, orders=[]` — ללא שינוי. שום הזמנה לא נשלחה.

- **בדיקה 1** — פקודה בודדת: queued → ה-DLL ביצע ו-ACK → ה-drainer מחק את קובץ-התור. **3.0 שניות.**
- **בדיקה 2** — *מקרה-הכשל של 08-07 עצמו* (שתי פקודות מהירות): A ב-fast-path, **B נשארה בתור
  וה-drainer לבדו העביר אותה** וקיבלה ACK נפרד. **שתיהן נוקו ב-5.0 שניות.**
  זו בדיוק התקלה שבה PLACE #652 + CANCEL ישבו בתור לנצח — **המחלקה סגורה מול ה-DLL האמיתי.**
- צד-בקאנד: 3× `[FillPoller] command queue: 1 command(s) completed`; **0** שורות `drain error` בכל הלוג.

**מה לא הוכח (בכוונה):** PLACE אמיתי, הצמדת-bracket, FLATTEN, ו-MODIFY_STOP שמזיז סטופ עובד.
**הובלת-הפקודות** ירוקה; סמנטיקת-ה-op לא שונתה.

---

## 2. בדיקות-קדם — כולן עברו

| בדיקה | תוצאה |
|---|---|
| `flag_guard.py` | ✅ **PASS — 157/157** דגלים תואמים |
| `mems26_verify.sh` | ✅ **verdict: OK · 0 warn** |
| שירותים | backend :8000 → 200 (0.003s) · bridge · export-promoter — כולם רצים |
| LaunchAgents | backend · bridge · export_promoter — כולם `running` |
| DLL ↔ ריפו | ✅ ה-DLL המותקן == המונוליט המקומיט · `sc_study/` נקי ב-git |
| אינדקסים | ✅ FLAG_INDEX עדכני · SYSTEM_INDEX קיים |
| פיד | ✅ `woodies_5min.json` בן 1.4s · `sierra_state.json` בן 0.4s |
| DB | ✅ `v9_bars_5min_woodies` (מקור-האמת) lag **00:00:36** |
| **תור-פקודות** | ✅ **`command_queue/` ריק** — 0 קבצים תקועים (רק `archived_stale/`) |
| frontend :3000 | ✅ 200 (0.31s) |
| עסקאות פתוחות | ✅ **0** — אין פוזיציה, אין אורפן |

### `sierra_state.json` (מופשט מ--inf)

```
position_qty = 0          orders = []            working_orders = 0
is_sim = 0                trade_account = 37138283
symbol = MESU26_FUT_CME   last_price = 7784.25
order_placement_armed = 1 send_orders_to_trade_service = 1
acct_ok=1  acct_trading_disabled=0  acct_under_margin=0  acct_loss_limit_reached=0
```

**⚠️ שים לב:** `is_sim=0` + `order_placement_armed=1` — **סיירה כבר מחומשת על חשבון-האמת.**
לא נגעתי (המשימה = בדיקות בלבד).

---

## 3. קונפיג-שני שנטען בתהליך הרץ — ✅ מאומת

התהליך: PID **58340**, `uvicorn backend.main:app`, עלה **Sun Aug 9 16:04:03**.
`.env` mtime = **2026-08-09 16:04:03** → **הריסטארט אחרי העריכה** ⇒ הקונפיג חי בתהליך.

שורת-האתחול (שיטת-האימות הפסוקה, לא `ps eww`):

```
[env_loader] applied 211 vars from .../.env | HFE_DISABLED=1 NONTREND_DISABLE_ALL=1
DIRECTION_LSMA_VETO=1 S1_NEW_CLASSIFIER=1 ZLR_SPEC_V2=1 VEGAS_SPEC_V2=1
DAYTYPE_POSITION_GATE=0 DAYTYPE_PLAYBOOK=1
INFO: Started server process [58340]
```

**211 vars — בדיוק כמצופה.** שלושת דגלי-שני ב-`.env` (ו-flag_guard מאשר אותם 157/157):

```
FIXED_CONTRACTS_4=1        T0_TARGET_PTS=3.0        S1_TREND_ELONGATION_V1=1
RISK_HALT_V1=1             SIZE_CAP_CUT_V1=1
```

### בדיקת-מרג'ין — ✅ עוברת

| | |
|---|---|
| שווי-חשבון (`acct_account_value`) | **$2,432.64** |
| כספים-פנויים | $2,432.64 · מרג'ין-מנוצל $0.00 |
| דרוש ל-4 חוזים | 4 × $276 ≈ **$1,104** |
| **עודף** | **$1,328.64** (יחס 2.2×) — ✅ עובר עם כרית |
| תקרת-הפסד-יומית של הברוקר | −$1,459.58 (`loss_limit_reached=0`) |
| `RISK_HALT_V1` שלנו | נעצר ב-−$450 — **קודם לתקרת-הברוקר**, כמתוכנן |

**הערה:** זהו מרג'ין-יום. 4 חוזים **לא מחזיקים בין-לילה** — מרג'ין-לילה של MES גבוה בהרבה
משווי-החשבון. סטופ-מלא ב-4 חוזים ≈ 10 נק' = $200, הרבה מתחת ל-halt.

---

## 4. קונפיג-המסחר של היום

**4 חוזים, סולם מוסט (`FIXED_CONTRACTS_4=1`, `T0_TARGET_PTS=3.0`):**

| חוזה | יעד | תפקיד |
|---|---|---|
| **C1** | **T0 = 3.0 נק'** | לקיחה-מהירה חדשה — מקבע רווח מוקדם |
| **C2** | T1 | (מה שהיה C1) |
| **C3** | T2 | (מה שהיה C2) |
| **C4** | T3 | ראנר |

`S1_TREND_ELONGATION_V1=1` — הודלק אחרי replay-GO (`d4892f91`).
פסק-מלאי אחרון: `SIZE_CAP_CUT_V1` גובר כלפי-מטה על 4 החוזים.

---

## 5. פריטי-מעקב (לא-חוסמים, לא-חדשים)

### א. Redis למטה — WS-fanout מושבת, ה-UI על polling

```
[WARNING] [ws_manager] Redis publish failed for v9:levels:
Error 61 connecting to localhost:6379. Connection refused.   ← כל ~60 שניות
```

אין LaunchAgent ל-Redis מקומי; ב-`.env` מוגדר Upstash (ענן) אך ה-publish מכוון ל-localhost.
**השפעה:** ה-WS לא מפזר → הפרונט נופל ל-polling (5s ל-price/system-state — רצפות-ה-polling
המאושרות). ה-UI חי (200 ב-0.31s). **לא חוסם מסחר** — מנוע-ההחלטות לא תלוי ב-Redis.
*(מחלקה מוכרת: 07-14 "Redis DOWN".)*

### ב. `TS-OFFSET-GATE` דוחה `bars/5min` — **השומר עובד כמתוכנן**

17,869 שורות ERROR בלוג (8,426 היום, 8,185 אתמול):

```
[bars/5min] TS-OFFSET-GATE REJECTED batch: newest bar ts 198425s behind now (> 900s)
while feed advances — live-but-mislabeled TS
```

- הטבלה הישנה `v9_bars_5min` **קפואה על 2026-08-07 23:30** (lag 2 ימים 7:32).
- **מקור-האמת `v9_bars_5min_woodies` טרי** (lag 00:00:36) — S1/S2/S4 קוראים ממנו.
- הצרכן היחיד שנפגע הוא `globex_range` ב-`/api/v9/key_levels`, והוא מחזיר **`null` ביושר**
  (Rule 1 — כישלון-כן > ערך-סינתטי). IB/POC/VAH/VAL/RTH מגיעים מ-**Sierra TPO Studies חיים**, לא מהטבלה.
- `atr_5min` היא **פונקציה טהורה** שמקבלת ברים כארגומנט (`five_min_system.py:1137`) —
  ה-docstring שמזכיר `v9_bars_5min` ישן, הקוד לא נוגע בטבלה. **אין ATR מנופח.**

**זו ההתנהגות המכוונת** (מחלקת ה-🔴 של `v9_bars_5min` מזוהם → ATR הועבר ל-woodies + שומר-קליטה).
**סיכון היחיד: רעש-לוג** — 8.4k ERROR/יום עלולים להסתיר שגיאה אמיתית. ראוי לנקות (הורדה ל-WARNING
עם rate-limit) אחרי-הלייב, לא היום.

### ג. פער-שדות ב-`sierra_state`

`daily_pnl = -831.25` בעוד `acct_daily_pl = 0.0`. ככל-הנראה שריד לא-מאופס משישי.
**לוודא ב-16:00** ששני השדות מתאפסים עם פתיחת-הסשן.

---

## 6. ✅ מה מייקל חייב לוודא ב-16:00

1. **סיירה פתוחה ומחוברת** לחשבון-האמת **37138283**, סימבול `MESU26_FUT_CME`.
2. `order_placement_armed = 1` + `send_orders_to_trade_service = 1` (**כרגע שניהם 1**).
3. `position_qty = 0` ו-`orders = []` **לפני** הפתיחה — פלאט-סטארט.
4. **שווי-החשבון עדיין ≥ $1,104** (כרגע $2,432.64) — 4 חוזים.
5. `daily_pnl` ו-`acct_daily_pl` **מתאפסים** לסשן החדש (§5ג).
6. `command_queue/` עדיין ריק (כרגע 0 קבצים).

---

## 7. 👀 רשימת-מעקב ליום

| # | מה לצפות | למה |
|---|---|---|
| 1 | **הירי הראשון ב-4 חוזים** | הפעם הראשונה ש-`FIXED_CONTRACTS_4` פוגש שוק חי — לוודא ש-qty=4 באמת יוצא, ושה-bracket נצמד לכל 4 |
| 2 | **התנהגות T0 (3.0 נק')** | יעד חדש לגמרי. לוודא ש-C1 נלקח מהר ושהסולם C2=T1/C3=T2/C4=T3 לא נדרס |
| 3 | **ה-drainer על MODIFY-ים** | הוכח על פקודה-אינרטית בלבד. היום הוא יפגוש **MODIFY_STOP אמיתי** (סטופ→BE אחרי T1). לחפש `[FillPoller] command queue: N command(s) completed` ו-**אפס** `drain error` |
| 4 | **שורות-צל S7/TSF מצטברות — יום 2 מתוך 3** | כרגע **2 שורות בכל טבלה**, אחרונה 08-07 19:35. סופ"ש = 0 חדשות (צפוי — נכתבות רק על אירוע-עסקה). היום צריך להוסיף שורות בכל ירי |
| 5 | `S1_TREND_ELONGATION_V1` | הודלק אחרי replay-GO אך **טרם ראה לייב** — לעקוב אחרי סיווג-היום |

**עסקה אחרונה:** #652 (live, S4, SHORT) — `CMD_NEVER_SENT_P0-1`, 08-07 19:35.
זו בדיוק התקלה שה-drainer סוגר. **#653 יהיה המבחן האמיתי.**

**שבוע אחרון (7 ימים):** live n=21 · **+$815.00** · shadow n=45 · +$2,348.75.

---

*נכתב אוטומטית ע"י cowork-dev · לא שונו דגלים · לא בוצע חימוש · בדיקות בלבד.*
