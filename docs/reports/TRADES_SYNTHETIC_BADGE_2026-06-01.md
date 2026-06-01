# Trades: Synthetic Badge + UX Redesign · 2026-06-01

**Date:** 2026-06-01 · **Author:** CC

---

## Synthetic Badge (Michael chose: show with badge)

### Backend
- Removed `is_synthetic == 0` hard filter from `GET /trades` (line 332) and `/trades/recent` (line 361)
- Added `is_synthetic: bool` to `_trade_list_row()` response payload
- Synthetic trades now **included** in API response with `is_synthetic: true`

### Frontend
- **TradesTable:** synthetic rows show amber "TEST" badge next to trade ID + dimmed (0.6 opacity) + yellow tint background
- **TradesSummaryStrip:** WR%, PnL, counts computed from `real = trades.filter(t => !t.is_synthetic)` — synthetic excluded from stats
- **PatternPerformanceStrip:** same — synthetic excluded from pattern aggregates
- **Trade type:** `is_synthetic?: boolean` added to Trade interface

### Aggregate guard
```typescript
// TradesSummaryStrip.tsx — compute stats on real trades only
const real = trades.filter((t) => !t.is_synthetic);
const closed = real.filter(...);
const withPnl = real.filter(...);
```

---

## UX Improvements

### Modal: Trade Timeline (management_log)
Replaced flat `action` list with visual timeline:
- **ENTRY** (green) → timestamp + price
- **STOP_MOVE** (amber) → from → to + reason
- **SMART_BE** (blue) → from → to
- **T1/T2/T3_HIT** (green) → timestamp
- **STOP_HIT** (red) → timestamp + stop price
- **EXIT** (red) → timestamp + price + reason

Timeline has left border, color-coded actions, max height with scroll.

### Table: Outcome coloring
State column now shows:
- WIN → green, bold
- LOSS → red, bold
- OPEN/FILLED/PARTIAL → blue
- T1_NO_BE badge → amber, inline

### Test isolation
- Backend `is_synthetic` default=0 on `V9Trade` model — unchanged
- Test DB isolation (`conftest.py`) — unchanged
- No new synthetic trades created in prod

---

## Commits
1. `ac393ff` — feat(trades): show synthetic trades with TEST badge
2. `a407d0e` — feat(trades): UX improvements — timeline, outcome colors

## Golden regression
2556 passed, 0 failed.

---

*Visual UAT deferred to RTH when real trades + management_log entries exist.*
