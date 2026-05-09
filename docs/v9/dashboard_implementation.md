# V9 Dashboard Implementation — W4

## Version: v9.0.0
## Created: 2026-05-09

## Overview

TradingView-style dark theme dashboard for MES futures trading, built with Next.js 16 + Tailwind + Zustand + TanStack Query + lightweight-charts v5.

## Stack

| Layer | Technology |
|-------|-----------|
| Framework | Next.js 16.2.6 (App Router, Turbopack) |
| Styling | Tailwind CSS (dark theme, `#0d1117` base) |
| State | Zustand (4 stores) |
| Server data | TanStack Query |
| Charts | lightweight-charts v5 |
| Layout | react-resizable-panels |
| Icons | lucide-react |

## Directory Structure

```
frontend/v9/src/
├── app/
│   ├── globals.css          # Tailwind + CSS vars
│   ├── layout.tsx           # Root layout
│   ├── providers.tsx        # QueryClient provider
│   ├── page.tsx             # Dashboard (/)
│   └── trades/page.tsx      # Trades view (/trades)
└── v9/
    ├── types/index.ts       # All TS types + system metadata
    ├── stores/
    │   ├── marketStore.ts   # Bars, levels, EMAs
    │   ├── systemStore.ts   # Signals, markers, configs
    │   ├── tradeStore.ts    # Trades, account, filters
    │   └── layoutStore.ts   # UI state (persisted)
    ├── lib/
    │   ├── api.ts           # REST API client
    │   └── websocket.ts     # WebSocket manager
    ├── hooks/
    │   └── useWebSocket.ts  # WS hook
    └── components/
        ├── layout/
        │   ├── DashboardLayout.tsx  # Main resizable layout
        │   └── TopBar.tsx           # 40px top bar
        ├── chart/
        │   ├── ChartArea.tsx        # Main candlestick chart
        │   ├── TPOLines.tsx         # Dynamic POC/VAH/VAL
        │   ├── VegasEMAs.tsx        # 6 trailing EMAs
        │   ├── StaticLevels.tsx     # PDH/PDL/ONH/ONL/Open
        │   ├── RightSideLabels.tsx  # Sierra-style stacked
        │   └── TradeMarkerOverlay.tsx  # Colored trade markers
        ├── volume/
        │   └── VolumePanel.tsx      # Volume + cumulative delta
        ├── panels/
        │   ├── SystemPanelsBar.tsx   # Container
        │   ├── SystemPanelWrapper.tsx # Shared wrapper
        │   ├── System1Panel.tsx      # Day Type (firing)
        │   ├── System2Panel.tsx      # 5-min Patterns (firing)
        │   ├── System3Panel.tsx      # Footprint (observer)
        │   ├── System4Panel.tsx      # Woodies CCI (firing)
        │   ├── System5Panel.tsx      # TPO Profile (data)
        │   └── System6Panel.tsx      # Killzone (gate)
        ├── settings/
        │   └── SettingsDrawer.tsx    # Per-system config drawer
        └── trades/
            ├── TradesView.tsx       # Full trades page
            ├── TradeFilters.tsx     # Mode/System/Outcome/Date
            ├── TradesTable.tsx      # Trade list table
            └── TradeDetailsModal.tsx # Trade detail modal
```

## System Colors

| System | Color | Role |
|--------|-------|------|
| S1 Day Type | `#58a6ff` blue | Firing |
| S2 5-Min Patterns | `#56d364` green | Firing |
| S3 Footprint | `#d2a8ff` purple | Observer |
| S4 Woodies CCI | `#fb950b` orange | Firing |
| S5 TPO Profile | `#79c0ff` light blue | Data |
| S6 Killzone | `#8b949e` gray | Gate |

## Trade Markers

- Color = system color
- Border style = mode (solid=LIVE, dashed=SHADOW, none=SIM)
- Icons: ▶ entry, ✓ win, ✗ stop

## TPO Lines

Dynamic — POC/VAH/VAL update via WebSocket `/ws/v9/levels`.
Lines are recreated on every price change using `createPriceLine` API.

## WebSocket Channels

| Channel | Data |
|---------|------|
| `/ws/v9/bars/5min` | Real-time 5-min bars |
| `/ws/v9/bars/tick_reversal` | Real-time tick reversal bars |
| `/ws/v9/markers/{system_id}` | System markers (1-6) |
| `/ws/v9/trades` | Trade updates |
| `/ws/v9/levels` | Dynamic levels (POC/VAH/VAL/PDH/PDL/ONH/ONL) |
| `/ws/v9/account` | Account status |

## API Endpoints Used

All via `lib/api.ts` with Bearer token auth.

## V8 Features NOT Included

V9 is a parallel namespace. V8 (`frontend/src/v8/`) is untouched.
V9 excludes: old Angular components, V8 chart library, V8 routing.

## Running

```bash
cd frontend/v9
npm install
npm run dev     # http://localhost:3000
npm run build   # Production build
```

Environment variables:
- `NEXT_PUBLIC_API_URL` — Backend API base (default: `http://localhost:8000`)
- `NEXT_PUBLIC_WS_URL` — WebSocket base (default: `ws://localhost:8000`)
- `NEXT_PUBLIC_BRIDGE_TOKEN` — Auth token (default: `michael-mems26-2026`)
