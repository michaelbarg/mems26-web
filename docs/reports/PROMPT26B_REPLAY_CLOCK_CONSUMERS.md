# Prompt 26b: Replay Clock Consumers — TPO + TradeManager

**Date:** 2026-05-16  
**Commit:** (this prompt)  
**Tests:** 5/5 pass  
**No SHADOW/DEMO/LIVE enabled.**

---

## Changes

| Consumer | Before | After |
|----------|--------|-------|
| TPO `_ib_locked_ts` (3 locations) | `datetime.utcnow()` | `_market_now_utc()` |
| TPO POC migration `now_dt` | `datetime.utcnow()` | `_market_now_utc()` |
| TradeManager `entry_ts` | `datetime.now(timezone.utc)` | `_market_now_utc()` |
| TradeManager `hit_ts` (2 locations) | `datetime.now(timezone.utc)` | `_market_now_utc()` |
| TradeManager `exit_ts` | `datetime.now(timezone.utc)` | `_market_now_utc()` |

**Total:** 7 timestamp sources migrated to `market_clock.now_utc()`.

---

## Wall-Clock vs Market-Clock Decision

| Timestamp | Type | Reason |
|-----------|------|--------|
| `trade.entry_ts` | MARKET | When was the trade entered (market time) |
| `trade.exit_ts` | MARKET | When was the trade closed (market time) |
| `hit_ts` (T1/T2/T3/stop) | MARKET | When did the hit occur (market time) |
| `_ib_locked_ts` | MARKET | When was IB locked (session time) |
| `poc_migration now_dt` | MARKET | POC stuck duration (session time) |
| `created_at` (DB default) | WALL | Audit trail (when was DB row written) |
| `TradeEventEmitter.ts` | WALL | When was event published (observability) |

---

## Remaining Real-Clock Consumers (documented, intentional)

| Location | Timestamp | Why wall-clock is correct |
|----------|-----------|--------------------------|
| `TradeEventEmitter.emit()` | event publish time | Observability/debugging — when did the system emit |
| DB `created_at` columns | row creation time | Audit trail — independent of market session |
| `_replay_updated_at_utc` in MarketClock | last update time | Clock service internal tracking |

---

## Replay Clock Coverage Status: READY

| Component | Status |
|-----------|--------|
| Central MarketClock | ✅ (Prompt 26a) |
| BarRouter bar timestamps | ✅ (Prompt 26a) |
| SessionClassifier | ✅ (Prompt 26a) |
| Killzone timing | ✅ (Prompt 26a) |
| DayType session_min | ✅ (Prompt 26a) |
| TPO IB lock + POC migration | ✅ (Prompt 26b) |
| TradeManager lifecycle | ✅ (Prompt 26b) |
| BarLevelDetector (uses bar.ts) | ✅ (already bar-driven) |
| DB audit `created_at` | WALL (intentional) |
| Event emitter `ts` | WALL (intentional) |

**All market-time consumers now use `market_clock.now_utc()`.**

---

*Generated: Prompt 26b. No push.*
