# PROMPT 8 — System 5 TPO Profile (OBSERVER)

**Completed:** 2026-05-12
**Color:** Yellow #eab308
**Atomic sub-prompts:** 8.1-8.6

## Components
- v9_tpo_sessions + v9_tpo_journal tables (8.1)
- Opening classifier (8.2)
- TPOSystem with profile builder, POC/VAH/VAL, shape detection (8.3)
- API: /api/v9/tpo/{current,journal,sessions} (8.4)
- TPOPill + TPOLensContent + Switcher + SidePanel (8.5)
- Tests (8) + UAT (8.6)

## Architecture
- OBSERVER — publishes POC/VAH/VAL/shape, no trade signals
- Subscribes to 5min via BarRouter
- Per-session profiles (GLOBEX + CASH separate)
- 30-min letter assignment (A-M for RTH)
- IB tracking + lock at bar 12 (60 min)
- Shape detection: D/b/P/double/trend/neutral/NA

## CRITICAL
Unlocks Day Type adaptive logic (Prompt 5.1).
Day Type reads TPO's POC/VAH/VAL + profile shape for classification.

## Next
PROMPT 9: Killzone (System 6 Teal) — last system
