# Adversarial review — `aa5b6af9..32e42558` (2026-08-14 → 2026-08-17)

Read-only audit. No code, flag, `.env`, service or `~/SierraChart_Data` write was
touched. Reviewer: independent agent, 2026-08-17 07:15–08:05 IL, before the 16:30 open.

Scope: 15 commits, `176 files changed, 6204 insertions(+), 436 deletions(-)`.

```
$ git log --oneline aa5b6af9..HEAD | wc -l
15
$ git diff --stat aa5b6af9..HEAD | tail -1
 176 files changed, 6204 insertions(+), 436 deletions(-)
```

---

## 0. Live state at review time (this is the context every finding sits in)

```
$ cat ~/SierraChart_Data/v9_export/sierra_state.json
{"ts":1786940193,"is_sim":0,...,"position_qty":5,"avg_price":7807.25,
 "trade_account":"37138283",...,"working_orders":1,
 "orders":[{"id":10237,"type":3,"bs":2,"price":7806.00,"qty":8}]}
```

The **LIVE** account (`is_sim:0`) currently holds **5 long contracts** protected by a
single **qty-8 SELL stop**. This is Michael's manual position. Every finding below
about `FLATTEN_ACCOUNT` and about the scale-in ceiling is not hypothetical today.

```
$ ps -o pid,lstart,command -p $(pgrep -f uvicorn)
47659 Mon Aug 17 06:42:55 2026  ... uvicorn backend.main:app --host 0.0.0.0 --port 8000
$ git log --format='%h %ci' -3 aa5b6af9..HEAD
32e42558 2026-08-17 07:07:41   ad300377 2026-08-17 06:44:44   c75e61c7 2026-08-17 05:03:31
```

**The running backend was started at 06:42:55 — before `ad300377` (06:44:44).** The
scale-in guards reviewed below are *not loaded in the live process*.

---

## 1. BLOCKERS — do not trade until fixed

### B1 · T1 armed an account-wide wipe on two auto paths, while Michael holds 5 manual contracts

`sc_study/MES_AI_DataExport_merged.cpp:3636-3644`

```cpp
else if (cmd_content.find("\"FLATTEN_ACCOUNT\"") != std::string::npos)
{
    int r = sc.FlattenAndCancelAllOrders();
```

`FLATTEN_ACCOUNT` is **account-wide** and also **cancels every working order**. It is
explicitly *not* gated on `order_armed` and not gated on `is_sim`.

Before T1, all three callers raised `TypeError` and wrote nothing — that was the #682
bug. T1 fixed the call shape (`backend/v9/services/sierra_command.py:501` →
`write_flatten_account`). Two of the three callers now fire **automatically**:

| path | file:line | flag | state |
|---|---|---|---|
| `MAE_SCRATCH` | `bar_level_detector.py:817-822` | `S6_MAE_SCRATCH_V1` | **=1 in `.env`** |
| `TARGET_APPROACH_REALIZE` | `bar_level_detector.py:741-745` | `S6_TARGET_APPROACH_REALIZE_V1` | **=1 in `.env`** |

Neither call site performs any ownership check before writing. The first MAE_SCRATCH
today closes Michael's 5 contracts and cancels his qty-8 stop. This is a direct
violation of the 07-24 ownership ruling and of the 08-17 12:20 ownership ruling that
`exit_verifier.py:116-122` itself cites.

The irony: `exit_verifier._account_holds_foreign_position` was written to stop exactly
this — but it only guards the **retry**, never the **first** emission. And it does not
work either (see F1).

**Smallest correct change (today):** set `S6_MAE_SCRATCH_V1=0` and
`S6_TARGET_APPROACH_REALIZE_V1=0` for any session where Michael holds a manual
position. **Proper fix:** before writing, require
`abs(_sierra_state_qty()) == trade_contract_count(trade)`; otherwise alert-only.
Longer term these paths need a per-position exit, not `FlattenAndCancelAllOrders`.

---

### B2 · T2's write-back records *intent* as *fact* — the opposite of T4, in the same commit set

`backend/v9/services/trade_manager/manager.py:270-283`

```python
try:
    trade.stop = float(new_stop)
    self._db.commit()
```

`write_modify_stop` only **writes a command file**. There is no DLL ACK, no fill, no
confirmation. The write-back sets `trade.stop = new_stop` unconditionally.

`backend/v9/systems/system6_supervisor.py:158-164` — the invariant that used to catch
this reads the **books**:

```python
at_be = (d == "LONG" and stop >= entry) or (d == "SHORT" and stop <= entry)
if not at_be:
    issues.append(Issue("stop_not_at_be", WARN, AUTO, ...))
```

Sequence that loses money:

1. T1 hits. `_emit_modify_stop(trade, BE)` writes `cmd_NNN.json`, sets `trade.stop = BE`, commits.
2. The command is rejected (`r=-1`) or expires unsent in the queue — **measured 110 times on 08-14**, see below.
3. `stop_not_at_be` now reads `stop == BE` → **never fires again**. The 60s dedup is irrelevant; the invariant is silenced permanently.
4. Sierra's stop is still at the original level. The panel, the API and S6 all report BE.
5. Price returns → full stop loss instead of a BE scratch.

T4 exists because "a written command is not an exit." T2 asserts, in the same batch,
that a written command *is* a stop move. One of the two is wrong, and it is T2.

**Smallest correct change:** keep the 60s in-memory dedup (it does fix the flood), drop
the unconditional `trade.stop` write-back, and re-key the invariant against
`_sierra_state_orders()` — the DLL already publishes working orders with price
(`orders:[{"id":10237,"type":3,"bs":2,"price":7806.00,...}]`). If the write-back must
stay, it needs a `stop_ack` flag cleared until a working order at that price is seen.

The flood claim itself **verifies**:

```
$ grep -ho '"op": *"[A-Z_]*"' ~/SierraChart_Data/v9_export/command_queue/archived_stale/* | sort | uniq -c
   1 "op": "CANCEL"
 110 "op": "MODIFY_STOP"
   1 "op": "NOOP_TTL_PROBE"
   3 "op": "PLACE"
$ head -c 200 .../archived_stale/cmd_000400.json
{"op":"MODIFY_STOP","trade_id":"657","order_id":10110,"new_stop":7775.25,"mode":"demo",...,"_seq":400}
```

110 expired MODIFY_STOP, trade 657, identical `new_stop=7775.25`, ~2.4s apart. Note
`"mode":"demo"` — the flood was a demo trade, not live.

---

### B3 · The "zero new failures" claim is FALSE. Three P&L tests are now red.

```
$ git worktree add /tmp/rev_base aa5b6af9 && cp .env /tmp/rev_base/.env
$ /tmp/runsuite.sh <tree> <out>     # same cmd, same .env, both trees:
                                    # python3 -m pytest tests -q -p no:randomly
HEAD : 406 failed, 4028 passed, 4 skipped, 2 xfailed, 133 warnings in 88.36s
BASE : 402 failed, 3935 passed, 4 skipped, 2 xfailed, 129 warnings in 94.96s

$ comm -23 head_fail.txt base_fail.txt
FAILED tests/v9/regression/test_live_execution.py::test_stop_pnl_uses_fill_price_not_stop_level
FAILED tests/v9/services/test_trade_manager.py::TestPnlCalculation::test_short_stop_loss
FAILED tests/v9/services/test_trade_manager.py::TestPnlCalculation::test_stop_loss_pnl
FAILED tests/v9/systems/test_woodies_process_bar_perf.py::test_process_bar_under_1s_...
$ comm -13 head_fail.txt base_fail.txt      # nothing fixed
(empty, modulo one log-line diff)
```

Reproduced in isolation:

```
$ python3 -m pytest tests/v9/services/test_trade_manager.py::TestPnlCalculation::test_stop_loss_pnl ... -q
E  AssertionError: pnl should be -$120 (fill-based), not -$105 (stop-based), got -37615.0
E  assert -37615.0 == -120.0
3 failed, 2 warnings in 0.49s
```

The 4th (`woodies_process_bar_perf`) is a timing flake. The other **three are the P&L
tests for the stop path** — precisely the code T3 rewrote. They are red because
`_legs()` now builds `n_contracts` legs instead of the old fixed 3, and nobody
re-derived the expected values. Whatever the merits of the change, **the regression net
over `_calculate_pnl` is currently torn open**, and it was torn open by the commit that
rewrote `_calculate_pnl`.

The claim "I compared the full suite against a baseline worktree and saw zero new
failures" does not hold. My best reconstruction of how it was reached: the suite was
run without `.env` in the environment, in which case *both* trees die at collection on
`RuntimeError: BRIDGE_TOKEN env var is required` and the FAILED lists are trivially
equal. That is what happened on my first attempt.

---

### B4 · The DLL ladder is **not compiled**. The deployed binary is from July 28.

```
$ find ~/ -maxdepth 5 -name "MES_AI_DataExport*.dll" | xargs ls -la
-rw-r--r--  863744  Jul 27 13:49  ~/SierraChart/Data/MES_AI_DataExport_ARM64.dll
-rw-r--r-- 1113088  Jul 28 12:59  ~/SierraChart/Data/MES_AI_DataExport_64.dll
-rw-r--r-- 1047040  May 16 12:05  ~/SierraChart/Data/archive/..._2026-05-16.dll
$ ls -la ~/SierraChart/ACS_Source/MES_AI_DataExport.cpp
-rw-r--r--  190000  Aug 17 04:07
$ git log --since=2026-07-28 --format='%h %ci' -- sc_study/MES_AI_DataExport_merged.cpp
e43cd0eb 2026-08-16 22:13:29     # the ladder
a178d965 2026-07-28 12:58:06     # last one that was actually built
```

The `.cpp` was copied to `ACS_Source` this morning, but **no Remote Build was run** —
there is no binary newer than 2026-07-28 12:59 anywhere on the machine.

Worse, the two things that are supposed to catch this both report green:

- `scripts/mems26_verify.sh:37-43` compares the **deployed `.cpp`** hash against the repo `.cpp`. It says "deployed DLL == committed monolith" while the binary is three weeks old.
- `tests/v9/regression/test_contract_size_resolver.py::test_backend_ladder_matches_the_dll_table` asserts `"lq[0]=1; lq[1]=2; lq[2]=2; lq[3]=1;" in src` — it greps the **source text**. Same failure mode as the six green tests that missed #682, one level up.

**Consequence:** if `FIXED_CONTRACTS_5` or `FIXED_CONTRACTS_6` is switched on today, the
*deployed* DLL still hard-codes `OCOGroupNQuantity = 1` (sum = 4) while
`o.OrderQuantity = contracts`. **1–2 contracts enter with no stop and no target**,
invisible because the position looks bracketed. That is the naked-orphan class of
07-10 / 07-14 / 07-17 / 07-20 / 07-23.

At `FIXED_CONTRACTS_4=1` the ladder is a no-op (`lq = 1,1,1,1`, `lq_sum = 4`), so there
is no risk at today's size. But "the DLL ladder shipped" is false, and `5`/`6` are
**hard-blocked** until a build is done and its timestamp verified.

---

### B5 · `exit_verifier` can wedge the LIVE slot for the rest of the day

`backend/v9/gateway/trading_gateway.py:3179-3180` — the LIVE slot is released only
inside `on_trade_close`:

```python
if self.live_slot and str(self.live_slot.get("trade_id")) == str(trade_id):
    self.live_slot = None
```

`on_trade_close` runs only from `_mae_close` / the fill path — i.e. only after
`exit_verifier` calls `p.on_confirmed()`. Trace the failure branches in
`backend/v9/services/exit_verifier.py`:

| branch | line | outcome |
|---|---|---|
| stale `sierra_state` > 300s | 286-295 | `del _pending[tid]`, alert, **books stay OPEN forever** |
| account holds "foreign" position | 305-318 | `del _pending[tid]`, alert, **books stay OPEN forever** |
| attempts exhausted | 335-343 | `del _pending[tid]`, alert, **books stay OPEN forever** |

In all three, the pending is dropped and nothing ever closes the trade. `live_slot`
stays occupied → **no further LIVE trade for the remainder of the session.** The
comments say "an open book over a live position is the recoverable side," which is true
for *risk* but not for *opportunity* — and nothing in the code recovers it. The only
path that could is `POSITION_TRUTH_SYNC_V1` 'SIERRA_FLAT', which requires the whole
account to go flat — impossible while Michael holds his 5.

Concretely today: system trade open (4c) + Michael's 5c = account 9. MAE_SCRATCH fires
→ FLATTEN_ACCOUNT wipes everything → account 0 → `qty == 0` → confirmed. Fine. But if
the FLATTEN is rejected while Michael's contracts remain, `_exit_happened` needs
`moved >= 4`; if he simultaneously adds one, the delta is ambiguous, the retry path
runs, and after 2×45s the slot is dead for the day.

**Two exits pending:** `_exit_happened` line 174 — `if len(_pending) > 1: return False`
→ **both** now demand `qty == 0`. With any manual position open, `qty` never reaches 0,
so *both* trades wedge. This is a deliberate safety choice (avoiding mis-attribution)
with an unmanaged cost.

**Can it close the WRONG trade?** With `len(_pending) == 1` and a manual position:
`moved = abs(before) - abs(qty) >= n`. If Michael manually closes 4 of his own
contracts during the 45s window, `moved == 4 == n` → the verifier confirms an exit that
never happened and closes the books over a live system position. **That is #682 again**,
and the `len(_pending) > 1` guard does not cover it because it is one pending, not two.

**Smallest correct change:** verification must be attributed, not measured by account
delta — compare `sierra_state.orders[]` for the trade's own `stop_ids`/`order_id`, or
require the fills journal to show `n` exit fills for this trade. Failing that, the three
`del _pending[tid]` branches must hand the trade to a terminal state that releases the
slot (e.g. `close_trade(reason="UNVERIFIED")` + a loud alert), not leave it hanging.

---

## 2. FIX-TODAY

### F1 · `_account_holds_foreign_position` is inoperative — it fails open exactly when it matters

`backend/v9/services/exit_verifier.py:196-206`

```python
_open = {int(getattr(t, "id", -1)) for t in (getattr(_tm, "get_active_trades", ...)() or [])}
owns = any(int(v) in _open for v in _omap.values() if str(v).isdigit())
return not owns
```

The whole premise of T4 is that **the pending trade's books stay OPEN**. So the pending
trade is always in `_open`. `_omap` (`fill_poller.py:60,132`) is a historical
`order_id → trade_id` index that contains that trade's own entry order. Therefore
`owns` is **True on every real pending exit**, `_account_holds_foreign_position` returns
**False**, and the retry fires a second account-wide `FLATTEN_ACCOUNT` over Michael's
manual position — the precise outcome the function's docstring promises to prevent.

The correct test is the complement of what is written: the account is foreign if
`abs(qty) > sum(contracts of open system trades)`.

### F2 · "One resolver replacing a ladder duplicated in 8 files" — 4 sites were not converted

```
$ grep -rn "FIXED_CONTRACTS_[0-9]" --include=*.py backend scripts | grep -v tests | grep -v contract_size.py
backend/v9/api/v9/system6_routes.py:22,24,26     # _ct_resolve()  — stops at 4
backend/v9/api/v9/system6_routes.py:68,69,70     # diagnose()     — stops at 4
backend/v9/services/trade_manager/manager.py:82,84,86,88   # trade_contract_count — has _6, MISSING _5
backend/v9/systems/five_min/five_min_system.py:1515-1516   # EDGE_FADE — INVERTED precedence
scripts/fire_drill.py:109-111                    # stops at 4
```

`contract_size.py:3-7` names `system6_routes` and `fire_drill` as converted. They are
not. Two are materially wrong:

- `five_min_system.py:1515` — `3 if FIXED_CONTRACTS_3 else (4 if FIXED_CONTRACTS_4 else 1)`. `_3` is checked **before** `_4`, the opposite of every other site. Inert today (`FIXED_CONTRACTS_3=0`), live the moment anyone sets both.
- `manager.py:82-88` — `trade_contract_count` handles `_6` but **not `_5`**. Under `FIXED_CONTRACTS_5=1`, `sierra_command` sizes 5 and the P&L books 3 legs. This is precisely the "trade the old size and report the new one" hazard the module was written to abolish.

`test_contract_size_resolver.py::test_every_choke_point_agrees_on_four` only inspects
four modules (`qt, sz, sc, mm`) — it is scoped to the sites that were converted, so it
passes by construction.

**Verified no behaviour change at today's config** (`FIXED_CONTRACTS_4=1`,
`SIZE_CAP_OVER_FIXED_V1=1`, `SIZE_CAP_CUT_V1=1`): old `_fixed = 4 if _fc4_on else (2 if
_fc2_on else (3 if _fc3_on else _contracts))` = 4; new `_ruled()` = 4 (`_6`,`_5` unset).
The `min(_fixed, _cut)` and the `"half"/"full"/"quarter"` string path
(`sierra_command.py:663`) are untouched. `_on()` adds `.strip()`, which only widens
acceptance. **The 4-contract path is byte-identical — that part of the claim holds.**

### F3 · `_legs()` ignores `target_index_for_contract` — wrong at 5 and 6

`manager.py:1649-1655` maps contract *i* → `_targets[i]`. Under the ruled 1/2/2/1
ladder at six, two contracts ride T1 and two ride T2. `contract_size.target_index_for_contract`
was written for exactly this and is **called from nowhere outside its own tests**:

```
$ grep -rn "target_index_for_contract" --include=*.py . | grep -v tests | grep -v contract_size.py
(no output)
```

At six, `_legs` gives `c0→t1, c1→t2, c2→t3, c3→t4, c4→fill, c5→fill` instead of
`1@T0, 2@T1, 2@T2, 1@T3`. Dead code that is also the fix. Harmless at 4 (LADDER =
1,1,1,1, one-to-one) — verified `t4` is never populated (`SELECT count(t4) FROM
v9_trades` → **0** of 597), so leg 4 correctly falls back to the fill.

### F4 · The live backend predates the scale-in guards

`ad300377` (06:44:44) landed after the backend started (06:42:55). `SCALE_IN_V1=1` is
ON and the **old, unguarded** scale-in is what is running. Restart before 16:30, or the
two "BLOCKER" fixes in that commit message are not in effect.

### F5 · Tests I judge worthless

`tests/v9/regression/test_fusion_gate_does_not_block_early.py` — **all 6 tests, the
entire file**, are `inspect.getsource()` substring matches (`assert "if self._oe_fusion
is not None or len(self._oe_bars) >= 8:" in blk`). It executes no fusion logic, no bar
sequence, no gate. It asserts that a line of source exists. This is verbatim the
mistake the same commit set calls out — "six regression tests were green the whole
time; they were `inspect.getsource()` string matches." It will pass forever, including
after a refactor that breaks the gate, and it will fail on a whitespace change.

Others with the same defect (counts = source-matching assertions / total tests):

| file | source-match asserts | tests |
|---|---|---|
| `test_fusion_gate_does_not_block_early.py` | 6 | 6 — **delete or rewrite** |
| `test_flatten_account_executes.py` | 11 | 7 |
| `test_reconciler_alert_spam.py` | 11 | 8 |
| `test_scale_in_guards.py` | 7 | 13 |
| `test_exit_verified_before_close.py` | 5 | 24 |
| `test_contract_size_resolver.py` | 2 (incl. the DLL one) | 14 |

`test_scale_in_guards.py:97-119` asserts `"n_open = abs(int(_acct))" in blk` — an exact
source string. Rename the local and the test fails; break the semantics while keeping
the name and it passes.

`test_trend_step_entry.py::TestWiring` — `assert 'bar_router.subscribe("5min",
_trend_step_on_bar)' in src`. Same class.

**Genuinely executing and worth keeping:** `test_modify_stop_idempotent.py` (0
source-matches, 6 executing tests), `test_pnl_all_contracts.py` (0/7),
`test_opening_fusion_volume_units.py` (0/5), and the executing half of
`test_exit_verified_before_close.py` (19 of 24).

### F6 · `wire_guard` is blind to the pattern the new code actually uses

`scripts/wire_guard.py:122-126` resolves a call by **name only**:

```python
name = (f.id if isinstance(f, ast.Name) else f.attr if isinstance(f, ast.Attribute) else None)
if name not in _SIGS: continue
```

Aliased imports are invisible. The MAE_SCRATCH FLATTEN — the #682 call site itself — is
now written as:

```python
from backend.v9.services.sierra_command import write_flatten_account as _mae_write   # :818
_mae_write(trade_id=str(trade.id), source="mae_scratch", reason=_scratch_reason)     # :821
```

`_mae_write` is not in `_SIGS`, so **wire_guard skips it**. 13 more aliased sites
(`push as _pp`, `on_close as _oc`, …) are equally unchecked:

```
$ grep -rn "import \(write_[a-z_]*\|push\|on_close\|on_fire\) as " --include=*.py backend | wc -l
14
```

Also `SCAN_DIRS = ["backend"]` only — `scripts/sim_matrix_e2e.py:161` calls
`write_modify_stop` and is never checked. Fix: resolve aliases from the module's
`ImportFrom` nodes, and add `scripts` + `bridge` to `SCAN_DIRS`. Current output
(`23 call sites bound`, exit 0) overstates coverage.

### F7 · The scale-in ceiling now counts Michael's contracts — reinforcement is near-dead on mixed days

`bar_level_detector.py:~995-1010`:

```python
_acct = _sierra_state_qty()
if _acct is None: return                       # stale file → no add
if (_want_long and _acct <= 0) or (not _want_long and _acct >= 0): return
n_open = abs(int(_acct))
```

Right now `_acct = +5` (Michael, LONG). If the system opens a **SHORT 4**, net = `+1` →
`_want_long` False, `_acct >= 0` → **no reinforcement, ever, all day**. If the system
goes LONG 4, `n_open = 9` → already over the 8 ceiling → **no reinforcement**. Either
way `SCALE_IN_V1` (live since 08-13) is inert whenever Michael holds a manual position.

It also answers the stale-file question directly: **yes** — `_acct is None` returns
without adding, and `_sierra_state_qty` returns `None` on a file older than 10s
(`sierra_position_reconciler.py:61`). In a fast market with the DLL write lagging, the
reinforcement silently does not fire. Failing safe, but the log line is a `warning`
that nobody will correlate to a missing add.

The direction of caution is right; the denominator is wrong. `n_open` should be the
system's own open contracts (for `should_scale_in`) while the **cap** may legitimately
count the account (margin is account-wide) — two different numbers, currently one.

---

## 3. LATER

- **L1 · T5's throttle does not fix the reported symptom.** `_div_state = (tm_qty, sierra_qty, src)`; `_div_changed` → alert. Michael's complaint was alerts *while he scaled out by hand* — every partial fill changes `sierra_qty`, so every one is a "new state" and still pushes immediately. The throttle only silences a genuinely frozen divergence.
- **L2 · T3 does not reproduce the number in its own commit message.** #682 in DB: entry 7799.25, exit 7804.25, `contracts=4`, `pnl_usd = -75` (= 5pt × $5 × **3** legs). The new `_legs()` books **4** legs = **−$100**, not the −$83.75 claimed from the fills journal. The model still applies one `exit_price` to all non-target legs, so partial fills at different prices remain unrepresentable. "P&L counts every contract" is true; "P&L matches reality" is not.
- **L3 · "102 four-contract trades" is wrong.** `SELECT quality->>'contracts', count(*) FROM v9_trades WHERE exit_price IS NOT NULL GROUP BY 1` → `4: 98`, `2: 60`, `3: 37`, `1: 9`, `0: 7`, `NULL: 254`. It is **98**. Separately, those 254 NULL-contract closed trades now resolve through `trade_contract_count` → env → **4**, which is wrong for every one of them that was a 2- or 3-contract trade.
- **L4 · T6 uses a clock test, not a completeness test.** `ts <= now() - interval '5 minutes'` is correct in principle — verified `ts` is the bar **open** time (`max(ts)=00:10:00 ET` at `now()=00:13:13 ET`, i.e. the 00:10 row exists mid-bar). But at exactly T+5:00 the row for T may still be mid-rewrite by the DLL, and if the feed lags the query happily returns a stale "closed" bar. A `ts < (SELECT max(ts) …)` form is completeness-based and immune to both. **First 30 minutes:** `build_setup` needs ≥6 closed bars and `detect_trend_step` needs `i >= 4` plus 2 zigzag pivots at 5.0pt — so the first possible TREND_STEP is ~10:00 ET, one bar later than before. That is the intended cost and it is acceptable.
- **L5 · T7 fusion latch — walked minute by minute, it is correct.** 09:30–09:55 → `len(_oe_bars) < 6`, no fusion attempted, gate not consulted (`_oe_fusion_done` False at `five_min_system.py:1383`). 10:00 (6th live bar) → fusion queried; if the 6th row is not closed, `get_opening_dir_fusion` returns `None` (`trade_context.py:~985`, `_n_closed < 6`) and the latch does **not** close, so the gate is skipped and the candidate is judged on its other merits. 10:05/10:10 → retried. 10:15 (8 bars) → latch closes on whatever the answer is. **Not gated, not dropped; delayed by at most 2 bars, and only for the gate, not for the fire.** The design is sound. Its test file is worthless (F5) but the code is right. One nit: the `_ov` subquery filters `< '16:00'` while `_n_closed` does not — harmless here, inconsistent.
- **L6 · `Gateway.on_trade_close` push.** `_close_notified` is a set that never resets; unbounded over a long uptime and it would suppress a legitimate re-close after a restart-less book reopen. Trivial. Verified no double-notify: `fill_poller.py:116` calls `on_trade_close`, and the local `ntfy_notify.on_close` was removed at `fill_poller.py:124`.
- **L7 · `v9_bars_5min_sessions`** is applied (`information_schema.views` → 1) and has zero consumers. Harmless.
- **L8 · `mobile_monitor.py:278`** — `out["contracts_cfg"] = _ruled() or 3`. `ruled_contracts()` never returns 0, so `or` is safe today, but it is the kind of truthy-fallback the repo has been bitten by. `ruled_contracts_or(3)` already exists and is unused.

---

## 4. Behaviour changed with no executing test

- `write_flatten_account` sending an **account-wide** flatten while a foreign position is open (B1) — no test covers ownership at the first emission, because no such check exists.
- `_account_holds_foreign_position` (F1) — `test_exit_verified_before_close.py` never constructs a populated `_order_map` + open-trade set, so the inoperative branch is never executed.
- The three `del _pending[tid]` terminal branches and their effect on `gateway.live_slot` (B5) — the slot is never asserted in any test.
- `exit_verifier` with `len(_pending) > 1` and a **non-zero manual** position — the double-wedge.
- The MODIFY_STOP write-back's interaction with `stop_not_at_be` (B2). `test_modify_stop_idempotent.py` tests the dedup and the rollback; nothing tests that a *rejected* command leaves the books lying.
- `trade_contract_count` at `FIXED_CONTRACTS_5` (F2).
- `_legs()` at 5 or 6 contracts (F3) — `test_pnl_all_contracts.py` covers 1–4 only.
- The compiled-DLL ladder (B4) — only the `.cpp` text is asserted.
- Scale-in with a same-side manual position inflating `n_open` (F7).
- `system6_routes._ct_resolve` / `fire_drill` divergence from the resolver (F2).

---

## 5. Verdict

The diagnoses in this batch are good — #682, the 393-command flood, the `[:3]` slice,
the fusion unit mismatch and the forming-bar bug are all real, and I verified the two
that are checkable from raw data (110 expired MODIFY_STOP; 89,246 opening volume on
08-14). The **fixes** are where it goes wrong: three of them (B1, B2, B5) replace a
silent failure with an active one, and two of the safety nets built to catch that class
(wire_guard, the DLL-ladder test) do not cover the code that was actually written.

At today's `FIXED_CONTRACTS_4=1` configuration the sizing path is byte-identical and the
DLL ladder is a no-op. The risk today is **not** sizing. It is (a) an armed
account-wide FLATTEN on two auto paths while Michael holds 5 manual contracts, (b) a
stop-move path that now lies to its own supervisor, and (c) a LIVE slot that can be
wedged for the session.

---

*Read-only review. Commands and raw output pasted per Rule 5; every number re-derived
from DB / filesystem per Rule 2. `/tmp/rev_base` worktree left in place for
re-verification — `git worktree remove /tmp/rev_base --force` to clean up.*
