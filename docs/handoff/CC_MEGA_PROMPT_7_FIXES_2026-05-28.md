# CC MEGA-PROMPT — 7 Pre-LIVE Fixes · 2026-05-28
## REVISED 2026-05-28 EVENING (post-Michael decisions)

**For:** Claude Code (CC) — fresh session
**Author:** CC (self-authored for continuity)
**Approved by:** Michael (verbal 2026-05-28 morning + evening revisions)
**Branch:** `stabilize/mems26-local-truth-2026-05-16`
**Codebase:** `/Users/michael/Downloads/mems26_web_git`
**Mode:** Diagnose → Fix → Test → Restart → UAT

---

## §0a · MICHAEL DECISIONS — 2026-05-28 EVENING (AUTHORITATIVE)

These decisions OVERRIDE every conflicting paragraph in this prompt and in
the sibling `MEGA_PROMPT_CC_AUDIT_IB_TIMESTOP_2026-05-28.md`. Read both
prompts together; on any conflict §0a wins.

1. **IB only from Sierra Initial Balance Study.** No bars-derived synthesis.
   - Fix #4 in this prompt is REPLACED. Do NOT keep `_ib_from_bars()`. The
     evening directive is to DELETE it (regardless of whether Fix #2 TZ
     is landed first). When Sierra reports `ib.found=false`, propagate
     `ib_high=None, ib_source="missing"` downstream.
   - The earlier same-day approval comment in `tpo_routes.py:325-330`
     (*"Restored with Michael's explicit approval (2026-05-28 18:31 IDT)"*)
     is REVOKED. Log the revocation in `docs/reports/AMENDMENTS_LOG.md`
     before deleting the function.

2. **W-10 (Registry #11) is sole TIME_STOP authority — fix in code, not via
   YAML kill switch.** This REVERSES the morning Option B decision.
   - Fix #3 in this prompt is **ACTIVE** (was contradicted by morning
     Option B; that contradiction is now resolved in favour of Fix #3).
   - Fix #5 in this prompt is **ACTIVE** (same reason — explicitly added
     by Michael 2026-05-28 evening).
   - Re-enable YAML: `dispatcher_config.yaml::time_stop.time_stop_minutes: 90`.
   - REMOVE Layer 4 entirely from `bar_level_detector.py`:
     `TIME_STOP_BY_DAY_TYPE` constant, the time-based exit block in
     `on_bar`, and `_check_time_stop` method. Stop/target hit logic STAYS.

3. **Cite-by-symbol discipline.** Every `path:line` cite below was accurate
   at author time but has drifted (Cursor verified 2026-05-28 evening:
   most cites in this prompt are within 1–17 lines, but `Fix #6` cites the
   wrong region — see §2.Fix #6 revised note). Locate every target by
   `rg -n "<symbol>" <file>` BEFORE editing.

---

## §0 · Context — read first

This prompt addresses 7 bugs discovered during the first SHADOW trading day
(2026-05-28). The system fired S4 trades but the lifecycle was broken.
Three root causes produce all 7 symptoms:

```
Root A: Chicago TS over-correction (+1h)
  → Bug #2 (all DB timestamps +1h)
  → Bug #4 (IB query reads wrong hour → wrong Day Type)
  → Bug #7 (exit_ts = 09:30 instead of UTC)

Root B: TIME_STOP counts pushes, not bars
  → Bug #3 (TIME_STOP fires in 52s instead of 90min)
  → Bug #5 (exit_price=NULL, pnl=0 on TIME_STOP)

Root C: S2 hydrate gap
  → Bug #6 (current_day_type=None after mid-session restart)

Root D: DLL frozen-tail (separate — not fixed here)
  → Bug #1 (Sierra study values frozen for last 13 bars)
  → Already mitigated by current_bar routing override
```

Bug #1 (DLL frozen-tail) requires a Sierra Remote Build — out of scope for
this prompt. The `current_bar` routing override already mitigates it.

---

## §1 · Pre-work: read these files BEFORE any edits

```
backend/v9/systems/woodies/woodies_system.py      — TIME_STOP wiring (lines 200-210, 430-440, 533-567)
backend/v9/systems/woodies/time_stop.py            — TimeStopEnforcer.check()
backend/v9/services/trade_manager/manager.py       — close_trade() (line 349), _calculate_pnl() (line 504)
backend/v9/services/trade_manager/bar_level_detector.py — on_bar(), _check_time_stop(), _parse_ts()
backend/v9/api/v9/tpo_routes.py                    — _ib_from_bars() (line 322), _normalize_sierra_tpo() (line 359)
backend/v9/systems/five_min/five_min_system.py     — hydrate() (lines 187-213), process_bar() (lines 660-700)
bridge/v9_streams/base_stream.py                   — _chicago_to_utc() (line 283)
backend/v9/api/v9/woodies_chart_routes.py          — line 43 (hardcoded +5h)
backend/main.py                                    — _day_type_on_bar (lines 195-260)
sc_study/v9_exports.h                              — v9_sc_datetime_to_unix (line 147)
```

Also run:
```bash
sqlite3 data/mems26_local.db <<'SQL'
SELECT date, day_type, ib_high, ib_low, ib_width_class, opening_type FROM v9_day_type_history WHERE date='2026-05-28';
SELECT ts, high, low FROM v9_bars_5min WHERE symbol='MES' AND ts BETWEEN '2026-05-28 13:30:00' AND '2026-05-28 14:30:00' ORDER BY ts LIMIT 5;
SELECT ts, high, low FROM v9_bars_5min WHERE symbol='MES' AND ts BETWEEN '2026-05-28 14:30:00' AND '2026-05-28 15:30:00' ORDER BY ts LIMIT 5;
SQL
```

This confirms the +1h shift: 13:30-14:30 UTC bars are pre-RTH (08:30-09:30 ET),
14:30-15:30 UTC bars are the real IB window (09:30-10:30 ET).

---

## §2 · The 7 fixes (in dependency order)

### Fix #2 — Chicago TS: make `woodies_chart_routes.py` DST-aware

**Root cause:** `woodies_chart_routes.py:43` has `ts_unix += 5 * 3600` (hardcoded
CDT). Sierra chart is in ET (EDT = UTC-4 in summer), so this over-corrects by 1h.

**File:** `backend/v9/api/v9/woodies_chart_routes.py`
**Line:** 43

**Fix:** Replace hardcoded +5h with the same DST-aware conversion the bridge uses:
```python
# BEFORE:
ts_unix += 5 * 3600

# AFTER — use bridge's Chicago-to-UTC logic (DST-aware):
from bridge.v9_streams.base_stream import BaseV9Stream
ts_unix = BaseV9Stream._chicago_to_utc(ts_unix)
```

**BUT** — the bridge assumes Chicago (CDT/CST), and Sierra is actually in ET
(EDT/EST). The real fix is to change the bridge timezone from `America/Chicago`
to `America/New_York`. **HOWEVER** — verify first:

```bash
# Check: does Sierra use Chicago or New York?
# If MES chart says "Chart Time Zone: US/Eastern" → use America/New_York
# If "US/Central" → keep America/Chicago
# Michael needs to check Sierra: Chart Settings → Time Zone
```

**If Sierra is ET:** Change `base_stream.py:73` from `America/Chicago` to
`America/New_York`. This fixes the bridge AND makes `woodies_chart_routes.py:43`
correct when it reuses the bridge function.

**If Sierra is CT:** Keep `America/Chicago` — then the +1h drift has a different
cause. Diagnose further before patching.

**ASK MICHAEL before implementing.** This is a strategic decision.

**Test:** After fix, verify:
```python
# Bar at wall-clock 12:00 ET should have DB ts = 16:00 UTC (not 17:00)
sqlite3 data/mems26_local.db "SELECT MAX(ts) FROM v9_bars_5min WHERE symbol='MES'"
# Compare to wall clock — delta should be < 10 minutes, not +1 hour
```

---

### Fix #4 — IB query window (REPLACED 2026-05-28 evening — DELETE `_ib_from_bars()`)

**§0a #1 OVERRIDES the original "auto-fixed by #2" approach.** Michael's
evening directive: IB only from Sierra Initial Balance Study; bars-derived
synthesis is forbidden regardless of TZ correctness. Whether Fix #2 (TZ)
makes the synthesis return Sierra-matching values is now IRRELEVANT — the
synthesis itself is the wrong source of truth per CLAUDE.md
(*"Forbidden without explicit approval: inventing proj_*, synthetic time
grids, or rolling-window price levels when the DLL omits them."*).

**Files (locate by symbol — line drift expected):**
- `backend/v9/api/v9/tpo_routes.py` — `_ib_from_bars()` function and
  its caller in `_normalize_sierra_tpo()` `else:` branch.
- `backend/v9/api/v9/key_levels_routes.py` — any consumer that switches
  on `ib_source == "v9_bars_5min_09_30_10_30_ET"`.

**Diff sketch:**
```python
# tpo_routes.py — DELETE entire _ib_from_bars() function (was ~lines 322-356).

# In _normalize_sierra_tpo() — replace the else branch:
ib_found = bool(ib.get("found"))
if ib_found:
    ib_high = ib.get("high")
    ib_low = ib.get("low")
    ib_mid = ib.get("mid")
    ib_source = "sierra_live"
else:
    ib_high = ib_low = ib_mid = None
    ib_source = "missing"
```

**Pre-flight (mandatory before delete commit):**
1. Add an entry to `docs/reports/AMENDMENTS_LOG.md` recording the
   revocation of the 18:31 IDT same-day approval. Timestamp + reason.
2. Verify each downstream consumer handles `ib_high=None` cleanly. Cursor
   audited and confirmed safe (2026-05-28 evening):
   - `day_type_seed.maybe_seed_ib_from_tpo` returns False on None inputs.
   - `state_machine._stage_a3` guards on `bar.ib_high is not None`.
   - `main.py:_day_type_on_bar` guards on `_sierra_tpo.get("ib_found")`.
   - UI strips: `KeyLevelsStrip.tsx` / `TPOLensContent.tsx` — re-confirm
     they render "—" on `null` rather than crashing.
3. If any consumer crashes on `None`, INCLUDE the guard in the same
   commit as the delete. Do not split.

**Regression test (mandatory):**
`tests/v9/api/test_tpo_routes_no_ib_synthesis.py`:
```python
def test_normalize_sierra_tpo_returns_missing_when_dll_silent(monkeypatch):
    """When ib.found=false, response carries ib_high=None, ib_source='missing'.

    Anti-regression for the 2026-05-28 EVENING revocation of bars-synthesis.
    The previous _ib_from_bars() fallback flipped ib_found to True with a
    derived value — forbidden per CLAUDE.md source-of-truth rules.
    """
    from backend.v9.api.v9.tpo_routes import _normalize_sierra_tpo
    out = _normalize_sierra_tpo(
        {"ib": {"found": False}, "session": {"poc": 100, "vah": 102, "val": 98}},
        age_s=0.5,
    )
    assert out["ib_high"] is None
    assert out["ib_low"] is None
    assert out["ib_found"] is False
    assert out["ib_source"] == "missing"
```

**Note on Fix #2 interaction:** if Fix #2 (TZ) lands AFTER this delete, no
re-work is needed — there's no synthesis path to re-test. If Fix #2 lands
BEFORE, the synthesis will briefly produce Sierra-matching numbers but the
delete still removes it; consumers may briefly see correct IB then "missing"
when DLL is silent. That's the intended honest-failure behaviour.

---

### Fix #7 — BarLevelDetector exit_ts uses raw bar timestamp

**Root cause:** `bar_level_detector.py:89` passes `fill_ts=bar_ts` to
`on_stop_hit()`. The `bar_ts` comes from `_parse_ts(bar_ts_raw)` which
parses the raw bar timestamp. If the 5min bars have the Chicago-shifted ts,
the exit_ts is wrong.

**Fix:** Also auto-fixed by #2. Once bar timestamps are correct UTC,
`_parse_ts` will produce correct datetimes.

**Verify:** After #2, check:
```sql
SELECT entry_ts, exit_ts FROM v9_trades WHERE exit_ts < entry_ts;
-- Should return 0 rows
```

---

### Fix #3 — TIME_STOP counts pushes instead of bars · STATUS: ACTIVE (per §0a #2)

**Status note:** the morning Option B disabled W-10 via YAML kill switch,
which TEMPORARILY made this fix moot. §0a #2 REVERSES that — W-10 is
restored as sole authority and Bug A is fixed in code, not band-aided.
This fix is ACTIVE and must land in the same package as the YAML re-enable
(see §3 execution order revised below).

**Root cause:** `woodies_system.py` at `process_bar()` start increments
`self._bar_count` on every call. The bridge pushes every ~3s (same bar
being built). After 18 pushes (~54s), `bars_open >= 18` → TIME_STOP fires.

**File:** `backend/v9/systems/woodies/woodies_system.py`
**Locate by symbol (line drift expected):**
`rg -n "_bar_count \+= 1" backend/v9/systems/woodies/woodies_system.py`
(was `:204` at author time; was cited as `:201` in sibling prompt — both
drifted).

**Fix:** Only increment `_bar_count` when bar timestamp changes:

```python
# In __init__, near self._bar_count = 0, add:
self._last_bar_ts_for_count: Optional[float] = None

# In process_bar(), replace:
self._bar_count += 1

# With:
_bar_ts_key = bar.get("ts")
if _bar_ts_key is not None and _bar_ts_key != self._last_bar_ts_for_count:
    self._bar_count += 1
    self._last_bar_ts_for_count = _bar_ts_key
```

**Test:** `tests/v9/systems/woodies/test_w10_bar_count_per_close.py`:
```python
def test_bar_count_increments_once_per_unique_ts():
    """Push same bar 5× (same ts) → _bar_count increments once.

    Anti-regression for Bug A from DIAGNOSIS_TRADE_LIFECYCLE_BUGS_2026-05-28.md.
    The previous behaviour made W-10 fire after 54s (18 pushes ≈ 18 fake
    bars), not 90 minutes (18 real closed bars).
    """
    from backend.v9.systems.woodies.woodies_system import WoodiesSystem
    system = WoodiesSystem(db_path=":memory:", rth_only=False)
    base = system._bar_count

    # 5 pushes with identical ts
    for _ in range(5):
        # Use the actual process_bar entry — adjust event shape as needed.
        # Asyncio loop: run_until_complete on system.process_bar(...)
        ...
    assert system._bar_count == base + 1

    # 1 push with new ts → +1
    ...
    assert system._bar_count == base + 2
```

**Impact:** TIME_STOP fires after 18 real 5-min bars (= 90 minutes), per Registry #11.

---

### Fix #5 — TIME_STOP exit_price=NULL, pnl=0 · STATUS: ACTIVE (per §0a #2)

**Status note:** explicitly added by Michael 2026-05-28 evening as part of
the W-10 restoration package. Lands together with Fix #3 + YAML re-enable +
Layer 4 removal.

**Root cause:** `_check_time_stops()` calls `tm.close_trade(trade_id, "TIME_STOP")`
without setting `exit_price` first. `close_trade()` → `_calculate_pnl()` falls
through to `exit_p = trade.exit_price or trade.entry_price` (verified at
`backend/v9/services/trade_manager/manager.py:553`) → pnl=0.

**File:** `backend/v9/systems/woodies/woodies_system.py`
**Locate by symbol (line drift expected):**
`rg -n 'close_trade\(int\(trade_id\), "TIME_STOP"\)' backend/v9/systems/woodies/woodies_system.py`
(was `:573` actual when this revision was authored; sibling prompt cited `:556`).

**Fix (with defensive guards required by sibling prompt §2.1 pushback):**
```python
# Inside the `if result.fired:` block of _check_time_stops().
# BEFORE the existing close_trade call, add:

if tm is not None and self._closes:
    try:
        trade_obj = tm._get_trade(int(trade_id))
        if trade_obj is not None:
            trade_obj.exit_price = float(self._closes[-1])
    except Exception as exc:
        logger.warning(
            "[woodies] TIME_STOP exit_price set failed for trade %s: %s",
            trade_id, exc,
        )
        # Skip the close_trade call rather than passing NULL → pnl=0 regression.
        to_remove.append(trade_id)
        continue

if not self._closes:
    logger.warning(
        "[woodies] TIME_STOP fired but _closes is empty — skipping close "
        "for trade %s (no exit_price available)", trade_id,
    )
    to_remove.append(trade_id)
    continue

# THEN the existing close_trade call:
tm.close_trade(int(trade_id), "TIME_STOP")
```

**Test:** `tests/v9/systems/woodies/test_w10_time_stop_sets_exit_price.py`:
```python
def test_time_stop_sets_exit_price_before_close():
    """exit_price = self._closes[-1] is set on the trade BEFORE close_trade.

    Anti-regression for Bug D (pnl=0 because manager._calculate_pnl falls
    back to entry_price when exit_price is NULL).
    """
    # Wire fake gateway/TM; populate system._closes=[100.5];
    # force bars_open >= limit_bars; assert trade_obj.exit_price == 100.5
    # AND that assignment happened before close_trade was called.

def test_time_stop_skipped_when_closes_empty():
    """If _closes is empty, close_trade is NOT called and a WARNING is logged.

    Defensive — passing NULL exit_price would re-introduce Bug D.
    """
    # Same harness with system._closes=[] → mock_tm.close_trade.assert_not_called()
```

**Impact:** PnL correctly calculated on TIME_STOP exits. Bug D resolved.

---

### Fix #6 — S2 current_day_type=None after restart · REVISED — diagnose first

**Status note:** the original "add a third fallback in process_bar()" approach
was based on an incorrect line-number cite (the prompt cited `:202-213` and
`:660` for the day_type hydrate region, but Cursor verified the actual day_type
hydrate is at `:129-153` of `five_min_system.py`). The morning approach would
add a redundant THIRD path on top of two existing ones. Replaced 2026-05-28
evening with diagnose-first.

**Existing code (verified by Cursor 2026-05-28 evening):**
- `five_min_system.hydrate()` at `:129-153` already reads from `v9_day_type_state`
  with `func.current_date()` and assigns `self.current_day_type`.
- `_on_day_type_update` at `:259-274` updates `current_day_type` on every event
  from BarRouter.

So if `current_day_type=None` after restart, ONE of these is broken — adding a
third path masks the diagnosis.

**File:** `backend/v9/systems/five_min/five_min_system.py`

**Step 0 — Reproduce deterministically (DO NOT SKIP):**
```bash
sqlite3 data/mems26_local.db <<'SQL'
SELECT id, ts, day_type, classification, lock_state
FROM v9_day_type_state
WHERE date(ts)=date('now')
ORDER BY id DESC LIMIT 5;
SQL
```

Three cases:
- **(a) Table empty for today** → expected pre-RTH. NOT a bug. The lazy-load
  proposal would have added overhead with no payoff. STOP — no fix needed.
- **(b) Rows exist with `day_type` set** → `hydrate()` query missed them.
  Likely cause: `func.current_date()` semantics (UTC vs local). FIX is in
  `hydrate()`, not `process_bar()`.
- **(c) Rows exist but `day_type=NULL`** → state machine wrote NULL. Bug is
  upstream in `_day_type_on_bar` (`backend/main.py:181-310`), not in S2.

**DO NOT promote a hypothesis to code before identifying which case applies.**
This is Mistake #6 in `.cursor/rules/mems26-pre-live-protocol.mdc`.

**Step 1 — Once the case is identified, ship the SMALLEST correct fix:**
- Case (b): change the WHERE clause in `hydrate()` `:129-153` to a 24h
  sliding window: `ts > now() - interval '1 day'` (SQLAlchemy: filter on
  `V9DayTypeState.ts >= datetime.utcnow() - timedelta(hours=24)`). Test:
  insert a row whose `ts` is "yesterday-UTC but today-local" (or vice
  versa), call `hydrate()`, assert `current_day_type` is set.
- Case (c): patch `_day_type_on_bar` so it never persists NULL. Test
  reproduces the upstream condition and asserts the row carries day_type.

**Test:** under `tests/v9/systems/five_min/` — name it after the
ACTUAL failure case identified, e.g. `test_hydrate_handles_utc_date_boundary.py`,
not the placeholder "lazy_loads_day_type_when_none".

**Impact:** Chart patterns (H&S, Flags, DblBT) unblocked AFTER the right
fix is applied to the right file.

---

### Fix #1 — DLL frozen-tail (DEFERRED — document only)

**Root cause:** `v9_woodies_export.h:460-462` — `GetContainingIndexForDateTimeIndex`
maps DLL bar indices to Woodies chart indices. For the last ~13 bars of each
session, Sierra clamps to the same chart index → all 7 Sierra study fields freeze.

**Status:** MITIGATED by `current_bar` routing override (bars.py:852). The S4
routing path now uses `current_bar` (direct `arr[idx]` read, always live) instead
of `history[-1]` (frozen).

**Full fix requires:** Sierra Remote Build + DLL code change. Options:
- (a) Change `woodies_chart` input to `sc.ChartNumber` (same chart → bypass mapping)
- (b) Add a staleness check: if `mapIdx` returns same index for N consecutive bars, fall back to local calc
- (c) Use `v9_calc_cci` for ALL bars (abandon Sierra study arrays for history)

**Not in scope for this prompt.** Document as Pipeline 3 item.

---

## §3 · Execution order (REVISED 2026-05-28 evening)

```
Phase 1 — ASK MICHAEL (before any code):
  → What timezone is Sierra chart set to? (ET or CT?)
  → This determines whether Fix #2 changes to America/New_York or stays America/Chicago.
  → Sierra UI: Global Settings → General → Time Zone tab. Screenshot mandatory.

Phase 2 — Code changes (after Michael confirms TZ):
  Group A1 (IB cleanup, lands FIRST, no service restart between A1 sub-fixes):
    A1.1  AMENDMENTS_LOG entry — revoke 18:31 IDT IB synthesis approval
    A1.2  Fix #4 (REPLACED) — DELETE _ib_from_bars(); ib_source="missing" on silence
    A1.3  Verify consumers handle ib_high=None (UI strips, seed, state machine)

  Group A2 (W-10 restoration — sole TIME_STOP authority, lands SECOND):
    A2.1  AMENDMENTS_LOG entry — reverse Option B, document V3 → Registry #11 deviation
    A2.2  Fix #3  (W-10 _bar_count per closed bar, not per push)
    A2.3  Fix #5  (W-10 exit_price = self._closes[-1] before close_trade)
    A2.4  YAML: dispatcher_config.yaml::time_stop_minutes: 90 (un-disable)
    A2.5  REMOVE Layer 4 from bar_level_detector.py:
            - delete TIME_STOP_BY_DAY_TYPE constant
            - delete time-based exit block in on_bar
            - delete _check_time_stop method
            (KEEP stop/target hit logic and _parse_ts)
    A2.6  Tests cleanup: invert test_w10_time_stop_disabled → test_w10_time_stop_enabled,
            delete test_layer4_time_stop_authority.py, un-skip the 7 currently-skipped tests

  Group B (Chicago TS — coordinated, off-RTH):
    B.1   Fix #2 — DST-aware TZ (after Michael confirms ET vs CT, dry-run script first)
    B.2   Verify Fix #4 IB query is moot (function deleted in A1)
    B.3   Verify Fix #7 — entry_ts < exit_ts via SQL after first post-fix trade

  Group C (S2 — diagnose first):
    C.1   Fix #6 — DIAGNOSE the actual case (a/b/c) before any code change

Phase 3 — Tests:
  pytest tests/v9/api/test_tpo_routes_no_ib_synthesis.py -v       # Group A1
  pytest tests/v9/systems/woodies/test_w10_bar_count_per_close.py -v        # Group A2
  pytest tests/v9/systems/woodies/test_w10_time_stop_sets_exit_price.py -v  # Group A2
  pytest tests/v9/systems/woodies/test_w10_time_stop_enabled.py -v          # Group A2
  pytest tests/v9/services/trade_manager/test_bar_level_detector_no_time_stop.py -v  # Group A2
  pytest tests/v9/systems/test_time_stop.py -v                   # un-skipped tests
  pytest tests/v9/systems/ -q                                     # full regression

Phase 4 — Restart + UAT (4-axis per pre-LIVE protocol):
  Kill backend → start fresh → verify EACH axis on EACH endpoint:

  Group A1 verification:
    Quality:     /api/v9/tpo/current.ib_source == "sierra_live" OR "missing", never "v9_bars_*"
    Recency:     /api/v9/tpo/current.export_ts within 30s of file mtime
    Cardinality: /api/v9/tpo/history?limit=20 returns exactly 20 rows
    Latency:     p95 of /api/v9/tpo/current under 100ms

  Group A2 verification:
    Quality:     S4 fire → wait 90 real minutes → exit_reason == "TIME_STOP" AND exit_price != NULL AND pnl != 0
    Quality b:   S4 fire → push the same bar 30× in 90s → TIME_STOP does NOT fire (Bug A regression test)
    Recency:     /api/v9/status reflects open trade ts within 5s
    Cardinality: /api/v9/trade_history?limit=20 returns 20 rows
    Latency:     p95 of /api/v9/status under 100ms

  Group B verification:
    Quality:     SELECT MAX(ts) FROM v9_bars_5min → delta < 10min from wall clock
    Recency:     /api/v9/bars/5min latest_ts == DB MAX(ts)
    Cardinality: /api/v9/bars/5min?limit=300 returns 300
    Latency:     p95 under 100ms

  Group C verification:
    Quality:     /api/v9/five_min/current.current_day_type matches v9_day_type_state today's row
```

---

## §4 · Forbidden surface

```
- sc_study/*.cpp, *.h                    — DLL changes need Remote Build (not in scope)
- docs/spec_authority/                    — LOCKED
- docs/decisions/                         — LOCKED
- backend/v9/systems/woodies/patterns/    — W-6 frozen
- backend/v9/systems/woodies/pattern_dispatcher.py — W-8 frozen
- backend/v9/systems/woodies/atr_stop.py  — W-1 frozen
- frontend/                               — not in scope
```

---

## §5 · Verification checklist — REVISED 2026-05-28 evening

Phase 3 / Phase 4 cannot declare done until ALL boxes are checked or
explicitly marked SKIP/SUPERSEDED with a reason.

### Group A1 — IB cleanup
```
[ ] AMENDMENTS_LOG entry "IB bars-synthesis revocation" recorded with timestamp
[ ] _ib_from_bars() function fully deleted from tpo_routes.py
[ ] _normalize_sierra_tpo() else: branch returns ib_source="missing"
[ ] No remaining reference to "v9_bars_5min_09_30_10_30_ET" in repo (rg -n confirms 0)
[ ] tests/v9/api/test_tpo_routes_no_ib_synthesis.py passes
[ ] /api/v9/tpo/current returns ib_source ∈ {"sierra_live","missing"} on live curl
[ ] /api/v9/key_levels does not crash on ib_high=None
[ ] UI strips render "—" instead of crashing on ib_high=null
```

### Group A2 — W-10 restoration
```
[ ] AMENDMENTS_LOG entry "W-10 Option B REVERSED" recorded
[ ] dispatcher_config.yaml::time_stop_minutes == 90 (un-disabled)
[ ] YAML kill-switch comment block replaced with restoration note
[ ] Fix #3: woodies_system._bar_count only increments on new bar ts
[ ] Fix #5: woodies_system._check_time_stops sets exit_price before close_trade
[ ] Layer 4 removed from bar_level_detector.py:
      - TIME_STOP_BY_DAY_TYPE constant deleted
      - time-based exit block in on_bar deleted
      - _check_time_stop method deleted
      - stop/target hit logic intact
[ ] tests/v9/systems/woodies/test_w10_bar_count_per_close.py passes
[ ] tests/v9/systems/woodies/test_w10_time_stop_sets_exit_price.py passes
[ ] tests/v9/systems/woodies/test_w10_time_stop_enabled.py passes (was test_disabled, inverted)
[ ] tests/v9/services/trade_manager/test_layer4_time_stop_authority.py DELETED
[ ] tests/v9/systems/test_time_stop.py — 6 tests un-skipped, all pass
[ ] tests/v9/systems/test_woodies_rth_gate.py — 1 test un-skipped, passes
[ ] No trade in v9_trades has exit_reason="TIME_STOP" with exit_price=NULL post-fix
[ ] No regression: an open trade does NOT close at 52s post-entry (Bug A anti-regression)
```

### Group B — Chicago TS
```
[ ] Sierra chart TZ confirmed by Michael (screenshot in AMENDMENTS_LOG)
[ ] scripts/probe_tz_assumptions.py shows the chosen TZ matches Sierra wall-clock
[ ] base_stream.py TZ updated atomically with woodies_chart_routes.py
[ ] /api/v9/bars/5min latest_ts delta to wall clock < 10 min
[ ] Fix #4 (auto-fix) is N/A — _ib_from_bars deleted in Group A1
[ ] Fix #7: SELECT * FROM v9_trades WHERE exit_ts < entry_ts → 0 rows
```

### Group C — S2 day_type hydrate
```
[ ] Step 0 reproduction completed; identified case (a)/(b)/(c)
[ ] Fix targets the identified case ONLY (no extra fallback paths added)
[ ] Test reproduces the actual failure condition, not a placeholder
```

### Cross-cutting
```
[ ] All 969+ existing tests still pass
[ ] Backend restart clean (no traceback in /tmp/backend.err.log)
[ ] docs/reports/STATUS_BOARD.md updated with one line per landed group
[ ] No file outside §1 / §0a target list was modified (run git diff --name-only and audit)
```

---

## §6 · Self-report format

After completing, write: `docs/reports/FIX_REPORT_7_BUGS_2026-05-29.md`

```
# Fix Report — 7 Pre-LIVE Bugs · 2026-05-29

## §1 · Per-fix summary (table: bug # | file:line | diff | test)
## §2 · Sierra TZ confirmation (Michael's answer + evidence)
## §3 · Test results (pytest output verbatim)
## §4 · UAT 4 axes results
## §5 · Remaining open items (Bug #1 DLL frozen-tail status)
```
