# REPORT -- PROMPT FRONTEND BRIDGE

Date: 2026-05-15

## Changes

### api.ts
- Added `DayTypeV9Response` interface (typed V9 schema)
- Added `fetchDayTypeV9()` function calling `/api/v9/day_type/v9/current`

### TopBar.tsx
- Calls V9 endpoint first, falls back to V1 on failure
- Shows probability as percentage (was V1 confidence)
- Shows directional certainty initial (H/M/L) after day type
- Extended DT_LABELS with lowercase keys for V9 compatibility

### DayTypeLensContent.tsx
- Fully rewired to V9 data structure
- Shows: probability, directional certainty, trading confidence
- Shows: IB range with width class, opening type
- Shows: active Zohar rules when present
- Graceful empty state when no data

### systemStateStore.ts
- V9 endpoint primary, V1 fallback
- Stores raw V9 data for downstream components

## Verification

- Build: SUCCESS (compiled + TypeScript clean)
- V9 endpoint: returns data (Neutral, probability 0.6)
- No design changes, no new components
