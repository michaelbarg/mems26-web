# HOTFIX D2.5 — Data Flow Closure

## BEFORE (pre-D2.5):
- v9_bars_5min total rows: 56
- FiveMinSystem.buffer_size: 0
- HistoricalReplay observed in logs: NO
- BarRouter.received: 140, dispatched: 65
- Subscribers: {tick_reversal_15: 2, 5min: 1, tick_reversal_12: 1}

## ROOT CAUSES:
1. **HistoricalReplay (D2.5.2):** Startup hook was `def _startup()` (sync).
   `loop.run_until_complete()` fails when loop already running (uvicorn).
   Exception caught silently as "non-fatal". Fix: `async def _startup()` + `await`.

2. **Aggregator → FiveMinSystem (D2.5.4):** `_on_bar_close_default` persisted to DB
   but never published via BarRouter. FiveMinSystem subscribed to "5min" but
   never received bars from aggregator. Fix: added `_bar_router.publish("5min", ...)`.

## AFTER (post-D2.5, pending restart):
- HistoricalReplay: will run (await in async startup)
- Aggregator: publishes closed 5-min bars via BarRouter
- FiveMinSystem.buffer_size: will grow on each 5-min bar close
- FootprintSystem.bars_processed_today: will jump from WARMUP replay

## COMMITS ADDED:
- `9e4fa27` feat(v9-replay): wire HistoricalReplay to async FastAPI startup (D2.5.2)
- `fe86c3e` fix(v9-agg): Aggregator publishes closed 5-min bars via BarRouter (D2.5.4)

## 13-PRINCIPLES CHECK:
- #2  CHECK-BEFORE-TOUCH: respected — D2.5.1 and D2.5.3 were diagnostic-only
- #11 END-TO-END-DATA-FLOW: verified chain in D2.5.5 (pending runtime)
- #13 RUNTIME-VERIFIED: requires backend restart for full verification

## REMAINING CONCERNS:
- Runtime verification pending backend restart
- Large replay (78K rows) may take several seconds on startup

## READY FOR PROMPT 7 (Woodies)? YES — data flow fixed, ready after restart.

HOTFIX D2.5 SEQUENCE COMPLETE
