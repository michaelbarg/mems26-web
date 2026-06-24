# CC Handoff — Stage 3: Nontrend-Disable (Michael's firing rule) 2026-06-24

_Author: Cowork · contract: `docs/handoff/CC_HANDOFF_CONTRACT.md`. CC develops; Cowork verifies + fixes-to-index._

## Michael's rule (the whole of Stage 3)
> **Every pattern fires FULL on every day-type — EXCEPT Nontrend, where ALL patterns are disabled.**
> The selectivity that decides *which* fires actually go comes from two layers that are **already live**:
> (1) **location × day-type** = `DAYTYPE_POSITION_GATE` (direction × price-vs-POC/IB), and
> (2) **LSMA + CVD** = `DIRECTION_LSMA_VETO` (the LSMA-veto engine).

So the firing cascade is: `day_type != Nontrend` **AND** position-gate passes **AND** LSMA+CVD passes → fire.

## What this means (important — scope is SMALL)
- ❌ **Do NOT enforce the `config/daytype_playbook.yaml` pattern×day-type SKIP/REDUCED matrix.** It is NOT Michael's rule (he does not want per-pattern suppression by day-type). Leave `DAYTYPE_PLAYBOOK` off / inert; do not un-short-circuit it.
- ✅ **The position gate being "pattern-blind" (CASCADE_AUDIT R2) is CORRECT** under this rule — Michael wants all patterns allowed, gated only by location. No change there.
- 🎯 **The ONLY missing enforcement = Nontrend-disable (CASCADE_AUDIT R3).** Today `daytype_position_gate.py` Nontrend branch returns `(True, "Nontrend (playbook handles SKIP)")` and defers to the dead playbook → Nontrend currently allows everything. Fix: on Nontrend, block ALL fires.

## The fix
**File:** `backend/v9/systems/daytype_position_gate.py` (the Nontrend branch, ~line 57, `(True, "Nontrend (playbook handles SKIP)")`).
- New flag **`NONTREND_DISABLE_ALL`** — code default **OFF** (no behavior change); set **`=1` in `.env`** (Michael's rule). Trading-surface → his sign-off (given) + backtest.
- When ON and `day_type == "Nontrend"` → return `(False, "Nontrend — all patterns disabled (Michael rule)")` for **every** pattern/direction (S2 + S4). When OFF → today's behavior (defer).
- Keep `NONTREND_WIDTH_FLOOR` (already ON) so a wide day isn't mis-stamped Nontrend and wrongly silenced.
- Document the flag in `docs/FLAG_REGISTRY.yaml` → run `gen_flag_index.py` (`--check`=0).

## Backtest (mandatory before enable)
06-22 stamped **5 fires Nontrend** in the morning: **188/190 (TLB SHORT), 191/193/194 (HFE SHORT)** — the counter-drive top-picking that lost **≈ −$555** (`docs/reports/TRADES_TODAY_2026-06-22.md`). With Nontrend-disable ON, all 5 are **blocked**. Report the P&L delta across the shadow history (expect: removes the Nontrend-day bleed; confirm it doesn't block winning Nontrend fires — there should be ~none, since Nontrend = no edge).

## Regression test (anti-tautological)
`tests/v9/regression/test_nontrend_disable.py`:
- `day_type=Nontrend` + flag ON → gate returns block for S2 REACTIVE *and* S4 ZLR/HFE, both directions.
- `day_type=Normal/Variation/Trend/Neutral` + flag ON → **unchanged** (not blocked by this rule).
- flag OFF → identical to today (the anti-tautology: proves the flag gates it).

## Verify (Rule 5 — paste raw)
1. `pytest tests/v9/regression/test_nontrend_disable.py -q` → pass.
2. `gen_flag_index.py --check` → 0; show the new flag row.
3. After restart: a Nontrend-stamped setup → `blocked_by` shows the Nontrend rule; a Normal-day setup is unaffected.
4. NOT-DONE section.

## Cascade note for the report
Confirm the full live path matches Michael's rule end-to-end: Nontrend-disable (this) → `DAYTYPE_POSITION_GATE` (location) → `DIRECTION_LSMA_VETO` (LSMA+CVD). No per-pattern matrix in the path.
