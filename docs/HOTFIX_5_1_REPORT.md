# HOTFIX V9.0.5.1 — Wire FiveMinPill into Switcher

**Date:** 2026-05-12

## Problem
Switcher.tsx used generic `SwitcherSlot` via `FIRING_SYSTEMS.map()` for
all systems. While System 2 rendered with correct cyan color (from
SYSTEM_META), it didn't use the dedicated `FiveMinPill` component.
Self-QA Check 4 was a false positive.

## Fix
Replaced generic map in Firing row with explicit component references:
- System 1: `<DayTypePill />`
- System 2: `<FiveMinPill />`
- System 4: `<SwitcherSlot systemId={4} />` (placeholder until Prompt 7)

## Self-QA
- Check 1 (Import exists): **PASS** — 1 match
- Check 2 (JSX rendered): **PASS** — 1 match
- Check 3 (Build clean): **PASS** — 0 errors
- Check 4 (Regression): **PASS** — uat_prompt_4.sh 13/13
- Check 5 (DayTypePill intact): **PASS** — 1 match
