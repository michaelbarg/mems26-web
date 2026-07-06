# LIVE Flag Config — 2026-07-06 (first real-money session)

Snapshot of the flags we want ACTIVE for the LIVE session. `.env` is not
git-tracked (protected by `scripts/mems26_snapshot.sh`), so this file is the
recoverable record of intent. `docs/FLAG_INDEX.md` (generated) has the full
94-flag state + semantics.

## Execution + mode (the live-critical set)
| Flag | Value | Role |
|---|---|---|
| `MEMS26_MODE` | `live` | Display/label mode (FillPoller gated on DEMO_EXECUTION_ENABLED, not this) |
| `LIVE_TRADING_V1` | `1` | Gateway routes S2/S4 to `_execute_live` (main.py enable_live(2,4); live REPLACES demo) |
| `LIVE_EXECUTION_V1` | `1` | `_execute_live` actually writes `mode:"live"` to Sierra (APEX-125218-13) |
| `DEMO_EXECUTION_ENABLED` | `1` | Starts the FillPoller (processes demo+live fills → P&L from Sierra) |

**Real orders require BOTH** `LIVE_TRADING_V1=1` AND `LIVE_EXECUTION_V1=1`.

## Sizing
| Flag | Value | Role |
|---|---|---|
| `FIXED_CONTRACTS_2` | `1` | 2 contracts (precedence over _3) |
| `FIXED_CONTRACTS_3` | `1` | 3-contract fallback (06-24 standing decision, kept) |
| `SIZING_CONSOLIDATION_V1` | `1` | One sizing authority; S4 risk-cap → explicit gateway blocked_by |

## Risk / safety
| Flag | Value | Role |
|---|---|---|
| `RISK_HALT_V1` | `1` | Daily-loss halt (block-only, all modes) |
| `RISK_DAILY_LOSS_CAP` | `400` | −$400 daily halt |
| `EOD_RISK_WINDOW_V1` | `1` | No new entries last 45 min → **no entry after 22:15 IL** |

Plus the 22:15 flatten-alert scheduled task `mems26-flatten-2215-rth`.

## Stops / targets (all ON)
`STOP_ANCHORS_V2` · `STOP_RESOLVER_V1` (structural stop + T1 3-pt floor) ·
`TARGET_ZONES_V1` (T2/T3 confluence) · `RUNNER_TARGETS_V1` · `RUNNER_TRAIL_V1` ·
`DYNAMIC_STRUCT_TRAIL` · `GIANT_BAR_STOP_V1` · `PATTERN_RISK_CAPS` ·
`DAYTYPE_TARGETS_STRUCTURAL`. Risk cap 25 pts ($125/ct). T1 bounded 3-10 pts.

## System 6 (advisory only)
`SYSTEM6_SUPERVISOR=1` · `SYSTEM6_EXIT_SIGNALS=1` · `SYSTEM6_EXIT_JOURNAL=1`.
**`SYSTEM6_AUTOCORRECT` = OFF** (never auto-applies to a live trade).

## Entry / opening
`RR_ENTRY_GATE_V1=1` · `S4_ENTRY_CONFIRM_V1=1` · `OPENING_TYPE_GATE=1` ·
`OPENING_FIRE_CVD_V1=1` · **`OPENING_WINDOW_FIRE_V1=1`** (item-10 — positive-drive
opening override; auto-enabled 15:43 by the Monday scheduled task per the 07-03
ruling. ⚠ See note below — this was a DEMO-era ruling; now live on real money).

## Day-type / direction / classifier
`S1_NEW_CLASSIFIER=1` (7-type) · `S1_ENGINE_NEW_CLASSIFIER=1` · `S1_*` staging set ·
`DAYTYPE_GATE_LIVE_V1=1` · `DAYTYPE_PATTERN_AWARE_V1=1` · `DAYTYPE_PLAYBOOK=1` ·
`DIRECTION_CONTEXT=1` · `DIRECTION_LSMA_VETO=1` · `CONT_TREND_FILTER=1` ·
`HTLB_DIRECTION_GATE=1` · pattern specs `ZLR/TLB/VEGAS_SPEC_V2=1`.

## Deliberately OFF (standing decisions — do NOT re-enable without Michael)
`SYSTEM6_AUTOCORRECT` · Layer-0 chop gate · S2 `choppiness_ok` ·
`S2_REQUIRE_COT_AMT` (S2 ⟂ S3) · `T1_LADDER_V2` (backtested flat/negative).
`S3_MUTE=1` / `FOOTPRINT_DISABLED=1` / `HFE_DISABLED=1` / `NONTREND_DISABLE_ALL=1` — intentional mutes.

## ⚠ Open decision for the live session
`OPENING_WINDOW_FIRE_V1` (item-10) fires the system MORE aggressively with the
drive in the first 30 min. It was auto-enabled for "Monday" per a 07-03 ruling
made in a DEMO-validation context; today is real-money LIVE. Michael to confirm
keep-ON (aggressive open) vs OFF (conservative first live open).
