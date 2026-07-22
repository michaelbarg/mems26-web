# FAULTS_AND_FIXES_2026-07-22 — מגה-אימות (cc-macbook)

cowork מאמת כל שורה סימטרית (חוק-5). שורה סגורה = cowork ✅.

| # | תקלה (כפי-שנצפתה-חי) | שורש | תיקון (קומיט+דגל) | הוכחת-סים | סטטוס |
|---|---|---|---|---|---|
| **P2** | 11 זוגות +1h ב-DB (woodies+5min). TS-gate עיוור | `_hour_shift_fix` (bars.py:460) ±120s window caught normal 3-bar re-sends; gate ran AFTER fix (saw shifted ts≈0) | `WOODIES_TS_HOUR_FIX` default→OFF + gate BEFORE fix + gate logs non-advancing stale. RULED `WOODIES_TS_HOUR_FIX=0` | `test_ts_offset_ingest_gate.py` 8/8 green (2 new: default-off, explicit-on) | ✅ code |
| **P3** | zlr_detected=True in export, =0 in DB. Flags land in -1h ghost slot | Downstream of P2: hour-fix wrote ghost row at ts+3600, flags went there | Fixed by P2 (no more ghost rows when hour-fix OFF) | — | ✅ (by P2) |
| **P8a** | #462/#464 r=-1 → CANCELLED but outcome=BE in OPS_LOG and DB | `close_trade()` → `_set_outcome()` sets "BE" (pnl=0) → `flush()` before fill_poller override | Added `outcome_override` param to `close_trade()`. fill_poller passes `outcome_override="CANCELLED"` | — | ✅ code |
| **P8b** | CANCELLED trade counted toward daily_pnl/daily_trades | `on_trade_close` didn't check outcome before updating counters | Skip counter update when `outcome == "CANCELLED"` | — | ✅ code |
| **P9a** | trade_fills.json = 0B | By design: fill_poller clears file every 250ms. Durable record = `trade_fills_journal.jsonl` | No fix needed — documented | — | ✅ (not bug) |
| **P9b** | Activity feeder not tracking Sim1 today | Feeder looks for `TradeActivityLog_...Sim1.simulated.data` but Sierra writes to real account (37138283) even in sim | Added Sim1→live fallback in `trade_activity_feed.py:run_once()` | — | ✅ code |
| **P9c** | No pnl_sierra cross-check column | Column didn't exist | Migration 023 adds `pnl_sierra DOUBLE PRECISION` to `v9_trades`. Model updated | — | ✅ code |
| **P10a** | outcome=order_failed missing from code. #462 shows "live" in panel | decisions endpoint returns routing outcome ("live") without checking trade DB state | `/decisions` enriches fired decisions: if trade.state=CANCELLED → outcome="order_failed". Frontend shows red "Sierra דחתה" | — | ✅ code |
| **P10b** | decisions cleared on restart | In-memory deque only | Added JSONL persistence (`gateway_decisions.jsonl`) + hydration from file on boot. Today's decisions survive restart | — | ✅ code |
| **P6a** | Trend label stuck (escalation-only, no demotion) | No acceptance-return demotion existed. Dalton D2 (06-30) never coded | `DAYTYPE_ACCEPTANCE_DEMOTION_V1`: Trend→Normal_Variation when K=3 bars close inside IB. RULED=1 | — | ✅ code |
| **P6b** | boot-replay gives Normal-0.12, canonical says Variation | Engine replay != canonical classify_session conclusion | `DAYTYPE_BOOT_SEED_CANONICAL_V1`: after replay, run classify_session and seed result. RULED=1 | — | ✅ code |
| **P6c** | cross_check match=false on Normal_Variation vs Variation | get_live_day_type remaps NV→V but classify_replay returns raw "Normal_Variation" | Normalize both sides before comparing in opening_panel endpoint | — | ✅ code |

## דגלים חדשים לריסטארט

| דגל | ערך | פסיקה |
|---|---|---|
| `WOODIES_TS_HOUR_FIX` | `0` | P2: OFF (ברירת-מחדל חדשה) |
| `DAYTYPE_ACCEPTANCE_DEMOTION_V1` | `1` | P6a: D2 06-30 + 07-22 |
| `DAYTYPE_BOOT_SEED_CANONICAL_V1` | `1` | P6b: boot-seed canonical |

## תחנות שטרם-בוצעו (P4/P7/P1/P5 — verify/research)

- **P4**: Mechanism-C edge-trigger כבר בנוי (woodies_system.py:439-447). צריך טסט, לא בנייה.
- **P7**: sim_matrix 60/60 PASS (pre-existing).
- **P1**: DLL export freshness — needs live sim observation over 1h.
- **P5**: S2 threshold research — report-only for Michael ruling.

## P12 שערים (stub — cowork/cursor)

Tasks remaining for tomorrow or post-market.

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
