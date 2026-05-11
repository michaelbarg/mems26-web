# HOTFIX V9.0.4.3 — V8 Cleanup + Connection Fix

**Date:** 2026-05-11
**Branch:** feature/v9_architecture_rebuild

## What Changed

### Group A — V8 Cleanup
No files deleted. V8 components (ChartArea, LeftTabs, VolumePanel, 
SystemPanelsBar) remain on disk but are disconnected from the render
tree. DashboardLayout.tsx preserved for reference. Tech debt logged.

### Group B — page.tsx Rewrite
Created `V9Dashboard.tsx` as the new V9-only client component:
- TopBar + Layer0Strip + Chart placeholder + SidePanel
- All colors from `COLORS` tokens (zero hardcoded hex)
- `useSystemEvents` hook active
- `PriceDebugConsole` preserved

`page.tsx` now imports `V9Dashboard` instead of `DashboardLayout`.

### Group C — UAT Script
`scripts/uat_hotfix_4_3.sh`: 6 automated checks, all pass.

### Group D — WS Relay
Already running (relay_running: true, 1 client). No fix needed.
Relay is lazy-initialized — starts on first WS client connection.

### Group E — Tech Debt
`docs/TECH_DEBT_LOG.md` created with 3 entries:
- lightweight-charts (7 files, remove in Prompt 10)
- LeftTabs sidebar (13 tabs, remove in Prompt 10+)
- SystemPanelsBar (remove in Prompt 10+)

## Self-QA Results

- Check 1 (Hardcoded colors): **PASS** — zero `bg-[#`, `text-[#`, `border-[#` in page.tsx
- Check 2 (V8 remnants): **PASS** — zero TradingView/lightweight-charts/Hebrew strings
- Check 3 (V9 integration): **PASS** — TopBar, Layer0Strip, SidePanel, Chart V5a, COLORS all present
- Check 4 (Build): **PASS** — Compiled successfully
- Check 5 (Regression): **PASS** — uat_prompt_4.sh 13/13 PASS
- Check 6 (WS relay): **PASS** — relay_running: true
- Check 7 (Status): **PASS** — all 7 layers healthy

Manual verification pending: User must open browser to confirm visual.
