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
