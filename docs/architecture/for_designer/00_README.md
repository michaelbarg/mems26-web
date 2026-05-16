# MEMS26 — Designer Handoff Package

**Status:** living document — update as the project advances
**Last updated:** 2026-05-16
**Audience:** External UI/UX designer joining mid-project
**Project owner:** Michael (single user, single machine, single account)
**Repository:** `/Users/michael/Downloads/mems26_web_git` (local-only until LIVE)

---

## 1. What this package is

A self-contained brief for a designer who has never seen the project. After reading these 5 documents, the designer should be able to start on a Figma file without asking the dev team architectural questions.

| # | File | What it covers | Read time |
|---|---|---|---|
| 00 | `README.md` (you are here) | Index, glossary, brand & technical constraints, out-of-scope | 10 min |
| 01 | [`01_ARCHITECTURE.md`](./01_ARCHITECTURE.md) | System map, 6 systems overview, decision flow, mode states — all with mermaid | 20 min |
| 02 | [`02_SYSTEMS_SPEC.md`](./02_SYSTEMS_SPEC.md) | Per-system spec (S1–S6): role, inputs/outputs, API + sample JSON, current UI, visual gaps | 45 min |
| 03 | [`03_FRONTEND_AND_TOKENS.md`](./03_FRONTEND_AND_TOKENS.md) | Existing component inventory (80 files), design tokens, API inventory (25 endpoints), current dashboard layout | 30 min |
| 04 | [`04_DESIGN_BRIEF.md`](./04_DESIGN_BRIEF.md) | Screens to design, REQ-UI-001..014, open questions, success criteria, Figma deliverable format | 30 min |

Total: ~2.5 hours of reading. Re-read 04 last as it crystallizes the ask.

---

## 2. One-paragraph project context

MEMS26 is a **local autonomous trading system** for **MES (Micro E-mini S&P 500) futures**. It ingests live market data from **Sierra Chart** via a DLL → `bridge/json_bridge.py` → **FastAPI backend** → **Next.js (App Router) frontend**. There are **6 systems** that together produce one trading decision per setup; that decision flows through a **gateway** with three execution **modes** — `SHADOW` (log-only), `DEMO` (Sierra simulator), `LIVE` (real money). The project promotes strictly `SHADOW → DEMO → LIVE`, each gated by manual UAT approval and quantitative soak criteria. The current phase is **stabilizing the data pipeline** before SHADOW can begin accumulating evidence (see [`../../reports/handoff/GANTT_TO_LIVE.md`](../../reports/handoff/GANTT_TO_LIVE.md)).

---

## 3. Glossary (read this first)

### Market & trading

| Term | Meaning |
|---|---|
| **MES** | Micro E-mini S&P 500 futures contract (the one symbol this system trades) |
| **RTH** | Regular Trading Hours (09:30–16:00 ET for equity index futures) |
| **GLOBEX / Overnight** | The pre-RTH and post-RTH session |
| **T1 / T2 / T3** | First / second / third profit target on an open position |
| **Stop** | Stop-loss price; if hit, trade closes at a loss |
| **PnL** | Profit and Loss, in US dollars |
| **WR** | Win Rate, percent of trades closed with `pnl > 0` |
| **Drawdown (DD)** | Cumulative loss from peak equity; tracked per day and per soak |
| **Risk cap** | Hard daily limit (`$250/day, 5 trades, 2 contracts, 14:30 ET cutoff`) |
| **Tick (MES)** | 0.25 index points; 1 tick = $1.25 per micro contract |

### Profile & structure

| Term | Meaning |
|---|---|
| **TPO** | Time Price Opportunity — Market Profile chart of where the market spent time |
| **POC** | Point of Control — highest-volume / longest-time price in the profile |
| **VAH / VAL** | Value Area High / Low — boundaries of the 70% time/volume window |
| **IB** | Initial Balance — first hour's range (09:30–10:30 ET); width classified S/M/W/EW |
| **HVN / LVN** | High / Low Volume Node — clusters or gaps in the volume profile |
| **PD H / PD L / PD C** | Previous Day High / Low / Close — context levels for today's open |
| **ONH / ONL** | Overnight High / Low |
| **OPEN** | Today's RTH open price |

### Sierra Chart streams (what the bridge ingests)

| Stream | Bar type | Used by |
|---|---|---|
| `5min` (woodies_5min) | 5-minute OHLCV | S2, S4, S5 |
| `tick_reversal_15` | 15-tick reversal bars | S3 |
| `tick_reversal_12` | 12-tick reversal bars | S3 |
| `footprint` | Order-flow per bar | S3 |
| `imbalance_flags` | Stacked imbalances | S3 |
| `cumulative_delta` | Running buy-sell delta | S2, S3 |
| `volume_profile` | POC/VAH/VAL per period | S5 |
| `tpo` | TPO letters per price | S5 |
| `live_price` | Current tick | TopBar, ChartV5b |

### Decision pipeline

| Term | Meaning |
|---|---|
| **Firing system** | A system that emits trade setups (S2, S3, S4) |
| **Observing system** | A system that provides context but never fires (S1, S5, S6) |
| **Gate** | A boolean check that can BLOCK a fire (S6 Killzone WEEKEND / CLOSED; pre_fire validator) |
| **Setup** | A candidate trade emitted by a firing system, before validation |
| **Fire** | A setup that passed pre_fire validation and was routed to the gateway |
| **Pre-fire validator** | Service that runs cool-down, daily cap, stop-range, risk-cap checks before a fire is allowed |
| **TradingGateway** | The component that owns the three slots (SHADOW/DEMO/LIVE) and routes a fire to the correct executor |
| **Executor** | The component that turns a routed setup into an action — `ShadowExecutor` (DB write), `DemoExecutor` (Sierra Sim `trade_command.json`), `LiveExecutor` (real Sierra command) |
| **Reason Tree** | The structured audit log explaining why a setup did or did not fire — every decision branch is recorded |
| **First-wins** | The slot-locking rule: only one of SHADOW/DEMO/LIVE owns a trade at a time |
| **BarLevelDetector** | Closes open trades on T1/T2/T3 or stop hit; applies time-stops per Day Type |

### Operating modes

| Mode | What it does | Visual hint |
|---|---|---|
| `SHADOW` | Records what *would* have happened — **no order leaves the machine** | yellow `#facc15`, subtle |
| `DEMO` | Writes `trade_command.json` for Sierra **simulator** account | cyan `#06b6d4`, normal weight |
| `LIVE` | Writes `trade_command.json` for Sierra **real** account | red `#dc2626`, pulsing, prominent |

The promotion path is strictly **SHADOW → DEMO → LIVE**, never skipping, never simultaneous on the same setup.

---

## 4. Brand & technical constraints (non-negotiable)

| Constraint | Why |
|---|---|
| **Chart library: `lightweight-charts`** (TradingView Inc., Apache 2.0) | Open-source, local-only, no third-party data dependency. **Not** the TradingView widget. |
| **Dark mode only** | All trading happens at night relative to the user's chronotype; eye strain; matches `globals.css` `--bg-primary: #0d1117` baseline |
| **Desktop only** | Single-user local app; no mobile, no tablet, no responsive below ~1280 px |
| **English UI** | The system runs in English; the user (Michael) speaks Hebrew but works the UI in English |
| **No login / no auth** | Single user, single machine, `localhost:3000` only |
| **Local network only** | Backend bound to `127.0.0.1:8000`; frontend bound to `127.0.0.1:3000`; no public exposure until LIVE pre-flight is signed off |
| **Data source: Sierra Chart only** | No third-party live-data feeds (no Polygon, no Yahoo, no broker direct) |
| **Symbol: MES only** | The whole UI assumes one instrument |
| **Mode is global** | The whole UI shifts visual state when mode changes (yellow / cyan / red); not a per-system toggle |
| **Kill-switch must be one click** | One button reachable from every screen instantly demotes to SHADOW + flatten LIVE position |
| **Hebrew tab labels are allowed** | `REQ-UI-001` calls for Hebrew labels on the left tab nav specifically; all other strings stay English |

---

## 5. External references (request from Michael if needed)

These are the canonical UX specs already referenced in the codebase. They were not found locally during the 2026-05-16 session and likely live on Michael's Google Drive:

| Reference | Drive doc id | Status |
|---|---|---|
| **Master Visual Reference V5** | (not catalogued in `MEMS26_REGISTRY.yaml`; check Drive) | Referenced from `frontend/v9/src/v9/design/tokens.ts` |
| **Cockpit UX Spec V5** | `1saLdFQ_gqmcTCModM3RQZQ5Tt6mcBzN6pJ1_6fVEK58` | Referenced from `MEMS26_REGISTRY.yaml::REQ-UI-001..014` (sections 2–9) |
| **Specs delta / GAP doc** | `12-42kSgfzSN7uHsnr2F8Iw1FE-SQwkn2CAZa0sziTAI` | Referenced from `REQ-UI-009` |
| **Constitution V3 D-049** | (cross-cutting decision doc) | Referenced from `system_colors.ts` (defines firing vs observing) |

If any of these can be shared, do that first — this package was written assuming the designer does **not** have them, so anything the existing docs already pin down is restated here, but the original specs are the source of truth.

---

## 6. Out of scope (do **not** design)

- Mobile, tablet, or any layout below 1280 px wide
- Light theme
- Multi-account / account switching
- User registration, login, password reset
- Email or SMS notifications (Slack webhook is the only out-of-app alert channel)
- Backend admin console (this exists as `REQ-ADMIN-001..005` in the registry but is dev-internal, not user-facing)
- The Sierra Chart UI itself (the user runs Sierra in a separate window; we never style Sierra)
- The bridge / DLL internals (this is dev-only; the designer's UI never represents them directly except as a green/red dot in TopBar)

---

## 7. Where to start if you only have an hour

1. Skim sections 3 (Glossary) and 4 (Constraints) above.
2. Read [`01_ARCHITECTURE.md`](./01_ARCHITECTURE.md) — focus on the system map mermaid and the mode-states mermaid.
3. Jump to [`04_DESIGN_BRIEF.md`](./04_DESIGN_BRIEF.md) §2 ("Screens to design") and §3 ("Open questions").
4. Come back to [`02_SYSTEMS_SPEC.md`](./02_SYSTEMS_SPEC.md) and [`03_FRONTEND_AND_TOKENS.md`](./03_FRONTEND_AND_TOKENS.md) as references while you sketch.

---

## 8. Maintainer notes

- This folder is the canonical designer handoff. When the dev team makes a UI change that invalidates anything here, the file must be patched in the same PR (no stale references).
- When the designer delivers a Figma file, link it from [`04_DESIGN_BRIEF.md`](./04_DESIGN_BRIEF.md) §7 ("Deliverable").
- This package never carries new D-### decisions — it documents the project's existing decisions for the designer.

*No SHADOW / DEMO / LIVE is enabled at the time this document was created.*
