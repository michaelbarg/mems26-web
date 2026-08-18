# FRONTEND (scale-in) + INDEX — 2026-08-18

מכונה: mac-1 · HEAD `eb2cf400` · שעון: `Tue Aug 18 07:50:31 IDT 2026`
מצב: READ-ONLY. לא שונו דגלים, לא הופעל/הופסק שירות, לא נכתב ל-`~/SierraChart_Data`,
לא נגעתי בקוד backend/frontend. הקובץ הזה הוא הכתיבה היחידה.
הפוזיציה הפתוחה כרגע = מסחר ידני של מייקל — הוצאה מהדיון בכוונה.

---

# חלק א' — הפרונט-אנד לא סימן הגדלת חוזים

> מייקל, מילה במילה: *"בסוף היום סגרתי עסקה שזה בסדר, בפרונט אנד זה לא סומן הגדלת חוזים"*

## א.0 — הכרעה ראשונה: החיזוק **כן** קרה

```
$ grep -n "ScaleIn" /tmp/backend.err.log | tail -4
76736:2026-08-13 17:00:33 [WARNING] [ScaleIn] +2c LONG  parent=660 child=661 @7822.50 stop@7816.00 (BE)
82635:2026-08-13 17:45:56 [WARNING] [ScaleIn] +2c LONG  parent=661 child=662 @7830.25 stop@7822.50 (BE)
180870:2026-08-14 18:14:39 [WARNING] [ScaleIn] +2c SHORT parent=670 child=673 @7806.50 stop@7812.50 (BE)
405311:2026-08-17 22:32:05 [WARNING] [ScaleIn] +2c SHORT parent=699 child=708 @7769.75 stop@7776.25 (BE)
  — reinforce SHORT: T1 banked + 6.5pt past entry + with-trend (DOWN) → +2c, stop@parent-entry 7776.25
```

**אתמול 22:32:05 נורה חיזוק אחד: הורה 699 → ילד 708, +2 חוזים.** זו העסקה שמייקל סגר ידנית.

```
$ psql postgresql://localhost/mems26 -c "SELECT id,state,entry_ts,t1_hit_ts,exit_ts,
    quality->>'contracts' c, quality->>'scaled_in' scaled,
    quality->'metadata'->>'scale_in_parent' parent FROM v9_trades WHERE id IN (699,708);"
 id  | state  |           entry_ts            |       t1_hit_ts        |            exit_ts            | c | scaled | parent
-----+--------+-------------------------------+------------------------+-------------------------------+---+--------+--------
 699 | CLOSED | 2026-08-17 20:50:04.544551+03 | 2026-08-17 22:32:03+03 | 2026-08-17 23:06:03.659627+03 | 2 | true   |
 708 | CLOSED | 2026-08-17 22:32:09.85549+03  |                        | 2026-08-17 22:45:25.767608+03 | 2 |        | 699
```

- 699: ZLR SHORT, 2 חוזים, T1 נבנק ב-22:32:03 — **6 שניות** לפני החיזוק. `exit_reason=manual`, `pnl_usd=63.75`.
- 708: SCALE_IN SHORT, 2 חוזים, `metadata.scale_in_parent=699`, `exit_reason=SIERRA_FLAT`, `pnl=0`.
- בין 22:32 ל-22:45 **שתיהן היו פתוחות בו-זמנית** — 2+2 = **4 חוזים בחשבון**.

## א.1 — האם לפרונט הייתה דרך לדעת? כמעט. הוא איבד את זה בשלושה מקומות

### הפאנל: `SidePanel.tsx:34` → `ActiveTradeCard.tsx` → `GET /api/v9/trades/active` (poll 10s)

```
$ curl -s http://localhost:8000/api/v9/trades/active
null            # כרגע אין עסקה מנוהלת — הפוזיציה הידנית של מייקל אינה ב-TM
```

### 🔴 השורש — `/active` מחזיר **עסקה אחת**, והילד **מחליף** את ההורה

`backend/v9/api/v9/trades.py:311-319`:

```python
for _mode in ("live", "demo"):
    trade = (db.query(V9Trade)
             .filter(V9Trade.state.in_(_active_states), V9Trade.mode == _mode)
             .order_by(V9Trade.entry_ts.desc())
             .first())
```

`entry_ts DESC ... .first()` — ברגע שהילד 708 נכתב עם `entry_ts=22:32:09` (מאוחר מ-699 ב-20:50:04),
**הכרטיס עבר לילד**. מה מייקל ראה על המסך ב-22:32:

| | לפני 22:32 (הורה 699) | אחרי 22:32 (ילד 708) |
|---|---|---|
| כניסה | 7776.25 | **7769.75** |
| תבנית | `S4 · ZLR · ZLR` | **`S4 · SCALE_IN · SCALE_IN`** |
| סיכום | `1/2 hit` | **`0/2 hit`** |
| P&L | חיובי | **$0 (0.0R)** |

זו לא "הגדלה שלא סומנה" — זו **החלפה**. העסקה המנצחת נעלמה מהפאנל והוחלפה בעסקה
חדשה, קטנה יותר, בלי רווח. שום מקום במסך לא אמר "4 חוזים". הצ'יפ `SCALE_IN` הוא
העקבה היחידה, והוא **דרס** את `ZLR` במקום להתווסף אליו.

### 🔴 נקודת-נפילה 2 — payload ההורה לא נושא שום סימן שהוגדל

`backend/v9/services/trade_context.py:772-791` — dict ההחזרה של `extract_trade_display`:

```python
return {"pattern_id":…, "pattern_group":…, "trigger":…, "classification":…,
        "confidence":…, "firing_system":…, "pnl_usd":…, "pnl_r":…, "outcome":…,
        "exit_reason":…, "state":…, "day_type":…, "woodies_trend":…,
        "footprint_classification":…, "footprint_confluence":…,
        "blocked_by":…, "metadata": meta}
```

אין `scaled_in`. אין `scale_in_child_id`. אין מספר חוזים. `quality["scaled_in"]=true`
יושב ב-DB על 699 מ-22:32 ומעולם לא עזב את ה-DB.

### 🔴 נקודת-נפילה 3 — הקישור **כן** הגיע לדפדפן, והקומפוננטה זרקה אותו

`metadata` **כן** בתוך ה-spread, ולכן ה-payload של הילד נשא את הקישור. אומת חי:

```
$ curl -s "http://localhost:8000/api/v9/trades/recent?limit=3" | jq '.[0].metadata'
{
 "reason": "reinforce SHORT: T1 banked + 6.5pt past entry + with-trend (DOWN) → +2c, stop@parent-entry 7776.25",
 "stop_initial": 7776.25,
 "scale_in_parent": 699          ← הקישור הגיע לדפדפן
}
```

ונזרק כאן:

- **`frontend/v9/src/v9/lib/activeTrade.ts:38-57`** — הטיפוס `ActiveTrade` מונה 14 שדות
  (`trade_id … day_type`) ו**אינו מכיל `metadata`**. השדה קיים ב-JSON, לא קיים בטיפוס.
- **`frontend/v9/src/v9/components/sidepanel/ActiveTradeCard.tsx:203`** —
  `{trade.contracts.map(c => …)}` מרנדר רק רגלי C1/C2/C3, ו-`:287` מרנדר
  `trade.summary` = `"0/2 hit"`. אין רינדור של `metadata`, אין מונה-חוזים.

```
$ grep -rni "scale_in\|scaleIn\|scale-in" frontend/v9/src --include=*.ts --include=*.tsx
(אין התאמה אחת — 3 התאמות שווא של "autoscaleInfoProvider" בלבד)
```

**אפס אזכורים של scale-in בכל הפרונט-אנד.** גם `TradeDetailsModal.tsx` לא מרנדר `metadata`,
ולכן `scale_in_parent` נעלם גם בדיעבד.

### 🔴 נקודת-נפילה 4 (DB) — אין קישור קדימה הורה→ילד

`bar_level_detector.py:1196` כותב `scale_in_child_pending: True` **לפני** ה-PLACE, ו-`:1213`
מקבל `child_id = self._tm.accept_setup(...)` — **ולא כותב אותו חזרה להורה**:

```
$ grep -rn "scale_in_child_pending" --include=*.py . | grep -v test
backend/v9/services/trade_manager/bar_level_detector.py:1196:  q2["scale_in_child_pending"] = True
```

מקום אחד בלבד — נכתב ולעולם לא נוקה ולא הוחלף ב-`scale_in_child_id`. גם ב-DB אי-אפשר
לשאול "מי הילד של 699" בלי סריקה הפוכה של כל `metadata`.

### מה כן היה מראה 4 חוזים? כלום

`live_ledger` בנוי על fills לפי `entry_order_id`, לא מאחד הורה+ילד, ו-`backend_trade_id: null`:

```
$ curl -s "http://localhost:8000/api/v9/live_ledger" | head
{"enabled": true, "source": "trade_fills.json", "trades":[
  {"entry_order_id": 8510, "contracts": 3, "backend_trade_id": null, …
```

## א.2 — אם ייפול חיזוק היום, ה-UI יראה אותו?

**לא.** התשובה נבנתה מה-payload החי (`curl` למעלה), לא משמות קומפוננטות:

1. `/active` יעבור לילד באותה שנייה (`entry_ts DESC`) — הכרטיס יתאפס, לא יגדל.
2. `metadata.scale_in_parent` יגיע לדפדפן ויֵזרק ב-`activeTrade.ts` (לא בטיפוס) וב-
   `ActiveTradeCard.tsx` (לא מרונדר).
3. שום שדה בשום endpoint לא נושא "כמות חוזים בפוזיציה" כמספר — רק אורך מערך רגלי C1/C2/C3.

## א.3 — התיקון הקטן-והנכון (4 שינויים, אף אחד לא נוגע בנתיב-הכניסה)

| # | קובץ:שורה | שינוי |
|---|---|---|
| 1 | `bar_level_detector.py:1213` | אחרי `child_id = accept_setup(...)`, לכתוב להורה `q2["scale_in_child_id"] = child_id` + לנקות `scale_in_child_pending`, ואז commit. זה הקישור-קדימה שחסר גם ב-DB. |
| 2 | `trade_context.py:772-791` | להוסיף ל-dict של `extract_trade_display`: `"contracts": trade_contract_count(trade)`, `"scaled_in": bool(quality.get("scaled_in"))`, `"scale_in_child_id": quality.get("scale_in_child_id")`, `"scale_in_parent": meta.get("scale_in_parent")`. תצוגה בלבד — נקרא ע"י `/active`, `/recent` ו-`/trades` באותה נשימה. |
| 3 | `trades.py:311-319` (**הליבה**) | `/active` ימשיך להחזיר את ה**הורה** (הישן ב-`entry_ts`) כשלילד יש `scale_in_parent` המצביע על עסקה פתוחה, ויוסיף שדה מצטבר: `"position_contracts": parent_n + child_n` ו-`"scale_in": {"child_id":…, "added": n, "at": entry_ts, "child_stop": stop}`. הילד לא מחליף — הוא נספח. |
| 4 | `activeTrade.ts:38-57` + `ActiveTradeCard.tsx:110-143` | להוסיף לטיפוס `position_contracts?: number; scale_in?: {...}`, ולרנדר בכותרת ליד הכיוון: `▼ SHORT 7776.25 · 4c` ותג `+2c ⬆ חיזוק 22:32` (כמו תג ה-BE הקיים ב-`:275-286`). |

**שורה תחתונה של הדרישה** — "4 חוזים הפכו ל-6" ייראה **בזמן שהעסקה פתוחה** כי
`position_contracts` יושב בכותרת הכרטיס ומתעדכן ב-poll של 10 שניות, ותג `+2c ⬆` מסמן
את רגע החיזוק. היום המספר הזה לא קיים בשום payload.

**הערה על התקרה:** אחרי הידוק 08-17 הספירה היא מול **החשבון** (`_sierra_state_qty()`,
`bar_level_detector.py:1170-1186`) — ולכן `position_contracts` צריך להיות מוצג מאותו מקור
כדי שהמסך והשער יספרו את אותו דבר. `SCALE_IN_MAX_TOTAL=8` אינו מתועד ב-`FLAG_REGISTRY`
(ראה חלק ב' §2).

---

# חלק ב' — ארבעת האינדקסים, מצב נוכחי

לא חזרה על `INDEX_AUDIT_2026-08-17.md` — כל מספר נמדד מחדש היום (כלל 2).

| # | אינדקס | קומיט אחרון | ישן | מצב | הממצא החמור |
|---|---|---|---|---|---|
| 1 | `SYSTEM_INDEX.md` + 118 `_INDEX.md` | 2026-08-17 04:09 | 1 יום | 🟠 DRIFT | 3 קבצים מאתמול **חסרים לגמרי**; 120 קבצים בדריפט |
| 2 | `docs/FLAG_INDEX.md` | 2026-08-17 10:07 | 1 יום | 🟠 `--check` אדום | **19** דגלים לא-מתועדים (היו 22); 16 מהם מסחריים. 🔴 חדש: 3 דגלים חיים מסומנים "לא-בקוד" |
| 3 | `docs/SOURCE_OF_TRUTH.md` | 2026-07-02 08:51 | **47 יום** | 🔴 משקר | 2 endpoints שמסומנים "DEAD" מחזירים **HTTP 200 עם נתונים חיים** |
| 4 | `docs/SYSTEM_MANIFEST.md` | 2026-07-11 23:55 | **38 יום** | 🟠 חסר | 4 מתוך 9 LaunchAgents לא מתועדים; 3 plists ללא עותק בריפו |

## ב.1 — SYSTEM_INDEX + _INDEX.md

ל-`gen_index.py` **אין מצב dry-run** — `--help` הריץ את הגנרטור בשקט:
```
$ python3 scripts/gen_index.py --help
{"files": 963, "dirs_indexed": 118, "orphans": 43}
$ git diff --stat | tail -1
 120 files changed, 136 insertions(+), 133 deletions(-)
```
הדריפט שוחזר במלואו (`git checkout --`), עץ-העבודה נבדק ונקי — זהה בית-לבית למצב לפני.

ששת הקבצים שנשאלו:

| קובץ | באינדקס? | תיאור מדויק? |
|---|---|---|
| `backend/v9/services/exit_verifier.py` | ✅ | ✅ "T4 — books close only after Sierra proves the exit actually happened." (LOC מיושן 345→341) |
| `backend/v9/services/contract_size.py` | ✅ | ✅ "The one place that answers 'how many contracts did Michael rule for?'." (מונה-מייבאים 6→7) |
| `scripts/wire_guard.py` | 🔴 **חסר** | — |
| `scripts/task_log_guard.py` | 🔴 **חסר** | — |
| `scripts/week_replay.py` | 🔴 **חסר** | — |
| מיגרציה `023_pnl_sierra_column.py` | ✅ | ✅ "Migration 023: v9_trades pnl_sierra cross-check column (P9, 2026-07-22)." |

אף תיאור אינו שגוי — הפגם הוא **השמטה בלבד**. גם `bar_level_detector.py` צמח 180 שורות
מאז הריג'ן האחרון (1080→1260) — הפיגור הגדול ביותר בשורה בודדת.

## ב.2 — FLAG_INDEX

```
$ python3 scripts/gen_flag_index.py --check
UNDOCUMENTED behavior flags (add to docs/FLAG_REGISTRY.yaml):
  BAR5_FAILOVER_SECONDS · EXIT_VERIFY_MAX_ATTEMPTS · EXIT_VERIFY_TIMEOUT_S
  EXIT_VERIFY_UNKNOWN_MAX_S · EXIT_VERIFY_V1 · IB_BARS_VALIDATE_V1
  LEG_EXEMPT_LSMA_FLAT_V1 · MACHINE_TAG · OPENING_BIAS_BAR_CLOSE_REFRESH_V1
  OPENING_CONF_ENGINE_FUSE_V1 · OPENING_OR_ATR_SCALE_V1 · OR_NARROW_MAX_PTS
  RELEASE_LEG_EXEMPT_V1 · SCALE_IN_ADD_CONTRACTS · SCALE_IN_MAX_TOTAL
  SCALE_IN_MIN_PROFIT_PTS · STEP_ZZ_REV · TREND_LEG_CHASE_EXEMPT_V1
  TREND_STEP_ENTRY_V1
REAL_EXIT=1
```

**19, לא 22** (`FIXED_CONTRACTS_6`, `PUSHOVER_API_TOKEN`, `PUSHOVER_USER_KEY` נסגרו).
**16 מסחריים** (יציאה / כניסה / סייזינג): 4× `EXIT_VERIFY_*`, 3× `SCALE_IN_*`,
`TREND_STEP_ENTRY_V1`, `STEP_ZZ_REV`, `RELEASE_LEG_EXEMPT_V1`, `TREND_LEG_CHASE_EXEMPT_V1`,
`LEG_EXEMPT_LSMA_FLAT_V1`, `OPENING_CONF_ENGINE_FUSE_V1`, `OPENING_OR_ATR_SCALE_V1`,
`OR_NARROW_MAX_PTS`, `OPENING_BIAS_BAR_CLOSE_REFRESH_V1`. 2 נתוני-שלמות
(`IB_BARS_VALIDATE_V1`, `BAR5_FAILOVER_SECONDS`), 1 קוסמטי (`MACHINE_TAG`).

### 🔴 ממצא חדש (לא היה באודיט אתמול) — "5 דגלים לא-בקוד" שקרי ל-3 דגלים חיים

`FLAG_INDEX.md:14` מזהיר על 5 דגלים "dead or renamed?". שלושה מהם **חיים בקוד וב-.env**:
```
sierra_position_reconciler.py:839   RECONCILER_OWNERSHIP_AWARE_V1   .env=1
daytype_playbook.py:216             RESPONSIVE_WITH_DAY_TREND_V1    .env=1
risk_checks.py:35 (_env_int)        RISK_MAX_TRADES_DAY             .env=999
```
שורש: `gen_flag_index.py:106-107` דורש שהשם יהיה **באותה שורה** עם `getenv(` — שני הראשונים
עוטפים את הקריאה לשתי שורות, והשלישי עובר דרך העוזר `_env_int`. רק שני
`NEWS_BLACKOUT_{BEFORE,AFTER}_MIN` באמת מתים (docstring בלבד).

בדיקה נגדית: `python3 scripts/flag_guard.py → FLAG-GUARD: PASS — all 175 ruled flags match.`
שני מרשמים על אותם דגלים, אחד ירוק ואחד אדום. הבוט-ליין מאשר ש-.env=חי
(backend עלה `Mon Aug 17 10:06:49`, `.env` נכתב `Aug 17 10:06:15`).

עדיין פתוח: `FLAG_INDEX.md:362` מדפיס `NTFY_TOPIC` בערכו המילולי בקובץ git-tracked
(ערוץ push לא-מאומת לטלפון של מייקל).

## ב.3 — SOURCE_OF_TRUTH (47 יום; הכותרת שלו מצהירה 55)

```
$ psql … -c "SELECT 'woodies',max(ts) FROM v9_bars_5min_woodies UNION ALL …"
 v9_bars_5min_woodies    | 2026-08-18 07:50:00+03 | 83 היום
 v9_bars_5min_continuous | 2026-08-18 07:45:00+03 | 28 היום
 v9_bars_5min            | 2026-08-17 23:55:00+03 |  0 היום
 v9_five_min_setups      | 2026-08-17 22:30:00+03 |  0 היום
 v9_trades               | entry 2026-08-17 22:32 | 614 שורות
 v9_trade_management_log | 2026-08-17 22:35       | 58,495
 v9_day_type_state       | 2026-08-18 04:05:34    | 27
 v9_tpo_sessions (CASH)  | 2026-08-17             |  0 היום
```
**אף מקור שהמסמך מכריז כקנוני לא נותר ימים בלי שורה.** כל האפסים הם קריאת פרה-מרקט
ביום ג' 07:53 מול סגירת יום ב' 23:xx.

ארבעה כשלים אמיתיים:
1. 🔴 `/api/v9/day_type/v9/current` ו-`/api/v9/day_type/current` מסומנים
   **"DEAD — returns None"**. שניהם מחזירים **HTTP 200** עם סיווג מלא
   (`Trend_DD`, `probability 0.62`, `stage C3`, `OPEN_REJECTION_REVERSE`).
2. 🟠 `v9_bars_5min_continuous`: המסמך מנמק 🔴 AVOID ב-"3 שורות פגומות נמחקו".
   מדידה: `total=8145, garbage=929, min(close)=1, max=19413`. **929 עדיין שם, לא נמחקו.**
   הפסק נכון, הנימוק קורס — וזה מסוכן יותר מהיעדר נימוק.
3. 🟠 `v9_bars_5min` חלוני (08-13/14 מ-13:30, 08-17 מ-16:30; 78/81/90 שורות) — ההוראה
   "בדוק שהבר האחרון עדכני" מייצרת 🔴 שווא כל בוקר.
4. 🔴 חסרים לגמרי (0 אזכורים): `sierra_state.json` (**אמת-הפוזיציה**, טרי 43 שניות),
   `trade_activity_events.jsonl`, `trade_result.json`, `v9_exit_decisions` (5,900 שורות, חי).
   בנוסף `v9_bars_30min_woodies` מת מ-`2026-07-02` (47 יום) — הטבלה היחידה שבאמת מתה.

## ב.4 — SYSTEM_MANIFEST (38 יום)

```
$ ls ~/Library/LaunchAgents/ | grep mems   →  9 plists
$ launchctl list | grep mems               →  6 טעונים
```
**חסרים מהמניפסט (4 מתוך 9):**
`com.mems26.eod_handoff.plist` · `com.mems26.mobile_relay.plist` (נתיב התרעות-הטלפון) ·
`com.mems26.startup_check.plist` · `com.mems26.update_check.plist`

עובדות נוספות שהמניפסט לא נושא:
- 3 סוכנים טעונים ויוצאים בקוד **126** (`update_check`, `eod_handoff`, `startup_check`).
- 3 לא טעונים כלל: `activity_feed`, `export_promoter`, `mobile_relay`.
- **עותקי-הריפו מפוצלים לשתי תיקיות** — המניפסט מפנה רק ל-`scripts/launchagents/`.
  `eod_handoff` ו-`mobile_relay` יושבים ב-`launchagents/` בשורש (לא מתועד), ואילו
  `backend`, `bridge`, `startup_check` **אינם בשום תיקייה בריפו** —
  ו-`com.mems26.backend.plist` הוא בדיוק הקובץ שסעיף LaunchAgent-Stability ב-CLAUDE.md שולט בו.
- `~/SierraChart2/Data/MES_AI_DataExport_64.dll` **לא קיים**; זה שכן קיים מתוארך
  `Jul 28 12:59` מול מקור `Aug 17 04:07` — **הבינארי שסיירה מריצה מפגר 20 יום אחרי המקור**,
  ו-`mems26_verify.sh` משווה `.cpp` ל-`.cpp` בלבד ולכן מדווח ✅.
- `mems26_verify.sh` מדווח `🔴 export promoter NOT running` על מערכת שהפיד שלה טרי 3 שניות —
  אזעקת-שווא קבועה שמאמנת סוכנים לזלזל בבודק. §4 "אין דריפט באינדקס" בודק רק
  `[ -f SYSTEM_INDEX.md ]` ולכן 3 הקבצים החסרים מ-ב.1 בלתי-נראים לו מבנית.
- חסרים מטבלת §1: `config/RULED_FLAGS.yaml`, `scripts/flag_guard.py`,
  `docs/handoff/LIVE_CHANNEL.md`, `docs/FLAG_REGISTRY.yaml`, ו-`docs/plans/TASK_LOG.md` —
  האחרון הוא הקובץ ש-CLAUDE.md מכנה מאתמול *"מקור-האמת היחיד"*.

---

## מה סוכן יטעה בו מחר אם יסמוך על האינדקס כמו שהוא

1. **`FLAG_INDEX.md` → ימחק שלושה דגלים חיים.** הוא פותח את הקובץ, קורא בשורה 14
   *"5 registry flag(s) not referenced in code (dead or renamed?)"*, ועושה את הניקיון שהשורה
   מזמינה. הסרת `RECONCILER_OWNERSHIP_AWARE_V1=1` מחזירה את המצב שבו כל פוזיציה שאינה
   ב-TradeManager מוכרזת **אורפן-עירום** — המחלקה שהפיקה את תקריות 07-10/14/17/20/23.
   הסרת `RESPONSIVE_WITH_DAY_TREND_V1=1` מחזירה את הירי הנגד-מגמתי שמייקל הרג ב-07-23.
   **זה הממצא החמור ביותר היום, והוא חדש.**
2. **`FLAG_INDEX.md` → יכוון סייזינג מול סמנטיקה ריקה.** `SCALE_IN_MAX_TOTAL=8` הוא תקרת-החוזים
   הקשה. מול `FIXED_CONTRACTS_4=1` וממצא 08-16 ("6 חוזים חסום פיזית — ACSIL נותן 5 קבוצות-OCO"),
   סוכן שקורא `8` מהקוד בלי הערה יסייז בדיוק אל הקיר שמייקל כבר נחבט בו.
3. **`SOURCE_OF_TRUTH.md` → יחווט endpoint "מת" שמחזיר תשובה חיה.** סוכן שמדבג פער בסוג-יום
   פותח את המפה, מדלג על שני ה-endpoints שמסומנים 🔴 DEAD — או פוגע באחד, רואה `Trend_DD`
   סביר, ומחווט אותו — ומשחזר את הפסד שני-המסווגים של 06-29, בעזרת המפה שנכתבה למנוע אותו.
4. **`SOURCE_OF_TRUTH.md` → יכריז על פיד-הברים כמת ב-07:00.** `v9_bars_5min` יראה 0 שורות
   היום; ההוראה המילולית "בדוק שהבר האחרון עדכני" תחזיר 🔴 על מערכת בריאה, והוא "יתקן" ingest תקין.
5. **`SOURCE_OF_TRUTH.md` → לעולם לא ילמד ש-`sierra_state.json` הוא אמת-הפוזיציה.** נשאל
   "האם הפוזיציה באמת שטוחה?", ימצא במפה רק `v9_trades`, ויענה מהספרים — בדיוק כשל
   T4/#682 (נסגר בספרים 20:00:07 בעוד סיירה החזיקה SHORT 4 עוד 62 דקות).
6. **`SYSTEM_INDEX.md` → לא יידע ש-`wire_guard.py` קיים.** נשאל "יש משהו שבודק שנקודת-הקריאה
   החדשה שלי באמת ניתנת לקריאה?", יגרפ באינדקס, לא ימצא, ויכתוב בודק חדש — או ידלג. הקובץ
   קיים בדיוק כי שלוש נקודות-קריאה בייצור העבירו `trade_id` שגוי וכל פקודה נכשלה בשקט בכסף אמיתי.
7. **`SYSTEM_MANIFEST.md` → יחפש plist בתיקייה הלא-נכונה לפני שינוי.** יפתח
   `scripts/launchagents/` כפי שהמניפסט מורה, ולא ימצא את `com.mems26.backend.plist`
   (וגם לא `bridge`, גם לא `startup_check`) — הם אינם בשום תיקיית ריפו. הוא גם לא יידע
   ש-`mobile_relay` — נתיב-ההתרעות שכבר נכשל בשקט ב-08-12 ועלה כסף — **אינו טעון כרגע**.
8. **`SYSTEM_MANIFEST.md` → יאמין שה-DLL הפרוס עדכני.** `mems26_verify.sh` מדפיס
   ✅ כי הוא משווה מקור למקור; הבינארי מפגר 20 יום.

---

### קבצים שנגעתי בהם
רק הקובץ הזה. `gen_index.py` הורץ (אין dry-run) ושוחזר במלואו ב-`git checkout --`;
`gen_flag_index.py --check`, `flag_guard.py`, `mems26_verify.sh` הם קריאה-בלבד.
לא שונו דגלים, לא הופעל מחדש שירות, `~/SierraChart_Data` לא נגעתי.
