# CC evening handoff — 2026-07-03 (market closed) · all of today's fixes

**Contract:** obey `docs/handoff/CC_HANDOFF_CONTRACT.md` — anti-tautological
fail-on-old tests · mandatory NOT-DONE section · paste raw verification (Rule 5).
Item specs: `docs/handoff/CC_PATTERN_ECONOMICS_PACKAGE_2026-07-02.md`.
**Pushed:** origin `stabilize/mems26-local-truth-2026-05-16` @ 49128cd (all of
today's Cowork commits are on GitHub).

Backend runs under **launchd** (`com.mems26.backend`). Restart =
`launchctl kickstart -k gui/$(id -u)/com.mems26.backend`, NEVER manual nohup.
DB = local Postgres; psql at `/Applications/Postgres.app/Contents/Versions/18/bin/psql`.

---
## What Cowork built today — DO NOT REBUILD (all flag-OFF, committed, tested)

| item | module | flag | tests |
|---|---|---|---|
| 10 | `opening_type_gate.opening_window_override` | `OPENING_WINDOW_FIRE_V1` | 12 (enable scheduled Mon) |
| 19 | daily-loss halt in `trading_gateway` | `RISK_HALT_V1` (−$450 in .env) | 5 |
| 4 | `stop_anchors/stop_resolver.py` (CC) + **backtest** | `STOP_RESOLVER_V1` | backtest + fuzz |
| 20 | `services/reconcile.py` | (module) | 9 |
| 18 halt-proof | `systems/day_direction.py` | `DAY_DIRECTION_DOCTRINE_V1` | 10 |
| 22 | `systems/target_zones.py` | `TARGET_ZONES_V1` | 8 |
| 6 | `systems/entry_confirm.py` | `S4_ENTRY_CONFIRM_V1` | 10 |
| — | `test_property_invariants_2026-07-03.py` (15k fuzz) | — | 5 |

Property/fuzz already **found + guarded** a real bug: `resolve_stop` could emit a
stop on the wrong side of entry (side-guard added, CC's 8 tests still green).
**Live-now flags:** `RR_ENTRY_GATE_V1=1` (Michael 07-03), `FIXED_CONTRACTS_3=1`,
`DAYTYPE_TARGETS_STRUCTURAL=1`, resolver floor/grid/monotonic, I-57..I-61, cooldown
OFF (standing). 76 regression tests green last run; `gen_flag_index --check` PASS (87).

---
## ⛔ PRE-RESTART GATE — resolve I-62 first
Before ANY restart: confirm **0 open positions**. Today's live orphan (I-62,
ledger): trade 290 (demo SHORT) was marked CLOSED by `BarLevelDetector` on a
bar-close price while **Sierra still held the position**; `demo_slot` is stuck at
290 (DB shows 0 open). Michael was to flatten 290 manually in Sierra. Verify:
`psql ... "SELECT count(*) FROM v9_trades WHERE state NOT IN ('CLOSED','closed')"`
== 0, and ask Michael that Sierra is flat. The restart clears the stuck in-memory
slot; do not free it manually while a Sierra position may be live.

---
## Priority 1 — I-62 fix (the real bug that bit today)
**Root:** demo/live trades are closed from `BarLevelDetector` bar-price inference
(exit_ts landed on an exact bar boundary 19:20:00) instead of the authoritative
**Sierra fill event** (per-contract stop order-ids 8356/8359/8362 via FillPoller).
Fine for SHADOW, WRONG for demo/live → internal "closed" while Sierra holds → orphan.
**Build:** (a) for demo/live, close a trade ONLY on the FillPoller stop/target fill
event, not on `BarLevelDetector` (keep BarLevelDetector for SHADOW). (b) Wire the
item-20 `reconcile.gather_and_reconcile()` into a periodic check + surface a loud
warning + an API route `/api/v9/reconcile/status`. (c) Harden the I-57 self-heal to
also fire when the slot is stuck with a CLOSED DB row even without a new route
attempt. Add a fail-on-old regression reproducing 290 (bar-close hit while no
Sierra fill → must NOT mark demo closed).

## Priority 2 — item-4 wiring + net-P&L backtest
Wire `resolve_stop()` at the S2 (`setup_emitter`) and S4 (`woodies_system.py`
per-pattern) stop-anchor choke points behind `STOP_RESOLVER_V1`, using the REAL
per-pattern ladders (not the backtest's generic proxy). Then extend
`scripts/backtest_stop_resolver_item4.py` to net saved-R against the wider-loser $
cost. Backtest evidence today: 31/86 stops financed, 30 preventable stop-outs
(`docs/reports/BACKTEST_STOP_RESOLVER_ITEM4_2026-07-03.md`). Keep the flag OFF until
the net pass is green + Michael signs off.

## Remaining package (evening)
item-11 (sizing consolidation: retire legacy `calculate_size` in the routing path,
V2-only, + TradeManager single-point notify) · item-12 (`TT_SPEC_V2` from the
transcribed source) · item-13 (`PB_SHAPE_FILTER_V1`) · item-16 (`VOL_REGIME_V1` —
**ask Michael** whether the volatile-day 2-contract override beats `FIXED_CONTRACTS_3`)
· item-17 (decision-journal PG table + "why no trade" tab) · Mechanism-C behavioral
test (replace the string-check e291bed).

---
## On completion (every item)
Fail-on-old test · `gen_flag_index.py` if a flag changed · update
`docs/plans/STATUS_BOARD.md` (finding+fix+raw verification) and
`ROADMAP_TO_LIVE.html` · one final `launchctl kickstart` restart AFTER the
0-open-trades check, paste boot-line + health. **End with an explicit NOT-DONE
list.** STOP and ask Michael before enabling any flag or any trading-risk decision
(item-16 contracts, the consecutive-loss number, starting the 5-demo-day window).
