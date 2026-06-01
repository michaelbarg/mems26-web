# Trades Page Audit · 2026-06-01

**Date:** 2026-06-01 · **Author:** CC · **Mode:** READ-ONLY audit
**DB state:** 0 trades, 0 management log entries (SHADOW, pre-RTH)

---

## A1 — Link Map (UI → API → DB → Calc)

| UI Element | api.ts Call | Endpoint | DB Query | Calc Function |
|------------|------------|----------|----------|---------------|
| TradesTable (12 cols) | `fetchTrades(mode,500)` | GET `/trades?mode=X&limit=500` | `V9Trade.filter(is_synthetic==0, mode, system).order_by(entry_ts.desc)` | `_trade_list_row()` + `compute_trade_pnl()` |
| TradeHistoryStrip | `fetchRecentTrades(20)` | GET `/trades/recent?limit=20` | Same model, no mode filter | `_trade_list_row()` |
| TradeDetailsModal | `fetchTradeById(id)` | GET `/trades/{id}` | `V9Trade.get(id)` + `V9TradeManagementLog.filter(trade_id)` | `extract_trade_insight()` + `compute_trade_pnl()` |
| Active trade card | `fetchActiveTrade()` | GET `/trades/active` | `V9Trade.filter(state IN (FILLED,PARTIAL))` | Direct fields |
| Exit button | `exitTrade(id, {})` | POST `/trades/{id}/exit` | `tm.close_trade()` → state CLOSED | `compute_trade_pnl()` |

**Classification:** All links → **KEEP** (correctly wired, functional).

## A2 — Filter Audit

| Filter | UI | Backend Param | Works? | Evidence |
|--------|-----|--------------|--------|----------|
| Mode | TradeFilters dropdown (ALL/SHADOW/SIM/LIVE) | `mode` query param, line 333 | ✅ KEEP | `GET /trades?mode=SHADOW` → filters by mode |
| System | TradeFilters (S1-S6/ALL) | `firing_system` or `dominant_system`, line 336 | ✅ KEEP | Accepts either param name |
| Limit | Hardcoded 500 in fetchTrades | `limit` param, max 1000 | ✅ KEEP | Was 200, fixed to 500 in E2E report |
| is_synthetic | Hardcoded filter | `is_synthetic==0`, line 331 | ✅ KEEP | Always excludes synthetics |
| Outcome | Frontend-only (Zustand store) | N/A (client filter) | ✅ KEEP | Filters after fetch |
| Date range | Frontend-only (tradeStore) | N/A (client filter) | ✅ KEEP | Fixed lexical→Date compare in E2E report |
| Pattern search | Frontend-only (tradeStore) | N/A (client filter) | ✅ KEEP | Text match on pattern_id |

**All 7 filters functional.** Combinations work (client-side filtering after server query).

## A3 — Calculation Audit

### compute_trade_pnl (trade_context.py:69-144)

**Math:** Per-contract: `points = (exit - entry) × direction_mult`, `pnl = points × $5`, `R = pnl / (|entry - stop| × $5)`

**Numerical example:**
```
LONG entry=7600, stop=7595, T1=7605
risk_per_contract = |7600-7595| × 5 = $25
C1 (50%): T1 hit → points=5, pnl=$25, R=1.0 ✓
C2 (30%): exit@7608 → points=8, pnl=$40, R=1.6 ✓  
C3 (20%): stopped@7602 (trail) → points=2, pnl=$10, R=0.4 ✓
Total: $75, avg R = 75/(3×25) = 1.0 ✓
```

**Status:** ✅ KEEP — math correct.

### compute_trade_excursion (trade_excursion.py:98-160)

**Math:** MFE(LONG) = max(0, price_high - entry), MAE(LONG) = max(0, entry - price_low)

**Status:** ✅ KEEP — correct per direction.

### _stop_initial_from_trade (trade_context.py:219-230)

Reads `quality.metadata.stop_initial` or falls back to `trade.stop` if T1 not hit.

**Status:** ✅ KEEP — preserves initial stop before trail.

## A4 — Source-of-Truth

| Axis | Endpoint | Status | Evidence |
|------|----------|--------|----------|
| Quality | GET /trades | ✅ | `is_synthetic=0` hardcoded, no mock data |
| Recency | GET /trades | ✅ | `order_by(entry_ts.desc)` → latest first |
| Cardinality | GET /trades?limit=5 | ✅ | Returns exactly min(total, limit) rows |
| Latency | GET /trades | ✅ | <50ms (0 rows, minimal) |

DB has 0 trades — all axes pass vacuously. Real UAT needs SHADOW data.

## A5 — Management Log Gap (CRITICAL FINDING)

**Finding: V9TradeManagementLog is never auto-populated.**

| Component | Writes to management_log? | What it does instead |
|-----------|--------------------------|---------------------|
| TrailEngine | **NO** | Logs to Python logger (line 785) + appends to `cross_context` JSON |
| TradeManager (Smart BE) | **NO** | Logs to Python logger (line 313) + appends to `cross_context` JSON |
| BarLevelDetector (stop/target hit) | **NO** | Logs to Python logger (lines 105, 125) |
| POST /trades/log | **YES** (only writer) | Manual API call — nobody calls it automatically |

**Evidence:**
```bash
$ grep -rn "V9TradeManagementLog" backend/v9/ --include="*.py" | grep -v import | grep -v relationship | grep -v query
backend/v9/api/v9/trades.py:405:    row = V9TradeManagementLog(
# ← ONLY write site, in the manual POST /trades/log endpoint
```

**Impact:** The TradeDetailsModal shows a "Management log" section (lines 290-302) that reads from `management_log[]` — but this array is **always empty** because no service writes to it. All stop-movement audit data lives in `cross_context` (JSON blob on the trade row) which the modal **does not display**.

**Root cause:** The management_log table was designed for observability but never wired into the actual management code path. The `cross_context` JSON was used as an ad-hoc substitute.

---

## Summary of Findings

| # | Finding | Classification | Fix Needed |
|---|---------|---------------|-----------|
| F1 | All 7 filters work | KEEP | No |
| F2 | PnL/excursion/stop math correct | KEEP | No |
| F3 | Management log table empty (never auto-populated) | **ADAPT** | Wire writes from TrailEngine + TradeManager + BarLevelDetector |
| F4 | Modal shows management_log (always []) but not cross_context | **ADAPT** | Read cross_context as fallback/supplement |
| F5 | DB has 0 trades (pre-SHADOW) | Expected | Need SHADOW collection or controlled trade for live UAT |
| F6 | E2E report fixes (limit 500, date filter, WR%) | KEEP | Verified held |

---

*Part B (fixes) follows. Critical path: F3 (wire management log writes).*
