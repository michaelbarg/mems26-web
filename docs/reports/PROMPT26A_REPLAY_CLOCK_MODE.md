# Prompt 26a — Replay Clock Mode

Status: PARTIAL
Date: 2026-05-16

## Verdict

Replay Clock Mode now exists as the central market-clock path for backend replay validation. `REALTIME` preserves the existing system-clock behavior. `REPLAY` uses the latest ingested Sierra/replay bar timestamp as authoritative market time and returns an explicit `PENDING` state until a replay timestamp has arrived.

This does not enable SHADOW, DEMO, or LIVE and does not change trading mode activation logic.

## What Changed

- Extended `backend/v9/services/market_clock.py` with `ClockMode.REALTIME`, `ClockMode.REPLAY`, `ClockStatus.READY`, and `ClockStatus.PENDING`.
- Added central replay timestamp ingestion via `update_replay_timestamp()` and shared timestamp parsing via `parse_market_timestamp()`.
- Updated `BarRouter` to record every parseable bar timestamp into the central replay clock before dispatching consumers.
- Updated `SessionClassifier` no-argument classification to use the central clock.
- Updated `KillzoneSystem` hydrate/tick to use the central clock and report pending clock state instead of falling back to machine time.
- Updated Day Type startup bridge session-minute calculation to use central market-clock time through `minutes_since_rth_open()`.
- Updated `/api/v9/clock/now` to expose mode/status/source and return explicit pending output when replay mode has no timestamp.

## How To Use

Default mode is realtime:

```bash
MEMS26_CLOCK_MODE=REALTIME
```

For Sierra Replay validation, start the backend with:

```bash
MEMS26_CLOCK_MODE=REPLAY
```

Then feed replay bars through the existing backend bar route/BarRouter path. Once the first parseable bar timestamp arrives, the central market clock becomes `READY` and consumers using `market_clock.now_et()`, `SessionClassifier.classify()`, `KillzoneSystem`, or `minutes_since_rth_open()` read the replay timestamp as current market time.

To return to normal behavior, restart or run with:

```bash
MEMS26_CLOCK_MODE=REALTIME
```

## Pending State

When `REPLAY` is enabled before any replay bar timestamp is available, the clock state is:

- `mode`: `REPLAY`
- `status`: `PENDING`
- `reason`: `replay_clock_enabled_but_no_replay_timestamp`

Time-sensitive code must not silently use machine time in this state. Direct calls to `now_et()` / `now_utc()` raise `MarketClockPendingError`.

## Validation

Focused tests added in `backend/v9/tests/test_replay_clock_mode.py` prove:

- `REALTIME` remains ready and preserves existing explicit-time behavior.
- `REPLAY` returns the latest bar timestamp as current market time.
- Missing replay timestamp is explicit `PENDING`, not real-clock fallback.
- Killzone uses replay timestamp.
- Session classification uses replay timestamp.
- Day Type session/open timing uses replay timestamp via central helper.
- BarRouter updates the central replay timestamp and tags session from bar time.
- Clock endpoint does not introduce SHADOW/DEMO/LIVE activation fields.

Focused suite run:

```bash
python3 -m pytest backend/v9/tests/test_replay_clock_mode.py backend/v9/tests/test_bar_router.py backend/v9/tests/test_killzone.py tests/test_session_classifier.py -q
```

Result: `43 passed`.

## Remaining Scope

Replay Clock Mode is PARTIAL, not READY, because not every possible time-sensitive backend consumer has been fully migrated/proven.

Remaining follow-up candidates:

- S5 TPO lock timestamps still contain a direct `datetime.now(...)` write path for `_ib_locked_ts`.
- Trade-manager entry/exit event timestamps still use real clock for lifecycle bookkeeping; active trade time-stop detection itself is already bar-timestamp based in `BarLevelDetector`.
- Additional direct `datetime.now()` paths in non-core persistence/journal code should be audited before SHADOW/DEMO/LIVE enablement.

Preserved:

- D-074 `woodies_5min`.
- S1/S5/S6 advisory-context behavior.
- Existing trading mode activation logic.
- Frontend untouched.
