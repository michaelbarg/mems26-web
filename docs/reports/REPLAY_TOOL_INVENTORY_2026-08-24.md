# MEMS26 Replay Tool Inventory — Stage 0A (2026-08-24)

**Scope:** inventory/spec only. No production code, DB, flags, services or tool
deletions.  
**Final Stage-0A scope:** 31 files matching `scripts/*replay*.py` + 20
historical engines/studies + 1 research availability probe = **52**.
The initial 43-count was the core P&L set; independent review identified nine
additional tools that can alter candidates, context, calibration or report
interpretation and therefore must be inventoried.

## 1. Census

```text
31 explicit *replay*.py
21 broad-scope siblings:
  5 backtest_* tools
  oracle_study
  cvd_effort_result
  daily_extremes_playbook
  daytype_stability_study
  good_pattern_fix / good_pattern_oos / good_pattern_ts_ladder
  + classifier/extreme/gate audits, stall v1/v2, binary convergence
  + one research availability probe
= 52
```

Related operational consumers outside the 52: `system2_full_audit`,
`s4_full_audit`, `e2e_fire_proof`, TP audits, execution SIM tools, migrations
and service checks. They need consumer mapping in Stage 0B but are not
historical replay engines.

## 2. Shared-surface census

Static evidence across `scripts/*.py`:

```text
oracle_study references                    15
entry_side_replay references                5
direct psycopg2 scripts                    38
backend.v9.db.read scripts                 30
v9_bars_5min_woodies references            59
v9_trades references                       43
gateway_decisions references               11
SCID readers                                6
sim_ladder references                       8
```

This is not 43 independent ideas; it is a small number of primitives copied,
wrapped and partially reimplemented many times.

## 3. Preliminary classification

Legend:

- **PRIMITIVE-SOURCE:** reusable logic to move behind the kernel contract.
- **ADAPTER:** scenario stays, implementation becomes a thin kernel caller.
- **ADAPT-MIRROR:** scenario stays; local mirror/monkey-patch must be removed
  after live-function parity.
- **RETIRE-PARITY:** obsolete/legacy; retire only after anchor parity.

| # | Tool | Population / purpose | Classification | Required migration |
|---:|---|---|---|---|
| 1 | `backtest_counter_flow.py` | executed trades · opposing-flow exit | ADAPTER | execution-policy scenario |
| 2 | `backtest_cvd_divergence.py` | executed trades · CVD exit | ADAPTER | execution-policy scenario |
| 3 | `backtest_exit_signals.py` | executed trades · S6 exits | ADAPTER | execution-policy scenario |
| 4 | `backtest_manager_combined.py` | executed trades · combined S6 | ADAPTER | compose named policies |
| 5 | `backtest_stop_resolver_item4.py` | executed trades · stop resolver | ADAPTER | stop-policy scenario |
| 6 | `cvd_effort_result.py` | bars+SCID · CVD studies | ADAPT-MIRROR | canonical CVD datasource/features |
| 7 | `daily_extremes_playbook.py` | bars/trades · day playbook | ADAPTER | context-policy scenario |
| 8 | `daytype_stability_study.py` | day labels/trades | ADAPTER | S1 publication scenario |
| 9 | `dead_pattern_replay.py` | live detector isolation | ADAPT-MIRROR | CandidateEngine adapters |
| 10 | `decision_replay.py` | gateway journal | ADAPTER | journal-policy scenario |
| 11 | `direction_accuracy_replay.py` | bars · direction | ADAPTER | direction-policy scenario |
| 12 | `entry_side_replay.py` | bars+SCID · entry timing | PRIMITIVE-SOURCE | migrate SCID/time/label primitives; script→adapter |
| 13 | `f1_compass_replay.py` | bars/trades · compass | ADAPTER | policy scenario |
| 14 | `good_pattern_fix.py` | live-detector mirrors · contention | ADAPT-MIRROR | remove duck/mirror after candidate parity |
| 15 | `good_pattern_oos.py` | wrapper over good-pattern stream | ADAPTER | split/report scenario |
| 16 | `good_pattern_ts_ladder.py` | TREND_STEP own ladder | ADAPTER | execution-policy scenario |
| 17 | `leg_exemption_replay.py` | decisions · gate exemption | ADAPTER | policy scenario |
| 18 | `oracle_study.py` | bars · shared costs/zigzag/sim | PRIMITIVE-SOURCE | split ceiling vs causal/execution primitives |
| 19 | `replay_a1_wrong_side_veto.py` | executed/blocked trades | ADAPTER | policy scenario |
| 20 | `replay_c2_c3_c4_e2.py` | multi-feature acceptance | ADAPT-MIRROR | named scenarios; import live functions |
| 21 | `replay_dalton_context.py` | bars/trades · Dalton prototype | ADAPT-MIRROR | structural-policy adapter |
| 22 | `replay_dalton_over_detectors.py` | persisted setups + Dalton | ADAPTER | setup-population scenario |
| 23 | `replay_day.py` | individual detector smoke | ADAPT-MIRROR | CandidateEngine smoke adapter; no swallowed errors |
| 24 | `replay_edge_fade.py` | SCID · edge fade | ADAPTER | candidate-policy scenario |
| 25 | `replay_excess_counter.py` | bars · EXCESS counter | ADAPTER | policy scenario |
| 26 | `replay_exit_size.py` | executed trades · X1–X4 | ADAPT-MIRROR | migrate execution model/policies |
| 27 | `replay_extremes_aware.py` | trades · target realization | ADAPTER | execution-policy scenario |
| 28 | `replay_f3_step_ladder.py` | trades · step ladder | ADAPTER | execution-policy scenario |
| 29 | `replay_f4_stair_struct_exempt.py` | blocked decisions · real gateway | ADAPTER | policy parity scenario |
| 30 | `replay_f5_runner_trail.py` | trades · runner trail | ADAPT-MIRROR | canonical trail policy |
| 31 | `replay_f6_daytype_stability.py` | labels · F6 | ADAPTER | S1 publication scenario |
| 32 | `replay_g1g2_opening_entry.py` | bars · opening entries | ADAPTER | CandidateEngine scenario |
| 33 | `replay_hlst.py` | bars · HLST | ADAPTER | detector scenario |
| 34 | `replay_maximized_opportunity.py` | all candidates · context | ADAPT-MIRROR | become named kernel scenario |
| 35 | `replay_opening_windows.py` | bars/trades · opening windows | ADAPTER | opening-policy scenario |
| 36 | `replay_release_leg_exempt.py` | decisions · release exemption | ADAPTER | policy scenario |
| 37 | `replay_s7_acceptance.py` | trades · S7 | ADAPTER | score-policy scenario |
| 38 | `replay_target_approach.py` | bars/trades · target approach | ADAPTER | execution-policy scenario |
| 39 | `replay_target_spacing.py` | trades · target spacing | ADAPTER | execution-policy scenario |
| 40 | `replay_trend_step_entry.py` | bars · TREND_STEP | ADAPTER | CandidateEngine scenario |
| 41 | `replay_trend_stop_floor.py` | trades+SCID · stop floor | ADAPTER | stop-policy scenario |
| 42 | `sim_woodies_replay.py` | legacy Woodies smoke | RETIRE-PARITY | replace with S4 CandidateEngine anchor |
| 43 | `week_replay.py` | executed trades · management | ADAPT-MIRROR | execution-policy scenario; no candidate claims |

### Scope expansion found by independent review (44–52)

| # | Tool | Purpose | Classification | Required migration |
|---:|---|---|---|---|
| 44 | `classifier_truth_audit.py` | classifier vs SCID truth | THIN-ADAPTER | DataSource validator + S1 policy report |
| 45 | `extreme_detection_audit.py` | bar-opportunity/bias census | THIN-ADAPTER | coverage scenario; no final-day TPO |
| 46 | `good_pattern_gates.py` | gate-side census | THIN-ADAPTER | decision-journal policy report |
| 47 | `stall_exit_backtest.py` | STALL exit v1 | RETIRE-AFTER-PARITY | superseded by named v2 policy |
| 48 | `stall_exit_backtest_v2.py` | drawdown-gated STALL v2 | THIN-ADAPTER | execution-policy scenario |
| 49 | `test_binary_convergence.py` | S1 binary convergence gate | KEEP-ACCEPTANCE | Task-4 acceptance scenario |
| 50 | `gate_profit_audit.py` | blocked-winner MFE/MAE | THIN-ADAPTER | ledger/coverage report |
| 51 | `audit_pattern_miss.py` | detector miss criteria mirror | RETIRE-AFTER-PARITY | replace rebuilt criteria with CandidateEngine diagnostics |
| 52 | `scripts/research/verify_cvd_atr_availability.py` | data availability probe | OUT-OF-SCOPE-RUNTIME | retain as DataSource preflight only |

## 4. Hidden-default contradictions already confirmed

### Data/population

- DB bars vs SCID truth differ on 14/34 sessions.
- persisted setups, decisions and trades are three different survivor layers.
- some tools re-run live detectors; others replay rows that already survived
  detection/gates.
- six scripts read SCID; most read DB.

### Time/context

- final-day TPO vs developing TPO vs `created_at` availability.
- ET hard-coded as +4 in some SCID utilities.
- date windows differ and are embedded in module constants.
- RTH filters appear in SQL, Python, or are absent.

### Execution

Static constants demonstrate divergence:

```text
contracts: 1 / 4 / 6 / (4,6)
slippage: fixed 1 or sensitivity (0,1,2)
commission: usually $1.50 RT, sometimes implicit/absent
detection window: 19 / 20 / 30 / 32 / full history
dedup: 20 / 30 / pattern-specific / none
slots: one / two / unlimited / actual-trade population
T-10: 15:45 bar-close in one tool, absent elsewhere
```

### Logic duplication

- `good_pattern_fix` mirrors `_detect_reactive/_detect_initiative`.
- `entry_side_replay` monkey-patches pivot functions.
- Dalton state/context is reimplemented in multiple scripts.
- exit/ladder/trail behavior is separately implemented in
  `oracle_study`, `week_replay`, `replay_exit_size`, and F5 scripts.

## 5. Kernel boundaries

See `docs/spec_authority/REPLAY_KERNEL_CONTRACT.md`.

| Boundary | Initial source to adapt |
|---|---|
| DataSource | validated DB reader; `rebuild_bar_truth` as validator |
| CandidateEngine | live S1/S2/S4 pure detector calls |
| Policy | named current/context/gate policies |
| ExecutionModel | consolidate oracle/week/exit-size semantics |
| Report | canonical candidate/decision/trade JSON + manifest/hash |

## 6. Five parity anchors

| Date | Coverage |
|---|---|
| 2026-08-18 | clean BALANCE control; deterministic CVD |
| 2026-08-17 | clean Trend_DD |
| 2026-08-20 | clean Neutral_Extreme / dual-side structure |
| 2026-07-15 | deliberate DB/SCID NOT_JUDGEABLE anchor |
| 2026-07-14 | deliberate TPO/CVD NOT_JUDGEABLE anchor |

The last two remain red until data truth is repaired. Full expected hashes:
`docs/spec_authority/REPLAY_PARITY_ANCHORS.md`.

## 7. Migration order

1. Freeze contract + inventory.
2. Implement manifest/canonical output.
3. DataSource + quality refusal.
4. CandidateEngine adapter.
5. Current-policy adapter.
6. Execution model.
7. Migrate one scenario at a time.
8. Parity on five anchors.
9. Deprecate old tool only after consumers/reports move.

## 8. Stage 0A NOT-DONE

- No kernel code exists.
- Per-tool line-level defaults still need independent verification.
- No anchor parity was run (future kernel does not exist).
- Related out-of-count audit/report tools need consumer mapping in Stage 0B.
- No script is approved for deletion.
