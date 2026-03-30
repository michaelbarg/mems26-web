# MEMS26 AI Trading System

## What This System Does

Real-time MES (Micro E-Mini S&P 500 Futures) trading dashboard with AI-powered setup detection.

Data flows: **Sierra Chart → Bridge → Redis → Backend API → Frontend Dashboard**

The system identifies 5 trading patterns in real-time, displays them on a candlestick chart, and provides entry/stop/target levels with trade management (C1/C2/C3 partial exits).

---

## Architecture

```
Sierra Chart (Windows/CrossOver)
  └─ MES_AI_DataExport.cpp → mes_ai_data.json (every 3s)

Bridge (Mac local)
  └─ json_bridge.py → Redis (Upstash)
     ├─ mems26:latest (current snapshot, 1s)
     └─ mems26:candles (960 × 3min bars, 48h)

Backend (Render)
  └─ main.py (FastAPI)
     ├─ GET /market/latest → Redis snapshot
     ├─ GET /market/candles → 960 historical bars
     ├─ GET /market/analyze → Claude AI signal
     ├─ POST /ingest → bridge writes live data
     ├─ POST /ingest/history → bulk candle load
     └─ GET/POST /trades → trade journal

Frontend (Netlify)
  └─ Dashboard.tsx (~2900 lines) + LightweightChart.tsx (~440 lines)
```

### File Responsibilities

| File | Role |
|------|------|
| `sc_study/MES_AI_DataExport.cpp` | Sierra Chart C++ study. Exports: OHLCV, CVD, VWAP, CCI, Market Profile, Woodies Pivots, IB, Day Type, Order Flow, Candle Patterns, Footprint (200 bars), Order Fills |
| `bridge/json_bridge.py` | Reads Sierra JSON, enriches with session state (ON high/low, daily open, reversals), builds 3min candles, writes to Redis, detects trades from fills |
| `backend/main.py` | FastAPI server. Reads from Redis, serves to frontend. Claude AI analysis endpoint. Trade journal (Redis-based). Footprint storage |
| `frontend/src/components/Dashboard.tsx` | Main app. Setup detection (calcSetups), historical sweep scanner (scanHistoricalSweeps), probability calculator, traffic light, day type bar, trade journal UI, pattern detection |
| `frontend/src/components/LightweightChart.tsx` | Candlestick chart (Lightweight Charts v4.1.3). Level lines, sweep markers, entry/stop/C1/C2/C3 price lines, click-to-select sweeps |
| `render.yaml` | Render deployment config for backend |
| `netlify.toml` | Netlify deployment config for frontend |

---

## Setup Detection (calcSetups)

Scans live bar + last 10 candles against 12+ levels. Returns opportunity direction + score.

### 5 Patterns (priority order)

1. **Sweep** — Wick breaks level by 0.5+ pts, candle closes back over. Classic liquidity sweep.
2. **Rejection** — Touches level (±1pt), long wick (>1.5x body), closes in reversal direction. Hammer/shooting star at key level.
3. **Momentum** — 2+ candles in one direction, then strong reversal bar with delta >100. Trend exhaustion reversal.
4. **Bounce** — Price within 2pt of level, previous bar slowing (small delta), current bar reverses. Support/resistance bounce.
5. **Breakout** — Previous bar on one side of level, current bar breaks through with volume >1.3x and confirming delta. Continuation after level break.

### Levels Checked
- **Fixed**: PDH, PDL, ONH, ONL, IBH, IBL, VWAP, POC, VAH, VAL, Session High, Session Low
- **Dynamic**: Prices touched 3+ times in last 50 bars (rounded to 0.5pt)

### Scoring
- 3 critical checks: pattern detected, price correct side of level, delta confirms
- 2 bonus checks: volume >1.2x, reversal candle pattern
- All criticals pass: 45-100% score
- Missing critical: max 40%
- Opportunity threshold: 60% (shown on traffic light)

### Trade Management
- **Entry**: Current price
- **Stop**: Sweep bar low/high ± 0.25
- **C1** (50% exit): R:R 1:1, move stop to breakeven
- **C2** (25% exit): R:R 1:2
- **C3** (25% runner): Woodies R1/S1 or R:R 1:3

---

## Historical Scanner (scanHistoricalSweeps)

Scans all 960 candles for past sweep and rejection events. Shows as small dots on chart, click to see details.

Same levels as calcSetups + level touch counting. Score threshold: 55. Min gap between same-level events: 4 bars.

---

## What Changed (Conversation Log)

### Bridge
- Added `json_bridge.py` to git repo (was only local)
- Fixed double-encoded candles in Redis (json= vs data=)
- Fixed history loading: direct Redis push instead of fragile API URL encoding
- Keep existing Redis candles when history file is stale
- Seed candles from Sierra footprint (200 bars) on startup
- Added `session_min` to trade context

### Sierra Chart Study
- Increased footprint from 10 to 200 candles (configurable input)
- Fixed CrossOver path: use `/users/michael/...` not `C:\...`

### Backend
- Fixed `footprint_summary` undefined in /market/analyze (caused 500)
- Added candle double-encoding tolerance in /market/candles parser
- Trade store with SQLite (backend/engine/trade_store.py) — created but not deployed (old repo version)

### Frontend — calcSetups
- Rewrote from 4-setup array (Liq Sweep/VWAP/IB/CCI) to single Liq Sweep focused object
- Added 12+ levels (was only PDH/PDL/ONH/ONL)
- Added dynamic multi-touch levels
- Added rejection pattern detection
- Added momentum reversal, bounce, breakout patterns
- Live bar included in scan (was missing — only Redis candles)
- Score cap at 40% when critical fails (was 45%)

### Frontend — Traffic Light
- Now uses calcSetups (real-time) instead of AI signal (was broken without /market/analyze)
- Shows opportunity direction + score + level name

### Frontend — Chart
- Level lines: dotted, transparent (66 alpha), thin
- Sweep entry/stop/C1/C2/C3 shown as horizontal price lines
- Historical sweep events shown as tiny dots (click to select)
- Markers: SWEEP on sweep candle, ENTRY on confirmation candle
- Correct marker positions for SHORT (stop above, targets below)

### Frontend — Side Panel
- Sweep events list with confirmation badge
- C1/C2/C3 card with pts/usd/description
- Level touches display
- Active setup with status tracking (T1_HIT/STOPPED)
- Time estimation for targets
- Removed SetupScanner (old 4-setup grid)

---

## Open Issues

### High Priority
- **Build may fail**: check Netlify deploy after each push. Common: missing TypeScript variables after refactor
- **AI analyze sometimes slow**: Claude API timeout. Backend returns 500 if no API key or prompt error
- **Candle gap**: if bridge stops, there's a gap in candle history. Bridge doesn't backfill

### Medium Priority
- **No alert sounds**: sweep detection is visual only. Need audio notification for score >= 80
- **No AI supervisor**: planned but not built. Should check setup validity every 30s
- **Trade journal**: SQLite version built for old backend, current backend uses Redis. Not fully integrated
- **scanHistoricalSweeps**: doesn't include momentum/bounce/breakout patterns (only sweep + rejection)

### Low Priority
- **Pattern detection (detectPatterns)**: basic chart patterns exist but accuracy unknown
- **Day type strategy**: DayTypeBar shows type but doesn't influence setup selection
- **CCI Turbo/ZLR**: available from Sierra but not used in current scoring
- **Footprint visualization**: data exists in Redis but not shown on chart

---

## Environment

- **Frontend**: Netlify, Next.js 14, `frontend/` directory
- **Backend**: Render, FastAPI + httpx, `backend/` directory
- **Bridge**: Local Mac, Python + aiohttp, `bridge/` directory
- **Sierra Chart**: CrossOver on Mac, paths use `/users/michael/SierraChart2/`
- **Redis**: Upstash (REST API)
- **AI**: Claude Sonnet 4.5 via Anthropic API

### Running the Bridge
```bash
cd bridge
python3 json_bridge.py
```

### Git
```bash
cd /Users/michael/Downloads/mems26_web_git
git add . && git commit -m "message" && git push origin main
```
Netlify auto-deploys on push. Render auto-deploys on push.
