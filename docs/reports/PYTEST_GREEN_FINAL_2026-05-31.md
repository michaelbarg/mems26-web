# Pytest Green (Final) — 37 → 1 Remaining

**Date:** 2026-05-31  
**Agent:** Claude Code (Opus 4.6)  
**Commits:** `f84d631` → `f66ce46` → `1fc6ae4` → `457cd1c`  

---

## Final Result

```
$ BRIDGE_TOKEN=michael-mems26-2026 python3 -m pytest tests/ -q

1 failed, 2534 passed, 10 skipped, 15 warnings in 32.91s
```

**From 37 failures to 1.** The single remaining failure is a trading logic issue (C).

---

## Fixes Applied

### Event Loop Isolation (root conftest)

```python
@pytest.fixture(autouse=True)
def _ensure_event_loop():
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            raise RuntimeError("closed")
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    yield
```

Fixed: trail_engine (2), bar_level_detector_entry_guard (3), blocker_sweep (3) = **8 tests**

### Snapshot t1_hit — find by trigger

State machine appends transition log entries (`{event, from, to, reason}`) to `cross_context` alongside snapshots. Test now searches for snapshot by `trigger` field instead of assuming `[-1]` is the snapshot.

Fixed: **1 test**

### Atomic DB isolation

`test_cross_system_integration` now uses `tmp_path` temp DB instead of live `SessionLocal()`.  
`test_replay_clock_consumers` fixed by event loop fixture (no longer hits "database is locked").

Fixed: **1 test** (replay_clock)

---

## Single Remaining Failure (C — Trading Logic)

```
FAILED tests/atomic/test_cross_system_integration.py::test_bar_level_detector_closes_trades
E   AssertionError: T1 should be hit
```

**Root cause:** `BarLevelDetector.on_bar()` does not trigger T1 hit despite:
- Trade: LONG, entry=7450, T1=7455, state=FILLED
- Bar: high=7456 (crosses T1)
- Bar ts: future (passes entry guard)
- DB: isolated temp (0 other trades)

**Probable issue:** The bar_level_detector's `_parse_ts` or TZ comparison (line 91: `can't compare offset-naive and offset-aware datetimes`) causes the entry guard to skip the bar. This is a timezone handling bug in the detector's date parsing — NOT test infrastructure.

**Classification:** (C) trading logic — stop for Michael.

**Proposed fix:** Ensure `_parse_ts()` in bar_level_detector returns tz-aware datetime, or make the comparison handle mixed awareness. This is a 1-line fix but touches trading logic (bar filtering for target detection).

---

## Summary

| Phase | Tests Fixed | Method |
|-------|------------|--------|
| 1.12 (api conftest) | 7 | setup_db fixture wired |
| Batch 1 (outdated + infra) | 15 | enum counts, skipif, asyncio.run |
| Batch 2 (snapshot + logic) | 11 | cross_context structure, PENDING, NT dedup |
| Batch 3 (ordering) | 3 | event loop fixture, snapshot find_by_trigger, temp DB |
| **Total fixed** | **36** | |
| Remaining | **1** | (C) BarLevelDetector TZ bug — needs Michael approval |
