# DIAGNOSIS — Initial Balance Ground Truth Divergence (2026-05-28)

**Status:** READ-ONLY forensic diagnosis. No code patched.
**Author:** Cursor agent (Claude Opus 4.7), 2026-05-28 ~21:55 IDT.
**Severity:** 🔴 LIVE blocker — three different IB values across system, none match Sierra UI.

---

## §0 — TL;DR

1. **Sierra DLL silently produces `ib_found=false`, `ib_high=ib_low=0`** even
   though Sierra UI clearly displays IB High=7574.00, IB Low=7525.50. Root
   cause is most likely **wrong ACSIL subgraph indices** (DLL reads SG idx 6 &
   8; Sierra "Initial Balance" Study probably exposes IB High/Low at
   different indices for Michael's current study version/config), or
   alternatively the study has "Extend Lines Forward" disabled so subgraph
   values at `sc.Index` are 0 post-lock.
2. **Backend silently synthesizes IB from `v9_bars_5min`** when DLL goes
   silent, marking it `ib_found=true` so every downstream consumer is fooled
   into trusting a non-Sierra number. Produces the (7583.5, 7575.0) we see in
   `v9_tpo_sessions` and `/api/v9/tpo/current`.
3. **Day Type state machine runs a cumulative `min`/`max` over the
   bars-derived synthetic IB across every A3 bar**, so the lowest synthetic
   `ib_low` ever observed (7553.25) gets latched into `v9_day_type_history`
   and is never re-evaluated. This explains the three-way divergence between
   the stores, none of which match Sierra.

The earlier-today snapshot (`Normal|PENDING|0.68|7574.0|7525.5|48.5|WIDE`)
**did** match Sierra. It was destroyed by a backend restart between 14:30 UTC
and 17:00 UTC that re-seeded the state machine from the bars-synthetic
fallback (now reporting `ib_locked=true` because of bug #2).

---

## §1 — Sierra UI ground truth (Michael's screenshot)

Source: `/Users/michael/.cursor/projects/Users-michael-Downloads-mems26-web-git/assets/image-c608e13e-aaad-4ee1-b1a5-d0ae1d8bc435.png`
Captured: 2026-05-28 ~21:42 IDT (14:42 ET, ~4 h after IB lock).

| Label (Sierra UI) | Value | Notes |
|---|---|---|
| **IB High** (green band) | **7574.00** | Locked at 10:30 ET, drawn forward |
| **IB Low** (green band) | **7525.50** | Locked at 10:30 ET, drawn forward |
| IB range | 48.50 pt | → **WIDE** (>25 pt) |
| TPO POC (red label) | 7535.25 | matches `previous_session.poc` in `tpo.json` |
| TPO VAH | 7549.75 | matches `previous_session.vah` |
| TPO VAL (lower) | 7520.75 | matches `previous_session.val` |
| TPO VAL (upper) | 7555.75 | matches today `session.val` |

Sierra **is** retaining and rendering the locked IB lines right now (image
shows them clearly). So our DLL is not seeing what Sierra is drawing.

---

## §2 — DLL findings (`sc_study/MES_AI_DataExport.cpp`)

### Code path
- Lines 42, 109: Sierra Study ID for IB = **6** (input 15).
- Lines 631–737 export `tpo.json`.
- Lines 717–730 read IB:
  ```cpp
  sc.GetStudyArrayFromChartUsingID(chart_num, ib_study_id, 6, ib_high_arr);
  sc.GetStudyArrayFromChartUsingID(chart_num, ib_study_id, 8, ib_low_arr);
  if (ib_high_arr.GetArraySize() > idx && ib_high_arr[idx] != 0) {
      ib_h = ib_high_arr[idx];
      ib_l = (ib_low_arr.GetArraySize() > idx) ? ib_low_arr[idx] : 0;
      ib_found = (ib_h > 0 && ib_l > 0);
  }
  ```
- Line 131: `int idx = sc.Index;` — **reads at the current bar only**, not
  at `ArraySize - 1`, not at the historical lock bar.

### Findings
1. **Which study ID?** ID 6 (correct per Michael's chart config).
2. **Which subgraphs?** ACSIL idx 6 = "IB High" and idx 8 = "IB Low". Per
   the in-file comment, this mapping was "verified" 2026-05-25 against the
   Sierra UI (`docs/forensics/SIERRA_UI_EVIDENCE_2026-05-25.md`). UI label
   "SG7" maps to ACSIL idx 6 (Sierra UI numbers SGs starting at 1, ACSIL
   starts at 0).
3. **`ib_found` condition:** `(ib_h > 0 && ib_l > 0)` where `ib_h` is set
   only if `ib_high_arr[idx] != 0`. So `ib_found=false` whenever the
   subgraph at the current bar is 0.
4. **Read position:** `[sc.Index]` (current bar). **NOT** persistent lookup.

### Live evidence
`~/SierraChart_Data/v9_export/tpo.json` (fresh, mtime = now − 1 s):
```json
"ib": { "found": false, "high": 0.0, "mid": 0.0, "low": 0.0 }
```
But Sierra UI clearly shows IB at 7574 / 7525.5 → **the DLL is reading the
wrong subgraph at this `sc.Index`** *or* the Sierra IB Study has "Extend
Lines Forward" disabled and the subgraphs only carry non-zero values during
09:30–10:30 ET.

### Cross-check with earlier today
Task description notes tpo.json earlier read `ib_high=7543.75, ib_low=7522.00`.
Neither matches Sierra's locked 7574 / 7525.5. Sanity:
- IB Mid would be (7574+7525.5)/2 = 7549.75 (not 7543.75).
- 2× IB Above = 7574 + 48.5 = 7622.5 (not 7543.75).
- 2× IB Below = 7525.5 − 48.5 = 7477.0 (not 7522.0).

So **even during the IB window earlier today, the DLL was reading the wrong
subgraphs** — it never agreed with Sierra UI numerically. Most likely the
subgraph indices for IB High/Low on Michael's chart are **not** 6 / 8; they
are some other pair the 2026-05-25 forensics misidentified.

---

## §3 — Backend write paths (who writes wrong values to each store)

### Path A — `/api/v9/tpo/current` and `v9_tpo_sessions.ib_high/low` (= 7583.5 / 7575.0)

`backend/v9/api/v9/tpo_routes.py:359-396` (`_normalize_sierra_tpo`):
```python
ib_found = bool(ib.get("found"))
if ib_found:
    ib_high = ib.get("high")
    ib_low  = ib.get("low")
    ib_source = "sierra_live"
else:
    bars_ib = _ib_from_bars()                       # MAX/MIN over 09:30-10:30 ET
    if bars_ib is not None:
        ib_high, ib_low = bars_ib
        ib_found = True                              # ⚠ marks synthetic as TRUE
        ib_source = "v9_bars_5min_09_30_10_30_ET"
```
- `_ib_from_bars()` (lines 322-356): `SELECT MAX(high), MIN(low) FROM
  v9_bars_5min WHERE symbol='MES' AND ts >= 13:30 UTC AND ts < 14:30 UTC`.
- Returns `(7583.5, 7575.0)` against the current DB (verified live).
- `_normalize_sierra_tpo` then sets `ib_locked = ib_found = True` (line 436)
  → downstream consumers (TPO system, Day Type seed, key_levels) cannot tell
  this number is synthesised.

`backend/v9/systems/tpo/tpo_system.py:363-455`:
- `_update_ib()` reads `_load_sierra_tpo()` → sees synthetic value with
  `ib_found=true` → unconditionally calls `_persist_ib_to_session()` (no
  COALESCE protection, line 446) → writes 7583.5 / 7575.0 into
  `v9_tpo_sessions`.
- `_open_session()` (line 473) only resets IB on **trading_date** change —
  CASH-session re-open does NOT clear bad IB.

### Path B — `/api/v9/day_type/v9/current` and `v9_day_type_history.ib_high/low` (= 7583.5 / 7553.25)

`backend/main.py:181-306` (`_day_type_on_bar`):
- Reads `_load_sierra_tpo()` → ib_h, ib_l come from the **same** synthetic
  fallback.
- Calls `day_type_machine.process_bar(bar_input)` where `bar_input.ib_high
  = ib_h` and `bar_input.ib_low = ib_l`.

`backend/v9/systems/day_type/state_machine.py:413-427` (`_stage_a3`):
```python
if bar.ib_high is not None:
    self.ib_high = max(self.ib_high, bar.ib_high)
if bar.ib_low is not None:
    self.ib_low  = min(self.ib_low,  bar.ib_low)
```
- **Cumulative `max` / `min`** across every A3 bar.
- When the synthetic `_ib_from_bars()` returned a momentarily lower `ib_low`
  (e.g. 7553.25 — present in bars before the 13:30-14:30 UTC window contents
  shifted to MIN=7575.0) the state machine *latched* the lower value and
  never revisits it.
- At A4 lock, `self.ib_high / self.ib_low` are frozen into
  `IBClassification`. After A4 → B1 the engine never re-reads IB.

`backend/v9/systems/day_type/consumer.py:71-122` (`DayTypeConsumer.consume`):
- UPSERT keyed by `date`. **No COALESCE.** Every classification overwrites
  `ib_high / ib_low` with whatever the state machine emits. Once latched at
  (7583.5, 7553.25) it sticks until process restart.

`backend/v9/api/v9/day_type_seed.py:36-130` (`maybe_seed_ib_from_tpo`):
- Triggered when `bar_count==0` after a mid-session restart and
  `session_min > ib_period_min`.
- Guards on `tpo_ib_locked` (boolean), `tpo_ib_high`, `tpo_ib_low`.
- **All three guards pass against the synthetic value** because
  `_normalize_sierra_tpo` set `ib_locked = ib_found = True` on synthesis
  (Path A). So a restart re-seeds the engine from the synthetic IB and
  marks `ib_locked=True`, jumping straight to B1 with bogus IB.

### Path C — `/api/v9/key_levels` (= 7583.5 / 7556.5 per task; live now = 7583.5 / 7575.0)

`backend/v9/api/v9/key_levels_routes.py:108-118`:
- `today_ib_high = _f(sierra.get("ib_high"))` straight off
  `_load_sierra_tpo()` → same synthetic value as Path A.
- `sources.ib` (line 209-221) reports `"v9_bars_5min (09:30-10:30 ET MAX/MIN
  · Sierra-sourced bars)"` when `ib_source == "v9_bars_5min_09_30_10_30_ET"`
  — the only honest part of the system, but the UI strip just shows the
  number, not the source string.

### Live evidence (forensic queries 21:45 IDT)

```
-- v9_day_type_history (2026-05-28):
ib_high=7583.5  ib_low=7553.25  ib_width=30.25  ib_width_class=WIDE
last_updated_at=2026-05-28 18:45:04

-- v9_tpo_sessions CASH_2026-05-28:
ib_high=7583.5  ib_low=7575.0   ib_width=8.5    ib_class=NARROW
ib_locked=1     ib_locked_ts=2026-05-28T18:16:31Z

-- v9_bars_5min MAX(high)/MIN(low) over 13:30-14:30 UTC (RTH IB window):
MAX=7583.5      MIN=7575.0   n=12

-- v9_day_type_state stage transitions:
14:30 UTC  → first B2 row, ib_width_class=MEDIUM, lock=PENDING
17:00 UTC  → first WIDE row, lock=LOCKED_LOW_CONF (after restart)
```

The MEDIUM→WIDE jump in `v9_day_type_state` is the smoking-gun timestamp for
the restart between 14:30 and 17:00 UTC.

---

## §4 — Root causes (4 independent bugs)

### Bug #1 — DLL: subgraph indices for IB High/Low are wrong (or "Extend Lines Forward" disabled)
- File: `sc_study/MES_AI_DataExport.cpp:722-723` (also 801-802 for Y-IB).
- Effect: `tpo.json.ib.found = false`, `high=0`, `low=0` post 10:30 ET (and
  numerically wrong even during 09:30-10:30 ET earlier today).
- Hypothesis A (likely): ACSIL idx 6 / 8 are **not** IB High / IB Low on
  Michael's current chart. The 2026-05-25 forensic mapping is wrong or has
  drifted since Michael adjusted Sierra Inputs.
- Hypothesis B (also possible): the study has "Extend Lines Forward = No"
  so subgraphs are non-zero only during the build window; after 10:30 ET
  `arr[sc.Index]` is 0 even at the right index.

### Bug #2 — Backend: `_normalize_sierra_tpo` synthesises IB from bars and flags `ib_found=true`
- File: `backend/v9/api/v9/tpo_routes.py:380-396`.
- Violates **CLAUDE.md** rule: *"Forbidden without explicit approval:
  inventing … rolling-window price levels when the DLL omits them."*
- The fallback masquerades as Sierra (`ib_found=true`, `ib_locked=true`) so
  every downstream consumer trusts it. Only the `ib_source` string betrays
  the synthesis, and no consumer gates on it.
- This is the single biggest amplifier: every other store (`v9_tpo_sessions`,
  `v9_day_type_history`, `/api/v9/key_levels`, `/api/v9/tpo/current`,
  `/api/v9/day_type/v9/current`) ends up consuming this synthetic value.

### Bug #3 — Day Type state machine: cumulative `min`/`max` over bars-derived IB
- File: `backend/v9/systems/day_type/state_machine.py:424-427`.
- Once a low synthetic `ib_low` (e.g. 7553.25) flows through any A3 bar,
  `self.ib_low = min(..)` latches it. Later bars carrying a higher synthetic
  IB (e.g. 7575.0) cannot recover. After A4 → B1 the value is permanently
  frozen for the session.
- Even if Sierra were truth, `min/max` is wrong: Sierra's IB is **locked at
  10:30 ET**, not a running aggregate.

### Bug #4 — `maybe_seed_ib_from_tpo` accepts synthesised IB as authoritative on restart
- File: `backend/v9/api/v9/day_type_seed.py:70`.
- Guard `if not tpo_ib_locked: return False` is satisfied by Bug #2
  (synthesis sets `ib_locked=True`).
- A mid-session backend restart therefore destroys whatever good IB the
  in-memory engine had (the original 7574 / 7525.5) and adopts the synthetic
  one.

### Bug #5 (latent, not active today but pre-LIVE blocker) — `_persist_ib_to_session` has no COALESCE
- File: `backend/v9/systems/tpo/tpo_system.py:446-451`.
- If Sierra returns `ib_found=true` once (correctly), then later flips
  `ib_found=false`, today the bars fallback will keep `ib_found=true` and
  paper over the gap — but if Bug #2 is fixed, then a transient Sierra
  silence will fall through to this path with `self.ib_high/low = None` …
  except current code is guarded by `if not sierra.get("ib_found"): return`
  (line 387) so the unconditional write only fires when synthesis is on.
  Once Bug #2 is removed this becomes lower risk; flagging for completeness.

---

## §5 — Fix proposals (file:line + ≤5-line diff sketch + regression test)

### Fix #1 (DLL) — confirm subgraph indices and switch read position
**File:** `sc_study/MES_AI_DataExport.cpp:717-730`.

Step A (forensic, before code change): ask Michael to open Sierra
Initial Balance Study → Subgraphs tab → screenshot the SG list with values
visible. Identify which numbered SG currently displays "7574.00" and which
displays "7525.50" right now. Map UI SG number → ACSIL index = UI − 1.

Step B (code, after A confirms indices `H_IDX`, `L_IDX`): replace `idx`
with a **persistent lookup** so we never miss the locked value:
```cpp
sc.GetStudyArrayFromChartUsingID(chart_num, ib_study_id, H_IDX, ib_high_arr);
sc.GetStudyArrayFromChartUsingID(chart_num, ib_study_id, L_IDX, ib_low_arr);
int last_h = _v9_last_nonzero(ib_high_arr, idx);   // helper: walk back from idx to 0
int last_l = _v9_last_nonzero(ib_low_arr,  idx);
if (last_h >= 0 && last_l >= 0) {
    ib_h = ib_high_arr[last_h];
    ib_l = ib_low_arr[last_l];
    ib_found = (ib_h > 0 && ib_l > 0 && ib_h > ib_l);
}
```
The `_v9_last_nonzero` helper handles both "Extend Lines Forward = No"
(value only at lock bar) and pre-lock pre-build (returns -1).

**Regression test (out-of-process, after Sierra rebuild):**
`tests/v9/sierra/test_tpo_export_ib.py` — load a recorded post-lock
`tpo.json` and assert `ib.found == True`, `ib.high == 7574.0`, `ib.low ==
7525.5` for the 2026-05-28 fixture. Bigger UAT: live four-axis check
(Quality, Recency, Cardinality, Latency).

### Fix #2 (Backend, HIGHEST PRIORITY) — remove bars-derived IB synthesis
**File:** `backend/v9/api/v9/tpo_routes.py:380-396`.

```python
ib_found = bool(ib.get("found"))
if ib_found:
    ib_high, ib_low, ib_mid = ib.get("high"), ib.get("low"), ib.get("mid")
    ib_source = "sierra_live"
else:
    ib_high = ib_low = ib_mid = None
    ib_source = "missing"           # ⬅ no more bars fallback, no false-true flag
```
Delete `_ib_from_bars()` and its caller path. Update `key_levels_routes.py`
`sources.ib` string to drop the "bars" branch.

**Regression test:** `tests/v9/api/test_tpo_routes_no_ib_synthesis.py`:
patch `_load_sierra_tpo`'s underlying file to `ib.found=false`, assert
`/api/v9/tpo/current` returns `ib_high=None`, `ib_low=None`, `ib_found=False`,
`ib_source="missing"`.

### Fix #3 (Day Type) — trust Sierra's locked IB, no running min/max
**File:** `backend/v9/systems/day_type/state_machine.py:413-427`.

```python
def _stage_a3(self, bar: BarInput):
    if not bar.is_rth:
        return
    if bar.ib_high is not None and bar.ib_low is not None:
        # Source-of-truth: Sierra reports a locked IB; adopt it verbatim,
        # do NOT min/max across bars (Sierra is the aggregator, not us).
        self.ib_high = bar.ib_high
        self.ib_low  = bar.ib_low
    if bar.session_min >= self.config.ib_period_min:
        self.stage = Stage.A4
```

**Regression test:** `tests/v9/systems/test_day_type_ib_no_accumulate.py`:
feed two A3 bars with `(ib_high=7574, ib_low=7525.5)` then `(ib_high=7574,
ib_low=7560)`; assert `state.ib_low == 7560` (latest Sierra value), not
7525.5. (Sierra is the authoritative aggregator — if it changes, we follow.)

### Fix #4 — `maybe_seed_ib_from_tpo` must reject synthesised IB
**File:** `backend/v9/api/v9/day_type_seed.py:70`.

Once Fix #2 is in, this becomes automatic (synthesis is gone). Belt-and-
braces guard:
```python
if not tpo_ib_locked:
    return False
if tpo_ib_source not in ("sierra_live",):     # ⬅ new
    return False
```
Pass `tpo_ib_source` through from `main.py:_day_type_on_bar` (read from
`_sierra_tpo.get("ib_source")`).

**Regression test:** `tests/v9/api/test_day_type_seed_rejects_synthetic.py`:
call `maybe_seed_ib_from_tpo(..., tpo_ib_source="v9_bars_5min_09_30_10_30_ET")`
and assert it returns `False`.

### Fix #5 (Defense in depth) — COALESCE on `_persist_ib_to_session`
**File:** `backend/v9/systems/tpo/tpo_system.py:444-451`.

```python
"""UPDATE v9_tpo_sessions SET
       ib_high=COALESCE(?, ib_high),
       ib_low=COALESCE(?, ib_low),
       ib_width=COALESCE(?, ib_width),
       ib_class=COALESCE(?, ib_class),
       ib_locked=CASE WHEN ? IS NULL THEN ib_locked ELSE ? END,
       ib_locked_ts=COALESCE(?, ib_locked_ts)
   WHERE session_id=?"""
```
Prevents a future Sierra → null transition from wiping a previously good
locked IB.

---

## §6 — Ranked fix order

1. **Fix #2 (remove bars synthesis from `_normalize_sierra_tpo`)** — single
   biggest blast-radius reduction. After this, `/api/v9/tpo/current` and
   `/api/v9/key_levels` will show `ib_high=None`, `ib_low=None`, `ib_source="missing"`
   while DLL is broken — **honest failure** instead of silent lies.
2. **Fix #4 (seed rejects non-sierra IB)** — prevents restart-induced
   contamination of the Day Type engine.
3. **Fix #3 (state machine: no running min/max)** — surfaces Sierra's
   authoritative value cleanly once it's available.
4. **Fix #1 (DLL: correct subgraph indices + persistent lookup)** —
   actually restores ground truth. Requires Michael in Sierra UI to identify
   the real SG indices, then a build & Remote-Build deploy.
5. **Fix #5 (COALESCE)** — belt-and-braces; can be deferred 24 h if needed.

After Fixes #1-#4, the canonical IB will be:
- `tpo.json.ib.found = true`, `high = 7574.0`, `low = 7525.5` (assuming
  Fix #1 lands).
- `/api/v9/tpo/current` and `/api/v9/key_levels`: 7574.0 / 7525.5,
  `ib_source = "sierra_live"`.
- `v9_tpo_sessions`: 7574.0 / 7525.5 (TPO `_update_ib` will overwrite the
  bad 7583.5/7575.0 once Sierra reports real values).
- `v9_day_type_history`: 7574.0 / 7525.5 (state machine adopts Sierra-as-is
  on the next A3 bar after the next restart, or via a one-shot UAT helper).

The post-lock `v9_day_type_history` row will need a **manual one-shot
correction** (UPDATE … SET ib_high=7574, ib_low=7525.5, ib_width=48.5,
ib_width_class='WIDE' WHERE date='2026-05-28') because the in-memory engine
won't naturally revisit IB until tomorrow's session. Defer that to Michael
after Fix #2 lands so we don't fight ourselves.

---

## §7 — What I could NOT verify without Michael's intervention

1. **Actual ACSIL subgraph indices for IB High / IB Low on Michael's chart**
   — requires looking at Sierra UI ("Initial Balance Study → Subgraphs"
   panel) and matching the SG that shows "7574.00" to its index. Forensic
   evidence strongly suggests idx 6/8 are wrong.
2. **Whether the Initial Balance Study has "Extend Lines Forward" enabled**
   — affects whether `arr[sc.Index]` is non-zero post-lock. Either way the
   Fix #1 helper (`_v9_last_nonzero`) covers both modes.
3. **Whether the bars window MIN was momentarily 7553.25 earlier today**
   — would require either a journaled audit log of `_ib_from_bars` calls or
   bridge-side bar revisions. We can infer it from the
   `v9_day_type_state` MEDIUM→WIDE transition between 14:30 UTC and 17:00
   UTC, but cannot prove the exact value.
4. **DLL rebuild + Sierra Remote-Build deploy** — Fix #1 requires
   `./scripts/build_monolithic_cpp.sh --deploy` + Sierra Chart "Remote Build
   Manager" reload. Cannot do this from Cursor; CC's docs show this is
   delegated to Claude Code or Michael (`docs/runbooks/SIERRA_DLL_OPS.md`).

---

## §8 — Risk assessment per fix

| Fix | Blast radius | Pre-LIVE risk | Notes |
|---|---|---|---|
| #1 DLL subgraph indices | LOW (DLL only) | HIGH (DLL build pipeline) | Requires Sierra UI verify + Remote Build; cannot ship same hour. Helper function changes are 5 lines. Regression test must use a recorded `tpo.json` fixture, not live Sierra. |
| #2 Remove bars synthesis | MEDIUM (5 endpoints, UI strip) | LOW | Behavioural change is "IB shows `—` while DLL is silent". The UI must already render `None` cleanly (key_levels does — `pre_open` path). Verify Strip + KeyLevelsCard render `None` without crashing. |
| #3 State machine adopts Sierra IB as-is | LOW | LOW | Behavioural change: future IB updates from Sierra will overwrite engine state. Sierra's IB is **locked at 10:30 ET** so further changes are normally impossible — this is safe. |
| #4 Seed rejects synthetic | LOW | LOW | Pure tightening; no false negative possible because Fix #2 removes the only synthetic path. |
| #5 COALESCE on `_persist_ib_to_session` | LOW | LOW | Mirrors existing `_persist_session` pattern; verified safe in the codebase already. |

Combined risk: Fixes #2-#5 are safe to land together as a small PR
(`tpo_routes.py`, `state_machine.py`, `day_type_seed.py`, `tpo_system.py`).
Fix #1 needs Michael-in-the-loop for subgraph verification + DLL rebuild
and ships separately.

---

## Appendix A — Live forensic queries (2026-05-28 21:45 IDT)

```sql
-- v9_day_type_history (today)
SELECT date, day_type, status, confidence, ib_high, ib_low,
       ib_width, ib_width_class, opening_type, last_updated_at
  FROM v9_day_type_history WHERE date='2026-05-28';
-- → 2026-05-28|Normal|LOCKED_LOW_CONF|68.0|7583.5|7553.25|30.25|WIDE|INDETERMINATE|2026-05-28 18:45:04

-- v9_tpo_sessions (today, CASH)
SELECT session_id, ib_high, ib_low, ib_locked, ib_width, ib_class
  FROM v9_tpo_sessions WHERE session_id='CASH_2026-05-28';
-- → CASH_2026-05-28|7583.5|7575.0|1|8.5|NARROW

-- bars-derived synthesis (current)
SELECT MAX(high), MIN(low), COUNT(*) FROM v9_bars_5min
 WHERE symbol='MES' AND ts>='2026-05-28 13:30:00' AND ts<'2026-05-28 14:30:00';
-- → MAX=7583.5  MIN=7575.0  n=12

-- IB stage timeline (restart detector)
SELECT MIN(ts) FROM v9_day_type_state WHERE ib_width_class='MEDIUM' AND date(ts)='2026-05-28';
-- → 2026-05-28T14:30:01+00:00  (initial A4 lock from bars synthesis)
SELECT MIN(ts) FROM v9_day_type_state WHERE ib_width_class='WIDE' AND date(ts)='2026-05-28';
-- → 2026-05-28T17:00:03+00:00  (post-restart re-seed widened the IB range)
```

## Appendix B — Files inspected (no edits made)

- `sc_study/MES_AI_DataExport.cpp` (DLL IB extraction)
- `~/SierraChart_Data/v9_export/tpo.json` (live DLL output)
- `backend/v9/api/v9/tpo_routes.py` (`_load_sierra_tpo`, `_normalize_sierra_tpo`, `_ib_from_bars`, `tpo_current`)
- `backend/v9/api/v9/key_levels_routes.py` (`get_key_levels`)
- `backend/v9/api/v9/day_type_seed.py` (`maybe_seed_ib_from_tpo`)
- `backend/v9/systems/day_type/state_machine.py` (`_stage_a3`, `_stage_a4`, `_build_state`, `to_classification`)
- `backend/v9/systems/day_type/consumer.py` (`DayTypeConsumer.consume`)
- `backend/v9/systems/tpo/tpo_system.py` (`_update_ib`, `_persist_ib_to_session`, `_open_session`, `_persist_session`)
- `backend/main.py:_day_type_on_bar` (bar wiring)
- DB tables: `v9_day_type_history`, `v9_day_type_state`, `v9_tpo_sessions`, `v9_bars_5min`, `v9_tpo_journal`.
