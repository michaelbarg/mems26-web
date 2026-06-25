# CC Handoff — Dynamic Structure-Trailing Manager (Michael's trade rule, the "heart") 2026-06-24

_Author: Cowork · contract: `docs/handoff/CC_HANDOFF_CONTRACT.md`. CC develops; Cowork verifies (code + tests + **backtest** + NOT-DONE — all four, raw output)._

## The rule (Michael, ratified 2026-06-24 — implement EXACTLY)
Entry = a pattern fire (S2/S4), already gated by day-type/location + LSMA+CVD. **3 contracts, ONE trade at a time (no concurrency).** Then:

1. **Contract-1** takes a **first profit target** (the existing T1 / risk-reduction target) → then **stop → breakeven** for the remaining contracts. _(Already built — KEEP.)_
2. **Runners (C2+C3) — DYNAMIC structure-trail:** the moment price **forms a NEW CONSOLIDATION** (a balance/congestion zone) in the trade's favor → **MOVE THE STOP** to just beyond that consolidation (below it for LONG / above it for SHORT, never widen). The **NEXT target = the EARLIER (לפי המוקדם) of {the new consolidation's projection, the next important level}** in the trade direction (POC / VAH / VAL / IB-high / IB-low / PDH / PDL).
3. **As long as the move continues, repeat the same principle** — each new consolidation re-anchors the stop and advances the next target — **through T3 and beyond**.
4. **"New place" = a new CONSOLIDATION** (Michael's choice 2026-06-24): NOT a single swing bar, NOT value-migration. A few bars that balance in a tight range after price advanced.
5. **Woodies (S4) trades use DIFFERENT management settings** (separate params — see §Woodies).

LSMA is the DIRECTION engine only — it is NOT an exit here. (I misread that 3×; do not wire LSMA into the exit.)

## What already exists — KEEP / ADAPT (from the 2026-06-24 audit)
- **KEEP** `services/trade_manager/manager.py` — lifecycle state machine, PnL, `v9_trade_management_log`.
- **KEEP** `services/trade_manager/bar_level_detector.py::on_bar()` (~L43–159) — per-bar hit detection. **This is the injection point** for the dynamic logic (the trailing-runner is already wired here at L101–107 — mirror that pattern).
- **KEEP** `_apply_smart_be_after_t1()` (manager.py L282–337) — C1→BE. Never-widen invariant. Reuse as-is.
- **ADAPT** `apply_trail_after_t1()` (manager.py L339–432) — shows the runtime stop-move + never-widen + HWM-in-`trade.quality` pattern. The new structure-trail replaces the `k×risk` math with consolidation-anchored math.
- **KEEP/REUSE** `systems/structural_targets.py` — already maps day-type → C1/C2/C3 structural levels (IB/POC/VAH/VAL), flag `DAYTYPE_TARGETS_STRUCTURAL=ON`. This is the "important points per day-type." Reuse its level-resolution for the "next important level."
- **KEEP/REUSE** the live key-levels module behind `/api/v9/key_levels` (`api/v9/key_levels_routes.py`) — POC/VAH/VAL/IB/PDH/PDL, live. The manager must read these at bar time (it currently does NOT).

## What's MISSING — BUILD (flag `DYNAMIC_STRUCT_TRAIL`, default **OFF**)
1. **Consolidation detector** — a pure, unit-tested function: given the bars since entry (or since the last anchor), detect a NEW consolidation = **≥ K bars whose total range ≤ R**, occurring **after** price advanced ≥ M in the trade direction since the last anchor. Returns `{anchor_extreme, zone_high, zone_low, bar_span}`. **All of K / R / M tunable** via `config/stop_anchors.yaml` (Michael wants every param YAML-tunable — see CLAUDE.md / [[project_config_tunable_stop_exits_contracts]]). Sensible defaults: K=3 bars, R ≤ 0.5×ATR-14 (or a tick floor), M ≥ 1×initial-risk. Pure CCI not involved — this is price-structure.
2. **Dynamic re-anchor loop** — in `bar_level_detector.on_bar()`, when `DYNAMIC_STRUCT_TRAIL=ON` AND the trade is past C1 (state PARTIAL, T1 hit + BE applied): on each new consolidation → (a) move stop just beyond the zone (never widen, fail-safe try/except like the existing trail), (b) recompute the next target = `min_by_distance({zone projection, next key level in trade direction})`. Log each move to `v9_trade_management_log` (action `STRUCT_TRAIL` with the zone + chosen target).
3. **Repeat through T3+** — not a one-shot; the loop keeps re-anchoring as new consolidations form while the move continues.
4. **Per-contract management** — today a trade is ONE atomic row (3 contracts share one stop/target). Decide + implement KEEP-atomic-with-runner-portion vs split-per-contract: at minimum C1 exits at its target then the **runner portion (C2+C3)** is managed by the dynamic trail. Document the choice; don't silently leave all-3-atomic if it breaks the rule.

## Woodies (S4) variant
S4 already differs (RUNNER_TARGETS_V1 T2=1R, GIANT_BAR_STOP_V1, per-pattern time-stops). For the dynamic trail, S4 must use its **own** consolidation params + level set (Woodies/structural). If Michael hasn't given the S4-specific K/R/M or level priority, build S2 first, parametrize S4 separately, and **put the S4 param gap in NOT-DONE** (do not assume S4==S2).

## Verify (Rule 5 — paste raw) + NOT-DONE
1. `pytest` new `tests/v9/regression/test_dynamic_struct_trail.py` — anti-tautological: **OFF** = today's static behavior unchanged · **ON** + crafted "advance → consolidation" → stop moves to the zone edge + next target = the nearer of {zone, key level} · **ON** + no consolidation → no move · never-widen invariant holds · one-trade-at-a-time preserved.
2. Run the FULL regression suite with `DYNAMIC_STRUCT_TRAIL=1` (flag-interaction check — this has bitten before).
3. **Backtest** on shadow history: dynamic structure-trail vs the current static T2/T3 — runner P&L delta, per day-type. Save `outputs/dynamic_struct_trail_backtest.*`. (Don't claim done without it — VEGAS/ZLR both shipped without one.)
4. `gen_flag_index.py --check`=0 (document `DYNAMIC_STRUCT_TRAIL` + the new YAML params in `FLAG_REGISTRY.yaml`).
5. **NOT-DONE** section: the per-contract decision, the S4 params, the consolidation default-tuning, and anything deferred.

Default OFF + SHADOW-validate + Michael sign-off before enable — this is a trading-risk-surface change.
