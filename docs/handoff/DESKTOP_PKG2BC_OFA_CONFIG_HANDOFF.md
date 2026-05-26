# Desktop Handoff · Pkg 2bc · OFA Config + Validators (merged 2b + 2c)

**Date:** 2026-05-23
**Author:** Cursor agent · supervised by Michael
**Target executor:** Claude Code (CC) via Claude Desktop mega prompt
**Status:** ✅ Spec locked · ready for mega prompt
**Predecessors:**
- Pkg 0 (Path B deletion · D-090) · ✅ G3 PASS
- Pkg 1 (Adaptive Stop Engine) · ✅ G3 PASS (18 tests)
- Pkg 2a (OFA Entry signal close-through-level + family mapping) · ✅ G3 PASS (20 tests)

---

## §1 · Why this Pkg exists

Master Summary Sheet 7 rows 6-7 specify two OFA quality improvements that are LIVE-blocking per D-091:

- **2b** · `belly_dominance_ratio` (default 1.5×) + `min_bars_for_drop` (default 3) · config-driven
- **2c** · 7 validator checks in `pre_fire_validator.py` · regression tests

After deep investigation Michael locked:

### §1.1 · Q1 belly_dominance_ratio · semantics
- **Ratio definition:** `buy_volume / sell_volume` on bar 3 (the belly bar) for LONG · mirror for SHORT
- **Threshold:** ≥ 1.5× (i.e., ≥60% of volume on buy side for LONG belly)
- **Implementation:** Pkg 2bc-X · S3 stores `_forces_history` of last 7 bars · S2 reads from `current_state["forces_history"]` and computes ratio locally

### §1.2 · Q2 min_bars_for_drop = 3 · semantics
- **Lock:** Option B (lookback before bar 1) · operationalized as Option C `max(lookback_3bars.volume) < bar1.volume × 0.6`
- **Pattern interpretation:** 3 bars BEFORE bar 1 (sellers spike) must show "normal/low" volume to confirm spike is real (not continuation)
- **Concrete check:** `max(bars[-7], bars[-6], bars[-5].volume) < bars[-4].volume × 0.6`
- **Buffer requirement:** Pattern now requires 7 bars total (3 lookback + 4 pattern) instead of 4

### §1.3 · Q3 7 validators
- **Discovery:** `backend/v9/shared/pre_fire_validator.py` already implements all 7 checks (5 explicit + 2 via Pydantic Field/Literal)
- **Pkg 2c reduces to:** completing test coverage with negative tests for previously untested checks (direction · t1/t2 equality · confidence bounds · time_stop bounds)

---

## §2 · Scope (FOUR parts)

### Part A · S3 Footprint · forces_history (additive)

**File:** `backend/v9/systems/footprint/footprint_system.py`

**A1.** In `__init__` (around line 31, with other `_last_forces` declarations):
```python
self._forces_history: List[Dict[str, Any]] = []  # Pkg 2bc · last 7 bars (oldest→newest)
self._FORCES_HISTORY_CAP: int = 7
```

**A2.** In the bar-process flow where `self._last_forces` is set (the line currently reads `self._last_forces = forces` around line 258), append to history:
```python
self._last_forces = forces
self._last_forces_source = forces["source"]
# Pkg 2bc · maintain forces history (cap at 7)
self._forces_history.append({
    "ts": bar.get("ts"),
    "ask_vol": forces["agg_buy_vol"],
    "bid_vol": forces["agg_sell_vol"],
})
if len(self._forces_history) > self._FORCES_HISTORY_CAP:
    self._forces_history = self._forces_history[-self._FORCES_HISTORY_CAP:]
```

**A3.** Expose via `current_state` in the post-bar update block (around line 173, where `aggressive_flow` is set):
```python
self.current_state["aggressive_flow"] = self._last_forces
self.current_state["forces_source"] = self._last_forces_source
self.current_state["forces_history"] = list(self._forces_history)  # Pkg 2bc · copy to avoid aliasing
```

### Part B · S2 Reactive · belly_dominance_ratio + lookback

**File:** `backend/v9/systems/five_min/five_min_system.py`

**B1.** Add module-level constants near the imports (after the imports block, before the first class definition — around line 25-35):

```python
# Pkg 2bc · OFA configuration (config-driven thresholds per Master Sheet 7)
DROP_THRESHOLD_PCT: float = 0.10               # bar 2 vol ≤ 10% of bar 1 vol (90% drop)
EXPANSION_MIN_PT: float = 1.5                  # Initiative bar 1 range min (points)
EXPANSION_MAX_PT: float = 1.75                 # Initiative bar 1 range max (points)
POC_RETURN_TOLERANCE_PT: float = 0.5           # Initiative bar 2 POC return tolerance
MIN_BARS_REQUIRED: int = 7                     # 4 pattern + 3 lookback (Pkg 2bc)
LOOKBACK_BARS: int = 3                         # bars before bar 1 to check "normal" volume
LOOKBACK_MAX_VOL_RATIO: float = 0.6            # max(lookback_3bars.volume) / bar1.volume must be < this
BELLY_DOMINANCE_RATIO: float = 1.5             # bar 3 buy/sell ratio threshold for Reactive
```

**B2.** Add helper method to `FiveMinSystem` class (location: right after `_get_belly_from_footprint` method around line 245):

```python
def _get_belly_ratio_from_footprint(self, direction: str) -> Optional[float]:
    """Pkg 2bc · compute belly dominance ratio for bar 3 from forces_history.

    LONG belly: ratio = ask_vol / bid_vol (buyers dominate at bottom).
    SHORT belly: ratio = bid_vol / ask_vol (sellers dominate at top).

    Returns None if history unavailable (graceful degradation — caller must SKIP check, not reject).
    """
    state = self._footprint_state()
    history = state.get("forces_history") or []
    if len(history) < 2:
        return None
    bar3 = history[-2]  # bar 3 (one bar ago · current = bar 4)
    ask = bar3.get("ask_vol")
    bid = bar3.get("bid_vol")
    if ask is None or bid is None:
        return None
    if direction == "LONG":
        if bid <= 0:
            return None
        return ask / bid
    if ask <= 0:
        return None
    return bid / ask
```

**B3.** Update `_detect_reactive` (current location starts ~line 316):

Replace `if len(bars_5m) < 4` (line 329) with:
```python
if len(bars_5m) < MIN_BARS_REQUIRED:
    return None
```

Replace `b2_drop = b2_vol <= b1_vol * 0.10` (around line 346) with:
```python
b2_drop = b2_vol <= b1_vol * DROP_THRESHOLD_PCT
```

Add the **lookback** + **belly_dominance** checks immediately AFTER the existing `b1_sellers, b2_drop, b3_buyers, b3_belly, b4_confirm, b4_close_above_b3_high, cot_above_amt` evaluation but BEFORE the firing return (around line 352-360 for LONG and 365-372 for SHORT).

Concrete edit for **Reactive LONG block** (replacing the `if b1_sellers and ...` line):
```python
# Pkg 2bc · lookback check (3 bars before bar 1 must be "quiet")
lookback = bars_5m[-MIN_BARS_REQUIRED:-(MIN_BARS_REQUIRED - LOOKBACK_BARS)]
lookback_quiet = all(b.get("v", 0) > 0 for b in lookback) and (
    max(b.get("v", 0) for b in lookback) < b1_vol * LOOKBACK_MAX_VOL_RATIO
)
# Pkg 2bc · belly_dominance_ratio (graceful degradation if history unavailable)
belly_ratio = self._get_belly_ratio_from_footprint("LONG")
belly_ratio_ok = (belly_ratio is None) or (belly_ratio >= BELLY_DOMINANCE_RATIO)

if (b1_sellers and b2_drop and b3_buyers and b3_belly
        and b4_confirm and b4_close_above_b3_high and cot_above_amt
        and lookback_quiet and belly_ratio_ok):
    return ("LONG", 0.80 if poc_rising else 0.75,
            {"kind": "REACTIVE", "stage": 4, "belly": belly, "poc_rising": poc_rising,
             "belly_ratio": belly_ratio})
```

Same pattern for **Reactive SHORT** — mirror the lookback (uses same `lookback_quiet` variable since direction-independent) and substitute `_get_belly_ratio_from_footprint("SHORT")`.

**B4.** Update `_detect_initiative` (current location starts ~line 374):

Replace `if len(bars_5m) < 4` (line 387) with `if len(bars_5m) < MIN_BARS_REQUIRED`.

Replace `1.5 <= b1_range <= 1.75` with `EXPANSION_MIN_PT <= b1_range <= EXPANSION_MAX_PT`.

Replace `abs(b2["c"] - b2_poc) <= 0.5` with `abs(b2["c"] - b2_poc) <= POC_RETURN_TOLERANCE_PT` (appears twice — both LONG and SHORT branches).

Add lookback check to Initiative LONG block:
```python
lookback = bars_5m[-MIN_BARS_REQUIRED:-(MIN_BARS_REQUIRED - LOOKBACK_BARS)]
lookback_quiet = all(b.get("v", 0) > 0 for b in lookback) and (
    max(b.get("v", 0) for b in lookback) < b1_vol * LOOKBACK_MAX_VOL_RATIO
)

if (b1_bull and b1_expansion and b2_test and b3_joining and b4_test
        and b4_close_above_b1_high and cot_below_amt and lookback_quiet):
    return ("LONG", 0.80, {"kind": "INITIATIVE", "stage": 4,
                           "b2_alt": "poc_return" if b2_poc_return else "higher_low"})
```

Same pattern for Initiative SHORT.

**Note · Initiative has no belly check** — belly_dominance_ratio applies to Reactive only (Initiative is breakout pattern, not exhaustion).

### Part C · pre_fire_validator tests (Pkg 2c)

**File:** `backend/v9/shared/tests/test_pre_fire_validator.py`

Add the following NEW negative tests after the existing 5 tests:

```python
def test_pydantic_rejects_invalid_direction():
    """Direction must be LONG or SHORT (Literal type)."""
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        FireRequest(system_id='T1_NUMBER_BAR', direction='UP',
                    entry_price=100, stop_price=99, t1_price=101, t2_price=102,
                    time_stop_minutes=60, confidence=75)

def test_pydantic_rejects_confidence_negative():
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        FireRequest(system_id='T1_NUMBER_BAR', direction='LONG',
                    entry_price=100, stop_price=99, t1_price=101, t2_price=102,
                    time_stop_minutes=60, confidence=-1)

def test_pydantic_rejects_confidence_above_100():
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        FireRequest(system_id='T1_NUMBER_BAR', direction='LONG',
                    entry_price=100, stop_price=99, t1_price=101, t2_price=102,
                    time_stop_minutes=60, confidence=101)

def test_pydantic_rejects_time_stop_zero():
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        FireRequest(system_id='T1_NUMBER_BAR', direction='LONG',
                    entry_price=100, stop_price=99, t1_price=101, t2_price=102,
                    time_stop_minutes=0, confidence=75)

def test_pydantic_rejects_time_stop_above_180():
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        FireRequest(system_id='T1_NUMBER_BAR', direction='LONG',
                    entry_price=100, stop_price=99, t1_price=101, t2_price=102,
                    time_stop_minutes=181, confidence=75)

def test_invalid_t1_ordering_long_equal():
    """LONG: entry == t1 violates strict ordering."""
    req = FireRequest(system_id='T1_NUMBER_BAR', direction='LONG',
                      entry_price=100, stop_price=99, t1_price=100, t2_price=102,
                      time_stop_minutes=60, confidence=75)
    resp = validate_fire(req)
    assert resp.valid is False
    assert "entry < t1 < t2" in resp.fail_reason

def test_invalid_t1_ordering_short_equal():
    req = FireRequest(system_id='T1_NUMBER_BAR', direction='SHORT',
                      entry_price=100, stop_price=101, t1_price=100, t2_price=98,
                      time_stop_minutes=60, confidence=75)
    resp = validate_fire(req)
    assert resp.valid is False
    assert "entry > t1 > t2" in resp.fail_reason

def test_invalid_t2_equal_t1():
    """t1 == t2 violates strict ordering."""
    req = FireRequest(system_id='T1_NUMBER_BAR', direction='LONG',
                      entry_price=100, stop_price=99, t1_price=101, t2_price=101,
                      time_stop_minutes=60, confidence=75)
    resp = validate_fire(req)
    assert resp.valid is False
```

### Part D · Pattern tests (Pkg 2b + cross)

**File:** `tests/atomic/test_five_min_patterns.py`

Add these NEW tests (keeping the 20 existing tests intact):

```python
# ── Pkg 2bc · belly_dominance_ratio ──

class TestBellyDominanceRatio:
    """Pkg 2bc · belly ratio gating on Reactive (graceful degradation when history missing)."""

    @patch("backend.v9.systems.five_min.five_min_system.FiveMinSystem._cot_amt_from_sierra",
           return_value=(None, None))
    @patch("backend.v9.systems.five_min.five_min_system.FiveMinSystem._get_amt_from_footprint",
           return_value=5)
    @patch("backend.v9.systems.five_min.five_min_system.FiveMinSystem._get_cot_from_footprint",
           return_value=10)
    @patch("backend.v9.systems.five_min.five_min_system.FiveMinSystem._get_belly_from_footprint",
           return_value=True)
    @patch("backend.v9.systems.five_min.five_min_system.FiveMinSystem._footprint_state",
           return_value={"forces_history": [
               {"ts": 1, "ask_vol": 50, "bid_vol": 50},
               {"ts": 2, "ask_vol": 50, "bid_vol": 50},
               {"ts": 3, "ask_vol": 50, "bid_vol": 50},
               {"ts": 4, "ask_vol": 50, "bid_vol": 50},
               {"ts": 5, "ask_vol": 50, "bid_vol": 50},
               {"ts": 6, "ask_vol": 100, "bid_vol": 80},  # bar 3 belly · ratio = 1.25 (< 1.5)
               {"ts": 7, "ask_vol": 90, "bid_vol": 60},
           ]})
    def test_reactive_long_rejected_when_belly_ratio_below_threshold(self, *_):
        sys = FiveMinSystem()
        bars = _make_lookback_quiet_reactive_long_bars()
        result = sys._detect_reactive(bars)
        assert result is None, "ratio=1.25 should reject"

    # similarly test_reactive_long_fires_when_belly_ratio_above_threshold (ratio=1.8)
    # similarly test_reactive_long_passes_when_forces_history_unavailable (graceful degradation)
    # similarly SHORT mirror

# ── Pkg 2bc · lookback (min_bars_for_drop) ──

class TestLookbackCheck:
    """Pkg 2bc · 3 bars before bar 1 must show max_volume < 60% of bar 1."""

    def test_pattern_rejected_when_buffer_below_7_bars(self):
        sys = FiveMinSystem()
        bars = _make_reactive_long_bars()[-6:]  # only 6 bars
        result = sys._detect_reactive(bars)
        assert result is None

    def test_reactive_long_rejected_when_lookback_has_high_volume(self):
        # bar 1 vol = 1000 · max lookback = 700 (≥ 60%) → REJECT
        ...

    def test_reactive_long_fires_when_lookback_quiet(self):
        # bar 1 vol = 1000 · max lookback = 400 (< 60%) → ALLOW
        ...

    def test_initiative_lookback_also_applies(self):
        # Verify Initiative LONG/SHORT also blocked when lookback noisy
        ...

# ── Pkg 2bc · module constants ──

class TestModuleConstants:
    def test_constants_have_documented_defaults(self):
        from backend.v9.systems.five_min.five_min_system import (
            DROP_THRESHOLD_PCT, EXPANSION_MIN_PT, EXPANSION_MAX_PT,
            POC_RETURN_TOLERANCE_PT, MIN_BARS_REQUIRED, LOOKBACK_BARS,
            LOOKBACK_MAX_VOL_RATIO, BELLY_DOMINANCE_RATIO,
        )
        assert DROP_THRESHOLD_PCT == 0.10
        assert EXPANSION_MIN_PT == 1.5
        assert EXPANSION_MAX_PT == 1.75
        assert POC_RETURN_TOLERANCE_PT == 0.5
        assert MIN_BARS_REQUIRED == 7
        assert LOOKBACK_BARS == 3
        assert LOOKBACK_MAX_VOL_RATIO == 0.6
        assert BELLY_DOMINANCE_RATIO == 1.5
```

**For S3 history tests** — add to `backend/v9/tests/test_footprint_system.py` (new test class):

```python
class TestForcesHistory:
    """Pkg 2bc · S3 maintains forces_history list of last 7 bars."""

    def test_forces_history_starts_empty(self):
        sys = FootprintSystem()
        assert sys._forces_history == []

    def test_forces_history_capped_at_7(self):
        # Feed 10 bars · expect history length == 7 · oldest = bar 4
        ...

    def test_forces_history_exposed_via_current_state(self):
        # After processing bars, current_state["forces_history"] reflects internal state
        ...
```

---

## §3 · Existing tests that MUST stay green (no regression)

| Suite | Count | Constraint |
|-------|-------|------------|
| `tests/atomic/test_five_min_patterns.py` (Pkg 2a) | 20 | All must pass after changes. **Important:** the 3 existing positive tests (`test_reactive_long`, `test_reactive_short`, `test_initiative_long`) currently use 4-bar fixtures · they must be extended to 7-bar fixtures with **quiet lookback** + **non-None forces_history** for them to continue passing. |
| `tests/v9/systems/test_five_min/test_adaptive_stop.py` (Pkg 1) | 18 | Untouched. |
| `backend/v9/tests/test_footprint_system.py` (existing) | 11 | All must pass with additive forces_history. |
| `backend/v9/shared/tests/test_pre_fire_validator.py` | 5 → 13 | All 5 original + 8 new |
| Full `backend/v9/tests/` suite | 517 | No regression |

---

## §4 · Forbidden changes (STOP signals)

| # | Constraint | Why |
|---|-----------|------|
| 1 | **Lines 205-207** in `five_min_system.py` must remain byte-identical | Chronic toxicity comment (Constitution V3 §Part 6 · D-091 explicit) |
| 2 | S3 firing decisions/thresholds must NOT change | D-089 locked S3 as firing system |
| 3 | `pre_fire_validator.py` runtime logic must NOT change | Adding tests only · validator code stays |
| 4 | Adaptive Stop Engine (`adaptive_stop.py`) must NOT be touched | Pkg 1 G3 PASSED |
| 5 | Family mapping fix from Pkg 2a (`kind == "REACTIVE"`) must remain | Don't accidentally revert |
| 6 | DLL / Sierra `5min.json` schema must NOT change | Out of scope · architecture stable |
| 7 | DB migration NOT allowed | Out of scope |

If CC encounters need to touch these → STOP, report, return to Michael.

---

## §5 · Acceptance criteria (G3 review)

CC's commit must pass ALL of:

1. ✅ `pytest tests/atomic/test_five_min_patterns.py -q` — 20 existing + ~9 new = **~29 passed**
2. ✅ `pytest tests/v9/systems/test_five_min/ -q` — **18 passed** (Pkg 1 no-regression)
3. ✅ `pytest backend/v9/tests/test_footprint_system.py -q` — **11 existing + ~3 new = ~14 passed**
4. ✅ `pytest backend/v9/shared/tests/test_pre_fire_validator.py -q` — **5 existing + 8 new = 13 passed**
5. ✅ `pytest backend/v9/tests/ -q` — full backend suite no-regression (≥517 passed)
6. ✅ `FiveMinSystem()` boots clean (run `python3 -c "from backend.v9.systems.five_min.five_min_system import FiveMinSystem; FiveMinSystem()"` with `BRIDGE_TOKEN=dummy`)
7. ✅ `FootprintSystem()` boots clean
8. ✅ `git diff HEAD~1 HEAD -- backend/v9/systems/five_min/five_min_system.py | grep -E "^[+-].*(chronic|toxicity)"` returns **no hits** (lines 205-207 untouched)
9. ✅ No linter errors (ReadLints on all 4 modified files)
10. ✅ Commit message: `feat(s2): OFA config + belly_dominance + lookback + validator tests per Pkg 2bc spec`

---

## §6 · Tests-are-authority rule (re-emphasized)

If during implementation CC discovers ambiguity between this handoff and the tests:
- **Tests win.**
- Handoff is illustrative.
- Report the conflict in the PR description.

If during implementation CC discovers ambiguity between this handoff and existing positive test data (e.g., the 3 Pkg 2a positive tests now fail because they don't include 7-bar fixtures):
- **The 3 positive tests must be extended** (not abandoned) — add 3 quiet lookback bars + populate `_footprint_state` mock with `forces_history` for those tests.
- Document the fixture extension in the commit body.

---

## §7 · Graceful degradation rule (production safety)

Per `CLAUDE.md` pre-LIVE protocol §"No silent failures":
- If `forces_history` is unavailable (empty list, None, or insufficient entries), `belly_dominance_ratio` check is **SKIPPED** (treated as True) — not REJECTED
- This prevents S2 from silently stopping all fires if S3 has a transient state issue
- The 7-bar buffer requirement (lookback) is enforced strictly — if buffer < 7, pattern doesn't fire
- Both behaviors are tested explicitly in §2.Part D

---

## §8 · Files modified summary

| File | Action | Estimated LOC |
|------|--------|---------------|
| `backend/v9/systems/footprint/footprint_system.py` | additive · forces_history | +15 LOC |
| `backend/v9/systems/five_min/five_min_system.py` | constants + helper + 4 detector edits | +60 LOC, –7 LOC |
| `backend/v9/shared/tests/test_pre_fire_validator.py` | append 8 new tests | +80 LOC |
| `backend/v9/tests/test_footprint_system.py` | append 3 new tests | +50 LOC |
| `tests/atomic/test_five_min_patterns.py` | append ~9 tests + extend 3 existing fixtures to 7-bar | +180 LOC |

**Total estimated diff:** ~+385 LOC / –7 LOC across 5 files.

---

## §9 · One-paragraph for Claude Desktop mega prompt

> Implement Pkg 2bc (OFA Config + Validators) per `docs/handoff/DESKTOP_PKG2BC_OFA_CONFIG_HANDOFF.md`. Four parts: (A) S3 Footprint additive `_forces_history` of last 7 bars exposed via `current_state["forces_history"]` · (B) S2 Reactive + Initiative use externalized constants `DROP_THRESHOLD_PCT/EXPANSION_MIN_PT/EXPANSION_MAX_PT/POC_RETURN_TOLERANCE_PT/MIN_BARS_REQUIRED=7/LOOKBACK_BARS=3/LOOKBACK_MAX_VOL_RATIO=0.6/BELLY_DOMINANCE_RATIO=1.5` plus new helper `_get_belly_ratio_from_footprint(direction)` reading `forces_history[-2]` plus lookback check `max(bars[-7:-4].volume) < bars[-4].volume × 0.6` plus belly_dominance check `ratio ≥ 1.5` (graceful skip if history None) · (C) 8 new negative tests in `pre_fire_validator` for direction/confidence/time_stop/ordering edge cases · (D) ~9 new pattern tests + extend 3 existing positive tests to 7-bar fixtures with `forces_history` mock. Strict constraints: lines 205-207 byte-identical, no DLL/DB changes, S3 firing logic untouched, Pkg 1 + Pkg 2a tests all green. Tests-are-authority. Acceptance: ~29 + 18 + 14 + 13 + ≥517 passed · ReadLints clean · commit `feat(s2): OFA config + belly_dominance + lookback + validator tests per Pkg 2bc spec`.

---

*End of Pkg 2bc handoff · Cursor agent · 2026-05-23 20:30 IL*
