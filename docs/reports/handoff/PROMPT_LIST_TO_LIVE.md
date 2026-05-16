**Status:** living document — update as the project advances
**Last updated:** 2026-05-16
**Author:** Cursor multitask session

# PROMPT_LIST_TO_LIVE — ordered prompts from "right now" to LIVE

Companion documents:

- [`NEXT_CHAT_PROMPT.md`](./NEXT_CHAT_PROMPT.md) — paste-and-continue prompt for the next session
- [`GANTT_TO_LIVE.md`](./GANTT_TO_LIVE.md) — phase view with exit criteria + mermaid timelines
- [`SESSION_LOG_2026-05-16.md`](./SESSION_LOG_2026-05-16.md) — what happened in session `2026-05-16`
- [`../SYSTEM_COMPLETION_CONTROL_BOARD.md`](../SYSTEM_COMPLETION_CONTROL_BOARD.md), [`../PROMPT27_REPLAY_VALIDATION_PLAN.md`](../PROMPT27_REPLAY_VALIDATION_PLAN.md), [`../PROMPT28_REPLAY_SMOKE_RUN.md`](../PROMPT28_REPLAY_SMOKE_RUN.md)

> Execute prompts strictly in order. Mark each one DONE in this file (and bump status in `GANTT_TO_LIVE.md`) before moving to the next. Every prompt body should be wrapped in a fresh worker / subagent and bounded by the canonical "Do NOT" list from [`NEXT_CHAT_PROMPT.md`](./NEXT_CHAT_PROMPT.md).

---

## Phase 0 — Backend data integrity (P27.5a → c)

### P27.5a — Backend bad-bar fix in `/api/v9/chart/bars5min`
**Phase:** 0 Backend data integrity
**Preconditions:** Bridge + Backend + Frontend healthy via `bash scripts/check_status.sh`; HEAD == `419f4cc` or later on `stabilize/mems26-local-truth-2026-05-16`; working tree clean.
**Goal:** Eliminate outlier rows returned by `/api/v9/chart/bars5min` (observed: bars with `low≈7172.5`/`7180.25` while surrounding window is `~7440–7476`, a ~300-point cliff). Client-side `looksOk` filter must become defense-in-depth, not the source of truth.
**Deliverable:** `docs/reports/PROMPT_27_5A_BAD_BAR_FIX.md` with root cause, fix diff, before/after sample payloads, and `tests/v9/api/test_chart_bars5min_integrity.py` (or equivalent) that fails on any row outside `low ≤ open,close ≤ high` and `(body - low) / body ≤ 2%` heuristic.
**Exit criteria:**
- Backend returns 240 consecutive bars with **zero** outliers over a full RTH day on replay.
- Client `ChartV5b.tsx` `looksOk` filter still in place but logs `0` filtered rows during normal operation.
- Pytest suite green; spec compliance unchanged.
**Notes / risks:** Root cause likely in the per-window 5-min aggregator UPSERT (`REQ-W5.4` in the registry) or stale rows surviving the session-cumulative cleanup. Do not touch the DLL or bridge stream — fix in `backend/v9/api/v9/bars_5min_history.py` and/or the ingestion path.

---

### P27.5b — Live-price freshness fix in `/api/v9/live_price`
**Phase:** 0 Backend data integrity
**Preconditions:** P27.5a DONE.
**Goal:** During RTH, `/api/v9/live_price` must return `age_ms < 60 000`. Observed in session 2026-05-16: `age_ms ≈ 64 minutes`. Client now drops anything `> 60s`, but the source pipeline must produce a fresh tick.
**Deliverable:** `docs/reports/PROMPT_27_5B_LIVE_PRICE_FIX.md` + a smoke script `scripts/uat_prompt_27_5b.sh` that asserts `age_ms < 60000` ten times in a row during RTH; weekend behavior unchanged (gracefully `null` or `stale=true`).
**Exit criteria:**
- During RTH, ten back-to-back `/api/v9/live_price` calls return `age_ms < 60 000`.
- Outside RTH, endpoint is explicit about stale state (does not pretend to be live).
- Replay clock mode (`MEMS26_CLOCK_MODE=REPLAY`) still drives `now_et` via `MarketClock` (regression check).
**Notes / risks:** Likely in `bridge/v9_streams/` live tick stream or in `backend/v9/api/v9/price_routes.py` cache. Verify the bridge actually pushes to the live-price topic and the backend cache TTL is sensible.

---

### P27.5c — TPO aggregator daily roll-over fix (`bars_processed_today=0`)
**Phase:** 0 Backend data integrity
**Preconditions:** P27.5a + P27.5b DONE.
**Goal:** `/api/v9/tpo/current` must report `bars_processed_today > 0` during RTH and a reasonable carry-over over the weekend. Observed: `bars_processed_today=0`, implying the daily aggregator never ran today.
**Deliverable:** `docs/reports/PROMPT_27_5C_TPO_AGGREGATOR_FIX.md`; tests under `tests/v9/systems/tpo/` proving (a) day-roll trigger fires at session start (ET), (b) `bars_processed_today` increments per 5-min bar, (c) POC/VAH/VAL recompute on each tick.
**Exit criteria:**
- During RTH, `bars_processed_today` increments each 5-min bar.
- Over weekend, value is non-negative and not lying (either last-RTH value with timestamp, or `0` plus an explicit `since=<ts>` field).
- S5 TPO compliance tests still green (`pytest tests/v9/compliance/v1_generated/test_system5_v1.py`).
**Notes / risks:** Likely tied to `MarketClock` day-roll or to consuming the wrong feed (woodies_5min instead of `chart_5min`). Cross-check with `PROMPT27_REPLAY_VALIDATION_PLAN.md` § S5.

---

### P27.5z — SCB + handoff refresh
**Phase:** 0 Backend data integrity
**Preconditions:** P27.5a + b + c DONE.
**Goal:** Update [`../SYSTEM_COMPLETION_CONTROL_BOARD.md`](../SYSTEM_COMPLETION_CONTROL_BOARD.md) "Remaining Blockers → Before SHADOW" to reflect the three fixes; mark the three issues in [`NEXT_CHAT_PROMPT.md`](./NEXT_CHAT_PROMPT.md) and `GANTT_TO_LIVE.md` as DONE.
**Deliverable:** Updated docs.
**Exit criteria:** All three documents agree; no stale "PARTIAL" markers for the three issues.
**Notes / risks:** Pure documentation; no source changes.

---

## Phase 1 — Replay smoke run

### P28 (re-run on clean data) — Replay Smoke Run
**Phase:** 1 Replay validation
**Preconditions:** Phase 0 complete; replay clock mode wired (already done in P26a/b); `bash scripts/run_stage.sh status_check` GREEN.
**Goal:** Re-execute the existing [`../PROMPT27_REPLAY_VALIDATION_PLAN.md`](../PROMPT27_REPLAY_VALIDATION_PLAN.md) smoke against the cleaned data path.
**Deliverable:** Refreshed [`../PROMPT28_REPLAY_SMOKE_RUN.md`](../PROMPT28_REPLAY_SMOKE_RUN.md) (overwrite the existing 11/11 PASS report with the post-P27.5 run; keep both `Pre-fix` and `Post-fix` columns for audit if useful).
**Exit criteria:** All 6 systems produce ≥1 valid event during replay; no `pre_fire_validator` errors; reason tree explainable for every fire; `bars_processed_today > 0` on replay.
**Notes / risks:** Use `bash scripts/run_stage.sh prompt_26_replay_clock_smoke` and `... status_check`. Stop on first critical failure.

---

## Phase 2 — Replay scenario pack

### P29 — Replay Scenario Pack (10 scenarios)
**Phase:** 2 Replay validation
**Preconditions:** P28 GREEN on clean data.
**Goal:** Validate the full pipeline against 10 historical scenarios, each documenting input stream, expected S1/S5/S6 advisory context, expected S2/S3/S4 firing behavior, expected reason tree, expected route/block outcome, and pass/fail criteria.
**Deliverable:** `docs/reports/PROMPT29_REPLAY_SCENARIO_PACK.md` with sub-sections P29.1..P29.10 (Trend day, Balance/Nontrend, Opening drive, S2 Five-Min setup, S3 Footprint/Reversal setup, S4 Woodies pattern, Killzone context change, TPO location/value context, Missing data/degraded, pre_fire/risk-blocked setup).
**Exit criteria:** 10/10 PASS; reason trees auditable per scenario; no DEMO/LIVE path engaged.
**Notes / risks:** Each scenario should be reproducible from a fixture in `tests/v9/replay/` or from the existing `data/` historical bars. Keep `MEMS26_CLOCK_MODE=REPLAY`.

---

## Phase 3 — Data collection package

### P29.5 — Data Collection Package
**Phase:** 3 Data collection
**Preconditions:** P29 GREEN.
**Goal:** Define and wire the storage/log contract for the soak: bars per stream + stream health + S1..S6 state + pre_fire decisions + gateway dry-run decisions + reason trees + lifecycle events.
**Deliverable:** `docs/reports/PROMPT29_5_DATA_COLLECTION_PACKAGE.md` with: (a) per-event JSON schema, (b) sink (SQLite/Postgres table list + Redis topic list), (c) retention policy, (d) example queries (per-system PnL aggregation, decision-tree breadcrumb, lifecycle).
**Exit criteria:** 1-hour replay produces parseable artifacts in all sinks; `scripts/uat_prompt_29_5.sh` validates schema completeness.
**Notes / risks:** Aligns with `REQ-DATA-001..010` in `MEMS26_REGISTRY.yaml`. Predicted vs Actual (`REQ-DATA-004..006`) is a stretch goal — can be deferred to a P29.6.

---

## Phase 4 — Frontend polish (deferrable, can run in parallel with Phase 5)

### P-UI-1 — Reassess `SystemPanelsBar` form
**Phase:** 4 Frontend polish
**Preconditions:** Data shape from P29.5 known.
**Goal:** Decide whether the removed bottom S1–S6 strip should return as (a) sidebar tabs, (b) overlay on the chart, (c) compact top-bar chips, or (d) stay removed and be reachable only via Tab navigation.
**Deliverable:** `docs/reports/PROMPT_UI_1_SYSTEM_PANELS_DECISION.md` with mockups and a recommended path; if option (a)/(b)/(c) selected, also produce a wiring sketch against the live `/api/v9/<sys>/current` endpoints.
**Exit criteria:** Decision recorded; if a new component is to be built, it is gated behind a flag (`NEXT_PUBLIC_V9_SHOW_SYSTEM_PANELS=true`) so the current single-pane layout is preserved by default until designer review.
**Notes / risks:** **Deferrable.** SHADOW activation does not require this. Do **not** re-introduce VolumePanel as a separate component — overlay the volume histogram inside `ChartV5b` if needed.

### P-UI-2 — Reassess Volume panel (overlay vs. separate)
**Phase:** 4 Frontend polish
**Preconditions:** P-UI-1.
**Goal:** Confirm volume rendering strategy (overlay histogram inside `ChartV5b` per current design, or separate pane).
**Deliverable:** Brief decision in `docs/reports/PROMPT_UI_2_VOLUME_DECISION.md`; if overlay is kept, ensure no second lightweight-charts watermark renders.
**Exit criteria:** Only one chart instance on screen; no duplicate "T7" watermark; volume readable.
**Notes / risks:** **Deferrable.**

### P-UI-3 — SHADOW dashboard spec + designer handoff
**Phase:** 4 Frontend polish
**Preconditions:** P29.5.
**Goal:** Produce a complete UI/UX spec for the SHADOW dashboard (top bar, chart pane, banners, strips, side panel, reason-tree drawer, blocked-setup drawer, replay timeline). Package it for a designer.
**Deliverable:** `docs/reports/PROMPT_UI_3_SHADOW_DASHBOARD_SPEC.md` with screen inventory, data sources per widget, color/typography tokens, accessibility notes.
**Exit criteria:** Designer can start without further questions; spec references actual endpoints and event schemas from P29.5.
**Notes / risks:** **Deferrable.** Aligns with `REQ-UI-001..014` in the registry.

---

## Phase 5 — SHADOW activation gate

### P-S0 — SHADOW activation
**Phase:** 5 SHADOW activation
**Preconditions:** Phase 3 complete; Michael's explicit go in chat; `git status` clean.
**Goal:** Flip `MEMS26_MODE=shadow` in `.env`, restart services, verify gateway is record-only.
**Deliverable:** `docs/reports/PROMPT_S0_SHADOW_ACTIVATION.md` with: env diff, restart log, `/api/v9/gateway/status` snapshot, first SHADOW trade recording proof.
**Exit criteria:**
- `/api/v9/status` reports `mode=shadow`.
- `/api/v9/gateway/status` shows `shadow_active_count` increasing; `demo_slot=null`, `live_slot=null`.
- No file written to Sierra's `trade_command.json`.
- Bridge + backend + frontend all green.
**Notes / risks:** This is a **mode switch**, not a code change. Do not modify executor code in this prompt.

---

## Phase 6 — SHADOW soak (≥10 trading days)

Each P-Sx is a parameterized daily run with the same structure. Mark each one DONE only after the EOD review passes.

### P-S1 — SHADOW soak day 1
**Phase:** 6 SHADOW soak
**Preconditions:** P-S0 complete; RTH session expected today.
**Goal:** Run SHADOW for one trading day; capture trade log, reason trees, pre_fire blocks, gateway records.
**Deliverable:** `docs/reports/shadow/SHADOW_SOAK_DAY_01_YYYY-MM-DD.md` (date in filename); daily EOD: trade count, win rate, max DD, anomalies.
**Exit criteria:** Day completes without bridge/backend/frontend crash; trade log non-empty (or explainable zero); reason trees auditable.
**Notes / risks:** If any system anomaly, pause and triage before P-S2. Re-use `scripts/run_stage.sh status_check` between trades for health.

### P-S2 — SHADOW soak day 2
*(same template as P-S1)*

### P-S3 — SHADOW soak day 3
*(same template as P-S1)*

### P-S4 … P-S10 — SHADOW soak days 4–10
*(same template; aggregate weekly EOD in `docs/reports/shadow/WEEK_SUMMARY_*.md`)*

### P-S-REVIEW — SHADOW soak EOD review and DEMO go/no-go
**Phase:** 6 SHADOW soak
**Preconditions:** ≥10 SHADOW days, including ≥20 closed trades.
**Goal:** Aggregate all SHADOW data, compare against `REQ-GOVERN-002` "Before DEMO" gate (≥7 days SHADOW soak with ≥20 trades closed).
**Deliverable:** `docs/reports/shadow/SHADOW_SOAK_FINAL.md` + recommendation (proceed to P-D0 / extend soak / pause + fix).
**Exit criteria:** Michael signs off in writing in the report.

---

## Phase 7 — DEMO activation

### P-D0 — DemoExecutor wired to Sierra Sim
**Phase:** 7 DEMO activation
**Preconditions:** P-S-REVIEW recommends GO.
**Goal:** Wire `DemoExecutor` to write `trade_command.json` consumed by Sierra Sim; enable for ONE firing system at a time (suggested order: S4 Woodies → S2 Five-Min → S3 Footprint).
**Deliverable:** `docs/reports/PROMPT_D0_DEMO_ACTIVATION.md` with first DEMO round-trip proof (signal → command file → Sierra Sim fill → trade close → PnL).
**Exit criteria:**
- `gateway_status.demo_slot` cycles between `null` and the active trade.
- SHADOW continues recording in parallel ("first wins" gate enforced).
- Round-trip latency measured (`T0..T5` per `REQ-INFRA-006`).
- No risk-cap breach.
**Notes / risks:** This is the first real outbound write. Do not enable for multiple systems simultaneously.

---

## Phase 8 — DEMO soak + bug-fix loop

### P-D1 … P-D7 — DEMO soak days 1–7
*(same template as P-S1; additionally compare SHADOW expected vs DEMO actual fills nightly per `REQ-DATA-011` EOD analysis)*

### P-D-REVIEW — DEMO soak EOD review and LIVE pre-flight go/no-go
**Phase:** 8 DEMO soak
**Preconditions:** ≥7 DEMO days; slippage within budget.
**Deliverable:** `docs/reports/demo/DEMO_SOAK_FINAL.md` with recommendation.
**Exit criteria:** Michael signs off; SHADOW-vs-DEMO slippage delta documented.

---

## Phase 9 — LIVE pre-flight

### P-L0a — Risk caps audit
**Phase:** 9 LIVE pre-flight
**Preconditions:** P-D-REVIEW GO.
**Goal:** Audit `REQ-S-061` ($250/day, 5 trades, 2 contracts, <14:30 ET) and `REQ-S-063` (risk gating order: time > news > loss > trades > consecutive > margin > manual > slot).
**Deliverable:** `docs/reports/PROMPT_L0a_RISK_CAPS_AUDIT.md` + a `tests/v9/services/test_risk_caps_live.py` suite that exercises every gate in both PASS and BLOCK direction.
**Exit criteria:** Every gate path covered by an automated test; manual UAT script `scripts/uat_prompt_l0a.sh` runs green.

### P-L0b — Kill-switch (UI button + API + CLI)
**Phase:** 9 LIVE pre-flight
**Preconditions:** P-L0a GREEN.
**Goal:** Implement a single kill-switch with three independent triggers (top-bar "PANIC" button, `POST /api/v9/admin/kill`, `bash scripts/kill_live.sh`). Each must immediately set `MEMS26_MODE=shadow`, flatten any open LIVE position via Sierra command, and write an audit row.
**Deliverable:** `docs/reports/PROMPT_L0b_KILL_SWITCH.md`; UAT script `scripts/uat_prompt_l0b.sh`.
**Exit criteria:** Kill-switch tested against Sierra Sim with an open position; flat in <2 s; audit row present.

### P-L0c — Alerting (Slack health + trade events)
**Phase:** 9 LIVE pre-flight
**Preconditions:** P-L0b.
**Goal:** Slack webhook receives: bridge/backend/frontend health flips, every LIVE trade open/close, every risk-cap block, kill-switch activation.
**Deliverable:** `docs/reports/PROMPT_L0c_ALERTING.md`; webhook URL set in Keychain (see `REQ-INFRA-020`); test message lands in Michael's Slack.
**Exit criteria:** All event categories verified in Slack.

### P-L0d — Redundancy review
**Phase:** 9 LIVE pre-flight
**Preconditions:** P-L0c.
**Goal:** Verify bridge `launchd` plist is enabled (`com.mems26.bridge`), `restart_all.sh` is idempotent, `MEMS26 Restart.command` works on a fresh boot, and there is a documented recovery procedure for "Cursor sandbox wedged" (the failure mode seen 2026-05-16).
**Deliverable:** `docs/reports/PROMPT_L0d_REDUNDANCY.md` with a printable runbook (Activity Monitor steps, `Cmd-Q` Cursor steps, fresh `start_all.sh` steps).
**Exit criteria:** Runbook stress-tested by killing services from Activity Monitor and recovering.

### P-L0e — UAT sign-off (Michael)
**Phase:** 9 LIVE pre-flight
**Preconditions:** P-L0a..d complete.
**Goal:** Michael performs manual end-to-end UAT and signs the report.
**Deliverable:** `docs/reports/PROMPT_L0e_UAT_SIGN_OFF.md` (signed).
**Exit criteria:** Signed report.

---

## Phase 10 — LIVE micro-position trial

### P-L1 — One micro-contract LIVE on one system
**Phase:** 10 LIVE micro-trial
**Preconditions:** P-L0e signed.
**Goal:** Enable LIVE for ONE system (recommended S4 Woodies) at 1 micro-contract for ONE trading day; all other systems remain SHADOW; abort on any anomaly via kill-switch.
**Deliverable:** `docs/reports/PROMPT_L1_LIVE_MICRO_TRIAL.md` with full trade log, latency T0..T5, PnL, anomalies.
**Exit criteria:**
- ≥1 closed LIVE micro trade (or zero with explanation if no setup fired).
- No risk-cap breach.
- No executor anomaly.
- Bridge/backend/frontend stable.

---

## Phase 11 — LIVE full activation

### P-L2 — Enable S2 LIVE (1 micro)
**Phase:** 11 LIVE full activation
**Preconditions:** P-L1 successful; Michael go.
**Deliverable:** `docs/reports/PROMPT_L2_S2_LIVE.md`.
**Exit criteria:** Same as P-L1, per system.

### P-L3 — Enable S3 LIVE (1 micro)
*(same template)*

### P-L4 — Enable S4 LIVE at scale (decide contract size with Michael)
*(same template; size step-up gated by report)*

### P-L5 — Ongoing SHADOW shadow-account parallel + EOD compare
**Phase:** 11 LIVE full activation
**Preconditions:** P-L2..L4 successful.
**Goal:** Keep SHADOW running in parallel forever as the "what-if oracle"; nightly compare SHADOW theoretical vs LIVE actual PnL; alert on systemic divergence.
**Deliverable:** Recurring `docs/reports/live/LIVE_DAY_*.md`; weekly aggregate.
**Exit criteria:** This is the steady state — no exit, only continuous review.

---

## Conventions for adding prompts

- New P-IDs follow the pattern `P<phase><suffix>` (e.g., `P-S-FIX-01` for a SHADOW soak fix, `P-L0c-1` for a sub-step of L0c).
- Each new prompt must specify **Phase, Preconditions, Goal, Deliverable, Exit criteria, Notes/risks** — same template as above.
- Add the prompt to `GANTT_TO_LIVE.md` in the relevant phase block.
- When a prompt completes, add `**Status:** DONE (commit `<sha>`, report `docs/reports/...`)` to its header.

*No SHADOW / DEMO / LIVE is enabled at the time this document was created.*
