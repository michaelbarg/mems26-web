# LIVE TODAY — exact execution path to real money (2026-07-07, RTH 16:30 IL)

Single source of truth for the remaining work. Each task: WHO · WHAT · ACCEPTANCE (ground-truth,
raw-pasted — unit tests do NOT count) · WHY. Phases are STRICTLY ordered — a phase's acceptance
must be green before the next starts. If any STRICT-blocker is not raw-green by 16:30 →
**DEMO/SIM only today** (the −$400 gate protects us; a rushed naked live trade does not).

Current proven state (Cowork-verified from artifacts, commit ba398f5):
- ✅ DLL fix is in the DEPLOYED source (sha256 064a743 == repo monolith, no drift) + binary Jul-7 13:42.
- ✅ Sierra CAN sim-fill (1c @7578.50 at 13:45).
- ❌ Running study is stale/unarmed → `GENERAL_ERROR_OR_NOT_ENABLED` still at 14:53 & 14:55.
- ❌ Even the one fill was DROPPED by the backend (`order_id=8394 fill dropped`) → not tracked.

---
## PHASE 0 — arm Sierra  [Michael · ~5 min · GATES EVERYTHING]
The binary is fixed but the RUNNING study isn't it. Until fixed, every order fails.
1. On the MES chart: **remove + re-add** the study `MES AI Data Export` (loads the 13:42 binary).
2. Study **Input 21 (Enable Order Placement) = 1**.
3. **Trade Simulation Mode ON** (for the proof) · **account 37138283 selected** on the DOM · Auto-Trading armed.
**ACCEPTANCE (CC pastes):** fire one test BUY → Message Log shows `Simulated order accepted`, **no**
`GENERAL_ERROR_OR_NOT_ENABLED`. → then Phase 1.
**WHY:** proven blocker — GENERAL_ERROR at 14:55 = stale/unarmed study.

## PHASE 1 — the backend must CAPTURE the fill  [Cowork builds · CC tests · HARD blocker]
Today's 1c fill was DROPPED (no TM trade) → we can't track/manage/close/P&L it = the I-62 orphan.
- **P1.2 (Cowork):** on a Sierra fill with no mapped trade → adopt/rebuild the TM trade from the fill
  AND raise the drop WARNING→CRITICAL. Fold into System 6's orphan invariant.
**ACCEPTANCE (CC pastes):** re-fire 1c SIM → a `v9_trades` row exists with `entry_price` == the Sierra
fill price (not "fill dropped"). Paste the DB row + the fill JSON — they must agree.
**WHY:** without capture, a real fill = an untracked live position = Thursday's I-62.

## PHASE 2 — SIM round-trip proof, 1c then 2c  [CC · the P0 gate]
With Phase 0+1 green:
1. 1c SIM → order→fill→**captured**→P&L from the Sierra fill price.
2. **2c SIM** → both contracts fill.
**ACCEPTANCE (CC pastes into evidence_2026-07-07/):** `p0_command.json` (contracts:2) ↔ `p0_fills.json`
(2 fills) ↔ `p0_db_rows.txt` (entry_price, contracts=2) — **all three agree**; `result=ORDER_SUBMITTED`.
**WHY:** this is THE proof the order path works end-to-end, for 2 contracts, with Sierra-sourced P&L.

## PHASE 3 — supervision + safety on the live trade  [Cowork builds P1.3 · CC enables]
Do in parallel with Phase 1-2; all must be green before real money.
- **P1.3 reconcile-live (Cowork):** wire reconcile for `mode=live` into the per-bar loop → detect
  orphan / naked-stop / slot↔DB↔Sierra mismatch. ACCEPTANCE: one pass prints 3-way MATCH (paste).
- **P2.4 System 6 (CC):** `SYSTEM6_SUPERVISOR=1` + restart → on the SIM trade, `[System6]` diagnosis
  logs each bar (AUTOCORRECT stays 0). ACCEPTANCE: paste one bar's 9-check log on the real trade id.
- **P1.1 EOD-flatten (CC):** `EOD_FLATTEN_V1=1`. ACCEPTANCE: force ET clock ≥15:59 on an open SIM
  position → CANCEL written + position flat. (If un-testable now, enable + note for live EOD.)
- **A7 stop attached (CC):** confirm the routed order carries a stop (naked order = forbidden). For a
  supervised/manual first trade the stop is in the command (ok); for an AUTO fire, verify no `failed_stages=['A7']`.
- **Config confirm (CC):** `CONT_TREND_FILTER=1` (Michael restored) · `RISK_HALT_V1=1`/CAP=400 ·
  `FIXED_CONTRACTS_2=1` · flatten time = RTH close — all live per the `[env_loader]` boot line.

## PHASE 4 — GO / NO-GO  [Michael · by 16:30]
**GO real money (2 contracts)** only if ALL are raw-green: Phase 0 armed · P1.2 capture · P0 2c
round-trip · a stop attached · reconcile MATCH · System 6 logging · −$400 halt on.
**Otherwise → DEMO/SIM today**, close the red items, go live next session. Supervise the first fire:
verify order→fill→P&L==Sierra to the cent on trade #1.

---
## Owner summary
- **Michael:** Phase 0 (Sierra study+arm) · Phase 4 decision.
- **Cowork (building now):** P1.2 fill-capture · P1.3 reconcile-live (+ unit tests, ground-truth specs).
- **CC (Mac):** Phase 0 acceptance paste · Phase 2 SIM re-run (1c+2c) · enable+paste P2.4/P1.1 · A7 · config boot-line.
## Quality bar (every task)
Raw command + output, artifacts copied into the repo, ≥2 sources triangulated (Rule 3), a NOT-DONE
line for anything incomplete. Cowork verifies each box from the artifacts before it counts.
