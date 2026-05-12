# HOTFIX V9.0.5.3 — Wire Pills to State (State-Aware Pattern)

**Date:** 2026-05-12

## Problem
Pills rendered static labels only. Did not display runtime state
(UNKNOWN, OVERNIGHT_MODE, etc.) even though APIs return it.

## Solution
- Created `systemStateStore.ts` (Zustand) — tracks state for all 6 systems
- Created `useSystemStatePolling.ts` — polls /api/v9/{system}/current every 2s
- Updated `DayTypePill` + `FiveMinPill` to read store and display abbreviated state
- Updated `SwitcherSlot` to accept `stateLabel` prop
- Integrated polling in `V9Dashboard.tsx`

## Self-QA (all 9 PASS)
- Check 1 (Store exists): PASS
- Check 2 (Polling hook exists): PASS
- Check 3 (DayTypePill reads store): PASS (2 refs)
- Check 4 (FiveMinPill reads store): PASS (2 refs)
- Check 5 (Polling integrated): PASS (2 refs)
- Check 6 (Build clean): PASS (0 errors)
- Check 7 (API returns mode): PASS (OVERNIGHT_MODE)
- Check 8 (Regression): PASS (66 tests)
- Check 9 (State interpolation): PASS (2 refs)

Principle 9 candidate: STATE-AWARE-PILLS — pills must subscribe to
runtime state, not just render static labels.
