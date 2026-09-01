# T-219 — `shadow_blocked`: give every refused candidate a measurable twin

**SPEC ONLY. Zero code written. Zero flag touched. Implementation requires Michael's ruling.**
מחבר: cowork-scheduled · 2026-09-01 night queue §3 · הפניה: `docs/plans/TASK_LOG.md` T-219

---

## 0. Why — the number that forces this

Section 3 of tonight's queue measured every gate over the full decisions
archive. Raw output is in `STATUS_BOARD.md` (2026-09-01 night). The two lines
that matter:

```
[ledger] 17 file(s), 8363 blocked rows with an entry
 sessions covered: 35  (2026-07-22 → 2026-09-01)
 ALL GATES                    8363     669       408         261    61%
                              ^blocks  ^judged
```

**669 of 8,363 blocks are judgeable = 8.0%.** And per-gate, for exactly the
three gates that are sitting on Michael's desk right now:

| gate | ruling | blocks (35 sessions) | judgeable | **judgeable since 2026-08-25** |
|---|---|---|---|---|
| `extreme_chase_guard` | T-218 | 69 | 1 | **1** |
| `location_gate` | T-216 | 132 | 5 | **10** |
| `daytype_playbook` | T-217 | 259 | 19 | **46** |

**T-218 would be ruled on n=1.** That is not a decision, it is a coin toss with
a paragraph attached.

### The cause is NOT a broken writer — it is history

Since `562f51d2` (2026-08-25, T-103B) `mfe_track` coverage on blocked rows is
**100% for every single gate** (measured: 745 blocked rows 08-25→09-01, all 19
distinct gates at 100%). Before that commit the field did not exist in the
schema at all (verified on a 2026-08-18 row: keys are
`blocked_by · confluence_tag · direction · entry · outcome · pattern · reason ·
system · trade_id · ts` — no `mfe_track`). So the archive cannot be repaired;
it can only be out-waited. **At today's rate `extreme_chase_guard` needs ~2
years to reach n=100.**

### And the ledger, even at 100% coverage, is still not the answer

`blocked_candidate_audit.py` walks bars forward and asks *did t1 or stop come
first*. That is an honest proxy and it is the best available today — but it
is **not** what a real trade faces. It cannot model: the T1/T2/T3 ladder,
stop→BE after T1, MAE-scratch, `STRUCTURE_EXIT_FAILBREAK_V1`, day-type
adaptation (T-214), size, or commission. It also cannot see whether the order
would have filled at all — that is T-213, open, `#942`'s T2 was touched by
4.00 pt and never filled.

⇒ **A blocked candidate needs the same lifecycle a fired one gets, or the
comparison is not apples-to-apples.** That is T-219.

---

## 1. Exact registration point in code

### 1.1 Where the shadow leg dies today

`backend/v9/gateway/trading_gateway.py`

```
759   def route_setup(self, setup, system_id)          ← OUTER wrapper
918   def _route_setup_inner(self, setup, system_id)   ← the gate chain
930       result = {"shadow": None, "demo": None, "live": None, "blocked_by": None}
...
          ~27 gates, each doing:  result["blocked_by"] = "<gate>"; return result
...
3575      shadow_trade = self._execute_shadow(setup, system_id, cross_context)   ← SHADOW LEG
3679+     demo / live slot assignment
```

**`_execute_shadow` sits at line 3575 — below every blocking gate.** Any
`return result` above it kills the shadow leg together with the live one. That
single fact is the whole of T-219: the shadow is not an independent observer,
it is a passenger in the same car.

### 1.2 The insertion point — ONE site, not 27

`route_setup` (line 759) is the only place that sees **every** `blocked_by`
exit, whichever gate produced it, and it runs **after** `_route_setup_inner`
has already returned — so it is structurally incapable of changing a gate
decision. Insert immediately before the existing decision-journal block
(the `try:` at line ~821 that builds `_dec`):

```
route_setup:
    result = self._route_setup_inner(setup, system_id)     # unchanged
    bb = result.get("blocked_by")
    # ── T-219 insertion point ────────────────────────────
    if bb and result.get("shadow") is None and _shadow_blocked_enabled():
        try:
            self._execute_shadow_blocked(setup, system_id, cross_context, bb,
                                         result.get("reason"))
        except Exception:
            logger.warning(...)      # never raises into the trading path
    # ─────────────────────────────────────────────────────
    ... existing _dec journal ...
```

`result.get("shadow") is None` is the precise condition: it fires only when the
block landed **above** line 3575. A block below it (`cluster_guard`,
`trading_paused`) already produced a real shadow row and must not get a second.

### 1.3 The one thing that must be built, not reused

`_execute_shadow_blocked` is `_execute_shadow` (line 4013) with **four
deletions**, not a new engine:

| `_execute_shadow` line | `_execute_shadow_blocked` |
|---|---|
| `accept_setup(tm_setup, "shadow")` | `accept_setup(tm_setup, "shadow_blocked")` |
| `self.shadow_trades.append(...)` (line 3576) | **omitted** — see §3.2 |
| `self._target_spacing_shadow(...)` | omitted (measurement of a measurement) |
| `log_s7_shadow` / `log_tsf_shadow` | omitted for v1 (add later if wanted) |

---

## 2. The fields

The row is a normal `v9_trades` row — no new table, no migration for the trade
itself. What distinguishes it:

| field | value | why |
|---|---|---|
| `mode` | `'shadow_blocked'` | new 4th mode next to `live`/`demo`/`shadow`. `v9_trades.mode` is `varchar(10)` — **`shadow_blocked` is 14 chars ⇒ ALTER COLUMN to varchar(20) is REQUIRED.** Alternative with zero migration: `mode='shadow'` + `quality.blocked_by` — **rejected**, it would silently pollute every existing shadow query in the repo. |
| `quality.blocked_by` | e.g. `location_gate` | the gate that refused it. **The field Michael asked for.** `quality` is already `jsonb`. |
| `quality.block_reason` | `result["reason"]` verbatim | e.g. `"SHORT entry 7641.00 too close to session_low 7632.75 (dist=8.25 < 8.6)"` |
| `quality.gate_stage` | index of the gate in the chain | lets us see "how far did it get" — a candidate killed by `session_gate_closed` is a different animal from one killed at `location_gate`. |
| `quality.candidate_id` | from `setup.metadata.candidate_id` | joins the row to its `gateway_decisions.jsonl` line — one candidate, two records, no guessing. |
| `firing_system`, `direction`, `entry_price`, `stop`, `t1..t4` | as `_execute_shadow` | identical bracket ⇒ identical management. |
| `day_type_at_entry`, `pattern_id_at_entry`, `session_at_entry` | `extract_g1_entry_context(cross_context)` | already computed; the ruling needs to slice by day-type (T-217). |
| `is_synthetic` | `0` | the row is a real simulation, not a reconstructed P&L. Do **not** reuse the T-160 synthetic flag. |

**Every consumer that counts trades must exclude `mode='shadow_blocked'` by
default.** That is the migration's real cost — see §4.3.

---

## 3. How isolation is guaranteed

Five independent locks. Each one alone would be enough; the point is that no
single mistake can turn a measurement into a trade.

**3.1 — Structural: it runs after the decision.**
`route_setup` receives `result` already final. There is no code path from
`_execute_shadow_blocked` back into the gate chain. Even a total failure
(exception, DB down) cannot change `blocked_by`.

**3.2 — Slot: it never touches `live_slot` / `demo_slot`.**
`self.live_slot` is assigned at exactly two sites (3717, 3784) and
`self.demo_slot` at one, all inside `_route_setup_inner`'s demo/live branches,
all below line 3679. `_execute_shadow_blocked` is called from the outer
wrapper and assigns neither. **Verification (T-178 rule): after a
`shadow_blocked` row is opened, `/api/v9/system6/diagnose` must still report
`slot_health.slot_trade_id = None` — read from the endpoint, never inferred
from the DB.**

**3.3 — Sierra: no order can exist.**
The DLL command writers (`write_entry`, `write_exit`, `MODIFY_STOP`) are
reached only from `_execute_live`. `_execute_shadow` today carries the explicit
comment *"no Sierra order exists on this path at all"* (line 4019). Same path,
same guarantee. **And per CLAUDE.md §op=EXIT-broken this spec wires no new
consumer to `_emit_exit`/`write_exit` — none, anywhere.**

**3.4 — Feedback: the measurement must not feed the gates.**
This is the sharp edge and the one that can silently corrupt trading:

- `self.shadow_trades.append(...)` — **omitted.** That list feeds
  `duplicate_fire` and `cluster_guard`. Appending blocked twins would make the
  guards see phantom fires and block *real* setups. This omission is the single
  most important line in the spec.
- `self._daily_trades` / `self._daily_pnl` — **not incremented.** They feed
  `RISK_HALT_V1` (−$450/5d) and `day_entry_budget`. A losing measurement must
  never halt live trading.
- `pattern_stop_cooldown` / `pattern_loss_breaker` state — **not written.**
- TradeManager must treat `shadow_blocked` exactly as `shadow` for
  management, and as *nonexistent* for any occupancy question.

**3.5 — Flag: `SHADOW_BLOCKED_V1`, code default OFF.**
Registered in `config/RULED_FLAGS.yaml` with the ruling pointer in the same
commit (CLAUDE.md §"Rulings are one-time and standing"). Flag off ⇒ the
insertion block is skipped ⇒ byte-identical behaviour to today.

---

## 4. What it costs — measured, not estimated

**4.1 Row volume.** Measured on the archive: **745 blocked rows in 6 sessions
= 124/day mean**, worst observed **468 on 2026-08-31**, today 68. Against ~12
real trades/day that is a **~10× growth of `v9_trades`** (835 rows total today
⇒ +2,600/month). Postgres does not care; **every human-facing query does.**

**4.2 Management load.** Each open row is re-evaluated by
`bar_level_detector` on every 5-min bar. 468 rows × 78 RTH bars ≈ **36.5k
evaluations/session** against ~940 today. The backend is single-worker uvicorn
(CLAUDE.md §Frontend Polling Floors — "aggressive polling chokes it").
**⇒ v1 MUST ship a daily cap** (proposal: `SHADOW_BLOCKED_MAX_PER_DAY=150`,
and skip `duplicate_fire` outright — it is 140 of the 745 and is by definition
a repeat of a candidate already recorded).

**4.3 Query blast radius — the real bill.** Every place that reads
`v9_trades` without a `mode` filter starts double-counting. Must be audited and
filtered *before* the flag is turned on: the P&L/EOD scripts
(`s6_eod_report.py`, `morning_briefing.py`, `pnl_reconcile`), the trade-history
API + `TradeHistoryStrip.tsx`, `phantom_reconcile`, and the replay/study tools.
**This is the work, not the writing of the row.**

**4.4 What it does NOT cost.** No Sierra order, no margin, no commission, no
slot, no risk-budget consumption, no DLL round-trip.

---

## 5. Verification gate before the flag is ever turned on

1. Unit: `_execute_shadow_blocked` called → `live_slot`/`demo_slot` unchanged,
   `shadow_trades` unchanged, `_daily_trades`/`_daily_pnl` unchanged.
2. Mutation: re-add `shadow_trades.append` → a `duplicate_fire`/`cluster_guard`
   test must go RED. If it stays green the guard test is worthless.
3. Anti-tautology: a gate that blocks must still block with the flag ON —
   replay a known blocked candidate and assert `blocked_by` is byte-identical.
4. Sim day with the flag ON: `slot_health.slot_trade_id = None` throughout
   (from `/api/v9/system6/diagnose`, **not** from the DB — T-178).
5. `flag_guard.py` PASS with `SHADOW_BLOCKED_V1` registered.

---

## 6. What this does NOT claim

- It does **not** claim any gate is wrong. It claims all of them are currently
  **undecidable**, and n=1 is not evidence in either direction.
- It does **not** promise the refused trades would have been profitable. It
  promises they would have been *counted*.
- It does **not** replace `blocked_candidate_audit.py`. That script stays as
  the cheap bars-only proxy and as the cross-check against the new rows —
  two independent methods disagreeing is a finding, not a bug to hide.

**עיקרון-העל (מייקל 26.08): "לא מנבאים — נותנים לשוק לענות."** A gate that is
never measured is a permanent prediction. This spec is how the market gets to
answer.
