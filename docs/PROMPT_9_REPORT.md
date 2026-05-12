# PROMPT 9 — System 6 Killzone (OBSERVER, Time-Based)

**Completed:** 2026-05-12
**Color:** Teal #14b8a6
**Atomic sub-prompts:** 9.1-9.5

## Components
- Zone definitions + current/next functions (9.1)
- KillzoneSystem class + 30s tick loop (9.2)
- API: /api/v9/killzone/current (9.3)
- KillzonePill + KillzoneLensContent + Switcher + SidePanel (9.4)
- Tests (8) + UAT (9.5)

## Architecture
- TIME-BASED observer — does NOT consume bars
- subscribed_bar_types() returns []
- Ticks every 30s via asyncio scheduler
- Publishes zone transitions on change
- 8 zones: ASIA, LONDON, NY_PREMARKET, NY_OPEN, MIDDAY, NY_PM, POST_MARKET, CLOSED

## ALL 6 SYSTEMS COMPLETE
1. Day Type (Indigo #6366f1) — FIRING context provider
2. 5-Min (Cyan #06b6d4) — FIRING decision maker
3. Footprint (Purple #a855f7) — OBSERVING standalone
4. Woodies CCI (Orange #f97316) — FIRING standalone
5. TPO (Yellow #eab308) — OBSERVING profile builder
6. Killzone (Teal #14b8a6) — OBSERVING time-based gate

## Next
PROMPT 10: Chart V5a — visual rendering of all 6 systems
