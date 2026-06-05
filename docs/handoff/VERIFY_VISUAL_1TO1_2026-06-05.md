# VERIFY -- Visual 1:1 Fidelity -- 2026-06-05

## Build Status (/build + dashboard tab)

### Changes (matching BUILD_STATUS_REDESIGN_MOCKUP_V2_2026-06-04.html)
- Token system: replaced old COLORS with mockup exact vars (--bg, --s1..s3, --line, --line2, --tp, --ts, --tt, --green, --amber, --red, --pend, --sys1-6, --mono, --sans, --r)
- Header: sticky, backdrop-filter blur(8px), rgba(11,11,13,.92) bg, 54px height, pulsing verdict dot
- Layout: 2-column grid (main + 296px right rail) on tree tab
- Context bar: direction agreement + day type + killzone status
- Blocker: gradient bg, chain visualization with ok/bad nodes
- Sources: 5-column grid
- System cards: 4px accent stripe, role badges with inset shadows, chevron rotation
- Steps: connected rail with 24px icons + 2px connector lines
- Right rail: status now / trade plans (pending) / freshness sparkline (SVG) / miss log
- Global Firewall: dashed border + pendD tint + checks grid
- Pending TARGETS/STOP: dashed border, schema grid
- Observer cards: 3-column grid, pendwire dashed border
- Dashboard tab: BuildStatusTab now renders BuildTreeView (unified, no legacy view)

### Typecheck
```
$ npx tsc --noEmit 2>&1 | grep build_tree
(no output -- zero errors)
```

## Trades (/trades)

### Changes (matching TRADES_PAGE_PROTOTYPE_2026-06-03.html)
- TradesView: scrollable column layout (max-width:1340px), proper header
- TradeFilters: .bar style with preset pills, separator dividers
- ExecModeToggle: segmented control (All/Parallel/Sequential) with comparison boxes
- EdgeKpiRow: .bar .edge flex row with sparkline
- EdgeMatrix: tab buttons + .card table + inline target dist bars + color legend
- TargetDistStrip: .panel with .hbar/.track bars per day-type + stacked overall bar
- HeatMaeStrip: SVG scatter plot (MAE vs exit-R)
- EquityCurveStrip: .panel card style, always visible
- StopBehaviorPanel: two-column .panel cards with track bars + calibration insight

### Typecheck
```
$ npx tsc --noEmit 2>&1 | grep -E "trades|Trades|Edge|Exec|Equity|Target|Heat|Stop"
(no output -- zero errors)
```

## NOT-DONE
- Side-by-side screenshot comparison: dev server not started per CLAUDE.md. Cowork should verify visually.
- Minor pixel differences may exist between mockup (static HTML) and React (dynamic data) -- e.g., mock data values vs live API data affecting column widths.
- EquityCurveStrip uses Recharts (existing) -- the mockup uses raw SVG. Visual may differ slightly in chart rendering.
