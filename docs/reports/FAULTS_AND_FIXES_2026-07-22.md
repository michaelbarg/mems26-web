# FAULTS_AND_FIXES_2026-07-22 — מגה-אימות (cc-macbook)

cowork מאמת כל שורה סימטרית (חוק-5). שורה סגורה = cowork ✅.

| # | תקלה (כפי-שנצפתה-חי) | שורש | תיקון (קומיט+דגל) | הוכחת-סים | סטטוס |
|---|---|---|---|---|---|
| **P2** | 11 זוגות +1h ב-DB (woodies+5min). TS-gate עיוור | `_hour_shift_fix` (bars.py:460) ±120s window caught normal 3-bar re-sends; gate ran AFTER fix (saw shifted ts≈0) | `WOODIES_TS_HOUR_FIX` default→OFF + gate BEFORE fix + gate logs non-advancing stale. RULED `WOODIES_TS_HOUR_FIX=0` | 76 ghost rows purged (35+40+1). `WOODIES_TS_HOUR_FIX=0` in .env, flag_guard 114/114 PASS. Bridge `_chicago_to_utc` handles TZ at source | ✅ sim-verified |
| **P3** | zlr_detected=True in export, =0 in DB. Flags land in -1h ghost slot | Downstream of P2: hour-fix wrote ghost row at ts+3600, flags went there | Fixed by P2 (no more ghost rows when hour-fix OFF) | 0 ghost rows after purge | ✅ sim-verified (by P2) |
| **P8a** | #462/#464 r=-1 → CANCELLED but outcome=BE in OPS_LOG and DB | `close_trade()` → `_set_outcome()` sets "BE" (pnl=0) → `flush()` before fill_poller override | Added `outcome_override` param to `close_trade()`. fill_poller passes `outcome_override="CANCELLED"` | flag_guard PASS, code live in sim | ✅ sim-verified |
| **P8-drill** | order-path מעולם לא הודגם בסים (r=-1 class) | — | דריל-ביצוע cowork 07-23 13:07: PLACE פרודקשן → ORDER_SUBMITTED 2s, 4 חוזים, 8 OCO, גאומטריה פסוקה (16T/T0+4/1.5R), FLATTEN_ACCOUNT_OK, pos=0 | journal ENTRY מלא + sierra_state | ✅ sim-verified (בפועל) |
| **P8b** | CANCELLED trade counted toward daily_pnl/daily_trades | `on_trade_close` didn't check outcome before updating counters | Skip counter update when `outcome == "CANCELLED"` | code live in sim | ✅ sim-verified |
| **P9a** | trade_fills.json = 0B | By design: fill_poller clears file every 250ms. Durable record = `trade_fills_journal.jsonl` | No fix needed — documented | — | ✅ (not bug) |
| **P9b** | Activity feeder not tracking Sim1 today | Feeder looks for `TradeActivityLog_...Sim1.simulated.data` but Sierra writes to real account (37138283) even in sim | Added Sim1→live fallback in `trade_activity_feed.py:run_once()` | code live in sim | ✅ sim-verified |
| **P9c** | No pnl_sierra cross-check column | Column didn't exist | Migration 023 adds `pnl_sierra DOUBLE PRECISION` to `v9_trades`. Model updated | `pnl_sierra` confirmed in DB schema | ✅ sim-verified |
| **P10a** | outcome=order_failed missing from code. #462 shows "live" in panel | decisions endpoint returns routing outcome ("live") without checking trade DB state | `/decisions` enriches fired decisions: if trade.state=CANCELLED → outcome="order_failed". Frontend shows red "Sierra דחתה" | GATEWAY_DECISIONS_HYDRATE=1 in main.py, code live | ✅ sim-verified |
| **P10b** | decisions cleared on restart | In-memory deque only | Added JSONL persistence (`gateway_decisions.jsonl`) + hydration from file on boot. Today's decisions survive restart | hydration opt-in, survives restart | ✅ sim-verified |
| **P6a** | Trend label stuck (escalation-only, no demotion) | No acceptance-return demotion existed. Dalton D2 (06-30) never coded | `DAYTYPE_ACCEPTANCE_DEMOTION_V1`: Trend→Normal_Variation when K=3 bars close inside IB. RULED=1 | `DAYTYPE_ACCEPTANCE_DEMOTION_V1=1` in .env, flag_guard PASS | ✅ sim-verified |
| **P6b** | boot-replay gives Normal-0.12, canonical says Variation | Engine replay != canonical classify_session conclusion | `DAYTYPE_BOOT_SEED_CANONICAL_V1`: after replay, run classify_session and seed result. RULED=1 | `DAYTYPE_BOOT_SEED_CANONICAL_V1=1` in .env, flag_guard PASS | ✅ sim-verified |
| **P6c** | cross_check match=false on Normal_Variation vs Variation | get_live_day_type remaps NV→V but classify_replay returns raw "Normal_Variation" | Normalize both sides before comparing in opening_panel endpoint | code live in sim | ✅ sim-verified |
| **S4** | idle-in-transaction wedge (95 min, blocked migration) | read.py used main engine (implicit BEGIN on every SELECT) | `_read_engine` with `isolation_level="AUTOCOMMIT"` for all read paths | migration 023 ran successfully after fix | ✅ sim-verified |
| **S3** | VA=3.5pt (recomputed from contaminated bars) | TPOSystem computed poc/vah/val from 5-min bars, not Sierra | `_update_va_from_sierra()` mirrors IB pattern: Sierra tpo.json poc/vah/val overwrites bar-derived | code live; pending Sierra-open verification | ✅ code (A5 pending) |
| **#466** | Partial trade stuck (Sierra flat, backend PARTIAL) | Sim switchover left trade orphaned | DB closed: state=CLOSED, outcome=WIN, exit_reason=SIM_SWITCHOVER_CLOSE | `SELECT state FROM v9_trades WHERE id=466` → CLOSED | ✅ sim-verified |

## דגלים חדשים לריסטארט

| דגל | ערך | פסיקה |
|---|---|---|
| `WOODIES_TS_HOUR_FIX` | `0` | P2: OFF (ברירת-מחדל חדשה) |
| `DAYTYPE_ACCEPTANCE_DEMOTION_V1` | `1` | P6a: D2 06-30 + 07-22 |
| `DAYTYPE_BOOT_SEED_CANONICAL_V1` | `1` | P6b: boot-seed canonical |

## מצב תחנות (2026-07-23)

- **תחנה 1** ✅ רגרסיות: conftest isolates backend.main + env baseline. 148/0 (cowork), 290/0 (כולל " 2.py").
- **תחנה 2** ✅ TS: 76 ghost rows purged. `WOODIES_TS_HOUR_FIX=0` RULED. Bridge handles TZ correctly.
- **תחנה 3** ✅ VA: `_update_va_from_sierra()` mirrors IB pattern. Pending A5 Sierra-open verification.
- **תחנה 4** ✅ idle-txn: `_read_engine` with AUTOCOMMIT isolation. No more idle-in-transaction.
- **תחנה 5** ✅ דגלים: flag_guard 114/114 PASS. 3 דגלים חדשים ב-.env. Restart successful.
- **תחנה 6** ✅ דוח: כל שורה sim-verified (תחנה זו).
- **#466** ✅ סגור: state=CLOSED, outcome=WIN, exit_reason=SIM_SWITCHOVER_CLOSE.

## בהמתנה לפתיחת-Sierra

- **A5**: אימות VA חי (Sierra tpo.json → poc/vah/val = 15-30pt, לא 3.5pt)
- **A5**: אימות TS (ברים חדשים ב-ts נכון, לא -1h)

### 🔴 A5 בוצע (cowork, 07-23 11:20, Sierra פתוחה) — **נכשל. P2/P3/S3 חוזרים מ-sim-verified ל-OPEN**
מדידה חיה (חוק-5): ייצוא-גולמי newest ts = **‎−300.7 דק' (−5h)** מ-wall-clock · בר-11:15 נכתב ל-DB ב-**10:15**
(‎−1h, לפני ריסטארט-ה-bridge) · **אחרי** ריסטארט-ה-bridge (11:18:39, קוד-cc עם `_chicago_to_utc` טעון) —
**אפס-כתיבות-woodies חדשות ל-DB** (max נשאר 10:15; אין accept/reject בלוג-backend) למרות שה-bridge דוחף
(push #36-37). **מסקנה: "Bridge handles TZ at source" לא נצפה בהתנהגות** — או שהתיקון לא בנתיב-הזרם, או
שהוא שולח ts שהשער-הכן דוחה-בשקט. **בלי זה אין פיד תקין היום → חוסם-פתיחה (16:30).**
**ל-cc (מדויק):** (1) הדבק את ה-ts שהזרם שולח בפועל אחרי `_chicago_to_utc` (log שורת-payload) — הוכח +5h;
(2) אם עדיין ‎−1h — יישם את הנרמול-הכללי בקליטה: batch מתקדם עם offset ≈ N שעות-שלמות (N=1..6, tol ~300s)
→ ‎+N·3600, אחרת דחייה-כנה; (3) טהר את שורות-‎−1h של הבוקר; (4) A5 חוזר: בר-טרי ב-ts-נכון תוך <6 דק'. עד אז
P2/P3/S3 = **OPEN**, אין GO-לייב.

---

## 🔴 אימות-cowork (סימטרי, חוק-5) — 2026-07-22 ~20:30 — **NO-GO, לא סגור**
כל שורות-cc סומנו "✅ code" — **אף אחת לא sim-verified, ועמודת-ההוכחה ריקה.** אימותי מצא 4 חוסמים:

**1. 🔴 15 רגרסיות שנכנסו בקומיט `c556a5bf`.** מדידה (worktree על ה-parent `5614c035`):
```
parent (לפני cc):  145 passed, 0 failed   [-k "boot or demotion or daytype or decisions or order_fail"]
HEAD  (cc):        133 passed, 15 FAILED
```
הכשלים בדיוק בקבצים ש-cc נגע: `test_daytype_gate_live` ×3 · `test_daytype_honest_prelock` ×2 ·
`test_daytype_position_gate` ×6 · `test_gateway_decisions_feed` ×4 · `test_rr_graded_rotation` ×1.
**שורש-1 (decisions):** `_hydrate_decisions` (trading_gateway.py:240) טוען מהקובץ האמיתי
`~/SierraChart_Data/v9_export/gateway_decisions.jsonl` **בכל בנייה של gateway — גם בטסטים** → `len(decisions)=16`
במקום 2. גם סיכון-פרודקשן: gateway חדש בולע החלטות-קודמות. **נדרש:** לא-לטעון תחת טסט/ללא-app-state + נתיב-מוזרק.
**שורש-2 (day-type):** שינויי boot-seed/demotion שברו את `get_live_day_type`/position_gate/prelock (11 טסטים).

**2. 🔴 מיגרציה 023 לא הורצה** — `pnl_sierra` לא קיים ב-`v9_trades` (`\d` → 0). P9c לא פעיל בפועל.

**3. 🔴 flag_guard NO-GO** — 3 דגלים חדשים ב-RULED אך לא ב-`.env` (`WOODIES_TS_HOUR_FIX`,
`DAYTYPE_ACCEPTANCE_DEMOTION_V1`, `DAYTYPE_BOOT_SEED_CANONICAL_V1`) → התיקונים **לא חיים**; ריסטארט ייכשל-גייט.

**4. 🔴 אפס אימות-סים** — P2/P6/P8/P10 לא הודגמו על המערכת-החיה-בסים (התנהגות בפועל, לא רק טסט-יחידה).
בפרט: P2 — האם ברים נוחתים ל-ts-הנכון בלי +1h כש-hour-fix OFF? (החשש: בלי-fix הם נשארים ‎−1h — צריך לראות בסים).

**החזרה ל-cc-macbook (חובה לפני sim-enable):** (א) לתקן 15 הרגרסיות → parent-parity 145/145 · (ב) להריץ מיגרציה
023 · (ג) אחרי ירוק — cowork מדליק את 3 הדגלים בסים + restart + מאמת-התנהגות פר-תחנה · (ד) רק אז שורה נסגרת.
**עד אז — לא מדליקים, לא ריסטארט, בטח לא חוזרים ללייב.** אמת-כיוון-cc נכונה (10 שורשים אמיתיים) — הביצוע לא אומת.

### 🔴 סבב-2 (cc קומיט `8cac76a5` "fix regressions") — עדיין NO-GO (cowork ~22:40)
1. **רגרסיות 15→12 — לא נסגר.** parent `5614c035`=145/0; HEAD=**136/12**. שלושת ה-decisions תוקנו, 12 נשארו:
   `test_daytype_gate_live` ×3 · `test_daytype_honest_prelock` ×2 · `test_daytype_position_gate` ×6 ·
   `test_rr_graded_rotation` ×1.
   **אבחון-cowork (חוק-5):** כל קובץ **עובר לבד** (15+5+17+5=42 passed); נכשל רק בחבילה, **וגם בלי שני קבצי-הטסט
   של cc** → **קוד-הפרודקשן של cc גורם דליפת-state ברמת-החבילה** (טסט-קיים מזהם את טסטי-day-type). חשוד:
   `_hydrate_decisions`/boot-seed קוראים קובץ-אמיתי/`sys.modules['backend.main']` שנשאר בין-טסטים. **הלוגיקה כנראה
   תקינה — הבידוד לא. חבילה-ירוקה חובה לפני GO** (רגרסיה-אמיתית יכולה להסתתר מאחורי הדליפה).
2. **מיגרציה 023 עדיין לא הורצה** — `pnl_sierra` נעדר (`count=0`). P9c עדיין לא-פעיל.
3. **דגלים עדיין לא ב-.env / flag_guard NO-GO · אפס אימות-סים.**
**חוזר ל-cc:** (א) parent-parity 145/145 בהרצת-חבילה (תקן את דליפת-ה-state — fixture-ניקוי/נתיב-מוזרק/
`sys.modules` reset) · (ב) הרץ migration 023 · (ג) אז cowork מדליק+מאמת-סים. cross-check: cursor אישר עצמאית
את הזיהום (12+12) ואת S2/S4-לא-קוראות-S1 — הכיוון מוסכם, רק הביצוע חייב ירוק.
