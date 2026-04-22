# MEMS26 Changelog

## [V6.7.0] - 2026-04-22
**Scope:** Web + Bridge + DLL

- Unified version tracking system
- Version badge in header + modal with changelog
- Warning on version mismatch

## [V6.6.6] - 2026-04-22
**Scope:** DLL

- 3 separate bracket orders with qty=1 each (was 1 bracket qty=3)
- Break-Even: C3 stop moves to entry +/-0.25 after C2 fills
- AllowMultipleEntriesInSameDirection=1

## [V6.6.5] - 2026-04-22
**Scope:** Web

- Pre-Entry Checklist panel maxHeight+scroll at 100% zoom
- SWEEP EVENTS default collapsed
- BUILDING NOW compact single-line cards
- Selected Sweep card pinned above scroll container

## [V6.6.4] - 2026-04-22
**Scope:** Web

- Traffic Light minHeight fix (alignItems flex-start)
- Selected Sweep card collapsible (click header)

## [V6.6.3] - 2026-04-22
**Scope:** Web + Bridge

- RESEARCH entry mode (relaxed thresholds for data collection)
- calcSetups reads entry_mode dynamically (fixes Bug 2)
- P3 informational in RESEARCH mode

## [V6.6.0] - 2026-04-21
**Scope:** Web

- Analytics tab React Error #185 fixed (Recharts ResponsiveContainer)

## [V6.5.8] - 2026-04-21
**Scope:** Web

- LIVE SETUPS overflowAnchor fix
- Scroll reset on tab change

## [V6.5.7] - 2026-04-21
**Scope:** Web + Backend

- Bracket order assertion test (verify_bracket.py)
- /trade/test-dispatch with real values + checksum

## [V6.5.6] - 2026-04-21
**Scope:** Backend

- Removed target recompute (frontend is authority for t1/t2/t3)
- Fixed 7147.50 bracket bug (T1_MIN_PT override)
