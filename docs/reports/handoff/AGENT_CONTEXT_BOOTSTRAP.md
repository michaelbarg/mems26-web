# Agent Context Bootstrap — MEMS26

**Purpose:** paste this BEFORE any task you give to a fresh AI agent (Claude web, ChatGPT, another Cursor session, etc.) so it doesn't hallucinate canonical names or contradict past decisions.

**How to use:**
1. Copy everything between `PASTE FROM HERE` and `PASTE TO HERE`.
2. Paste it at the top of the new agent's message.
3. Add a blank line.
4. Type your actual task (e.g. "Prepare a list of frontend components", "Audit the bridge for X", etc.).
5. Send.

If the agent says "I cannot read those files" — paste the contents of the listed files inline before your task, in this order: Master Index V2 first, then `NEXT_CHAT_PROMPT.md`, then `compliance_manifest.yaml` for the relevant system.

**Author:** Cursor agent
**Last updated:** 2026-05-16

---

## PASTE FROM HERE

You are about to help with MEMS26, an autonomous MES futures trading system. Before you do anything, read this context fully. **Do not invent component names, system names, or decisions. Use canonical names exactly. If anything is unclear, ASK rather than guess.**

### What MEMS26 is

A local autonomous trading system for MES (Micro E-mini S&P 500) futures. Data flows **Sierra Chart (ACSIL C++ DLL) → Python Bridge (`bridge/json_bridge.py`) → FastAPI Backend (`backend/main:app`, port 8000) → Next.js Frontend (`frontend/v9`, port 3000)**. All local; no third-party data dependency. Repository at `/Users/michael/Downloads/mems26_web_git`, current working branch `stabilize/mems26-local-truth-2026-05-16`.

### The six systems (canonical names — use exactly these)

| ID | Name | Role |
|----|------|------|
| S1 | Day Type | **OBSERVING / advisory** — classifies the day, provides context |
| S2 | Five-Min Patterns (T1) | **FIRING** — produces setups |
| S3 | Footprint (T3) | **FIRING** — produces setups |
| S4 | Woodies CCI (T2) | **FIRING** — produces setups |
| S5 | TPO Profile | **OBSERVING / advisory** |
| S6 | Killzone | **OBSERVING / advisory** |

Firing systems generate trade setups. Observing systems provide context and may degrade a setup's confidence but **never hard-block**.

### Trading modes (strict, ordered gates)

`SHADOW` → `DEMO` → `LIVE`. **NOT activated yet.** Currently the system is in a pre-SHADOW state. Anything you write that assumes SHADOW/DEMO/LIVE is running is wrong.

### Architectural rules (binding decisions — do not contradict)

- **D-074:** Woodies (S4) operates on **5-minute** timeframe (not 30-minute). Any component that says "Woodies 30min" is wrong.
- **Charting:** `lightweight-charts` (open-source library from TradingView, runs locally) is approved. The TradingView platform itself (the cloud service) is NOT used. Don't list "TradingView" as a data source or dependency.
- **Single chart pane:** the active dashboard layout is `V9Dashboard` rendering only `ChartV5b`. The following are **deprecated / removed** from the active route — don't list them as current:
  - `ChartV5a` (kept as backup file only)
  - `VolumePanel`
  - `SystemPanelsBar`
  - `DashboardLayout` (older multi-pane layout, not wired)
  - `usePriceRestPoll` hook (deleted)
- **Pre-fire validation:** every firing system routes its fire through `pre_fire_validator` before `TradingGateway.route_setup()`. Don't bypass it.
- **Market clock:** there is a central `market_clock` service supporting `REALTIME` and `REPLAY` modes (Prompts P26a/26b). All time-sensitive logic must read from it, not `datetime.now()` directly.

### Current open issues (don't claim they're fixed)

1. `/api/v9/chart/bars5min` ships at least 3 outlier rows (low spikes ~7172.5–7180.25 vs neighbors at ~7460). Backend ingestion bug.
2. `/api/v9/live_price` is currently 64+ minutes stale.
3. `/api/v9/tpo/current` has `bars_processed_today=0` — daily aggregator stuck.

The above three are blockers before SHADOW. A fix is drafted as P27.5a (`docs/reports/handoff/MEGA_PROMPT_P27_5A.md`) but not yet executed.

### Required reading order (read fully BEFORE answering)

If you have file-read access, read these in this exact order:

1. `MEMS26_REGISTRY.yaml` (repo root) — requirements registry
2. `backend/v9/systems/*/compliance_manifest.yaml` — per-system specs (S1 through S6)
3. `docs/reports/handoff/NEXT_CHAT_PROMPT.md` — session snapshot + 6 hard rules
4. `docs/reports/handoff/SESSION_LOG_2026-05-16.md` — what changed today, what was removed
5. `docs/reports/handoff/GANTT_TO_LIVE.md` — 11-phase plan
6. `docs/reports/handoff/PROMPT_LIST_TO_LIVE.md` — P27.5a → P-L5 ordered prompts
7. `docs/reports/SYSTEM_COMPLETION_CONTROL_BOARD.md` — current readiness state per system
8. `MEMS26_FIRST.md` (if present in repo root, otherwise ask) — D-### decision log

**Master Index V2 and Constitution V3** are the authoritative spec. They may not be in the repo (they live on Google Drive). **If your task involves naming, taxonomy, scope, or governance, and Master Index V2 is not available to you, STOP and ask the user to paste it before proceeding.** Do not infer naming from the files above alone.

### Do-not list

- Do not list TradingView platform / TradingView Cloud as a dependency.
- Do not list `ChartV5a`, `VolumePanel`, `SystemPanelsBar`, `DashboardLayout`, or `usePriceRestPoll` as active components.
- Do not refer to Woodies as a 30-minute system.
- Do not claim SHADOW / DEMO / LIVE is active.
- Do not invent D-### decisions; if you need one, propose it explicitly with `(DRAFT — needs governance review)`.
- Do not invent compliance line items not in the manifests.
- Do not commit, push, or modify files unless the user explicitly asks.

### When you don't have enough context

Say "I need X before I can answer reliably" and stop. List exactly which document, file path, or D-### you need. Do not guess.

---

(USER'S ACTUAL TASK FOLLOWS BELOW)

## PASTE TO HERE
