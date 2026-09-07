# פקודה · 07.09 לילה — A: גרירה הדדית סטופ⇄יעד · B: [[T-251]] ספרים סוגרים על רגל חיה — **הכנה + סים בלבד**

**מאת:** cowork-dev (21:50 IL) · **אל:** cc-macbook · **מצב:** הכנה. **אפס שינוי בוצע** (קוד/DLL/.env/סיירה).
**חלון:** סים **אחרי 01:00 IL** (Globex נפתח 18:00 ET) · **מחר RTH מלא: אין ריסטארט 16:10–23:00, אין deploy-DLL בשעות-מסחר.**
**כללים:** Rule-5 (פלט גולמי) · snapshot לפני כל משטח-חוץ-git · `op=EXIT` שבור — לא לגעת · החשבון משותף עם אתי.

---

## 0 · TL;DR

| | ממצא | קובץ:שורה | תיקון | סטטוס |
|---|---|---|---|---|
| **A** | **הגרירה אינה באג-DLL — היא הגדרה גלובלית של סיירה:** `Global Settings ▸ General Trade Settings ▸ **Maintain Same Offset Between Target and Stop Attached Orders**`. סיירה מוסיפה לרגל-האחות את אותו Δ **0.57ms** אחרי כל `sc.ModifyOrder`, ומ-v2148 גם על `Server side bracket` (Teton). | יומן-ברוקר 04.09 (§1.1) · `cpp:3131-3249` | **רמה-0:** לכבות את ההגדרה (שני המופעים) + אימות-סים · **רמה-1 (DLL):** להסיר את לולאת-השחזור `:3202-3218` (מזיקה) + tripwire · **רמה-2 (בקאנד):** §4 כ-**מאמת** בלבד (לא משחזר) + שער-ביניים ל-`MODIFY_TARGET` | 🔴 ממתין לסים + פסיקת-מייקל (הגדרת-סיירה = משטח-חוץ-git) |
| **A-שורש** | השחזור ב-`:3211` משווה `to2.Price1` — **שדה שמתעדכן רק ב-`Cancel/Replace complete`, 351ms אחרי הבקשה**; הבדיקה רצה בתוך אותה קריאת-study (<1ms) ⇒ תמיד שווה ⇒ 0/3 שחזורים. בסים (13.07) האישור סינכרוני ⇒ השחזור **כן** רץ ⇒ פינג-פונג (באג-350). | `cpp:3202-3218` · `scstructures.h:1365,1387` | **אין** תיקון-שחזור אפשרי: תחת ההגדרה **המרווח סטופ–יעד אינווריאנטי** לכל רצף `ModifyOrder` (§1.4) | מוכח |
| **B** | `on_stop_hit` עובר ל-`CLOSED` **ללא תנאי** — כל `STOP` של כל קבוצה. `#1008`: c4 נעצר 18:35:42 ⇒ CLOSED בעוד Σledger=4/5 ⇒ c3 (10983/10984) חיה 32 דק' **מחוץ ל-`get_active_trades()`** ⇒ S6 לא סורק (0 `runner_reversal`), טלפון קיבל "נסגר +72.5", StuckSlot צעק לשווא. | `manager.py:1717-1723` · `fill_poller.py:1216-1225` | `Σ exit_fills.qty < contracts ⇒ PARTIAL` · עוגן-בעלות = ה-ids **שלנו** ב-`orders[]`, **לא** `position_qty` (אתי) | 🔴 בקאנד + טסט |

---

## 1 · A — שורש (ראיות גולמיות)

### 1.1 יומן-הברוקר `TradeActivityLog_2026-09-04_UTC.37138283.data` (פענוח TLV דרך `scripts/sierra_activity_join.py`; שדות: 104 טקסט · 105 id · 110 `Price1` · 111 `Price2`; זמנים UTC = IL−3)

`#1008` SHORT 5c @7717 (18:05 IL). קבוצות: c1 10977/10978 · c2 10980/10981 (2c) · c3 **10983/10984** · c4 —/10986 (stop-only). הורים: 10982 (c1-c3), 10985 (c4 = `sierra_order_id` בספרים).

```
15:31:01.506345  10978 StopLmt  p1=7723.50  Order modification failed — no longer working   (c1 יצא ב-T0)
15:31:01.507537  10981 StopLmt  p1=7723.50  Order modification failed — no longer working   (c2 יצא ב-T1)
15:31:01.507577  10984 StopLmt  p1=7723.50  Auto-trade order modification … Requested Price: 7716.75   ← BE (Δ −6.75)
15:31:01.508148  10983 Limit    p1=7706.00  Auto-trade order modification … Requested Price: 7699.25   ← 🔴 האחות, +0.57ms, אותו Δ. p1 עדיין 7706.00
15:31:01.508212  10986 StopLmt  p1=7723.50  Auto-trade order modification … Requested Price: 7716.75
15:31:01.859077  10983 Limit    p1=7699.25  Teton CME Routing (Cancel/Replace complete)               ← Price1 מתעדכן רק כאן, +351ms
15:31:04.498913  10983 Limit    p1=7699.25  Auto-trade … Requested Price: 7707.25   ← MODIFY_TARGET (TARGET_REALISM, +8.00 כי היעד כבר נגרר)
15:31:04.498998  10984 StopLmt  p1=7716.75  Auto-trade … Requested Price: 7724.75   ← 🔴 הסטופ נגרר +8.00, +0.085ms — BE נמחק
15:35:42         10986 filled  7716.75  ⇒ ספרים CLOSED (+72.5)          [B]
16:07:59         10984 filled  7724.75  ⇒ P0-2 → +32.5  ⇒ c3: 8.00pt × $5 = −$40 (המספר של המשימה)
```

אותה חתימה ב-**3/3** אירועי-BE של 04.09: `16:52:39` (#1069 LONG: 10995/10997 +5.5 ⇒ 10994 7739.25→**7744.75**) · `17:29:41` (#1073: 11006/11008 −6.5 ⇒ 11005 7715→**7708.5** — המספר של המשימה). **אפס** רשומות-שחזור בכל היום.

מקור-הפקודות בצד שלנו (`v9_trade_management_log` #1008): `18:30:58 SMART_BE 7723.5→7716.75` · `18:31:00 TARGET_REALISM t2 7706→7707.25` · `18:35:42 STOP_HIT` · `19:08:02 PNL_CORRECTION 72.5→32.5`.

### 1.2 למה השחזור `cpp:3202-3218` לא רץ — הכרעה בין 4 ההשערות

| # | השערה | קובץ:שורה | הכרעה |
|---|---|---|---|
| **H1 ✅** | **תזמון + שדה שגוי.** `ModifyOrder` מחזיר מיד; סיירה שולחת את גרירת-האחות **בתוך** אותה קריאה (0.57ms), אך `s_SCTradeOrder::Price1` (`scstructures.h:1365`, double) מתעדכן רק ב-`Cancel/Replace complete` (+351ms, Teton). `:3211 if (to2.Price1 != tgt_prices[ti])` רץ <1ms אחרי הלולאה ⇒ `7706.00 == 7706.00` ⇒ אין שחזור. | `cpp:3207-3211` | **מוכח** בזמני-היומן (§1.1). ובסים (13.07, STATUS_BOARD:692) האישור סינכרוני ⇒ השחזור **רץ** ⇒ סיירה גררה את הסטופים חזרה ⇒ "MODIFY_STOP_OK אבל שום מחיר לא השתנה". שני התצפיות = מנגנון אחד. |
| H2 ✗ | סלוטים 2/4/6/8 ריקים | `cpp:2985-2993` (נכתבים ב-PLACE) · `:3739-3763` (מתאפסים **רק** במימוש) | ב-#1008 סלוט-6 = 10983 היה תקף (לא מומש). ⚠️ נכון רק אחרי **טעינה-מחדש של ה-study** (Remote Build/re-add מאפס persistent) — סייג, לא השורש. |
| H3 ✗ | epsilon float/double | `:3174 float tgt_prices` מול `:3185 to.Price1` double | מחירי-MES (רבע-נקודה) מדויקים ב-float; אי-שוויון היה גורם **שחזור-שווא**, לא החמצה. |
| H4 ✗ | ה-DLL שולח שדות נוספים שמזיזים את האחות | `scstructures.h:1172-1173` `Price1/Price2 = DBL_MAX` (=לא-נגעו) · `cpp:3195-3197` | הפקודה מינימלית (`InternalOrderID`+`Price1`). האחות זזה **ע"י סיירה** — רשומת-היומן היא "Auto-trade order modification" עם `Requested Price` נפרד, לא בקשה שלנו. |

### 1.3 ההגדרה

`Global Settings ▸ General Trade Settings ▸ **Maintain Same Offset Between Target and Stop Attached Orders**` — לפי תיעוד-סיירה (GlobalTradeSettings): כש-Yes, התאמת יעד **או** סטופ מזיזה את שניהם לשמירת ההיסט; **מ-v2148 תקף גם ל-server-side bracket דרך Teton** (סיירה שלנו: **2929**; כל שורת-כניסה ביומן: `AOE=true | AOU=true | Server side bracket order`). ⚠️ שם-ההגדרה מהתיעוד ולא מהמסך — **לאמת במסך בסים** (Rule 2). `Sierra4.config` בינארי (`strings` ⇒ 0 התאמות) ⇒ אין `grep`; האימות היחיד = **חתימת-היומן** (§3).

### 1.4 למה שום "שחזור"/"מעקף" לא יכול לעבוד — ואיפה זה הופיע כבר

תחת ההגדרה, כל `ModifyOrder` על רגל מוסיף **אותו Δ לשתי הרגליים** ⇒ `target − stop` **אינווריאנטי** לכל רצף פקודות. אימות: c3 של #1008 נכנס עם 7706/7723.5 (מרווח 17.5) ויצא עם 7707.25/7724.75 (**17.5**). ⇒
- שחזור-DLL (`:3202-3218`) — פינג-פונג (13.07, מדוד).
- שחזור-בקאנד `STOP_MOVE_TARGET_RESTORE_V1` (`manager.py:361-408`) — גם אם יתוקנו `c{n}_target_price` (`:386`, 0/479) ו-`_ord.get("order_id")` (`:396` מול `cpp:2047` `"id"`), ה-`MODIFY_TARGET` המשחזר (`:403`) **יגרור את הסטופ חזרה מ-BE** — בדיוק אירוע 15:31:04. ⇒ **§4 כמשחזר = מסוכן; §4 כמאמת = נכון.** `CC_FIX_DEAD_2026-09-07 §3` מתעדכן בהתאם (הפוסטולט "שחזור ≤2ש'" בטל).
- לא קיים API-ACSIL "modify בלי אחות" (`sierrachart.h:2819` `ModifyOrder` בלבד; `SetAttachedOrders :3547` = קונפיג-חלון, לא פקודות חיות).

**⇒ התיקון היחיד לשורש הוא ההגדרה.** ה-DLL והבקאנד הופכים ל-**tripwire** (ההגדרה חוזרת ל-Yes אחרי עדכון/התקנה-מחדש של סיירה — אין לנו `grep` עליה).

---

## 2 · A — תיקון, שלוש רמות

### 2.1 רמה-0 · הגדרת-סיירה (התיקון האמיתי; **פסיקת-מייקל** — משטח-חוץ-git, משפיע גם על פקודות ידניות שלו מאותו מופע)

1. **גיבוי** (הסקריפט **לא** מכסה `Sierra4.config` — `mems26_snapshot.sh:40-52` = DLL/.env/LaunchAgents):
   `scripts/mems26_snapshot.sh "sierra-offset-link"` **וגם** `D=$(ls -td ~/mems26_snapshots/*offset-link* | head -1); cp -p ~/SierraChart/Sierra4.config $D/Sierra4.config.SierraChart; cp -p ~/SierraChart2/Sierra4.config $D/Sierra4.config.SierraChart2` (סיירה כותבת את הקובץ ביציאה — הגיבוי הוא של המצב-הישן, וזה מה שרוצים).
2. **סים:** `is_sim=1` ב-`sierra_state.json` (חובה לפני כל צעד; `debug_gateway_fire` מסרב אחרת — `trade_commands.py:281-289`).
3. **Baseline** (§3 שלב-2) — לתעד את חתימת-הגרירה **לפני** השינוי.
4. `Global Settings ▸ General Trade Settings` ⇒ `Maintain Same Offset Between Target and Stop Attached Orders` = **No** ⇒ OK. **בשני המופעים** (`~/SierraChart` 2929 = הסוחר; `~/SierraChart2` 2744). צילום-מסך ⇒ `docs/reports/`.
5. **הוכחה** (§3 שלבים 3-4) ⇒ רק אז נשאר ב-No גם ללייב (אותו מופע).
6. **רישום:** `docs/SYSTEM_MANIFEST.md` (משטח חדש: Sierra global setting) · `docs/runbooks/SIERRA_DLL_OPS.md` (אחרי כל Build/עדכון-סיירה: לאמת No) · שורת STATUS_BOARD.
**Rollback:** ההגדרה חזרה ל-Yes במסך, או `cp` של הגיבוי כש-סיירה **סגורה**.

### 2.2 רמה-1 · DLL — הסרת השחזור + tripwire (אחרי רמה-0, **לילה נפרד**, לא ב-RTH; deploy = פסיקת-מייקל + `mems26_snapshot.sh` + `build_monolithic_cpp.sh --deploy` + Remote Build + reload + **re-arm Input 21** לפי הרנבוק)

`sc_study/MES_AI_DataExport_merged.cpp` (md5 `99bfa242…` == פרוס ב-`~/SierraChart/ACS_Source`, 17.08). ה-DLL כבר שולח את המינימום (`:3195-3197`, `:3237-3239`) — אין מה "לצמצם". הפאץ' = **לא להילחם, לדווח**:

- **מחק** `:3202-3218` (לולאת-השחזור — הפינג-פונג של 13.07; מסוכנת אם ההגדרה תחזור).
- **שמור** את הצילום `:3170-3186`, אבל צלם **גם** `LastModifyPrice1` (`scstructures.h:1387`) ו-`OrderStatusCode`.
- **אחרי** לולאת-הסטופים `:3188-3200`: לכל יעד מצולם — `GetOrderByOrderID` ⇒ אם `LastModifyPrice1 != snap` **או** `OrderStatusCode == SCT_OSC_PENDINGMODIFY` (=6, `scconstants.h:1340`) ⇒ `sibling_drag++`; `sc.AddMessageToLog("MEMS26: MODSTOP tgt=%d p1=%.2f lmp1=%.2f snap=%.2f osc=%d", 1)` לפני ואחרי (זו גם ההכרעה של H1 בסים). `result_status = sibling_drag ? "MODIFY_STOP_SIBLING_DRAG" : "MODIFY_STOP_OK"` (`:3219`), ו-`order_err = mod_count` נשאר.
- **`MODIFY_TARGET` `:3227-3249`:** לפני `ModifyOrder` — `GetOrderByOrderID(tgt_oid, to)` ⇒ `sib = to.OCOSiblingInternalOrderID` (`scstructures.h:1398`; fallback: סלוט-הסטופ הזוגי `2+ti*2 → 3+ti*2`) ⇒ צילום `Price1/LastModifyPrice1` של הסטופ; אחרי — אותה בדיקה ⇒ `"MODIFY_TARGET_SIBLING_DRAG"`. **לעולם לא** counter-modify.
- **בלי** שינוי ב-`sierra_state.json` (`:2041-2050`) — אבל לדעת: `orders[]` **משמיט** `PENDINGMODIFY` (רק OPEN/PENDING_CHILD) ⇒ פקודה "נעלמת" לרגע אחרי כל modify (רלוונטי ל-§2.3ב).
- **בקאנד:** `fill_poller._check_result` (`:729-749`) — ענף חדש: `status.endswith("_SIBLING_DRAG")` ⇒ `logger.warning` + `ops_log("sierra","ERROR","SIBLING_DRAG …")` (tripwire בלוג-המסחר; לא פעולה).

### 2.3 רמה-2 · בקאנד (עוקף-DLL; ניתן לבנות **היום**, ריסטארט ≤15:30 מחר רק אם ירוק ב-15:00)

**(א) שער-ביניים ל-`MODIFY_TARGET` — עד שההגדרה מוכחת-כבויה.** הכיוון המסוכן הוא היעד⇒סטופ (מרחיק סטופ = מגדיל סיכון: −$40 ב-#1008, −$26 ב-#862). `manager._emit_modify_target` (`:410-429`): אם `SIERRA_OFFSET_LINK_OFF_VERIFIED != 1` ⇒ `_warn_emit_skipped(trade, "MODIFY_TARGET", "sierra offset-link not verified OFF (T-271)")` + `_log_management(… "MODIFY_TARGET_HELD")` + **return** (הספרים כן מתעדכנים — `apply_target_realism_perbar :1169` — כמו היום כשהאמיט מדולג). מכסה את **כל** הקוראים האוטומטיים: TARGET_REALISM `:1184` · STRUCT_TRAIL `:1623` (⚠️ שולח `MODIFY_STOP` **ואז** `MODIFY_TARGET` ברצף — תחת ההגדרה הסטופ נגרר פעמיים) · StructureExit `bar_level_detector.py:1776` · §4 `:403`. (הידני `trade_commands.py:179` **מת ממילא** — §5.3.) **דגל חדש ⇒ `RULED_FLAGS.yaml`** עם ההפניה לפסיקה שתינתן; `expected: "0"` עד הוכחת-סים, `"1"` אחריה. ה-BE (סטופ⇒יעד) **לא** נחסם — הוא מקטין סיכון גם עם גרירה.

**(ב) §4 `STOP_MOVE_TARGET_RESTORE_V1` — מ"משחזר" ל"מאמת":**
- `c{n}_target_price`: **לא** ב-`accept_setup` (שם אין ids). ה-ids נכתבים ב-`set_sierra_order_ids` (`manager.py:431-447`) מה-ENTRY ב-`fill_poller.py:1163-1178`. המחירים = פקודת-PLACE: `get_last_place_command(trade_id)` (`sierra_command.py:206`) ⇒ `target_price`→`c1`, `context.t2/t3/t4`→`c2/c3/c4` (`:1060-1069`). לכתוב שם, ו**לעדכן** ב-`_emit_modify_target` אחרי כתיבה מוצלחת (אחרת המאמת יצעק על ההזזות שלנו).
- `:396` ⇒ `_ord.get("id")` (`cpp:2047`).
- `:403` **החלפה:** במקום `_emit_modify_target` ⇒ `logger.warning("§4 TARGET_DRIFT …")` + `_log_management(… "SIERRA_TARGET_DRIFT", {leg, expected, actual})` + ops_log ERROR. **אין שחזור** (§1.4).
- `orders[]` בלי PENDINGMODIFY: יעד שלא נמצא ב-1.5ש' = **לא-ידוע** (Rule 1) ⇒ ניסיון שני ב-+3ש', ואז שקט (לא "drift").
- הדגל נשאר `0` עד סים; אחרי אימות — `1` כמאמת (RULED note מתעדכן).

**(ג) קטן:** `_emit_modify_stop :311-315` שולח גם ids של קבוצות שכבר יצאו ⇒ 2 רשומות `modification failed` בכל BE. לסנן לפי `exit_fills` (`_exit_fill_ledger :2113`). לא דחוף.

---

## 3 · A — נוהל-סים (אחרי 01:00 IL · `is_sim=1` · חשבון `Sim1`)

**כלים קיימים:** `scripts/sim_matrix_e2e.py` (`_require_sim :66` · `debug_gateway_fire :128-130` · `write_modify_stop :160-162`) · פענוח-יומן: `scripts/sierra_activity_join.py` (`read_records/_s/_i/_f/_ts`). יומן-הסים: `~/SierraChart/TradeActivityLogs/TradeActivityLog_<UTC-date>_UTC.Sim1.simulated.data`.

```bash
cd /Users/michael/Downloads/mems26_web_git && TOK=$(grep ^BRIDGE_TOKEN= .env | cut -d= -f2)
export MEMS26_SIGNALS_DIR=/Users/michael/SierraChart_Data/v9_export   # חובה ל-python3 -c … write_modify_*: בלעדיו הפקודה נכתבת ל-/tmp/mems26_signals (sierra_command.py:24-28) ונבלעת בשקט
SS=~/SierraChart_Data/v9_export/sierra_state.json
python3 -c "import json;d=json.load(open('$SS'));print('is_sim',d['is_sim'],'qty',d['position_qty'],'orders',d['orders'])"   # חייב is_sim=1, qty=0, orders=[]
# פענוח-יומן (להריץ אחרי כל שלב; מדפיס id/type/Price1/Price2/טקסט לחלון-הזמן)
cat > /tmp/sim_drag_decode.py <<'EOF'
import sys,datetime as dt; sys.path.insert(0,'scripts')
from sierra_activity_join import read_records,_s,_i,_f,_ts,F_TEXT,F_INTERNAL_ORDER_ID,F_ORDER_TYPE
from pathlib import Path
p=sorted(Path.home().glob('SierraChart/TradeActivityLogs/TradeActivityLog_*_UTC.Sim1.simulated.data'))[-1]
since=dt.datetime.now(dt.timezone.utc)-dt.timedelta(minutes=int(sys.argv[1]) if len(sys.argv)>1 else 10)
for r in read_records(p):
    ts=_ts(r); t=_s(r,F_TEXT) or ''
    if ts and ts>=since and ('odif' in t or 'Replace' in t or 'Filled' in t):
        print(ts.strftime('%H:%M:%S.%f'),_i(r,F_INTERNAL_ORDER_ID),(_s(r,F_ORDER_TYPE) or '')[:10],'p1=',_f(r,110),'p2=',_f(r,111),'|',t[:140])
EOF
```

| שלב | פעולה | מדידה (לפני/אחרי מ-`sierra_state.orders[]`: `id,type,price` — type 1=Limit 2=Stop 3=StopLimit) | קריטריון |
|---|---|---|---|
| 1 | **כניסה 5c ⇒ 4 קבוצות:** `curl -s -X POST -H "Authorization: Bearer $TOK" "http://127.0.0.1:8000/api/v9/trade/debug_gateway_fire?sizing=full&direction=SHORT&stop_pts=8&classification=SIM_DRAG&pattern=SIM_DRAG"` ⇒ `trade_id`. להמתין ≤24ש'. עוקף רק `session_gate_closed/eod_entry_cutoff` (`trade_commands.py:323-327`); אם `gateway_result.blocked_by` אחר (למשל `awaiting_release`) — **ל-A בלבד** אפשר `POST /api/v9/trade/command {"action":"SELL","contracts":5,"price":<mid>,"stop_price":<mid+8>,"target_price":<mid-8>,"context":{"t2":<mid-16>,"t3":<mid-24>,"t4":null}}` (אין שורת-TM ⇒ ids מ-`orders[]`; B נבדק אז רק בטסטים + לילה-הבא). | `position_qty=-5` · `orders` = 3 יעדים (type 1) + 4 סטופים (c4 stop-only), ל-`c{n}_*_id` מ-`SELECT quality FROM v9_trades WHERE id=<id>` | 7 פקודות, ids תואמים |
| 2 | **Baseline (DLL נוכחי, הגדרה כמו שהיא): `MODIFY_STOP`** — `python3 -c "from backend.v9.services.sierra_command import write_modify_stop as w; w(trade_id='<id>', order_id=<sierra_order_id>, new_stop=<stop±2.00>, stop_ids=[c1..c4 stop ids], mode='demo')"` ⇒ `sleep 5` ⇒ `orders[]` + `python3 /tmp/sim_drag_decode.py 3` + `trade_result.json` + Message Log של סיירה | **צפוי (הגדרה=Yes, סים סינכרוני): חתימת 13.07** — יעדים זזים ב-Δ, השחזור `:3202` מחזיר, הסטופים נגררים חזרה ⇒ `MODIFY_STOP_OK error=4` **ואף מחיר לא השתנה** (או, אם הסים אסינכרוני: יעדים נשארים מוזזים, סטופים ב-BE). **שני המצבים מאשרים את ההגדרה; רק הראשון מאשר H1-סים.** לתעד איזה. | חתימה מתועדת (פלט גולמי) |
| 3 | **רמה-0:** ההגדרה ⇒ **No** (§2.1 צעד 4) · `FLATTEN_ACCOUNT` דרך `POST /api/v9/trade/command {"action":"FLATTEN_ACCOUNT","trade_id":"<id>"}` · כניסה חדשה (שלב 1) · שוב `MODIFY_STOP` ל-BE (`new_stop = entry`) | לפני/אחרי לכל 7 הפקודות | ✅ **כל 4 הסטופים = new_stop** (Δ=−8, ואינם חוזרים תוך 10ש' — אין פינג-פונג) · ✅ **כל 3 היעדים \|Δ\|=0** (c3 הוא המבחן של המשימה) · ✅ ביומן: **אין** `Auto-trade order modification` על id-של-יעד בתוך ±1ש' מבקשת-הסטופ · ✅ `trade_result.status=MODIFY_STOP_OK` |
| 4 | **`MODIFY_TARGET`** על יעד-c3: `python3 -c "from backend.v9.services.sierra_command import write_modify_target as w; w(trade_id='<id>', order_id=<c3_target_id>, new_target=<t3 ∓ 2.00 לכיוון הכניסה>, mode='demo')"` ⇒ `sleep 5` | לפני/אחרי | ✅ **יעד-c3 = new_target** · ✅ **סטופ-c3 \|Δ\|=0** (וגם c4) · ✅ אין רשומת-modification על id-של-סטופ · `MODIFY_TARGET_OK` |
| 5 | **B-סים (§4.3, פסקה אחרונה) — רק אם הבקאנד החדש כבר רץ** (ריסטארט-לילה מותר: מחוץ ל-16:10-23:00; תנאי: טסטים ירוקים + `git status` נקי + cowork מאמת ≤15:00 את מה שיסחר מחר). אחרת: `FLATTEN_ACCOUNT` ⇒ `qty=0, orders=[]` ⇒ B-סים בלילה-הבא | ספרים: `state`, `exit_fills`, `v9_trade_management_log` | `is_sim=1` נשאר · הסים נקי |
| 6 | (רק אם רמה-1 נפרסה בלילה נפרד) חזרה על 3+4 עם ה-DLL החדש: Message Log מראה `MEMS26: MODSTOP …` לפני/אחרי · `trade_result` **בלי** `_SIBLING_DRAG` · ואז **הגדרה=Yes זמנית** ⇒ שלב 3 ⇒ חייב `MODIFY_STOP_SIBLING_DRAG` (tripwire מוכח) ⇒ **חזרה ל-No** | — | tripwire דו-כיווני |

**Rollback:** הגדרה ⇒ Yes / `cp` הגיבוי (סיירה סגורה) · DLL: `scripts/mems26_restore.sh <dir>` (dry-run) ⇒ `--confirm` ⇒ Remote Build ⇒ reload ⇒ re-arm Input 21. **בסיום: `is_sim=0`, `qty=0`, `orders=[]`** (משימה #13 קיימת: תזכורת 15:30) — לפני שער 16:10.

---

## 4 · B — [[T-251]] ספרים סוגרים על רגל חיה

### 4.1 שורש (מי סוגר, התנאי המדויק)

`fill_poller._process_fill` (`:1073`) ⇒ `kind=="STOP"` (`:1216-1225`) ⇒ `TradeManager.on_stop_hit` (`manager.py:1682`) ⇒ **`:1717 machine.transition(CLOSED)` · `:1718 state=CLOSED` · `:1720-1723 exit_ts/exit_price/exit_reason`** — **ללא כל תנאי** על כמות. ה-T-62 ledger (`_record_exit_fill :1710-1712`) רק **רושם** את הרגל; לוגיקת-המצב לא הפכה ledger-aware. נתיב-היעדים כן סופר (`_close_on_final_target :833`, L7 `:782/:791/:802/:813`) — נתיב-הסטופ לא. ואז `:1225 _notify_gateway_close(trade_id,"STOP")` **ללא תנאי** (בענף-היעדים `:1211-1214` הוא מותנה ב-CLOSED).

**מה זה עולה (מדוד, #1008):** (1) `get_active_trades` (`:1860-1880`, `_ACTIVE_TRADE_STATES :33-38`) משמיט CLOSED ⇒ `bar_level_detector.py:821/:293` לא סורק ⇒ **0 `runner_reversal`** 18:36-19:08 (OPS_LOG 04.09, ET 11:36-12:08) בעוד השורט הפוך והסטופ ב-7724.75; (2) `on_trade_close` (`trading_gateway.py:4115`) — T-43c `:4156-4185` **שמר** את הסלוט (נכון) אבל ספר `_daily_trades/_daily_pnl` + הודעת-טלפון "+72.5" מוקדם; (3) `reconcile.py:456-459` לא מוצא 1008 ⇒ `[StuckSlot] LIVE PATH BLOCKED` (אזעקת-שווא, 18:45:44); (4) P0-2 `update_closed_trade_pnl :2405` רושם את הרגל-המאוחרת עם `ts=trade.exit_ts` ⇒ ב-DB שני ה-STOP של #1008 נושאים `15:35:42` (10984 באמת 16:07:59) — ה-ledger משקר על הזמן. **מסקנת-04.09 "(א) בוטל — התנהגות-תקן" נופלת על (1):** "הספרים צודקים בסוף" ≠ "הרגל מפוקחת בזמן שהיא חיה".

### 4.2 תיקון (הסמכות = ה-ledger; העוגן = ה-ids שלנו)

**`manager.on_stop_hit`** — אחרי `:1712`:
```python
n = trade_contract_count(trade)                               # :66
filled = sum(int(f.get("qty") or 0) for f in self._exit_fill_ledger(trade))   # :2113
if fill_qty and filled < n:                                   # רגל אחת מתוך ladder; fill_qty=None ⇒ נתיב-legacy (צל/BarLevelDetector) ללא שינוי
    if machine.state == TradeState.PENDING: machine.transition(TradeState.FILLED)     # שורת-ENTRY שלא הגיעה (POSITION_TRUTH class); PENDING→PARTIAL אסור (state_machine.py:30)
    if machine.state != TradeState.PARTIAL: machine.transition(TradeState.PARTIAL)   # FILLED→PARTIAL מותר (state_machine.py:31)
    trade.state = TradeState.PARTIAL.value
    # לא exit_ts / exit_price / exit_reason / stop_hit_ts ⇒ _calculate_pnl נשאר realized_only (:2278)
    self._log_management(trade_id, "STOP_HIT_PARTIAL", {"ts":…, "order_id": order_id, "qty": fill_qty, "fill_price": fill_price, "remaining": n - filled})
    self._calculate_pnl(trade); self._db.flush()
    self._emitter.emit("stop_hit_partial", trade_id, {...}); return
```
**`fill_poller.py:1225`** ⇒ `_notify_gateway_close` **רק אם** `state == CLOSED` אחרי `on_stop_hit` (שיקוף `:1211-1214`).

**עוגן-בעלות (החשבון משותף — `position_qty`/`daily_total_qty_filled` הם ברמת-חשבון וכוללים את אתי ⇒ פסולים לייחוס):** הרגליים שלנו = `{c1..c4 _stop_id/_target_id} ∩ {o["id"] for o in sierra_state.orders[]}` (`cpp:2047`). סטופ עובד ⇒ החוזים של הקבוצה עדיין בשוק (סיירה מבטלת את האחות במימוש). כללי-סגירה:
- `Σledger == contracts` ⇒ **CLOSED** (בלי תלות ב-`position_qty` — אתי עלולה להחזיק).
- `Σledger < contracts` **ו**-ids שלנו עובדים ⇒ **PARTIAL** (S6 ממשיך).
- `Σledger < contracts` **ו**-ids שלנו **לא** ב-`orders[]` ב-**2 קריאות טריות רצופות** (PENDINGMODIFY נעלם לרגע — `cpp:2041`) **ו**-`position_qty==0` מעבר ל-grace ⇒ סגירה `SIERRA_FLAT` עם `exit_price`=הפילוי-האחרון-הידוע + `quality.ledger_incomplete=true` (Rule 1 — לא להמציא מחיר). מימוש: להרחיב `_sync_position_truth` (`fill_poller.py:251-253`, כיום PENDING/FILLED בלבד) ל-PARTIAL **רק** בתנאי-הבעלות.
- `Σledger < contracts`, ids שלנו נעלמו, `position_qty≠0` ⇒ **ALERT** (`naked_leg_suspect`) — לא לסגור, לא לגעת (יכול להיות אתי; יכול להיות רגל ערומה — MANUAL_POSITION_GUARD מכסה את השני).

### 4.3 טסט (חובה, התנהגותי + מוטציה)

`backend/v9/tests/test_t251_partial_stop_keeps_books_open.py`: עסקה live 5c (`quality.contracts=5, has_t0, c1..c4 ids`, entry 7717 SHORT, stop 7723.5; env `BE_AFTER_REAL_T1_V1=1` ל-remap `:694-702`) ⇒ `on_target_hit("T1", qty=1, order=10977, 7714)` (→T0) ⇒ `on_target_hit("T2", qty=2, order=10980, 7711.5)` (→T1) ⇒ **`on_stop_hit(fill_qty=1, order_id=10986, 7716.75)` ⇒ `state==PARTIAL`, `exit_ts is None`, Σ=4, `pnl_usd==71.25` (realized-only)** ⇒ `on_stop_hit(fill_qty=1, order_id=10984, 7724.75)` ⇒ `CLOSED`, `pnl_usd==32.5` (= ה-DB האמיתי של #1008 אחרי P0-2: 15+55+1.25−38.75). **מוטציה:** הסרת `filled < n` ⇒ הסטופ הראשון סוגר ⇒ נכשל. + טסט `fill_poller`: `_notify_gateway_close` **לא** נקרא אחרי הסטופ הראשון, **כן** אחרי השני. + טסט-4.2-שלישי: ids נעלמו ×2 + qty=0 ⇒ SIERRA_FLAT + `ledger_incomplete`. `legacy`: `fill_qty=None` ⇒ CLOSED כמו היום (צל לא משתנה).

**אימות-סים (שלב 5 ב-§3, אותה עסקה):** אחרי שלב 4 — `MODIFY_STOP` על **c4 בלבד** (`stop_ids=[c4_stop_id]`) למחיר שיפעיל אותו מיד (סים) ⇒ c4 נעצר, c3 חיה ⇒ `SELECT state FROM v9_trades` ⇒ **PARTIAL** · `/api/v9/system6/diagnose` מראה 1008-כמוהו כפעיל · לוג: `STOP_HIT_PARTIAL … remaining=1` ואין `[Gateway] LIVE trade closed` ⇒ `FLATTEN_ACCOUNT` ⇒ CLOSED (דרך fill-line של c3 או SIERRA_FLAT). **מוטציה חיה:** אין.

---

## 5 · סדר · זמנים · אסור

| מתי (IL) | מי | מה |
|---|---|---|
| **עכשיו → 01:00** | cc | קוד בלבד: **B** (§4.2 + §4.3) · §2.3(א)+(ב)+(tripwire בקאנד) · טסטים ירוקים · `--re` · **בלי** `flag_guard` על דגל שלא נרשם ב-`RULED_FLAGS`. ריסטארט-לילה (מותר; מחוץ ל-16:10-23:00) **רק** עם `git status` נקי + ירוק — הוא הקוד שיסחר מחר |
| **01:00 → 03:00** | cc (+מייקל להגדרה) | **§3 שלבים 1-4** על ה-DLL הפרוס (A לא תלוי בקוד-הבקאנד). שלב 3 = שינוי-הגדרה ⇒ **פסיקת-מייקל לפני** (הודעה עם §1.3+§1.4, ושתי השאלות: (1) לכבות בשני המופעים? (2) זה משפיע גם על גרירה ידנית שלו מהמופע). שלב 5 (B) רק אם הבקאנד החדש רץ |
| 03:00 | cc | דוח גולמי ל-`LIVE_CHANNEL` (פלט-שלבים, יומן מפוענח, צילום-מסך) · **`is_sim=0`** · TASK_LOG (§5.1) |
| ≤15:00 | cowork | אימות B + tripwire מול פלט גולמי (ומול הלוג של ריסטארט-הלילה אם היה) ⇒ **ריסטארט ≤15:30** אם עדיין נדרש וירוק; אחרת — הקוד הישן, ו-§2.3(א) לא נדלק (זה בסדר: בלי ההגדרה-Yes אין גרירה) |
| 16:10-23:00 | — | **אפס** ריסטארט/deploy/דגל |
| לילה 08→09.09 | cc | **רמה-1 (DLL)** אם מייקל פסק: snapshot ⇒ build ⇒ Remote Build ⇒ reload ⇒ re-arm ⇒ §3 שלב 6. **לא באותו לילה עם רמה-0** (משתנה אחד בכל פעם) |

### 5.1 שורות ל-`TASK_LOG.md` (cc מוסיף; אני לא נגעתי בקבצי-מעקב)
- `| T-271 | 🔴 גרירה הדדית סטופ⇄יעד = הגדרת-סיירה "Maintain Same Offset Between Target and Stop Attached Orders" (Teton ≥v2148). 19/14 ב-10 ימים; #1008 −$40 · #862 −$26 · $91/3. DLL-restore :3202 לא רץ (Price1 מתעדכן +351ms) · מרווח אינווריאנטי ⇒ אין שחזור בשום שכבה | 🔴 | cc | §3 סים אחרי 01:00 ⇒ הגדרה=No ⇒ tripwire |`
- `T-251` ⇒ **לפתוח מחדש**: "(א) בוטל" נופל על אובדן-פיקוח-S6 (0 runner_reversal/32 דק'); הצעד-הבא = §4.2+§4.3.
- STATUS_BOARD בסגירה: `ממצא → תיקון → ראיה` (פלט §3 + טסט).

### 5.2 אסור
- **לכתוב לוגיקת counter-modify** בשום שכבה (§1.4) · להדליק `STOP_MOVE_TARGET_RESTORE_V1` כמשחזר · לחווט `_exec` ל-`MODIFY_TARGET` (T-255 — פסיקה נפרדת).
- deploy-DLL / ריסטארט / דגל ב-16:10-23:00 · deploy-DLL ורמה-0 באותו לילה · שינוי-הגדרה בלי גיבוי `Sierra4.config` ובלי פסיקה.
- `op=EXIT` · לגעת בפוזיציה שאינה של הסים · `is_sim=0` בזמן סים · להשאיר `is_sim=1` אחרי 03:00.
- להסיק "עובד" מ-`MODIFY_STOP_OK` — `error=N` הוא מונה-ניסיונות (`:3220`), לא הוכחת-מחיר; ההוכחה היחידה = `orders[]` לפני/אחרי + יומן מפוענח.
- לדרוש `position_qty==0` כתנאי-CLOSED (אתי) · לייחס לפי `daily_total_qty_filled`.

### 5.3 ממצאי-אגב (מחוץ להיקף, לרישום בלבד)
- **`Adjust Attached Orders to Maintain Same Offset on Parent Fill`** (Yes ברירת-מחדל): ה-DLL שולח מחירים **מוחלטים**, וסיירה מבססת אותם מחדש על פילוי-ההורה — 07.09 14:55:55: יעד 7702.25→7702.00, סטופ 7711.50→7711.25 (`Modifying Attached Order from parent fill. Parent base price: 7708.00`). ⇒ כל הבראקט זז בהחלקת-הכניסה מול הספרים ⇒ מקור ל-`target_divergence`/T-227 ±1 טיק. פסיקה נפרדת.
- `sierra_order_id` בספרים = ההורה של **הקבוצה האחרונה** (10985); c1-c3 תחת 10982 — רלוונטי ל-join של T-256 (`Parent:` ביומן).
- **`POST /api/v9/trade/modify_target` (ידני, `trade_commands.py:232-238`) מת:** שולח `op=PLACE, action=MODIFY` — ל-DLL אין ענף `"MODIFY"` (רק `BUY/SELL/MODIFY_STOP/MODIFY_TARGET/…`, `cpp:2861-3666`) ⇒ `status=UNKNOWN`, ה-DB מתעדכן וסיירה לא. לתקן ל-`write_modify_target` **רק** אחרי T-271 (אחרת מדליקים עוד נתיב-גרירה).
- `sierra_state.high/low_during_pos` = `DBL_MAX` כשאין פוזיציה (`std::isfinite` מעביר) — JSON תקין, ערך זבל.

**NOT-DONE (בכוונה):** אפס קוד · אפס DLL · אפס .env · אפס סיירה · אפס TASK_LOG/STATUS_BOARD. ברירת-המחדל של ההגדרה בסיירה ושם-המסך המדויק — לאימות במסך (§1.3). סמנטיקת `LastModifyPrice1` ברגע-הבקשה — מוכרעת ע"י שורות-הלוג של §2.2 בסים.
