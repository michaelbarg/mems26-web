# CC — INITIATIVE structural staircase scale-out + VAH/VAL-retest entry (IB-2) + BE-after-T1

**Date:** 2026-07-01 · **Owner:** Michael · **Prepared by:** Cowork
**Contract:** `docs/handoff/CC_HANDOFF_CONTRACT.md` — paste command + raw output (Rule 5), anti-tautological tests, mandatory NOT-DONE.
**Spec authority:** `docs/spec_authority/INITIATIVE_SPEC_TOOLCONSTRAINED_2026-06-30.md` (§C IB-2 variant, §D2 targets, §D3 trail). **Backtest context:** INITIATIVE_LONG +4.1R = the edge; REV off the table (−34.6R). Enabling is trading-risk → flag-gated, SHADOW first, Michael sign-off.

## What Michael asked for (three concrete asks)
1. **Structural staircase scale-out** — detect successive swing-highs (the "steps"); scale 3 contracts: **C1 out ½-way to the 2nd swing-high · C2 out at the 3rd · C3 (runner) out at the 4th.** Dynamic — each contract exits as *its* step forms (peaks 3/4 are forward). Tunable in `config/targets.yaml`.
2. **Stop → BE after T1** — on the T1 fill, move the stop to entry for C2/C3.
3. **Staircase detection + VAH/VAL anchoring (IB-2)** — detect an up-staircase (higher-highs **and** higher-lows) / down-staircase; **entry = retest-hold of the developing VAH (long) / VAL (short)** + CVD confirm. Long-only below; **short = exact mirror at VAL.**

## Do it in this order (verify → calibrate → build)

### Phase 1 · VERIFY the data exists (Pre-LIVE) — ✅ PRE-VERIFIED by Cowork 2026-07-01 (re-confirm the residual)
**Cowork findings (raw):** (a) **VAH/VAL LIVE** — `v9_tpo_history` carries `poc/vah/val`, updates ~30-min through RTH (e.g. 06-30 19:30 IL: poc 7553.25 / vah 7566 / val 7524.25). Source = TPO/chart 3. ✅ usable for the IB-2 retest (30-min value granularity; confirm it repopulates at today's open). (b) **smart_be WIRED** — `backend/v9/services/trade_manager/manager.py:328` calls `_apply_smart_be_after_t1(trade)`; `active_trade_manager/monitor.py:230 apply_smart_be` sets `stop = entry_price` + emits an alert. ✅ logic present in the W11 TradeManager that the demo path uses. **RESIDUAL to confirm on the first live demo trade:** that the demo BE actually issues a Sierra **MODIFY_STOP** (per `_execute_demo` docstring "mode=demo → dynamic MODIFY_STOP/TARGET reach Sierra"), not just a DB `stop` update. Original checklist kept below for that residual:
- **VAH/VAL live:** confirm the developing value-area (VAH/VAL/POC) is populated + fresh + reachable **per-bar** from **TPO / chart 3** (SOURCE_OF_TRUTH: POC/VAH/VAL come from chart 3, NOT chart 12). Query the live source (tpo tables / the value-area service) and show today's VAH/VAL updating. If stale/missing → stop, report (this blocks ask #3).
- **smart_be active:** trace that `smart_be` (`backend/v9/api/v9/trades.py:257`, UAT flag `:91`) doesn't just *flag* — confirm the demo/TM path actually issues a **MODIFY_STOP to entry after the T1 fill** (`_execute_demo` / trade_manager → Sierra `write_modify_stop`). If it only flags, that's the gap to close for ask #2.

### Phase 2 · CALIBRATE on the 41-day backtest (before building live)
- **swing-pivot params:** K bars that define a swing-high/low (prior K=1–2). Fit on the INITIATIVE sample.
- **C1 "½-way to peak 2":** define precisely (midpoint of the higher-low→peak-2 leg is the prior) and tune.
- **Decision test:** does the **structural staircase scale-out beat the current fixed IB-multiple targets** on the INITIATIVE_LONG sample — by **expectancy AND runner-R captured** (the +4.89R in-house came from the trail)? If it doesn't beat, report before building.

### Phase 3 · BUILD (flag-gated `INITIATIVE_STAIRCASE_V1`, default OFF → SHADOW)
- **Swing-staircase detector (NEW):** successive higher-highs + higher-lows sequence + a peak counter. Build on the existing Woodies swing logic (`backend/v9/systems/woodies/patterns/vegas.py`, `anti_patterns.py`) — don't reinvent.
- **Structural per-contract scale-out (NEW):** map C1/C2/C3 to the swing-highs (C1 ½-to-peak2, C2 peak3, C3 peak4), dynamic. Wire into the **#68 structural-targets engine** + `config/targets.yaml` (keep it tunable-without-code, per Michael's standing want).
- **VAH/VAL retest-hold entry (IB-2, NEW):** the §C STATE 4/5 IB-2 branch — price in an up-staircase retests the developing VAH and makes a higher-low at/above it (no acceptance below), + CVD new-high/no-divergence (§C STATE 6). Long; mirror at VAL for short.
- **BE-after-T1 (WIRE/verify):** complete `smart_be` if Phase 1 found it only flags.

## Tests (anti-tautological)
- swing detector on a known 4-peak staircase → counts 4 higher-highs; a non-staircase (lower-high) → not flagged.
- scale-out on a synthetic staircase → C1 exits ½-way to peak2, C2 at peak3, C3 at peak4 (exact ticks).
- BE: after a T1 fill, C2/C3 stop == entry (a MODIFY_STOP was issued).
- IB-2 entry fires ONLY on a retest-hold above the developing VAH (not on a close below it).
- **flag OFF (`INITIATIVE_STAIRCASE_V1` unset) → current behavior byte-identical.**

## Verification (Rule 5 · SHADOW)
On the next trend/CONT day, one staircase INITIATIVE-long: entry at VAH-retest → C1 out ½-way to peak2 → **BE after T1** → C2 at peak3 → C3 at peak4 (trailed). Paste the raw chain (detect → entry → per-contract fills → stop-move).

## NOT-DONE
- ❌ Do NOT enable live without SHADOW validation + Michael sign-off (trading-risk).
- ❌ Do NOT change the REV family or the gates (REV on trend = −34.6R, correct).
- ❌ Do NOT hard-code targets — keep C1/C2/C3 + swing params in `config/targets.yaml`.
- ❌ Do NOT build ask #3 if Phase 1 shows VAH/VAL isn't live — fix the data first.
- ❌ Short = mirror at VAL (accept below, CVD new session low) — do not treat as a separate ad-hoc path.
