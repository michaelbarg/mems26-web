# Old Version Discovery Report
Date: 2026-05-21T10:00:00Z
Author: Claude Code
Phase: 2
Mode: READ-ONLY

## Method
Searched the canonical repo (`Downloads/mems26_web_git`) via git history, file system, and grep for: "journal", "netlify", "thunderous", "old", "legacy", "v8", "blasttt", "angular". Then discovered and analyzed the second repo at `Documents/GitHub/mems26-web` which contains the complete old/Netlify version.

## 1. Git History Findings

### Canonical repo (Downloads/mems26_web_git)
- **507 total commits**, all on V9 architecture (starting 2026-05-09)
- **First commit**: `02e793f init: import MES_AI_DataExport.cpp v3.0 (372 lines)`
- **Two branches**: `feature/v9_architecture_rebuild` and `stabilize/mems26-local-truth-2026-05-16`
- **Two tags**: `pre-prompt-1` and `v9-day2-start-2026-05-13`
- **No V8 code in git history** -- this repo was initialized fresh for V9
- **V8 references in commits**: Only 3 commits reference V8, all as "ported from V8":
  - `da11e3d W2.5 v9: historical backfill ported from V8`
  - `1f5a1a2 feat(T1.1): V8 Bridge Live Price Restoration`
  - `e2637dd feat(T1.2): V8 Bridge Modules Port`
- **No "netlify" or "thunderous" in any commit message**
- **No deleted V8 files** in git history (V8 was never in this repo)
- **Referenced tag `v8-final-20260509`** in `.claude/MASTER_DEV_SKILL.md` does NOT exist in this repo

### Key documentation references found in canonical repo
- `docs/v9/dashboard_implementation.md:114` -- "V9 is a parallel namespace. V8 (`frontend/src/v8/`) is untouched."
- `docs/spec_authority/MEMS26_FIRST.md:28` -- "Stack: Sierra Chart C++ DLL -> Python bridge (Mac) -> Redis -> FastAPI (Render) -> Next.js (Netlify - blasttt.com)."
- `docs/spec_authority/MEMS26_CONSTITUTION_V3_FINAL.txt:678` -- "Frontend: blasttt.com (Netlify)"
- `docs/reports/FULL_INVENTORY_2026-05-16.md:149` -- "Two repos: Downloads/mems26_web_git | Documents/GitHub/mems26-web | Downloads is canonical"

## 2. File System Findings

### In canonical repo (Downloads/mems26_web_git)
- **No netlify.toml** anywhere
- **No .netlify/ directory**
- **No old/legacy/archive directories** (only node_modules legacy artifacts)
- **No HTML mockup files** on disk (referenced in design spec but not present)
- **V8 sidebar remnants exist**: `frontend/v9/src/v9/components/sidebar/LeftTabs.tsx` + 15 tab components (disconnected from render tree per TECH_DEBT_LOG.md)

### Second repo discovered: `/Users/michael/Documents/GitHub/mems26-web`
- **This IS the old Netlify version** -- complete and intact
- Contains `netlify.toml`, `render.yaml`, `vercel.json`
- Backend CORS allows `https://thunderous-sopapillas-7ddb4b.netlify.app` (line 723 of backend/main.py)
- Domain: **blasttt.com** mapped to Netlify site **thunderous-sopapillas-7ddb4b**

## 3. Netlify Configuration

### From `/Users/michael/Documents/GitHub/mems26-web/netlify.toml`:
```toml
[build]
  base    = "frontend"
  command = "npm run build"
  publish = ".next"

[[plugins]]
  package = "@netlify/plugin-nextjs"
```

### Netlify site details:
- **Site name**: thunderous-sopapillas-7ddb4b
- **Custom domain**: blasttt.com
- **Auto-deploys**: from `main` branch pushes
- **No `.netlify/state.json`** found (likely gitignored)

## 4. Branch Comparison

### In canonical repo
- `feature/v9_architecture_rebuild`: older branch, ends around P30.8 era (sierra monolith refresh)
- `stabilize/mems26-local-truth-2026-05-16`: current branch, 303 files changed / +32,596 lines ahead
- Both branches share the same V9-only history; neither contains V8 code

### Between the two repos
The repos are **completely independent git histories**. The canonical repo was started fresh on 2026-05-09 for V9. The old repo (`Documents/GitHub/mems26-web`) has its own separate git history (could not run git log due to permissions -- the repo is present but read-only analysis was restricted to file system inspection).

## 5. Recovery Assessment

**CASE A: Old code found -- in a SEPARATE REPO (not git history)**

The old "Netlify version" / "V8" code is **fully recoverable** from:
```
/Users/michael/Documents/GitHub/mems26-web
```

This is not inside the canonical repo's git history. It is a separate, complete copy of the old codebase sitting in `Documents/GitHub/`. The project's own inventory doc (`FULL_INVENTORY_2026-05-16.md`) explicitly documents this: "Two repos | Downloads/mems26_web_git | Documents/GitHub/mems26-web | Downloads is canonical".

The referenced tag `v8-final-20260509` mentioned in `.claude/MASTER_DEV_SKILL.md` does NOT exist in either repo's tags (could only verify the canonical repo's tags directly).

## 6. Old Architecture (V8 / Netlify Version)

### Framework
- **Frontend**: Next.js 14.2.5 (App Router), React 18.3.1, Tailwind CSS 3.4.10
- **Chart**: lightweight-charts v4.1.3 (TradingView open-source)
- **Backend**: FastAPI (Python), deployed on Render
- **Charting supplement**: recharts (for analytics/journal charts)
- **Package version**: `mems26-dashboard` v3.0.0

### Pages
1. **`/` (Dashboard)** -- Main trading cockpit, ~5,118 lines in `Dashboard.tsx`
   - Real-time candlestick chart
   - 6 setup detection patterns (Sweep, Rejection, Momentum, Bounce, Breakout, Approaching)
   - Traffic light signal display
   - Claude AI integration for trade analysis
   - ON/OFF system toggle
   - Hebrew UI labels
2. **`/journal`** -- Trade journal with analytics
   - Trade history with P&L tracking
   - Day type badges
   - Chart visualizations (recharts: Line, Bar, Scatter, Pie)
   - ET timezone display

### Components (26 total, ~10,825 LOC)
| Component | Lines | Purpose |
|-----------|-------|---------|
| Dashboard.tsx | 5,118 | Main monolithic cockpit |
| LightweightChart.tsx | 1,414 | Candlestick chart with levels |
| chartpanel.tsx | 520 | Chart panel wrapper |
| AnalyticsTab.tsx | 439 | Analytics display |
| ActiveTradePanelV2.tsx | 372 | Active trade management |
| AttemptsTable.tsx | 317 | Trade attempts log |
| QualityScorePanel.tsx | 272 | Quality scoring display |
| PreEntryChecklist.tsx | 272 | Pre-entry verification |
| VegasTunnelPanel.tsx | 238 | Vegas tunnel indicator |
| + 17 more components | -- | TPO, Triggers, Day Type, etc. |

### Data Flow
```
Sierra Chart (C++ DLL) --> mes_ai_data.json (every 3s)
    |
    v
Bridge (json_bridge.py, local Mac)
    |-- ZMQ bridge (zmq_bridge.py) for live data push
    |-- Feature engineering: IB calc, Rev 15/22, CVD, Effort
    |-- POST to cloud every 1 second
    v
Render Backend (FastAPI, main.py ~4,716 lines)
    |-- Redis (Upstash REST API) for state
    |   |-- mems26:latest (current snapshot)
    |   |-- mems26:candles (960 x 3min bars, 48h)
    |   |-- mems26:candles:5m/15m/30m/1h (MTF aggregation)
    |   |-- mems26:footprint (200 bars)
    |-- Claude AI signal engine (Sonnet 4.5)
    |-- Trade journal (Redis-based, later PostgreSQL)
    |-- WebSocket broadcast to dashboard
    v
Netlify Frontend (Next.js, blasttt.com)
    |-- REST polling: /market/latest, /market/candles, /market/analyze
    |-- WebSocket: /ws for real-time updates
    |-- Setup detection runs CLIENT-SIDE (calcSetups in Dashboard.tsx)
```

**Key differences from V9:**
- V8 uses **Upstash REST API** for Redis (HTTP, not direct connection)
- V8 uses **3-minute candles** (V9 uses 5-minute)
- V8 has **client-side setup detection** (V9 moves this server-side)
- V8 has **Claude AI live analysis** endpoint (V9 replaces with rule-based systems)
- V8 bridge uses **ZMQ** for live data push alongside JSON file polling
- V8 has **single monolithic Dashboard.tsx** (V9 splits into modular components)
- V8 backend is a **single main.py** (V9 has modular FastAPI with SQLAlchemy models)

### Backend Architecture
- **Single file**: `backend/main.py` (~4,716 lines)
- **Engine**: `backend/engine/signal_engine.py` -- Claude AI-powered signal scoring (1-10)
- **Gates**: `backend/gates/suffering_side.py` -- trade filtering
- **Database**: PostgreSQL on Render (`render.yaml`)
- **Analytics**: `backend/analytics.py`
- **Day config**: `backend/day_config.py`
- **Quality**: `backend/quality_score.py`

### 6 Systems Support
The V8 version has a **different system model**. Instead of V9's 6 numbered independent systems (Day Type, 5-Min, Footprint, Woodies, TPO, Killzone), V8 uses:
- **Pattern-based detection** (6 pattern types in calcSetups)
- **Claude AI scoring** (1-10 scale)
- **Traffic light** signal visualization
- **No numbered system taxonomy** -- the 6-system architecture is a V9 invention

V8 does include relevant data feeds that map to V9 systems:
- Day Type (DayTypeBadge, DayTypeHero components)
- TPO/Profile data (TPOPanel)
- Woodies pivots (in market data feed)
- Vegas tunnel (VegasTunnelPanel)
- Quality score (QualityScorePanel)

### Schema Compatibility
V9 and V8 share the same PostgreSQL database with different table prefixes:
- V8 tables: no prefix (original tables)
- V9 tables: `v9_` prefix (11 new tables)
- Per `docs/v9/database_schema.md`: "V9 tables sit alongside V8 in the same PostgreSQL database. V8 tables are untouched."

The bridge was ported from V8 to V9 with documented differences (see `docs/v9/bridge_history.md`):
- V8: single `mes_ai_history.json` file, RPUSH to `mems26:candles`, no dedup
- V9: per-stream DLL export files (7 files), per-stream Redis keys, export_ts dedup

## Evidence

| Finding | Path/Reference |
|---------|---------------|
| Old repo location | `/Users/michael/Documents/GitHub/mems26-web` |
| Netlify config | `/Users/michael/Documents/GitHub/mems26-web/netlify.toml` |
| Netlify site ID | `thunderous-sopapillas-7ddb4b` (in backend CORS, line 723 of main.py) |
| Domain | `blasttt.com` (in MEMS26_FIRST.md, Constitution V3) |
| Render backend | `https://mems26-web.onrender.com` (in Dashboard.tsx line 21, journal/page.tsx line 11) |
| Two-repo documentation | `/Users/michael/Downloads/mems26_web_git/docs/reports/FULL_INVENTORY_2026-05-16.md` line 149 |
| V8 fallback tag reference | `/Users/michael/Downloads/mems26_web_git/.claude/MASTER_DEV_SKILL.md` line 8 (tag does not exist) |
| V8 cleanup in V9 | `/Users/michael/Downloads/mems26_web_git/docs/HOTFIX_4_3_REPORT.md` |
| Tech debt from V8 | `/Users/michael/Downloads/mems26_web_git/docs/TECH_DEBT_LOG.md` |
| Bridge port docs | `/Users/michael/Downloads/mems26_web_git/docs/v9/bridge_history.md` |
| Dashboard (old) | `/Users/michael/Documents/GitHub/mems26-web/frontend/src/components/Dashboard.tsx` (5,118 lines) |
| Backend (old) | `/Users/michael/Documents/GitHub/mems26-web/backend/main.py` (4,716 lines) |
| Journal page (old) | `/Users/michael/Documents/GitHub/mems26-web/frontend/src/app/journal/page.tsx` |

## Open Questions

1. **Is blasttt.com still live on Netlify?** The old repo exists locally but we don't know if the Netlify deployment is still active or if the domain is still pointed there. Michael should check `https://thunderous-sopapillas-7ddb4b.netlify.app` and `https://blasttt.com`.

2. **What happened to the `v8-final-20260509` tag?** Referenced in MASTER_DEV_SKILL.md but does not exist in the canonical repo's tags. Was it intended to be created in the old repo? Should it be created as a preservation marker?

3. **Is the old repo's git history accessible?** Permissions prevented running `git log` on it during this analysis. Michael should verify it has intact git history and consider whether it needs to be archived or if the current file state is sufficient.

4. **Is the Render backend (`mems26-web.onrender.com`) still running?** The old frontend points to it. If it's still active, V9's local-only bridge rule means the Render backend may be receiving no data. Should it be shut down to avoid confusion/cost?

5. **Are the V8 PostgreSQL tables still receiving writes?** V9 docs say V8 tables are "untouched" but the old backend may still be writing to them if Render is active.

6. **Should `Documents/GitHub/mems26-web` be archived?** The FULL_INVENTORY doc marks Downloads as canonical. The old repo may benefit from a final git tag (`v8-final`) and archival.

7. **V8 sidebar components in V9**: The V9 repo still contains 15 V8 sidebar tab components under `frontend/v9/src/v9/components/sidebar/` that were ported/copied into V9 but are disconnected from the render tree. Should these be cleaned up or preserved for reference?
