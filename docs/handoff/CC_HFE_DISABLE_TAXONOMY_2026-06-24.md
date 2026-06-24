# CC Handoff — Disable HFE + Fix S4 Taxonomy + Investigate TT (2026-06-24)

_Author: Cowork · contract: `docs/handoff/CC_HANDOFF_CONTRACT.md`. CC develops; Cowork verifies._

## Michael's S4 Woodies pattern set (authority — the code drifted from it)
- **Continuation (trend):** ZLR · TLB · **TT** · GB100
- **Reversal:** VEGAS · GHOST · FAMIR · **HTLB**
- **HFE is NOT a pattern Michael uses** ("אני לא מכיר hfe"). The code added it (the "9-pattern engine"); it is the **single biggest loser**.

### Evidence (shadow history, `v9_trades` firing_system=4)
| pattern | fires | P&L | |
|---|--:|--:|---|
| **HFE** | 27 | **−$2,987** | ⚠️ not Michael's; disable |
| ZLR | 35 | −$268 | |
| GHOST | 3 | −$160 | |
| FAMIR | 3 | −$35 | |
| VEGAS | 1 | +$54 | |
| GB100 | 3 | +$228 | |
| HTLB | 3 | +$720 | reversal |
| TLB | 50 | +$793 | |
| **TT** | **0** | — | implemented (`tt.py`) but never fires — investigate |

## Fix 1 — Disable HFE (flag-gated)
HFE is detected from **two** sources: the Python detector `backend/v9/systems/woodies/patterns/hfe.py` AND the **Sierra DLL** (`hfe_detected`/`hfe_direction` flags consumed in `woodies_system.py:208-210, 301-303, 358`). The disable must drop **both**.
- New flag **`HFE_DISABLED`** — code default **OFF** (no change); `.env=1` (Michael's rule).
- When ON: `woodies_system` must **not emit any HFE fire** regardless of source — skip the Python HFE detection AND ignore the DLL `hfe_detected` for firing/routing. (Mirror the existing `TICK_REVERSAL_DISABLED` / `WOODIES_30MIN_DISABLED` pattern-kill flags.)
- Document in `docs/FLAG_REGISTRY.yaml` → `gen_flag_index.py` (`--check`=0).
**Backtest (already run by Cowork):** 27 HFE fires = **−$2,987** (9W/18L) → disabling removes the single largest drag.

## Fix 2 — Correct the taxonomy (HTLB = reversal, HFE removed)
- `woodies_system.py:5` docstring "9-pattern engine (… HFE)" → 8 patterns, HFE removed.
- The day-type×pattern grouping (`woodies/day_type_gate.py`, `config/daytype_playbook.yaml`, `docs/spec_authority/S4_WOODIES_TABLE_A_Pattern_Setup.csv`, `WOODIES_PATTERNS_SOURCE_VS_CODE_2026-06-23.md`): **HTLB belongs to REVERSAL** (not continuation). Final set: continuation = {ZLR, TLB, TT, GB100}; reversal = {VEGAS, GHOST, FAMIR, HTLB}.
- (Note: this grouping is documentation/spec — it does NOT re-enable the playbook matrix; Michael's firing rule is Nontrend-disable + position-gate + LSMA+CVD, per `CC_NONTREND_DISABLE_2026-06-24.md`.)

## Fix 3 — Investigate TT (diagnose, don't force)
`tt.py` exists but **0 shadow fires** ever. Find why: are its trigger conditions unreachable, is it gated off, or not wired into the active detector loop? Report the root cause + whether it's correct-as-is or needs Michael's TT spec. Do NOT loosen it without Michael's sign-off.

## Verify (Rule 5 — paste raw) + NOT-DONE
1. `pytest tests/v9/regression/test_hfe_disabled.py -q` → an HFE signal (Python + a DLL-flagged bar) with flag ON produces NO fire; other patterns unaffected; flag OFF → unchanged.
2. `gen_flag_index.py --check` → 0; show the `HFE_DISABLED` row.
3. After restart: a bar that would HFE-fire → no HFE trade; `grep` the trade log shows no new HFE.
4. TT investigation findings + the taxonomy doc updates committed.
