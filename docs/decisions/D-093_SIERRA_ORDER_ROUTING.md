# D-093 — Sierra Order Routing (Pipeline 5)

**Status:** 🟡 LOCKED · scope-locked; two execution sub-decisions deferred to verify-first
**Date:** 2026-05-23
**Decided by:** Michael Barg (post-Pkg 0 strategic review)
**Supersedes:** stub status of `LiveExecutor`, `DemoExecutor`, `_execute_live`
**Related:** D-090 (Path A canonical · same drift pattern in gateway/) · D-091 (S2 LIVE scope) · D-092 (S4 Woodies update)
**Registry:** `docs/reports/MEMS26_SYSTEMS_DECISIONS_REGISTRY_2026-05-23.md` §Pipeline 5

> **🆕 Research artifact added 2026-05-24:** `docs/research/SIERRA_ORDER_ROUTING_RESEARCH_2026-05-24.md` (615 lines · ACSIL deep-dive · file bridge architecture · D-093.Q1 recommendation · gotchas checklist for P5-1). The research **proposes 3 corrections** to currently-locked items below — flagged inline with 🔄. **NO RE-LOCKS APPLIED YET** — pending Michael review.

---

## Context

Pre-LIVE planning discovered that **no MEMS26 trade ever reaches Sierra Chart's order routing**. Audit of `sc_study/MES_AI_DataExport.cpp` + the Python gateway/bridge layer revealed 4 distinct gaps:

### Gap 1 · DLL does not call any ACSIL order function

`MES_AI_DataExport.cpp:791-855` (T2.2 · "Trade Command Polling") reads `trade_command.json`, classifies the action, and writes `trade_result.json` with one of `ACK_SHADOW` / `ACK_CLOSE` / `ACK_CANCEL` / `ACK_MGMT`.

**Line 813-815 (verbatim):**
```cpp
// TODO: Implement actual Sierra order placement via
// sc.SubmitOrder() / sc.SubmitOCOOrder() when DEMO/LIVE mode enabled.
// For now: acknowledge receipt (SHADOW mode = paper only).
result_status = "ACK_SHADOW";
```

`rg "SubmitOrder|SubmitOCOOrder|PositionData|CancelOrder"` in `sc_study/MES_AI_DataExport.cpp` returns **zero hits** outside the TODO comment. **No order is placed, no position is queried, no order is cancelled.** This is true in every mode — SHADOW, DEMO, and LIVE.

### Gap 2 · Two `TradingGateway` implementations · only one is wired

| Path | Location | Lines | Wired by | Sophistication |
|------|----------|-------|----------|----------------|
| **Legacy** | `backend/v9/gateway/trading_gateway.py` | 379 | `backend/main.py:344` + 6 test files | DEMO writes Sierra command file; LIVE is in-method stub. |
| **New** | `backend/v9/services/trading_gateway/gateway.py` | — | 2 test files only · NOT wired in `backend/main.py` | Has W14 `RiskValidator` + W11 `TradeManager` integration via `executors/{shadow,demo,live}.py` but does NOT write Sierra command file. |

This is the same Path A/B drift pattern that D-090 resolved for S2. **Verification + decision deferred to P5-0a** (see Implementation).

### Gap 3 · 3 dead executor files in legacy gateway/

| File | Lines | Status |
|------|-------|--------|
| `backend/v9/gateway/live_executor.py` | 24 | STUB — logs warning · NOT imported anywhere in production code |
| `backend/v9/gateway/demo_executor.py` | 24 | STUB — logs info · NOT imported anywhere in production code |
| `backend/v9/gateway/shadow_executor.py` | 23 | STUB — logs info · NOT imported anywhere in production code |

The wired `backend/v9/gateway/trading_gateway.py` defines its own `_execute_demo` / `_execute_live` / `_execute_shadow` methods internally and does not import these 3 files. They are pure dead code.

### Gap 4 · `bridge/trade_commands.py::TradeCommandHandler` not wired

193-line module with full protocol (sha256 checksum · timeout polling · clean read/write) exists in `bridge/` but **no file in `bridge/` instantiates it on startup**. It is reachable only via direct import in tests.

---

## Decision

Build a complete Sierra order routing path in **9 packages** under "Pipeline 5". The packages span DLL (ACSIL), backend (Python), bridge (Python), and end-to-end UAT. Two sub-decisions are deferred to verify-first audits before execution.

**Sub-decisions deferred (verify-first):**

- **D-093.Q1 · Gateway canonicality** — CC performs a 4-step audit of `backend/v9/gateway/` vs `backend/v9/services/trading_gateway/`, produces a recommendation report `docs/reports/P5_0_GATEWAY_AUDIT.md`, then Michael selects canonical. **DO NOT delete either path** without Michael's explicit lock.
  - 🆕 **Research recommendation (2026-05-24):** Canonical = `backend/v9/services/trading_gateway/` (New). **OVERRIDDEN by P5-0 audit (2026-05-31):** the New path is **missing** the 5 safety gates (cooldown/SSV/cluster/chop/strict) that Legacy runs in production → a cutover would regress safety. See `docs/reports/P5_0_GATEWAY_AUDIT.md`.
  - 🔒 **LOCKED 2026-05-31 · Michael Barg — canonical = MERGE.** Base = **Legacy** (`backend/v9/gateway/trading_gateway.py`, keeps all 5 safety gates); extract **only** the `RiskValidator` (W14) from New and integrate into Legacy's `_execute_live()`. New gateway + executors become dead code, deleted AFTER the RiskValidator extraction (P5-2). No rewrite — one targeted integration.
- **D-093.Q2 · Sierra DEMO account** — 🔒 **RE-LOCKED 2026-05-31 · Michael Barg** (corrected to real setup)
  - Broker/account: **IronBeam · account `37138283` · Teton CME Routing**
  - **No Apex — confirmed Michael 2026-05-31.** BOTH `PA-APEX-125218-01` (demo
    placeholder) AND `APEX-125218-13` (the "LIVE account" string found in the New
    gateway/`executors/live.py`) are DEAD — delete on sight. There is **no separate
    LIVE account**: live = the SAME account `37138283` with the global Trade
    Simulation Mode toggle OFF. Sim = same account, toggle ON.
  - **No separate `[simulation]` route exists.** The selected Service is `Teton CME Routing [trading]` (the LIVE route). Sim vs live is controlled ONLY by Sierra's global **Trade Simulation Mode On** toggle (Trade menu). Same account + same `[trading]` route serve both sim and live — the toggle is the only separator.
  - **Michael owns the sim/live toggle** (his explicit responsibility, 2026-05-31).
  - ⚠️ **P5-1 HARD-GATE (mandatory safety):** the DLL MUST validate `sc.GlobalTradeSimulationIsOn() == true` before EVERY demo order and **refuse** if the toggle is off. Because there is no separate sim route, this gate is the ONLY code-level protection against accidentally routing a DEMO order to the live broker. This elevates the D-093 mode-mismatch gotcha from "important" to "critical".

**Locked items (no further decisions needed):**

- 🔄 **PROPOSED RE-LOCK (research §1.1+§5.1):** ACSIL bracket order = `sc.BuyEntry(NewOrder)` / `sc.SellEntry(NewOrder)` with directly-defined Attached Orders (`Target1Offset`/`Stop1Offset` on `s_SCNewOrder`) — **NOT** `sc.SubmitOCOOrder()`. `sc.SubmitOCOOrder()` is reserved for the three native `SCT_ORDERTYPE_OCO_*` parent types (BUY_STOP_SELL_STOP / BUY_LIMIT_SELL_LIMIT / BUY_STOP_LIMIT_SELL_STOP_LIMIT) — not for entry+stop+target brackets (Sierra calls those "Attached Orders"). 🔒 **LOCKED 2026-05-31 — BuyEntry+Attached** (dev/execution-mechanism decision · no strategy impact · same entry/stop/target).
- 🔄 **PROPOSED RE-LOCK (research §1.1+§5.3):** Order modification = `sc.ModifyOrder(NewOrder)` (direct modify · preserves exchange queue priority · avoids naked-position race) — **NOT** `sc.CancelOrder() + new sc.SubmitOrder()`. Note: research confirms `sc.SubmitOrder()` does NOT exist in ACSIL · use `sc.BuyEntry`/`sc.SellEntry`/`sc.BuyOrder`/`sc.SellOrder` instead. 🔒 **LOCKED 2026-05-31 — ModifyOrder** (dev/execution-mechanism decision · no strategy impact). Wiring in P5-4/P5-5.
- Position reconciliation via `sc.PositionData(account)` written to `position_state.json` (new export from DLL).
- Heartbeat: DLL exports last-seen timestamp; backend alerts if stale > 30s.
  🔒 **LOCKED 2026-05-31 · Michael — ALERT-ONLY (no auto-KILL).** Alerting ladder
  OK (5s emit · 30s → WARN · 120s → critical), but **NO automated flatten** on
  stale heartbeat. Rationale: (1) the only order path is the DLL file-bridge — a
  flatten command can't execute through a dead/stale DLL anyway; (2) avoids
  false-positive flattening on a transient glitch. On a stale-with-open-position
  alert, Michael flattens manually (Sierra Flatten button). Revisit auto-KILL only
  if a redundant order path or Sierra-side auto-flatten is added.
- Bridge `TradeCommandHandler` is canonical (already complete · just needs wiring on startup).
- Mode promotion ladder: SHADOW (live now) → DEMO (P5-1 deliverable) → LIVE (P5-8 deliverable).
  - 🆕 **Research mode-toggle map (§1.3):** `sc.SendOrdersToTradeService` MUST match global `Trade Simulation Mode On` — mismatch = silent rejection with only Trade Service Log entry. Bridge MUST validate at boot via `sc.GlobalTradeSimulationIsOn`.

---

## Implementation (9 packages)

| # | Package | CC Days | Deliverables |
|---|---------|---------|--------------|
| **P5-0** | Gateway reconciliation | 1.5 | **a)** Audit report `docs/reports/P5_0_GATEWAY_AUDIT.md` (4-step audit · KEEP/ADAPT/REPLACE/DEFER classification per path). **b)** Michael decision (D-093.Q1 lock). **c)** Delete the non-canonical path + 3 dead executor stubs (`live_executor.py`, `demo_executor.py`, `shadow_executor.py`). **d)** Update tests to import from canonical path only. |
| **P5-1** | DLL `sc.SubmitOCOOrder()` (DEMO) | 2 | Replace `MES_AI_DataExport.cpp:813-816` TODO with real ACSIL bracket order: entry + stop + T1, fills `s_SCNewOrder` struct from JSON fields, returns real Sierra order ID in `trade_result.json`. Only enabled when payload contains `"mode":"demo"` (LIVE deferred to P5-3). |
| **P5-2** | DLL result mapping | 1 | Replace placeholder `ACK_SHADOW` / `ACK_CLOSE` / `ACK_CANCEL` / `ACK_MGMT` with real states: `FILLED` / `REJECTED` / `PARTIAL` / `WORKING` / `CANCELLED`. Include `sc_order_id`, `fill_price`, `fill_qty`, `error_code` in result JSON. |
| **P5-3** | Backend LIVE wiring | 0.5 | `_execute_live()` in canonical gateway must call `command_from_setup(..., mode="live")` and write the Sierra command file (currently logs warning + returns). Gate on `BRIDGE_LIVE_ENABLED=1` env var (defaults off · safety). |
| **P5-4** | Position reconciliation | 1.5 | DLL T2.4 (new) exports `position_state.json` from `sc.PositionData(account)` every bar. Backend service `services/position_reconciler.py` (new) reads it · compares to `trades` table · raises `DRIFT_ALERT` if DLL reports flat but DB shows open trade (or vice versa). |
| **P5-5** | Order modification | 1 | DLL handles `MODIFY_STOP` / `MODIFY_TARGET` / `ARM_BE` / `SCALE_OUT` / `BAILOUT` actions: `sc.CancelOrder(stop_order_id)` + `sc.SubmitOrder(new_stop_price)`. Result JSON includes `previous_stop`, `new_stop`, `cancel_status`. |
| **P5-6** | Heartbeat + watchdog | 0.5 | DLL writes `last_seen_ts` to `dll_heartbeat.json` every bar. Backend service `services/dll_watchdog.py` (new) alerts via existing health route if `now - last_seen > 30s`. **If alert fires during open trade → manual reconciliation required.** |
| **P5-7** | Bridge integration | 1 | Wire `bridge/trade_commands.py::TradeCommandHandler` into bridge startup (`bridge/v9_startup.py`). Add health metric `trade_handler_alive`. **Do not change** `TradeCommandHandler` itself (it is complete · just unwired). |
| **P5-8** | End-to-end UAT | 1 | Three full mode runs on Sierra DEMO account: (1) SHADOW: trade fires → command file → ACK only (unchanged · regression check). (2) DEMO: trade fires → command file → real Sierra order → fill → DB matches DLL. (3) LIVE (DEMO account · `BRIDGE_LIVE_ENABLED=1`): same as DEMO but via LIVE code path. Verify all 4 UAT axes per `mems26-pre-live-protocol.mdc`. |

**Total:** 9.5 CC days · ~5-6 calendar days with buffer.

---

## Decision rationale

1. **Why verify-first on gateway:** the Pkg 0 deep-dive showed that judging by `imports + line count` alone produced the wrong canonical choice initially. Same pattern here — `services/trading_gateway/` looks more sophisticated (W11+W14 integration) but `backend/v9/gateway/` is what production actually runs. Need CC's audit to make this lock cleanly.
2. **Why `sc.SubmitOCOOrder()` not `sc.SubmitOrder()`:** OCO atomically links entry+stop+target. Without OCO, a fill on entry without immediate stop attachment = risk window where a kill on Sierra leaves naked position. OCO is what D-091 §Exit assumes.
3. **Why DEMO before LIVE:** P5-1 deliverable hits the demo account only. P5-3 (LIVE wiring) requires explicit env var flip · cannot accidentally route to live.
4. **Why bridge handler is "just wire, don't change":** 193 lines including checksum verification and timeout polling — battle-tested code that's been in tree for months · only missing piece is startup integration.
5. **Why 30s heartbeat threshold:** matches existing health-poll cadence in `mems26-pre-live-protocol.mdc` polling table for diagnostic-only signals.

---

## Forbidden moves (during Pipeline 5)

- 🛑 **Do not delete `bridge/trade_commands.py`** — it is canonical · only P5-7 touches startup wiring.
- 🛑 **Do not call `sc.SubmitOrder()` in LIVE path before P5-3** — DEMO-only until env var flip.
- 🛑 **Do not assume PA-APEX-125218-01 is the correct DEMO account** — placeholder in legacy code · Michael to confirm.
- 🛑 **Do not skip P5-0** — `services/trading_gateway/` may contain risk_validator wiring that the canonical path needs to absorb. Audit first.
- 🛑 **Do not modify `MES_AI_DataExport.cpp` outside lines 813-815 (P5-1) and the new T2.4 (P5-4) and T2.5 (P5-6) blocks** — `sc_study/` is anti-regression per CLAUDE.md.

---

## Cross-system impact

- **S1 (Day Type · Observer):** no change.
- **S2 (5-Min · Firing):** D-091 §Exit assumes OCO. P5-1 satisfies the assumption.
- **S3 (Footprint · Firing):** D-089 routes to gateway. Same OCO benefit.
- **S4 (Woodies · Firing):** D-092 Pipeline 2 deliverable depends on P5-1 (fires routed to Sierra).
- **S5 (TPO · Observer):** no change.
- **S6 (Killzone · Observer):** no change.
- **TradeManager Pkg 6:** `MODIFY_STOP` + `ARM_BE` actions become real (P5-5) rather than logged-only.

---

## UAT axes (per P-LIVE protocol)

**P5-8 must verify all 4 axes for each of SHADOW / DEMO / LIVE mode runs:**

| Axis | Verification |
|------|--------------|
| **Quality** | DLL returns `FILLED` (not `ACK_*`) within < 2s of command write. Real `sc_order_id` populated. |
| **Recency** | `dll_heartbeat.json` `last_seen_ts` ≥ `now - 30s` throughout the trade lifecycle. |
| **Cardinality** | Trade table entries = setup fires = DLL fill events. No drops, no duplicates. |
| **Latency** | P95 `trade_command.json` → `trade_result.json` round-trip < 5s. |

---

## Open items locked to other prompts

- ATM template configuration (if Sierra requires per-symbol setup) — defer to P5-1 in-flight.
- Order rejection handling UI surface — deferred to a frontend prompt post-Pipeline 5.
- Multi-symbol routing (MES only for now · ES/NQ defer to post-LIVE).

---

## References

- `sc_study/MES_AI_DataExport.cpp` lines 791-855 (T2.2 · trade command polling · TODO at 813-815)
- `backend/v9/gateway/trading_gateway.py` lines 269-290 (`_execute_demo` / `_execute_live`)
- `backend/v9/services/trading_gateway/gateway.py` + `executors/{shadow,demo,live}.py` (unwired parallel impl)
- `backend/v9/services/sierra_command.py` (canonical · used by legacy gateway)
- `bridge/trade_commands.py` (canonical bridge handler · unwired)
- `backend/v9/api/v9/trade_commands.py` (POST `/command` route · already shipped)
- `docs/runbooks/SIERRA_DLL_OPS.md` (deploy ops · CC-maintained)

---

*End of D-093 · 2026-05-23 · Michael Barg + Cursor agent*
