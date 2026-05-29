# CC Handoff — Trade Lifecycle Bugs (5 findings) · 2026-05-28

**Owner:** Claude Code
**Author of handoff:** Cursor agent
**Discovered by:** Michael (verbal review of the 17:45 ET S4 fire on 2026-05-28)
**Mode:** **Phase 1 = DIAGNOSE-ONLY** (READ-ONLY code + DB · no patches yet) → Michael reviews → Phase 2 = patches one by one
**Estimated time:** Phase 1 = 30–45 min · Phase 2 = 60–90 min depending on findings
**Severity:** 🔴 LIVE blocker family — exits/PnL/stop direction are all wrong on a real fired trade

---

## §0 · TL;DR

Today (post `current_bar` routing fix) S4 fired correctly: GB100+HTLB LONG at
**13:45 ET** (entry 7579.0). But the **lifecycle of the trade is broken in
five distinct ways**, surfaced by direct DB inspection. Diagnose each, then
return to Michael with a per-bug classification + minimal fix proposal
BEFORE writing any patch. Do not bundle the five into one mega-patch — they
likely span 3 different subsystems (TimeStopEnforcer / TradeManager /
Gateway demo path) and must be triaged independently.

This is **pre-LIVE discipline (`.cursor/rules/mems26-pre-live-protocol.mdc`)**.
Mistakes #1 + #6 from the protocol log apply: "Diagnose first, fix second";
"Do not promote hypothesized fix to code before confirming the diagnosis."

---

## §1 · Required reading (BEFORE you query anything)

1. `.cursor/rules/mems26-pre-live-protocol.mdc` — the 4-step verification ritual.
2. `CLAUDE.md` — source-of-truth rules + LaunchAgent stability.
3. `docs/plans/STATUS_BOARD.md` — the `2026-05-28` sections (today's S2 vol fix,
   `current_bar` routing fix, and the "Convergence" entry). Section "Pipeline 2"
   mentions W-10 Time Stop (commit `210e1ca`, 35 tests).
4. `docs/handoff/OPEN_ITEMS_PRE_LIVE_2026-05-28.md` — this report will
   ADD items #14–18 to this file as a separate Phase 1 deliverable (see §6).
5. `docs/handoff/CC_HANDOFF_S4_CURRENT_BAR_ROUTING_FIX_2026-05-28.md` — the
   fix that finally let S4 fire today; provides the timeline of the
   17:45 ET trade.

After §1 reading, also read these source files end-to-end (do NOT edit):
- `backend/v9/services/trade_manager/manager.py` — TradeManager core
- `backend/v9/services/trade_manager/bar_level_detector.py` — per-bar exit checks (T1/T2/T3/stop hits)
- `backend/v9/services/trade_legs.py` — leg tracking (likely T1/T2/T3 leg accounting)
- `backend/v9/services/trade_context.py` — trade context model
- `backend/v9/gateway/trading_gateway.py` — demo vs shadow split, stop computation per direction
- `backend/v9/systems/woodies/time_stop.py` — W-10 TimeStopEnforcer (the per-bar enforcer)
- `backend/v9/systems/woodies/stages/b7_time_stop.py` — decision-tree stage feeding the enforcer
- `backend/v9/api/v9/trades.py` — the GET/POST endpoint shaping
- DB schema: `sqlite3 data/mems26_local.db ".schema v9_trades"` (already known: see §2)

---

## §2 · Live evidence (the 5 bugs)

All from `data/mems26_local.db`, captured 2026-05-28 ~20:55 IDT (after the
S4 fire). DO NOT trust prior summaries — re-query these rows yourself and
confirm before forming hypotheses.

### Reference query

```sql
SELECT id, mode, firing_system, direction, state,
       entry_ts, entry_price, stop,
       t1, t2, t3, t1_hit_ts, t2_hit_ts, t3_hit_ts,
       stop_hit_ts, exit_ts, exit_price, exit_reason, pnl_usd
FROM v9_trades
WHERE firing_system = 4 AND date(entry_ts) = '2026-05-28'
ORDER BY entry_ts;
```

### Trade #14 (shadow SHORT @ 09:35 ET) — earlier same-day reference

| field | value |
|---|---|
| mode | `shadow` |
| direction | `SHORT` |
| entry_ts | `2026-05-28 13:35:01.577785` (UTC; = 09:35 ET) |
| entry_price | `7529.75` |
| stop | `7531.0`  (above entry for SHORT ✓) |
| t1/t2/t3 | `7531.0 / 7526.25 / 7522.75` ⚠️ **t1 == stop!** |
| stop_hit_ts | (empty) |
| exit_ts | `2026-05-28 09:30:00.000000` ⚠️ **BEFORE entry by 4h05m** |
| exit_reason | `STOP_HIT` |
| pnl_usd | `-18.75` |

### Trade #15 (demo SHORT @ 09:35 ET)

| field | value |
|---|---|
| entry_ts | `2026-05-28T13:35:01.580156+00:00` |
| stop | `7531.0` |
| t1/t2/t3 | `7526.25 / 7522.75 / 0.0` |
| stop_hit_ts | `2026-05-28 09:30:00.000000` ⚠️ **same anomalous early ts** |
| exit_ts | `2026-05-28 09:30:00.000000` |
| exit_reason | `STOP_HIT` |
| pnl_usd | `-18.75` |

### Trade #155 (shadow LONG @ 13:45 ET — TODAY'S FIRE) 🔴

| field | value |
|---|---|
| entry_ts | `2026-05-28 17:45:05.897375` |
| entry_price | `7579.0` |
| stop | `7577.75`  (below entry for LONG ✓) |
| t1/t2/t3 | `7582.0 / 7585.0 / 0.0` |
| t1_hit_ts / t2_hit_ts / t3_hit_ts | (all empty) |
| stop_hit_ts | (empty) |
| exit_ts | `2026-05-28 17:45:57.788841` (**+52 seconds after entry**) |
| exit_price | (empty / NULL) |
| exit_reason | `TIME_STOP` |
| pnl_usd | `0.0` ⚠️ |

Cross-check with `v9_bars_5min` for the same window:
```sql
SELECT high, low FROM v9_bars_5min
WHERE date(ts)='2026-05-28' AND ts >= '2026-05-28 17:45:00';
-- Reported max(high)=7583.75 (>= t1=7582.0) and min(low)=7575.0
```
**T1 (7582.0) WAS reachable** — the highest bar after entry hit 7583.75.
The trade exited 52s after entry, BEFORE T1 could be recorded.

### Trade #156 (demo LONG @ 13:45 ET — TODAY'S FIRE) 🔴

| field | value |
|---|---|
| entry_ts | `2026-05-28T17:45:05.900045+00:00` |
| entry_price | `7579.0` |
| stop | `7579.25` ⚠️ **0.25 ABOVE entry — wrong direction for LONG** |
| t1/t2/t3 | `7582.0 / 7585.0 / 0.0` |
| t1_hit_ts | `2026-05-28 18:45:00.000000` |
| stop_hit_ts | `2026-05-28 18:45:00.000000` ⚠️ **identical to t1_hit_ts** |
| exit_ts | `2026-05-28 18:45:00.000000` |
| exit_price | `7579.25` |
| exit_reason | `STOP_HIT` |
| pnl_usd | `+17.5` ⚠️ **positive PnL on a stop-out** |

---

## §3 · The five bugs — diagnose, do NOT fix yet

For each, your Phase 1 output should contain:
**(a) Confirmed?** — code + DB evidence that the bug exists as described, or
falsified.
**(b) Subsystem owner** — file:line that owns the broken behavior.
**(c) Root cause hypothesis** — minimal mechanical explanation.
**(d) Minimum-change fix proposal** — file:line + ≤5-line diff sketch.
**(e) Regression test idea** — what would pin the fix.
**(f) Risk** — LOW / MEDIUM / HIGH for blast radius.

### Bug A — TIME_STOP fires after 52 seconds (shadow #155) 🔴

**Symptom:** trade closed `exit_reason="TIME_STOP"` 52s after entry, before any
T1/T2/T3 could be evaluated. Expected: W-10 enforcer fires at the close of
the **Nth 5-min bar after entry** (per `D-094 §3.B.3` / Pipeline 2 §16);
typically `N >= 6` bars (≈30 min), never on the next push.

**Where to look:**
- `backend/v9/systems/woodies/time_stop.py` — the enforcer. Read the `check()`
  / `tick()` method. Is the elapsed-bar accounting using `bar_index`
  (correct) or `wall_clock_delta` (wrong)? Does it use a `bars_remaining`
  counter that starts at 0 and treats "0 bars elapsed" as expired?
- `backend/v9/systems/woodies/stages/b7_time_stop.py` — the stage that
  passes context to the enforcer. Confirm `entry_bar_id` is set on the
  trade, not `now()`.
- `backend/v9/services/trade_manager/bar_level_detector.py` — the per-push
  detector. Is it invoking the time-stop check on every push (e.g. every
  ~2-3s from the bridge) instead of per closed bar?
- Search for `TIME_STOP` writes: `rg -n "TIME_STOP" backend/`.

**Crosscheck:** the `D-094` doc / `S4_WOODIES_TABLE_C_Strategy_Caveats.csv`
should specify N for time stop. Confirm the configured N value vs the
observed behaviour.

### Bug B — Stop direction inverted for demo LONG (#156) 🔴

**Symptom:** demo trade has `stop=7579.25` (entry 7579.0) — stop ABOVE entry
on a LONG (should be BELOW). Same fire's shadow trade got `stop=7577.75` 
(below entry, correct). So shadow path is fine; demo path is broken.

**Where to look:**
- `backend/v9/gateway/trading_gateway.py` — search for the demo branch.
  Look at how `stop_price` is computed. Is there a `mode == "demo"` branch
  that uses `entry + offset` instead of `entry - offset` for LONG (and
  vice versa for SHORT)?
- `backend/v9/services/trade_manager/manager.py` — search for `mode` ==
  `demo` / `shadow` split when persisting initial stop.
- Compare two related rows: shadow `#155` (stop 7577.75) vs demo `#156`
  (stop 7579.25). The shadow row has `entry - 1.25`, demo has `entry +
  0.25`. Different magnitudes too — so it's not just a sign flip; the
  demo path is computing a different stop, probably from a different
  source.
- Also check the 09:35 trades #14/#15: both stops are `7531.0`. Both got
  the SAME stop value, both SHORT direction. So for SHORT the demo and
  shadow agreed. The inversion only manifested on LONG today. **Hypothesis
  to confirm or refute:** direction-dependent code path that has a wrong
  sign on one branch.

### Bug C — `t1_hit_ts == stop_hit_ts` (demo #156)

**Symptom:** both `t1_hit_ts` and `stop_hit_ts` are `2026-05-28 18:45:00.000000`
(same instant). Real markets don't do both in the same atomic instant.

**Where to look:**
- `backend/v9/services/trade_manager/bar_level_detector.py` — the bar-level
  hit detector. When a bar's `[low, high]` range covers BOTH T1 and stop,
  what's the priority? If the detector writes BOTH timestamps when the
  range straddles them, that's the bug. The spec says (per `D-094`):
  fixed sequence — check stop FIRST if range covers both, else T1 first
  on LONG. The bar that closed at 18:45 was probably a wide-range bar.
- Also: the value `18:45:00` is suspiciously round. The fix may have
  defaulted the timestamp to "the bar's `ts`" (which IS bar-close time),
  but bar-close timestamps shouldn't be applied to "exact moment of T1
  hit" — that should be the tick that crossed the level. Per-tick
  granularity isn't required in shadow, but USING the same ts for both
  events is the actual bug.

### Bug D — `pnl_usd=0.0` and `exit_price=NULL` on TIME_STOP (shadow #155)

**Symptom:** the shadow LONG closed on TIME_STOP with `pnl_usd=0.0` and no
`exit_price`. Expected: compute PnL as `(market_close_price - entry_price) *
contract_size * direction_sign`.

**Where to look:**
- The TIME_STOP close handler. Search: `rg -n "TIME_STOP|time_stop" backend/`.
  Find the `close()` / `on_time_stop()` path.
- Compare to STOP_HIT path on the same row family — `pnl_usd` IS calculated
  there (#15 = -18.75; #156 = +17.5). So the calc code exists, just not
  on the TIME_STOP branch. Likely a missing call to `_compute_pnl()`
  before persisting the close.

### Bug E — `stop_hit_ts` (or `exit_ts`) defaults to `09:30:00` (shadow #14, demo #15)

**Symptom:** `exit_ts` / `stop_hit_ts` is `2026-05-28 09:30:00.000000` on
two trades whose entry_ts was `13:35:01.5xx`. The exit reportedly happened
**BEFORE** the entry — impossible.

**Where to look:**
- Likely a DB column default that gets serialised as `09:30:00` (e.g.
  `SessionStart` or similar). Inspect the SQLAlchemy model for `v9_trades`
  — is there a `default=` that resolves to `datetime.fromisoformat("…
  09:30:00")` for `exit_ts` or `stop_hit_ts`? Or a Python helper that
  writes the RTH-session-open time as a placeholder when the column is
  unfilled.
- Or: a TZ issue — `09:30:00` ET is `13:30 UTC` in summer (close to
  entry's 13:35). But the column shows `09:30:00` literal — that's a
  string, not a converted instant. So it's a string-default issue, not TZ.
- Cross-check: `rg -n "09:30|RTH_OPEN" backend/v9/services/trade_manager/`.

---

## §4 · Method (Phase 1)

For EACH bug A–E, **in this exact order**:

1. **Read the relevant source files** end-to-end. Do not propose anything
   from memory.
2. **Re-query the DB rows** yourself; do not trust the snapshots in §2 if
   the live DB has moved.
3. **Form one hypothesis**. Use the smallest unit of explanation that fits
   the evidence.
4. **Confirm with a probe** — write a 3-line one-shot Python script or
   `sqlite3` query that demonstrates the bug mechanically (e.g. for
   Bug B, instantiate the demo gateway with a fake LONG order and assert
   the computed stop is above entry).
5. **Only then write the diff sketch** (file:line + minimal change).

Sandbox-blocked actions:
- Restarting the backend is allowed (you have a real terminal).
- Spawning sub-processes for `pgrep` etc. is allowed.
- Editing files is **NOT** allowed in Phase 1 — diagnose-only.

If a diagnostic step fails twice in a row, change tactic (different file,
different query) — do not repeat hoping for a different result.

---

## §5 · Phase 1 deliverable

Write one file:

`docs/reports/DIAGNOSIS_TRADE_LIFECYCLE_BUGS_2026-05-28.md`

Structured as:

- §0 TL;DR (≤4 lines per bug)
- §1 Bug A · TIME_STOP 52s — (a)–(f) per §3
- §2 Bug B · Stop inverted on demo LONG — (a)–(f)
- §3 Bug C · t1_hit_ts == stop_hit_ts — (a)–(f)
- §4 Bug D · pnl=0.0 on TIME_STOP — (a)–(f)
- §5 Bug E · stop_hit_ts=09:30:00 — (a)–(f)
- §6 Cross-cutting observations (e.g. if two bugs share a root cause, say so)
- §7 What you couldn't verify (sandbox/missing data — including any tests
  you'd want to run before Phase 2)
- §8 Ranked fix order (which to fix first, why)

Hand the report back to me (Cursor) for Michael's review before any patches.

---

## §6 · Open-items update (also Phase 1, separate file)

Append entries 14–18 to `docs/handoff/OPEN_ITEMS_PRE_LIVE_2026-05-28.md` under
§1 (LIVE blockers), one row per bug A–E, linking back to
`DIAGNOSIS_TRADE_LIFECYCLE_BUGS_2026-05-28.md` § for each.

---

## §7 · Phase 2 (DEFERRED — only after Michael green-lights Phase 1)

Once Michael approves the diagnosis report:

1. **Fix one bug at a time**, smallest-change-first. Suggested order from
   §3 (revisit after Phase 1):
   - **B (stop inversion)** first — highest direct trading risk.
   - **A (TIME_STOP 52s)** second — caps the holding period below T1
     reachability; without this, no fire ever reaches a target.
   - **D (pnl on TIME_STOP)** third — telemetry trustworthiness.
   - **C (t1==stop ts)** fourth — exit accounting accuracy.
   - **E (09:30 default ts)** fifth — cosmetic but corrupts replay/audit.
2. **One regression test per bug**, named clearly. All tests live under
   `tests/v9/services/trade_manager/` or `tests/v9/systems/woodies/` as
   appropriate.
3. **Backend restart + 4 UAT axes** per the same pattern as the
   `current_bar` handoff (§5 / §6 there). Specifically for these fixes:
   - **Axis 1 Quality:** re-fire S4 (or use a synthetic replay) and verify
     each fixed field matches spec.
   - **Axis 2 Recency:** confirm the fix is hot in memory (no cached
     pickled state).
   - **Axis 3 Cardinality:** if Bug A is fixed, the next S4 fire should
     hold for at least N bars (per the spec's time-stop N); if Bug B is
     fixed, demo LONG should have stop BELOW entry.
   - **Axis 4 Latency:** no inspector or endpoint slowdown introduced.
4. **Update `STATUS_BOARD.md`** with a `2026-05-28 · Trade Lifecycle Fix Batch`
   section (one row per bug + UAT results).

---

## §8 · Hard rules (both phases)

- READ-ONLY in Phase 1. No `git add` / `git commit` / `git restore`.
- No `except Exception: pass`. Silent error handling is forbidden between
  now and LIVE (per `CLAUDE.md`).
- No `while I'm here` refactors. Smallest correct change.
- Strategic stop at any point you discover a 6th bug or the diagnosis of
  one bug contradicts the plan — write it up, stop, ask Michael.
- Do not run `bash scripts/start_all.sh` or any service-spawning command
  unless Michael explicitly asks.
- Pre-LIVE protocol mistakes log applies — do not promote hypothesized
  fixes to code before confirming the diagnosis (mistake #6 in
  `.cursor/rules/mems26-pre-live-protocol.mdc`).
