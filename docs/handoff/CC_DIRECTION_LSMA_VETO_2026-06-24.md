# CC Handoff — DIRECTION_LSMA_VETO (LSMA-lead + CVD-veto direction engine)

_Author: Cowork · 2026-06-24 (pre-open, CT 08:0x) · contract: `docs/handoff/CC_HANDOFF_CONTRACT.md`_
_Owner split (Michael 2026-06-24): **CC develops; Cowork verifies + fixes-to-index.**_

## Objective
Michael approved making **LSMA the trend, CVD the veto** the live direction used by the
fire-gate. Implement it **behind a new flag `DIRECTION_LSMA_VETO` (default-OFF in code)**, set
ON in `.env`, activate in **SHADOW** today. Fully reversible (flag off = today's engine).

## Decision / semantics (exact — pure rule)
Direction = the **LSMA side**; CVD only **vetoes** (→ NEUTRAL) when it **directly opposes** that side.

```
lsma_side  = +1 if close > lsma_value else -1        # price vs the LSMA line (woodies)
cvd_slope  = sign(cvd[-1] - cvd[-1-3])               # 3-bar slope, already computed in compute_direction
dir = NEUTRAL   if (cvd_slope != 0 and sign(cvd_slope) == -lsma_side)   # CVD opposes LSMA → flat
      else UP   if lsma_side > 0
      else DOWN
```

Truth table (must be the regression test):
| lsma_side | cvd_slope | dir |
|---|---|---|
| +1 (UP) | +1 | UP |
| +1 (UP) | −1 | **NEUTRAL** (CVD opposes) |
| +1 (UP) | 0 | UP (CVD silent → LSMA leads) |
| −1 (DOWN) | −1 | DOWN |
| −1 (DOWN) | +1 | **NEUTRAL** |
| −1 (DOWN) | 0 | DOWN |

This **replaces** the CVD+location+breakout branches **only while the flag is ON** (short-circuit at
the top of `compute_direction`). Flag OFF → today's brain, untouched. ⚠️ Note for Michael's awareness
(Cowork already flagged): when ON it also yields a direction **pre-IB-lock** (LSMA exists from the
open), so the gate becomes active in the opening window — `OPENING_TYPE_GATE` still applies on top.

## Files + integration (read before editing — index-grounded)
1. **`backend/v9/systems/direction_context.py`** — `compute_direction(...)` is a **PURE** function
   (keep it pure). Add params `lsma_side: Optional[int]=None, lsma_veto: bool=False`. Right after the
   `base = {...}` dict (≈line 84), insert the short-circuit override above using `cs` (cvd_slope) it
   already computes. Return `breakout_state="lsma_cvd_veto"`, plus `lsma_side`, `reason`.
   Prefer a tiny pure helper `lsma_cvd_veto_direction(lsma_side, cvd_slope) -> str` so the test hits it
   directly.
2. **`backend/v9/systems/direction_context_live.py`** — `current()` (the impure wrapper):
   - Read the flag here (e.g. `flag("DIRECTION_LSMA_VETO")` from `backend/v9/shared/atr.py:86`, or
     `os.getenv` to match the adjacent `DIRECTION_CONTEXT` style — either is fine, but the FLAG_INDEX
     generator must catch it).
   - Fetch the **latest** `close, lsma_value` for today from **`v9_bars_5min_woodies`** (SOURCE_OF_TRUTH:
     this is the canonical LSMA source) where `lsma_value IS NOT NULL` ORDER BY ts DESC LIMIT 1.
     `lsma_side = +1 if close>lsma else -1`.
   - Pass `lsma_side` + `lsma_veto` to `compute_direction`. **Fail-safe (Rule 1):** if the flag is on but
     lsma is missing/None → do NOT override; fall through to the existing dir (never break the gate).
   - Add `lsma_side`/`mode` into the returned dict for observability.
3. **Consumer (no change needed, just confirm):** `backend/v9/gateway/trading_gateway.py:284`
   (`DIRECTION_CONTEXT` gate) reads `direction_context_live.current()["dir"]` — it automatically picks
   up the new dir. Do **not** alter the gate logic.

## Flag (default-OFF) + index (this is the part Cowork will verify hardest)
- New flag **`DIRECTION_LSMA_VETO`**, code default **OFF**; `.env` → `DIRECTION_LSMA_VETO=1`.
- Add its semantics to **`docs/FLAG_REGISTRY.yaml`** (category: gateway/direction; what/why/status =
  "ON SHADOW 2026-06-24, Michael approved; LSMA-lead+CVD-veto; reversible").
- Run **`python3 scripts/gen_flag_index.py`** → commit refreshed `docs/FLAG_INDEX.md`; then
  **`python3 scripts/gen_flag_index.py --check`** must exit 0 (no undocumented drift).
- If a new test file/module is added, run **`python3 scripts/gen_index.py`** and commit the refreshed
  `_INDEX.md`/`SYSTEM_INDEX.md`.
- Update **`docs/SOURCE_OF_TRUTH.md` § Day-type/direction** to note: when `DIRECTION_LSMA_VETO=1`,
  `direction_now.dir` is LSMA-lead+CVD-veto (source = woodies lsma + cvd_slope).

## Regression test (anti-tautological — mandatory)
`tests/v9/regression/test_direction_lsma_cvd_veto.py`:
- All 6 truth-table rows on the **pure** helper / `compute_direction(..., lsma_veto=True, lsma_side=…)`.
- **flag-off / lsma_veto=False → identical to the current engine** on a fixture (proves it's gated, not
  always-on — the anti-tautology).
- An opposes-case that returns NEUTRAL **only** because CVD fights LSMA (not because data is missing).

## Verification to PASTE in the report (Rule 5 — raw cmd+output, not "✅")
1. `pytest tests/v9/regression/test_direction_lsma_cvd_veto.py -q` → all pass.
2. `python3 scripts/gen_flag_index.py --check` → exit 0; show the new `DIRECTION_LSMA_VETO` row.
3. After restart (pre-open, CT<08:30 — safe): `curl -s localhost:8000/api/v9/day_type/direction_now`
   → show `dir`, `lsma_side`, `mode/breakout_state=lsma_cvd_veto`, `source`.
4. One gateway proof: a setup whose direction == the LSMA-veto NEUTRAL/opposite is `blocked_by:
   direction_context` (or passes when aligned).

## NOT-DONE / risks (mandatory section — fill in honestly)
- Validated on **1 day (06-23)** standalone (74% hit, +$2,452; scripts `outputs/direction_compare_2026-06-23.py`).
  NOT multi-day. NOT the full fire-gated P&L.
- Replace-vs-augment: this **replaces** the breakout/location/trend-day brain while ON. If Michael wants
  augment-only (LSMA as an extra veto on top of the existing dir), that's a different change — flag it.
- Restart caveat: only restart **pre-open** (CT<08:30) or it starves the day-type promotion buffer
  (`_cls_rth_bars`). Check listeners on :8000 first.

## Cowork will then verify
test output reproduced, flag-index `--check` green, `direction_now` reflects the new mode, the gate
blocks/passes correctly, and **all three index docs (FLAG_INDEX, SOURCE_OF_TRUTH, SYSTEM_INDEX) are
consistent** — then report GO/NO-GO to Michael.
