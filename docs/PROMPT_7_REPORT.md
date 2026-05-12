# PROMPT 7 — System 4 Woodies CCI (FIRING Standalone)

**Completed:** 2026-05-12
**Color:** Orange #f97316
**Atomic sub-prompts:** 7.1-7.5

## Components
- v9_woodies_signals table (7.1)
- CCI(14) calculator (7.2)
- WoodiesSystem class with hydrate + process_bar (7.3)
- Wire + API + Frontend (7.4)
- Tests + UAT (7.5)

## Architecture
- FIRING decision maker — STANDALONE per Woodies V1
- Subscribes to 5min + tick_reversal_15
- Detects ZLC bull/bear, OB/OS, trend mode
- Publishes signals to v9_woodies_signals table
- No input from other systems (Day Type, etc.)

## Signal Types
- ZLC_BULL / ZLC_BEAR (Zero-Line Cross)
- OB_ENTER / OB_EXIT (Overbought)
- OS_ENTER / OS_EXIT (Oversold)
- TREND_BULL / TREND_BEAR
- NEUTRAL

## Next
PROMPT 8: TPO (System 5 Yellow) — CRITICAL, unlocks Day Type
