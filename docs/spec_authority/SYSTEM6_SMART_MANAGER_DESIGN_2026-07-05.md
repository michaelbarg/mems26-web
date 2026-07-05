# System 6 — Smart Manager design (Michael 2026-07-05)

Michael's spec (verbatim intent): while a trade is open, the system should
identify (1) a zone where a reaction/resistance was expected but the volume that
would confirm it failed, (2) price stuck / unable to continue, (3) two patterns
firing to the opposite side. It should **weight each separately, each with its
own decision option** (in addition to Michael's own call), **remember** the
signal+decision+outcome so **over time** the system learns to make the best
in-trade decisions and maximize the trade — and **T2/T3 must get perspective**,
not be fixed levels.

## 1. Exit-signal engine (BUILT, flag-OFF)
`backend/v9/systems/system6_exit_signals.py` — three pure detectors, each →
`ExitSignal(kind, score 0..1, fired, reason, action)`, plus `evaluate_exit()`
that blends them **without losing the per-signal detail**:

| signal | fires when | inputs |
|---|---|---|
| `failed_reaction_volume` | price within tol of an expected reaction level AND confirming flow (CVD/volume) is weak/absent | price, level (from target zones), flow_aligned 0..1 |
| `price_stall` | no new favorable extreme for N bars (move can't continue) | recent bars, direction |
| `opposite_patterns` | ≥2 counter-direction patterns fired recently | recent fire directions |

12 tests incl. fuzz. **OPEN — needs Michael:** the `failed_reaction_volume`
semantic assumes "confirming flow absent near the level = exit". If you mean
"opposing volume showed up to defend the level = exit", it's a one-line flip
(`flow_aligned` inverts). Confirm which.

## 2. Scoring + decision flow (the "יחס וכל אחד בנפרד")
Each signal is scored independently and shown as its own card in the System 6
panel with a suggested action ("take partial", "exit runner", "hold"). Michael
decides per-signal; the system also carries a default recommendation
(`evaluate_exit.recommend_exit`). Weights are tunable (`DEFAULT_WEIGHTS`) — the
learning loop below tunes them from real outcomes rather than guesswork.

## 3. Memory + learning loop (NEEDS RULING → then build)
Proposed PG table `v9_exit_decisions` (survives restart; extends item-17 journal):

| column | meaning |
|---|---|
| trade_id, ts | which trade, when the signal fired |
| signal_kind, score | the individual signal + its score |
| context_json | price, level, flow, bars-since-extreme, counter-count at the moment |
| recommendation | what System 6 suggested |
| decision, decided_by | hold / partial / exit · system or Michael |
| outcome_json | filled AFTER: MFE-after-the-signal, eventual close, "would exiting have helped?" (R saved/lost) |

Over time this yields a **per-signal hit-rate** ("when `stall` fired and we
held, we gave back X on average"). Two ways to use it: (a) surface the stat in
the panel ("this signal has been right 68% of the time"); (b) auto-tune the
weights so the aggregate leans on the signals that have actually paid off.
Start as an **advisory ledger** (record + show), graduate to **auto-weighting**
only after enough samples + Michael's OK.

## 4. T2 / T3 perspective (NEEDS RULING → then build)
Today T2/T3 are fixed levels the price often never reaches. "Perspective" =
make them **managed, structural, and signal-aware**:
- T2/T3 anchor to the item-22 confluence **zones** (real shelves), not R-multiples.
- Between T1 and T2, the runner is governed by the trail + the exit-signals
  above: a fired signal can take the runner off EARLY (near a real level) instead
  of waiting for a T2 that won't print.
- T3 becomes "hold-to-close / far-shelf" only on a confirmed Trend day (day-type
  aware), otherwise it collapses into the give-back logic.

## Build order (all flag-OFF, reversible)
1. ✅ exit-signal detectors (`SYSTEM6_EXIT_SIGNALS`).
2. Wire the detectors into `system6_supervisor.scan_active_trade` so they appear
   as recommendations in the panel (needs the live bars + flow + recent-fires
   feed at scan time).
3. `v9_exit_decisions` table + record-on-signal + outcome-fill at trade close.
4. Backtest on the 128 managed trades: for each signal + threshold, R saved on
   reversals vs R cost on trend days → data-driven weights + the give-back %.
5. Only then: enable advisory in DEMO → learn → optional auto-act.

Everything reversible: each stage is a flag (`SYSTEM6_EXIT_SIGNALS`, later
`SYSTEM6_EXIT_JOURNAL`, `SYSTEM6_EXIT_AUTOACT`), default OFF, snapshot + git.
