# MEMS26 AI Trading System

## What This System Does

Real-time MES (Micro E-Mini S&P 500 Futures) trading dashboard with AI-powered setup detection.

Data flows: **Sierra Chart → Bridge → Redis → Backend API → Frontend Dashboard**

The system identifies 6 trading patterns in real-time, displays them on a candlestick chart, and provides entry/stop/target levels with trade management (C1/C2/C3 partial exits).

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
  └─ Dashboard.tsx (~3100 lines) + LightweightChart.tsx (~470 lines)
```

### File Responsibilities

| File | Role |
|------|------|
| `sc_study/MES_AI_DataExport.cpp` | Sierra Chart C++ study. Exports: OHLCV, CVD, VWAP, CCI, Market Profile, Woodies Pivots, IB, Day Type, Order Flow, Candle Patterns, Footprint (200 bars), Order Fills |
| `bridge/json_bridge.py` | Reads Sierra JSON, enriches with session state (ON high/low, daily open, reversals), builds 3min candles, writes to Redis, detects trades from fills |
| `backend/main.py` | FastAPI server. Reads from Redis, serves to frontend. Claude AI analysis endpoint. Trade journal (Redis-based). Footprint storage |
| `frontend/src/components/Dashboard.tsx` | Main app. Setup detection (calcSetups), historical sweep scanner, setup accumulator, probability calculator, traffic light, day type bar, trade journal UI, pattern detection |
| `frontend/src/components/LightweightChart.tsx` | Candlestick chart (Lightweight Charts v4.1.3). Level lines, sweep markers, entry/stop/C1/C2/C3 price lines, detected setup markers, click-to-select sweeps |
| `render.yaml` | Render deployment config for backend |
| `netlify.toml` | Netlify deployment config for frontend |

---

## Setup Detection (calcSetups)

Scans live bar + last 10 candles against 14+ levels. Returns opportunity direction + score.

### 6 Patterns (priority order)

1. **Sweep** — Wick breaks level by 0.5+ pts, candle closes back over (same bar, next bar, or live price). Classic liquidity sweep.
2. **Rejection** — Touches level (±1pt), long wick (>1.5x body), closes in reversal direction. Hammer/shooting star at key level.
3. **Momentum** — 1+ candles in one direction, then reversal bar with delta >50. Trend exhaustion reversal.
4. **Bounce** — Price within 5pt of level, previous bar slowing (small delta), current bar reverses. Support/resistance bounce.
5. **Breakout** — Previous bar on one side of level, current bar breaks through with volume >1.3x and confirming delta. Continuation after level break.
6. **Approaching** — Price moving toward a level within 8pt. Early warning, lowest priority.

### Levels Checked
- **Fixed**: PDH, PDL, ONH, ONL, IBH, IBL, VWAP, POC, VAH, VAL, Session High, Session Low
- **Swing**: 30-bar swing low/high (SwL/SwH) — preserves levels that live ONL/SH moved past
- **Dynamic**: Prices touched 3+ times in last 50 bars (rounded to 0.5pt)

### Scoring
- 3 critical checks: pattern detected, price correct side of level, delta confirms (>50 / <-50)
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

## Setup Accumulator (DetectedSetup)

Setups are accumulated over time in a list (max 50). Each has a lifecycle:

```
detected → c1_hit → c2_hit (success)
detected → stopped (failure)
detected → expired (90 min no action)
```

Shown in Setups tab as "LIVE SETUPS" with status badges. Markers placed on chart at detection and entry candles.

---

## Historical Scanner (scanHistoricalSweeps)

Scans all 960 candles for past sweep and rejection events. Same expanded level set as calcSetups. Shows as small dots on chart, click to see details.

Score threshold: 55. Min gap between same-level events: 4 bars.

---

## AI Integration

- **On-demand**: "Ask AI Now" button calls /market/analyze → Claude Sonnet 4.5
- **Auto-fallback**: When calcSetups returns 'none', auto-calls AI every 60 seconds
- **Shows**: direction, score, rationale (Hebrew), wait_reason, entry/stop/T1/T2

---

## System ON/OFF

Toggle button in top bar. When OFF:
- All polling stops (fetchLive, fetchCandles, auto-AI)
- Render backend can sleep (no requests)
- Chart and data remain visible, no new updates
- Click ON to resume

---

## What Was Done (Session 30.03.2026)

### Bridge
- Added `json_bridge.py` to git repo
- Fixed double-encoded candles in Redis
- Fixed history loading: direct Redis push
- Keep existing Redis candles when history file stale
- Seed from Sierra footprint (200 bars) on startup

### Sierra Chart Study
- Increased footprint from 10 to 200 (configurable)
- Fixed CrossOver paths

### Backend
- Fixed `footprint_summary` undefined (caused 500 on /market/analyze)
- Added candle double-encoding tolerance

### Frontend — Setup Detection
- Rewrote calcSetups: 6 patterns, 14+ levels, swing levels
- Sweep detects delayed reversal (next bar or live price)
- Momentum: 1+ bar + delta 50 (was 2+ bars + delta 100)
- Bounce radius: 5pt (was 2pt)
- Approaching Level: early warning within 8pt
- Live bar included in scan
- Setup accumulator: tracks lifecycle, shows in setups tab

### Frontend — Display
- Traffic light uses calcSetups (real-time, not AI-dependent)
- Level lines: dotted, transparent, thin
- Entry/Stop/C1/C2/C3 as horizontal price lines
- Detected setup markers on chart candles
- Historical sweep dots (click to select)
- Sweep detail card with C1/C2/C3 + time estimates
- ON/OFF system toggle

### Frontend — AI
- Auto-AI fallback every 60s when no setup detected
- AI rationale displayed in signal tab
- "What's missing" section from Claude

---

## What To Do Next (Priority Order)

### 1. Alert Sounds
Add audio notification when setup detected with score >= 80. Browser notification API + sound file.

### 2. Improve Setup Accuracy
- Test patterns against historical data (backtest)
- Too many false positives from Approaching pattern — consider removing or making it info-only
- Momentum pattern may be too loose with delta 50 threshold

### 3. AI Supervisor
Every 30 seconds when setup is active, Claude checks if still valid. Recommends: HOLD / MOVE_BE / EXIT.

### 4. Trade Journal Integration
Connect detected setups to actual trade execution. Track P&L per setup type. Calculate real win rates.

### 5. Daily Summary
End-of-day report: setups detected, hit rate, P&L, best/worst setup type.

### 6. Visual Improvements
- Cleaner marker positioning on chart
- Setup type icons instead of text
- Mobile responsive layout

---

## Environment

- **Frontend**: Netlify, Next.js 14, `frontend/` directory
- **Backend**: Render, FastAPI + httpx, `backend/` directory
- **Bridge**: Local Mac, Python + aiohttp, `bridge/` directory
- **Sierra Chart**: CrossOver on Mac, paths use `/users/michael/SierraChart2/`
- **Redis**: Upstash (REST API)
- **AI**: Claude Sonnet 4.5 via Anthropic API
- **Git**: github.com/michaelbarg/mems26-web

### Running the Bridge
```bash
cd /Users/michael/Downloads/mems26_web_git/bridge
python3 json_bridge.py
```

### Git
```bash
cd /Users/michael/Downloads/mems26_web_git
git add . && git commit -m "message" && git push origin main
```
Netlify auto-deploys on push. Render auto-deploys on push.

---

## UI Flow Rule (added V6.5.6)

All vertical lists of dynamically-growing items MUST use:
- `flexDirection: 'column'` (NOT column-reverse)
- `justifyContent: 'flex-start'` (NOT flex-end/center)
- NO `marginTop: 'auto'` on children that flow naturally

New items append to the BOTTOM. Growth extends DOWN. Scroll extends downward. The TOP of the list stays anchored.

Applies to: BuildingNowSection, Signal tab section list, Sweep events list, Setups tab children, any panel that accepts items dynamically.

If content disappears from the top when new items load, this rule has been violated. Fix the parent flex direction, not child sizing.

## Backend /trade/execute Rule (added V6.5.6)

The backend MUST forward t1/t2/t3 from the frontend as-is. Do NOT recalculate targets. The frontend's `calcLevels()` computes correct C1/C2/C3 from the setup's entry/stop/risk. Backend recalculation caused the 7147.50 bracket bug (T1_MIN_PT=10pt override).

## Quick Commands

This repo has named commands defined in `docs/CC_COMMANDS.md`.
Validation protocol is in `docs/DATA_VALIDATION_PROTOCOL.md`.

When the user types any of these triggers, execute immediately without clarification:

| Trigger | Action |
|---------|--------|
| `בדיקת דופק` / `PULSE` / `dofek` | Run daily_check.sh |
| `STATUS` | Git status + last commits |
| `TODAY` | Today's performance metrics |
| `TRADES` | Last 10 trades with FULL timestamps |
| `V2-SIM` | Run V2 grid simulation |
| `RETRO` | Run multi-target retro |
| `BACKUP` | Run + verify backup |

Read `docs/CC_COMMANDS.md` and execute the defined action immediately.
Report in the specified format. Don't ask for clarification.

---

## Mandatory First Steps (Every Chat Session)

At the start of every chat session, automatically:

1. **Read the protocol:** `docs/DATA_VALIDATION_PROTOCOL.md`
2. **Read the commands:** `docs/CC_COMMANDS.md`
3. **Run PULSE:** `source ~/.mems26_env && ./scripts/daily_check.sh`
4. **Report status** in standard format
5. **Then wait** for user task

Do NOT ask permission to do these. They are mandatory and automatic.

---

## Security Rules (NEVER VIOLATE)

1. NEVER include `DATABASE_URL` value in any command or log
2. NEVER write secrets to files
3. NEVER push without user explicit approval
4. ALWAYS use `${DATABASE_URL}` substitution or `os.environ`
5. NEVER expose values in commit messages

---

## Trade Review Format (REQUIRED)

When showing trades to user, ALWAYS include for each trade:
- Date, Entry timestamp, Exit timestamp PER CONTRACT (t1/t2/t3/stop hit timestamps)
- Direction, Price ladder (entry, stop, T1, T2, T3)
- Day type, Killzone, Outcome
- PnL per contract + total
- Component scores (Vegas, TPO, FVG, Footprint), VWAP side
- Sierra Chart reference time

Without timestamps per contract, user cannot verify on Sierra Chart. This format is MANDATORY.
See `docs/DATA_VALIDATION_PROTOCOL.md` Layer 3 for full template.

---

## Working Style

- Hebrew responses for Hebrew users
- English code blocks
- Bash commands as single copy-paste blocks
- Use ASCII charts and visual aids
- Provide context + options + recommendation for decisions

---

## Current Sprint

Sprint 6 — Data Quality + Shadow Calibration
- Phase 3.2: Pure Observation (May 4-7)
- Phase 3.3: V2 Implementation (May 8-10)
- Target LIVE: May 28, 2026

## Key Files Reference

- Master Log: `MEMS26_LOG_2026-05-02.md`
- V2 Spec: `tools/multidim_sim/V2_SPEC_FINAL.md`
- Day Type: `MEMS26_DAY_TYPE_SPEC_V2.md`
- Health Check: `scripts/daily_check.sh`
- Validation Protocol: `docs/DATA_VALIDATION_PROTOCOL.md`
- Commands: `docs/CC_COMMANDS.md`
