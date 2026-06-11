# Trades Page Redesign — 2026-06-11

## Component Audit (per CLAUDE.md "Audit existing surfaces")

| Component | Lines | Decision | Reason |
|-----------|-------|----------|--------|
| TradesView.tsx | 83 | **ADAPT** | Add TradesSummaryStrip to layout |
| TradeCardList.tsx | 147 | **ADAPT** | Add risk-pts column, shared-anchor badge, expand/collapse |
| TradeRowExpand.tsx | 246 | **ADAPT** | Add chart, mgmt timeline, spec flags, capture quality |
| TradesSummaryStrip.tsx | 142 | **ADAPT** | Add PF, avg risk, biggest loss KPIs |
| TradePathVisual.tsx | 117 | KEEP | Already good R-level visual |
| TradeFilters.tsx | 290 | KEEP | 9 filter axes sufficient |
| tradeStore.ts | 178 | KEEP | Already has all needed filters/sorts |
| tradeMath.ts | 177 | KEEP | R-level, equity, cumulative calcs |
| All analytics strips | ~800 | KEEP | Working as-is |
| TradeChart.tsx | — | **NEW** | Per-trade candlestick chart (lazy) |
| MgmtTimeline.tsx | — | **NEW** | T1→BE→exit lifecycle dots |
| SpecFlags.tsx | — | **NEW** | Shared anchor, risk bounds, re-entry flags |

## Changes Made

### New Components

1. **`TradeChart.tsx`** (155 lines) — Lazy-loaded per-trade candlestick chart
   - lightweight-charts, 200px height, dark theme
   - Fetches `/api/v9/chart/bars5min?limit=120`, filters to trade window ±30min
   - Price lines: entry (blue), initial stop (red), BE stop (orange), T1 (green), T2 (green light)
   - Purple circle marker at exit
   - ResizeObserver for responsive width
   - Disposed on unmount (no memory leak)

2. **`MgmtTimeline.tsx`** (53 lines) — Horizontal lifecycle timeline
   - Colored dots: T1_HIT (green), SMART_BE (blue), STOP_HIT (red), TIME_STOP (yellow)
   - Connected by line segments
   - Hebrew fallback: "אין לוג ניהול" when empty
   - Pure CSS, no chart library

3. **`SpecFlags.tsx`** (72 lines) — Spec-conformance badges
   - 🔗 Shared anchor (red) — same stop_initial within 0.5pt same day
   - ⚠ Risk < 2pt (yellow) / Risk > 60pt (red) / Risk 25-60pt (orange)
   - 🔄 Re-entry after stop-out (yellow) — same pattern+direction after STOP_HIT

### Adapted Components

4. **`TradesSummaryStrip.tsx`** — Added 3 new KPIs:
   - **PF** (Profit Factor) — green ≥1.5, neutral ≥1.0, red <1.0
   - **Avg Risk** — green <10pt, yellow 10-25pt, red >25pt
   - **Max Loss** — largest single-trade loss in red

5. **`TradesView.tsx`** — Added `<TradesSummaryStrip />` at top of page (before filters)

6. **`TradeCardList.tsx`** — Three additions per trade card:
   - **Risk-in-points badge** — color-coded (green/yellow/red), shows e.g. "17.5pt"
   - **Shared anchor badge** — 🔗N when stop_initial matches other trades same day
   - **Expand/collapse toggle** — "▼ פרטים" / "▲ סגור" with inline `TradeRowExpand`

7. **`TradeRowExpand.tsx`** — Major enhancement:
   - **Spec flags** at top (SpecFlags component)
   - **Risk in points** with color coding in detail block
   - **MFE / captured** — "12.5pt MFE · 8.3pt captured (66%)"
   - **T1/T2 with actual prices** — "7284.35 (+0.4R) · —"
   - **Per-trade chart** — lazy-loaded Suspense with "טוען צ׳ארט…" fallback
   - **Mgmt log timeline** — T1→BE→exit dots with Hebrew header "ציר-זמן ניהול"
   - Management log data loaded from `/api/v9/trades/{id}` (existing endpoint)

## Files Changed

```
frontend/v9/src/v9/components/trades/TradeChart.tsx        NEW (155 lines)
frontend/v9/src/v9/components/trades/MgmtTimeline.tsx      NEW (53 lines)
frontend/v9/src/v9/components/trades/SpecFlags.tsx         NEW (72 lines)
frontend/v9/src/v9/components/trades/TradesSummaryStrip.tsx ADAPTED (+20 lines)
frontend/v9/src/v9/components/trades/TradesView.tsx        ADAPTED (+3 lines)
frontend/v9/src/v9/components/trades/TradeCardList.tsx     ADAPTED (+42 lines)
frontend/v9/src/v9/components/trades/TradeRowExpand.tsx    ADAPTED (+35 lines)
```

## Verification

- `npx next build` — compiled successfully, zero type errors
- Dev server (localhost:3000/trades) — page loads, no console errors from our changes
- Pre-existing TPO LineSeries errors (dashboard chart) — unrelated, not introduced

## Design Decisions

1. **Lazy chart rendering** — `React.lazy()` + `<Suspense>` ensures charts only load when
   a trade card is expanded. Collapsed list does NOT fetch bars data.
2. **No new polling** — chart fetches bars once on expand (not polling). Respects
   CLAUDE.md §Frontend Polling Floors.
3. **No new endpoints** — mgmt log comes from existing `/api/v9/trades/{id}` response.
   Bars from existing `/api/v9/chart/bars5min`.
4. **RTL preserved** — Hebrew labels ("ציר-זמן ניהול", "סגור/פרטים", "סיכון") consistent
   with existing RTL patterns. `<bdi>` wrappers for LTR numbers.

## NOT-DONE

1. **Component tests** — render test with fixture trade + mgmt log deferred. Framework
   (jest/vitest) not configured in this frontend; needs setup.
2. **Regression test** — collapsed list doesn't fetch bars. Verifiable by browser Network
   tab but no automated test yet.
3. **ROADMAP_TO_LIVE.html + STATUS_BOARD.md** — not updated (need Cowork coordination).
4. **Screenshot** — page loaded in browser but screenshot capture not automated from CLI.
   Manual verification: trades page shows summary strip, expandable cards with charts.
