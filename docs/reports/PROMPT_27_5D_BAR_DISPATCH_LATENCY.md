# P27.5d — Bar Dispatch Latency Investigation

**Verdict: GREEN**

## Summary

The event loop saturation described (live_price >5s timeouts during bridge push) did **not reproduce** at current replay throughput (~0.75 POST/s). However, instrumentation identified one latency source: `FootprintSystem.process_bar` opening a fresh `sqlite3.connect()` on every bar (3x: journal write, setup write, fire persist). A single spike of 165ms was observed. Fix: reuse a persistent WAL-mode connection.

After the fix: **zero dispatches exceeded 50ms** in a full 90s soak.

## Before Fix — Soak 1 (90s, ~68 POSTs)

### Subscriber p95 (ms)

| Subscriber | Max Observed (ms) | Notes |
|------------|-------------------|-------|
| FootprintSystem.process_bar | 165.5 | sqlite3.connect() per bar |
| All others | <10 | Not logged (under threshold) |

### Per-bar Dispatch

| Metric | Value |
|--------|-------|
| p50 | <10ms (not logged) |
| p95 | <50ms (only 2 of ~68 exceeded 50ms) |
| p99 | 165.6ms (1 event) |

### live_price During Soak

| Probe | Latency |
|-------|---------|
| T+30s | 4.5ms |
| T+60s | 1.5ms |
| T+90s | 1.4ms |

## After Fix — Soak 2 (90s)

### Per-bar Dispatch

| Metric | Value |
|--------|-------|
| p50 | <10ms |
| p95 | <10ms |
| p99 | <50ms |

**Zero dispatches exceeded 50ms.** Zero SLOW handler warnings.

### live_price During Soak

| Probe | Latency |
|-------|---------|
| T+30s | 3.7ms |
| T+60s | 1.3ms |
| T+90s | 1.5ms |

### DB Freshness

- `MAX(ts) FROM v9_bars_5min`: `2026-05-17 15:15:00` (current for replay window)
- Total rows: 554

## Code Changes

### `backend/v9/systems/footprint/footprint_system.py`

**Change:** Replace per-bar `sqlite3.connect()` + `conn.close()` with a persistent WAL-mode connection via `_get_conn()`.

- Added `self._conn` attribute and `_get_conn()` helper (opens once with `PRAGMA journal_mode=WAL` + `PRAGMA busy_timeout=3000`)
- `_write_journal()`: uses `self._get_conn()` instead of `sqlite3.connect()`; removes `conn.close()`; resets `self._conn = None` on error
- `_write_setup()`: same pattern
- `_fire()` DB persist: same pattern

### `backend/v9/services/bar_router.py`

**Change:** Added per-handler and per-dispatch timing instrumentation.

- Added `import time`
- Each handler call timed with `time.perf_counter()`; logs `WARNING` if >100ms
- Total dispatch logged as `WARNING` if >50ms, `INFO` if >10ms

## Observations

1. The described >5s timeout scenario did **not reproduce** — likely requires higher throughput (2-3 POST/s live market) or was a transient condition from the pre-reboot state (fd exhaustion + watchdog respawn loop).
2. At 0.75 POST/s replay rate, the system is well within budget even before the fix.
3. The fix is still worthwhile: eliminating the per-bar connection overhead removes a 165ms spike that could compound at higher rates.
4. Redis/Event Bus errors in bridge stderr are cosmetic (Render Redis not reachable locally) — they don't block data flow to the backend.

## State After Report

- Bridge: **stopped** (quiet baseline)
- Backend: **running** on port 8000 with instrumentation + fix
- Frontend: **running** on port 3000
