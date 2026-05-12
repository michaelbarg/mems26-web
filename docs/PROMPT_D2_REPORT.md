# PROMPT D2 — Historical Replay

**Completed:** 2026-05-12
**Atomic sub-prompts:** D2.1-D2.4

## Components
- HistoricalReplay service (D2.1)
- main.py startup wiring (D2.2)
- Status endpoint stats (D2.3)
- Tests + UAT (D2.4)

## Effect
On every backend restart: 12h of bars from DB -> BarRouter -> systems' buffers fill in ~1-2 seconds.

No SCID parsing. No waiting hours for buffer fill.
Systems "warm" from moment of restart.

## Next
PROMPT 6: Footprint (System 3 Purple) — consumes tick_reversal via BarRouter.
