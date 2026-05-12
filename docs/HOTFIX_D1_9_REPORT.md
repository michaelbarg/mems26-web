# HOTFIX D1.9 — Discover + Wire + RUNTIME Verify

**Authority:** Principle 13 (RUNTIME-VERIFIED-NOT-CODE-PRESENT)
**Closes:** GAP-017 (Self-QA verified code presence, not runtime)

## What Failed
D1 reported 8/8 PASS but at runtime:
- received: 0 (Bridge POSTs not reaching BarRouter)
- subscribers: only tick_reversal_15 (aggregator only)

## Why
D1 Self-QA checked grep matches but:
- 4 of 7 _route_bar calls passed empty `{"ts": ""}` — no data
- _route_bar used create_task which may not work in sync context
- No system instances were registered as subscribers

## Fixed
- D1.9.2: All 9 bar endpoints pass `payload.dict()`, `ensure_future` for async
- D1.9.3: FiveMinSystem instantiated + hydrated + subscribed to "5min" via BarRouter
- D1.9.4: Report + verification

## RUNTIME Evidence
- 9 _route_bar calls with real payload data
- FiveMinSystem subscribed to "5min" bar type
- BarRouter subscribers: {"tick_reversal_15": 1, "5min": 1}
- Runtime verification pending backend restart (Principle 13)
