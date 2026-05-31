# Trade Path Live Trace — End-to-End Diagnosis

**Date:** 2026-05-31  
**Agent:** Claude Code (Opus 4.6)  
**Type:** DIAGNOSE ONLY — zero code changes  
**Verdict:** All links CONNECTED in SHADOW mode. No broken chain.

---

## Chain Overview

```
Pattern Detection (five_min_system.process_bar)
  → emit_t1_setup() → T1Setup or None
  → gateway.route_setup(setup, 2)
    → risk gates (cooldown/SSV/chop/cluster)
    → _execute_shadow() → TradeManager.accept_setup() → DB flush
    → gateway commits (line 250)
  → DB: v9_trades row
  → GET /api/v9/trades → frontend fetchTrades() → tradeStore → UI

BarLevelDetector (subscribed to bar_router "5min" + "woodies_5min")
  → on_bar() → get_active_trades() → check stop/T1/T2/T3
  → on_target_hit() / on_stop_hit() → DB update → commit (line 128)
```

---

## Link-by-Link Verification

### Link 1: Pattern Detection → Setup Emission

| Item | Status | File:Line |
|------|--------|-----------|
| `process_bar()` calls detectors | CONNECTED | `five_min_system.py:775-810` |
| Detector returns `(direction, conf, info)` | CONNECTED | `five_min_system.py:824` |
| `emit_t1_setup()` called with results | CONNECTED | `five_min_system.py:1003` |
| Returns `T1Setup` or `None` | CONNECTED | `setup_emitter.py:24` |

**Gates that can return None:** Auth Table SKIP, pre_fire_validator reject, Nontrend NO_TRADE, R:R < 1.0.

### Link 2: Setup → Gateway Routing

| Item | Status | File:Line |
|------|--------|-----------|
| Gateway injected at startup | CONNECTED | `main.py:399` (`set_gateway(trading_gateway)`) |
| `if t1_setup and self._gateway:` | CONNECTED | `five_min_system.py:1012` |
| `self._gateway.route_setup(gateway_setup, 2)` | CONNECTED | `five_min_system.py:1026` |

**Key:** If `self._gateway` is None (e.g., unit test without main.py wiring), trade is never routed. In production, main.py always sets it.

### Link 3: Gateway → TradeManager → DB

| Item | Status | File:Line |
|------|--------|-----------|
| `_execute_shadow()` always runs (past hard gates) | CONNECTED | `trading_gateway.py:224` |
| Calls `trade_manager.accept_setup()` | CONNECTED | `trading_gateway.py:246` |
| `accept_setup` → `db.add(trade)` + `db.flush()` | CONNECTED | `manager.py:170-172` |
| Gateway does `db.commit()` | CONNECTED | `trading_gateway.py:250` |
| `_execute_demo()` → writes Sierra command file | CONNECTED | `trading_gateway.py:277` |
| `_execute_live()` → **STUB** (logs warning) | STUB (by design) | `trading_gateway.py:292` |

**DB Session:** `main.py:428` creates `tm_db = SessionLocal()` → shared by TradeManager + BarLevelDetector.

### Link 4: DB → API

| Item | Status | File:Line |
|------|--------|-----------|
| `GET /api/v9/trades` queries `V9Trade` | CONNECTED | `trades.py:322-338` |
| Same `DATABASE_URL` / DB file | CONNECTED | `session.py` |
| Filter: `is_synthetic == 0` | SAFE | `trades.py:331` (TM never sets synthetic=1) |
| Returns `{trades: [...], total, truncated}` | CONNECTED | `trades.py:338` |

### Link 5: API → Frontend

| Item | Status | File:Line |
|------|--------|-----------|
| `fetchTrades()` → `GET /api/v9/trades?limit=500` | CONNECTED | `api.ts:163` |
| `mapTradeRow()` normalizes fields | CONNECTED | `api.ts:133-161` |
| `tradeStore.setTrades()` stores array | CONNECTED | `tradeStore.ts:68` |
| Default filter: `mode='ALL'` | CONNECTED | `tradeStore.ts:46` |

### Link 6: BarLevelDetector → Target Detection

| Item | Status | File:Line |
|------|--------|-----------|
| Subscribed to bar_router | CONNECTED | `main.py:434` (`bar_level_detector.subscribe(bar_router)`) |
| Channels: "5min" + "woodies_5min" | CONNECTED | `bar_level_detector.py:37-39` |
| `on_bar()` → `get_active_trades()` | CONNECTED | `bar_level_detector.py:70` |
| Target check: `bar_high >= t1` | CONNECTED | `bar_level_detector.py:100` |
| `on_target_hit()` → updates DB | CONNECTED | `bar_level_detector.py:109` |
| Commits after all trades processed | CONNECTED | `bar_level_detector.py:128` |
| **TZ fix applied** (aware comparison) | FIXED | `bar_level_detector.py:88-92` |

---

## Risk Gates (conditions that block without error)

| Gate | Blocks | Effect |
|------|--------|--------|
| Mode OVERNIGHT/MAINTENANCE/WEEKEND | All | `process_bar` returns early (line 724) |
| Nontrend day_type | All | NT skip, counter incremented (line 762) |
| `emit_t1_setup` returns None | Gateway | No route_setup call (line 1012) |
| Cooldown blocked | SHADOW + DEMO + LIVE | No trade created at all |
| SSV veto | SHADOW + DEMO + LIVE | No trade created |
| Chop SEARCHING | SHADOW + DEMO + LIVE | No trade created |
| Cluster guard | DEMO + LIVE only | SHADOW still records |
| Demo slot occupied | DEMO | Only 1 demo trade at a time |
| Strict checks fail | LIVE only | LIVE blocked |
| BarLevelDetector `mode != "LIVE"` | Target detection | Skips bar (always "LIVE" in prod) |

---

## Issues Found (non-blocking)

### 1. Misleading Log (cosmetic)

**File:** `five_min_system.py:1027`  
```python
logger.info("[S2] Auto-routed → gateway (system=2, pattern=%s)", ...)
```
Logs "Auto-routed" even when gateway returns `{blocked_by: "cooldown"}`. The caller never inspects the return value.

**Impact:** Log confusion only. No data loss. Risk gates work correctly.  
**Fix:** Check return value and log differently if blocked. (Not urgent.)

### 2. LIVE Execution is a Stub

**File:** `trading_gateway.py:292`  
```python
logger.warning("[Gateway] LIVE trade (stub)... NOT sent to Sierra")
```

**Impact:** By design for pre-LIVE stage. P5 pipeline will implement this.

### 3. `_on_bar_closed()` is Vestigial Dead Code

**File:** `five_min_system.py:271`  
Part of older `process()` method. Not called by BarRouter. Harmless.

---

## Conclusion

**The trade path is fully connected in SHADOW mode.** Every link from pattern detection through to frontend display is wired and functional. The only structural gaps are intentional (LIVE stub) or cosmetic (misleading log). The TZ fix ensures BarLevelDetector now correctly detects targets after trades are created.

No action needed. Ready for SHADOW trading validation.
