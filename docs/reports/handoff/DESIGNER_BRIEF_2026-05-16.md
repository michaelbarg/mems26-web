# MEMS26 UI/UX Designer Brief

**Date:** 2026-05-16  
**Audience:** Human UI/UX designer  
**Product:** MEMS26 autonomous MES futures trading dashboard  
**Current UI entry point:** `frontend/v9/src/v9/components/layout/V9Dashboard.tsx`

---

## 1. Project One-Pager

MEMS26 is a local autonomous trading system for MES futures. It reads market data from Sierra Chart, passes that data through a Python bridge, computes system state in a FastAPI backend, and displays the result in a Next.js dashboard. The dashboard is for a single trader who supervises the system while it decides whether market conditions are safe, whether a setup exists, and how an active trade is being managed.

The system has three future operating modes, each gated by evidence before the next mode is allowed:

- `SHADOW`: log-only, no execution.
- `DEMO`: Sierra Chart simulation execution.
- `LIVE`: Sierra Chart live execution.

The project is currently pre-SHADOW for operational activation. The six systems are considered system-reliability READY, but live/replay validation and data-integrity fixes are still required before meaningful SHADOW accumulation.

Architecture:

```text
Sierra Chart ACSIL DLL
        |
        v
Python Bridge: bridge/json_bridge.py
        |
        v
FastAPI Backend: backend/main:app
        |
        v
Next.js Frontend: frontend/v9
        |
        v
Local dashboard using lightweight-charts
```

Absolute product rule: no external chart vendor, no TradingView SaaS, no Bloomberg, and no remote market-data source. The approved chart library is `lightweight-charts` because it is an open-source local rendering library. Its attribution/logo must be hidden in the production dashboard.

---

## 2. The 6 Systems

### S1 Day Type

S1 Day Type is an observing/advisory system. It classifies the session into a day type and provides context to firing systems. It does not hard-block trades. Main UI output: day type label, confidence/probability, opening/IB context, directional certainty, and whether the classification is still pending or degraded. Current readiness: READY.

Suggested UI states: `READY`, `PENDING`, `DEGRADED`, `UNKNOWN`. Use calm contextual colors because S1 is advisory, not a fire signal.

### S2 Five-Min Patterns (T1)

S2 Five-Min Patterns is a firing system. It looks for 5-minute patterns such as reactive and initiative long/short setups, then routes valid fire events through pre-fire validation. Main UI output: current pattern, direction, quality/confluence score, mode, and fire readiness. Current readiness: READY.

Suggested UI states: `IDLE`, `READY`, `FIRED`, `BLOCKED`, `PENDING`. Because S2 can trigger trades, it needs stronger visual urgency than observing systems.

### S3 Footprint (T3)

S3 Footprint is a firing system. It detects microstructure signals such as absorption, stacked imbalance, sweep-return, and exhaustion. Main UI output: signal name, direction, strength, supporting evidence, and whether it was routed through pre-fire validation. Current readiness: READY.

Suggested UI states: `IDLE`, `READY`, `FIRED`, `BLOCKED`, `DEGRADED`. This cube should communicate order-flow pressure clearly without overwhelming the trader.

### S4 Woodies CCI (T2)

S4 Woodies CCI is a firing system. Per D-074, Woodies operates on the 5-minute timeframe, not 30-minute. It evaluates Woodies patterns and a decision tree before routing valid setups. Main UI output: detected Woodies pattern, CCI condition, direction, decision-tree stage status, and `ready_to_route`. Current readiness: READY.

Suggested UI states: `NEUTRAL`, `READY`, `FIRED`, `BLOCKED`, `PENDING`. The Woodies display should be visually distinctive because the user specifically wants a "Woody" character/mascot associated with this system.

### S5 TPO Profile

S5 TPO Profile is an observing/advisory system. It provides market-structure context such as POC, VAH, VAL, IB high/low, POC migration, tails, and single prints. Main UI output: POC/VAH/VAL levels, POC migration direction, IB locked/building state, and profile context. Current readiness: READY.

Suggested UI states: `READY`, `BUILDING`, `PENDING`, `DEGRADED`. TPO should look like structural context, not a trade signal.

### S6 Killzone

S6 Killzone is an observing/advisory system with gate-like behavior for session timing. It describes the current market zone and whether the current time is appropriate for firing. Main UI output: current zone, edge class, gate open/closed, time remaining, and next zone. Current readiness: READY.

Suggested UI states: `OPEN`, `CLOSED`, `WEEKEND`, `MAINTENANCE`, `DEGRADED`. This system should be immediately visible because it explains why otherwise-good setups may not be allowed.

---

## 3. Data Contracts The UI Consumes

The designer does not need exact JSON payloads for visual work, but every design should assume the frontend receives data from local backend endpoints only.

### Chart And Price

- `/api/v9/chart/bars5min`  
  Returns 5-minute OHLCV bars for the main candle chart. Known current issue: some historical bars may contain bad outlier lows and must be fixed before SHADOW validation.

- `/api/v9/live_price`  
  Returns current/last local price. Known current issue: this endpoint has shown stale data and needs backend validation.

### System Current State

- `/api/v9/day_type/current`  
  S1 Day Type state.

- `/api/v9/five_min/current`  
  S2 Five-Min Patterns state.

- `/api/v9/footprint/current`  
  S3 Footprint state.

- `/api/v9/woodies/current`  
  S4 Woodies CCI state.

- `/api/v9/tpo/current`  
  S5 TPO Profile state. Known current issue: `bars_processed_today=0` has been observed.

- `/api/v9/killzone/current`  
  S6 Killzone state.

### Trade State

- `/api/v9/trades/active`  
  Current active-trade endpoint found in backend. Use this for active trade overlay and side-panel trade details unless engineering later exposes a gateway-specific path.

- `/api/v9/gateway/active_trade`  
  TBD by engineer. Mentioned as a desired gateway-oriented contract, but not confirmed as the implemented path.

### Layout/Status Supporting Endpoints

- `/api/v9/status`  
  Mode, backend health, bridge/subscriber status.

- `/api/v9/layer0/state`  
  Layer 0 chop indicators and state.

- `/api/v9/veto/state`  
  Suffering-side/veto state.

---

## 4. Current Dashboard Layout

The current active dashboard is `V9Dashboard`, not the older `DashboardLayout`. It renders a full-height desktop layout with a top bar, Layer 0 strip, main chart area, right side panel, trade strips below the chart, and a price debug console.

```text
+--------------------------------------------------------------------------------+
| TopBar: connection | mode | MES | day type | killzone | price | WR | PnL        |
+--------------------------------------------------------------------------------+
| Layer0Strip: chop indicators | suffering side | news window                     |
+-------------------------------------------------------------+------------------+
|                                                             | ActiveTradeCard  |
| Main chart area: ChartV5b                                  +------------------+
| - lightweight-charts candles                               | System switcher  |
| - integrated volume histogram                              +------------------+
| - TF selector: 3m/5m/15m/30m/1h                             | System lens      |
| - TPO price lines: POC/VAH/VAL/IBH/IBL                      | Now/Plan/Shadow  |
|                                                             | Hist/Chart tabs  |
+-------------------------------------------------------------+------------------+
| TradeHistoryStrip                                                              |
+--------------------------------------------------------------------------------+
| ShadowSoakStrip                                                                |
+--------------------------------------------------------------------------------+
| PriceDebugConsole                                                              |
+--------------------------------------------------------------------------------+
```

### Top Bar

`TopBar` shows connection state, a mode badge, symbol `MES`, day-type summary, killzone status, chart-type buttons, live price, backend/bridge status dots, win-rate today, PnL/trade counts, and navigation to trades/library. The designer should simplify its visual hierarchy so the most important items are visible at a glance: mode, live connection, price, active trade, and emergency/risk state.

### Main Chart Area

`ChartV5b` is the active chart. It uses `lightweight-charts` locally, displays candles, a volume histogram inside the chart, timeframe buttons, a killzone label, a time-to-next-bar countdown, live price updates, and TPO price lines. The chart is the primary trading surface and should remain visually dominant.

### Right Panel

`SidePanel` contains `ActiveTradeCard`, a system switcher, and a system-specific lens. The switcher/lens supports S1 through S6. Today this panel is functional but could be redesigned into a clearer "six system cubes plus selected-system detail" experience.

### Lower Strips

`TradeHistoryStrip` and `ShadowSoakStrip` appear below the chart. They are secondary surfaces and should not compete visually with the main chart or active trade state.

---

## 5. What's Missing Or Broken

### Active Trade Visualization Layer

The chart needs a clear active trade overlay: entry marker, stop line, target lines, exit marker, active direction coloring, and visual fade after exit. The trader should never need to read a table to understand whether the system is in a trade.

### Woody Mascot

The user wants a "Woody" mascot in the left/side area. This should be a friendly trader character associated with Woodies, but it should not look childish or distract from risk. It should react to system state.

### Six System Cubes

The current system switcher/lens exists, but the user wants all six systems visible at a glance as status cubes/cards. The right panel should make it obvious which systems are ready, pending, degraded, firing, or blocking.

### Mode Badge

Mode exists in `TopBar`, but it must become more prominent. SHADOW/DEMO/LIVE should be impossible to miss. LIVE should have the strongest visual treatment because it means real money risk.

### Reason Tree Expansion

The UI needs a clear reason-tree drawer explaining why a setup fired or did not fire. For example, Woodies should show A1..A7 and B1..B14 delegation status with `PASS`, `FAIL`, `PENDING`, `DEGRADED`, or `DELEGATED`.

### Branding And Attribution

No external service branding is allowed. The chart may use `lightweight-charts`, but no visible TradingView watermark/logo should appear in the trading dashboard.

---

## 6. Design Tasks For The Human Designer

### 1. Active Trade Overlay

Input data:

- Active trade direction: `LONG` or `SHORT`.
- Entry price and timestamp.
- Initial/final stop.
- T1/T2/T3 target prices.
- Target hit timestamps.
- Exit timestamp, exit price, exit reason, PnL.
- Dominant system: S2, S3, or S4.

Interaction model:

- Entry triangle appears on the candle where the trade opened.
- Stop line is horizontal and visually different from targets.
- Target lines show T1/T2/T3 and change state when hit.
- Active candles are tinted green for long and red for short.
- After exit, the trade overlay fades but remains reviewable.
- Clicking the trade marker opens a detail panel in the right side panel.

Success criteria:

- Trader can tell within one second whether there is an active trade.
- Entry, stop, targets, and exit are unambiguous.
- Overlay does not hide candle price action.
- Long and short states remain readable in dark mode.

### 2. Woody Mascot

Input data:

- S4 Woodies state.
- Current detected pattern.
- Fire readiness.
- Blocked/pending/degraded reason.

Interaction model:

- Mascot sits in the side panel or a compact left/status area.
- It reacts to system state:
  - calm: neutral/no setup.
  - alert: setup forming.
  - firing: setup passed validation.
  - blocked: setup rejected or market closed.
  - degraded: data missing or stale.
- Hover/click reveals the Woodies reason summary.

Visual style options:

- Cartoon: warm, expressive, friendly trader character; highest personality.
- Line-art: minimal monochrome/duotone character; most professional.
- Pixel: retro trading terminal style; playful but compact.

Success criteria:

- Adds personality without reducing seriousness.
- Does not distract during LIVE mode.
- Makes S4 status memorable and immediately recognizable.

### 3. Six System Cubes In Right Panel

Input data:

- S1-S6 current state.
- Readiness or degraded/pending status.
- Last-update timestamp.
- Main metric per system.
- Optional fire/block reason.

Each cube should show:

- System ID and name.
- Role: observing or firing.
- Status: `READY`, `PENDING`, `DEGRADED`, `FIRED`, `BLOCKED`, `IDLE`.
- Main metric.
- Last update age.
- Small role indicator: firing vs observing.

Option A: 2x3 grid of equal-size cards.

```text
+-----------+-----------+
| S1 Day    | S2 5-Min  |
+-----------+-----------+
| S3 Foot   | S4 Woody  |
+-----------+-----------+
| S5 TPO    | S6 KZ     |
+-----------+-----------+
```

Best for: balanced overview and compact layout.

Option B: vertical stack with priority sizing.

```text
+-----------------------+
| S2 Five-Min   large   |
+-----------------------+
| S3 Footprint  large   |
+-----------------------+
| S4 Woodies    large   |
+-----------------------+
| S1 | S5 | S6 compact  |
+-----------------------+
```

Best for: emphasizing firing systems that can generate setups.

Option C: hex-tile cluster with status halos.

```text
      [ S2 ]
[ S1 ]     [ S3 ]
      [ S4 ]
[ S5 ]     [ S6 ]
```

Best for: distinctive cockpit feel. Use only if it remains readable and does not waste space.

Success criteria:

- All six systems visible without scrolling.
- Firing systems are visually distinct from observing systems.
- Degraded/stale data is obvious.
- Clicking any cube opens that system's lens/reason detail.

### 4. Mode Badge

Input data:

- Current mode: `SHADOW`, `DEMO`, or `LIVE`.
- Backend health/connection status.
- Whether the system is allowed to advance modes.

Interaction model:

- Always visible in the header.
- Click opens mode controls and explanation.
- SHADOW is neutral/gray or muted yellow.
- DEMO is blue/cyan.
- LIVE is red and visually serious.

Success criteria:

- Trader can identify mode instantly.
- LIVE mode cannot be mistaken for simulation.
- Mode badge does not imply SHADOW/DEMO/LIVE is active before the user explicitly enables it.

### 5. Reason Tree Drawer

Input data:

- Firing system decision result.
- Stage labels and statuses.
- Pre-fire validator result.
- Gateway route result.
- Advisory context from S1/S5/S6.

Interaction model:

- Drawer opens from the right or bottom when a fire/block event is clicked.
- Shows tree of conditions with status chips.
- Collapsed view shows only failure/block reason.
- Expanded view shows full path:
  - S4 Woodies: A1..A7 and B1..B14 delegation.
  - S2 Five-Min: pattern/confluence/pre-fire.
  - S3 Footprint: detector evidence/pre-fire.

Success criteria:

- Trader understands "why fired" or "why blocked" without reading logs.
- PASS/FAIL/PENDING/DEGRADED states are visually distinct.
- The drawer supports post-trade review.

---

## 7. Technical Constraints

- Desktop-first product. Mobile is not required.
- Primary theme is dark mode. Light mode may be secondary.
- Frontend stack: React + Next.js 16 App Router.
- Styling: Tailwind CSS and existing design tokens. Avoid hardcoded hex in final implementation.
- Charting: use `lightweight-charts` only. Do not introduce another charting library.
- Data source: local backend only.
- Do not design around external widgets, embedded iframes, or vendor chart UIs.
- The UI should tolerate pending/stale/degraded data and make that status visible.
- Do not assume SHADOW/DEMO/LIVE are already operational.
- Avoid tiny unreadable text in critical states. This is a trading cockpit, not a dense analytics report.

---

## 8. Acceptance Criteria

- All six systems are visible at a glance with clear status and role.
- Active trade state is unambiguous on the chart.
- Entry, stop, targets, and exit markers are visually clear.
- Mode is obvious at a glance.
- LIVE mode is visually unmistakable.
- No external service branding appears in the dashboard.
- The chart remains local and uses `lightweight-charts`.
- Reason tree can explain why a setup fired, blocked, or stayed pending.
- Degraded/stale data is visible and not silently treated as normal.
- Designer provides a Figma file plus 2-3 PNG mockups per major layout option.

---

## 9. Proposed Designer Deliverables

1. Current-state cleanup mockup based on `V9Dashboard`.
2. Active-trade overlay mockup on the chart.
3. Three right-panel options for six system cubes.
4. Woody mascot concepts in three styles: cartoon, line-art, pixel.
5. Mode badge/header redesign.
6. Reason-tree drawer design.
7. Dark-mode component library for:
   - system cube.
   - status chip.
   - fire/block badge.
   - active trade marker.
   - target/stop line.
   - stale-data warning.
8. Redline/spec page for engineer handoff.

---

## 10. Open Questions For The Engineer

1. Is `/api/v9/trades/active` the canonical active-trade endpoint, or should a gateway-specific `/api/v9/gateway/active_trade` endpoint be added?
2. What exact status enum should every system cube use across S1-S6?
3. Which timestamps should the UI treat as stale: 5 seconds, 30 seconds, 60 seconds, or per-endpoint thresholds?
4. Should observing systems ever show `BLOCKED`, or should that label be reserved for firing systems only?
5. What is the canonical color-token map for S1-S6?
6. Should the active trade overlay show only the latest trade or allow review of recent closed trades?
7. Should target lines show contract-level state C1/C2/C3, or only aggregate T1/T2/T3?
8. Should the Woody mascot appear only for S4 or act as a general assistant for the whole dashboard?
9. What is the safest visual treatment for LIVE mode that is strong but not distracting?
10. Should the designer preserve the current right-side lens tabs (`Now`, `Plan`, `Shadow`, `Hist`, `Chart`) or replace them with a new interaction model?

