# PROMPT 6 — System 3 Footprint (STANDALONE Observer)

Completed: 2026-05-12
Atomic sub-prompts: 6.1 through 6.6
Color: Purple #a855f7

## Components
- DB tables: journal + setups (6.1)
- Detectors: cluster, empty zone, context, signals (6.2)
- FootprintSystem class with hydrate + process_bar (6.3)
- API endpoints + main.py wiring (6.4)
- FootprintPill + Lens + Switcher (6.5)
- Tests + UAT (6.6)

## Architecture
- STANDALONE observer (per Spec V3)
- Subscribes to tick_reversal_15 + tick_reversal_12 via BarRouter
- Logs every bar to journal (including NO_SETUP)
- Marks TACTICAL/STRATEGIC setups to setups table
- NO setup output to Trading Layer

## Next
PROMPT 7: Woodies CCI (System 4 Orange)
