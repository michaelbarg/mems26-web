# MEMS26 — Tech Debt Log

## TradingView / lightweight-charts pending removal
- Files still importing: 7 files in frontend/v9/src
  - ChartArea.tsx, StaticLevels.tsx, TPOLines.tsx, TradeMarkerOverlay.tsx,
    VegasEMAs.tsx, RightSideLabels.tsx, chartSyncStore.ts
- Remove in: PROMPT 10 (Chart V5a rebuild)
- Date logged: 2026-05-11
- Status: Disconnected from render tree (not imported by V9Dashboard)

## V8 Sidebar (LeftTabs) disconnected
- Files: frontend/v9/src/v9/components/sidebar/
- 13 tab components (TraderTab, MarketTab, etc.)
- Remove in: PROMPT 10+ (replaced by SidePanel + Lens)
- Date logged: 2026-05-11
- Status: Disconnected from render tree

## V8 SystemPanelsBar disconnected
- File: frontend/v9/src/v9/components/panels/SystemPanelsBar.tsx
- Remove in: PROMPT 10+
- Date logged: 2026-05-11
