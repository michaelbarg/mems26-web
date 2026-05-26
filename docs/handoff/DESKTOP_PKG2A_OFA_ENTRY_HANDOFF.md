# Pkg 2a · OFA Entry Signal Fix — Handoff to Claude Desktop

**Date:** 2026-05-23 19:35 IL
**From:** Cursor agent
**To:** Claude Desktop (mega-prompt builder)
**Recipient of mega prompt:** Claude Code (CC)
**Spec authority:** `~/Downloads/S2_Master_Summary.xlsx` Sheet 2 (10 תבניות) · `docs/decisions/D-091_S2_LIVE_SCOPE.md` · `docs/spec_authority/MEMS26_CONSTITUTION_V3_FINAL.txt` §T1

---

## TL;DR for Claude Desktop

Pkg 2a is a **tight 3-change patch** to `backend/v9/systems/five_min/five_min_system.py`. No new modules. No new tests files — extend the existing `tests/atomic/test_five_min_patterns.py`. The patch:

1. **Reactive Entry signal** — add close-above-prior-bar-high check (currently missing · existing only checks bullish close).
2. **Initiative Entry signal** — add close-above-expansion-bar-high check (currently missing · existing only checks 4th-bar test ≥ Bar 2 extreme).
3. **Family mapping bug** absorbed from Pkg 1 G3 finding — `kind == "REACTIVE_LONG"` was checked but actual `kind` is `"REACTIVE"` (no `_LONG`/`_SHORT` suffix). Causes all Reactive trades to get `multiplier=1.5` (OFA) instead of `1.0`.

CC delivers all 3 in one commit. ReadLints clean. No regression on existing tests. 6+ new negative tests added.

---

## Scope reminder

Pkg 2a is **NOT**:

- ❌ Belly ratio config (= Pkg 2b)
- ❌ 7 validator checks expansion / drop threshold / cot window / amt window / etc. (= Pkg 2c)
- ❌ Stop anchor change (belly_low vs broken_level for Initiative · deferred to a later package)
- ❌ Pattern detection schema changes
- ❌ Layer 4 day-type targets (= Pkg 3a)

Pkg 2a is **ONLY**:
- ✅ Close-through-level entry confirmation (Reactive + Initiative · both directions)
- ✅ Family mapping bug fix (Pkg 1 absorb)

---

## 1 · Spec authority (verbatim)

### Source 1 · S2 Master Summary Sheet 2 (`~/Downloads/S2_Master_Summary.xlsx`)

Read rows 3-6 verbatim:

| # | Pattern | Entry signal (verbatim Hebrew → English) |
|---|---------|-------------------------------------------|
| 1 | Reactive LONG | "Close above bar -1 high · COT > AMT" |
| 2 | Reactive SHORT | "Close below bar -1 low · COT < AMT" |
| 3 | Initiative LONG | "Close above bar 0 high · expansion 6-7 ticks · COT" |
| 4 | Initiative SHORT | "Close below bar 0 low · COT > AMT" |

**Bar numbering convention (from Master Summary · spec authority):**
- `bar 0` = first bar of the 4-bar window (= `bars_5m[-4]` = current code's `b1`)
- `bar -1` = third bar = penultimate (= `bars_5m[-2]` = current code's `b3`)
- `bar 0` for Initiative refers to the **expansion bar** (the bar that broke the level by 6-7 ticks · which is bar 1 of the 4-bar window).

### Source 2 · Constitution V3 §T1 (`docs/spec_authority/MEMS26_CONSTITUTION_V3_FINAL.txt:59-82`)

Confirms the same 4-bar Reactive + Initiative spec but does NOT add the close-through-level check. Master Summary Sheet 2 is the **stricter spec** and is authoritative — close-through-level is the missing piece in current code.

### Source 3 · D-091 §Adaptive Stop Engine `ATR_MULTIPLIERS` (already shipped in Pkg 1)

```python
ATR_MULTIPLIERS = {
    "Reactive":  1.0,   # tight stops for rotation
    "OFA":       1.5,   # Initiative
    "Flag":      1.5,
    "Double_BT": 2.0,
    "HnS":       2.0,
}
```

The family mapping bug (current line 563) causes Reactive trades to receive `1.5×` instead of `1.0×` — they get **wider** adaptive_cap than spec, biasing Layer A binding more often than designed.

---

## 2 · Files and lines CC may touch

| File | Lines | Allowed action |
|------|-------|----------------|
| `backend/v9/systems/five_min/five_min_system.py` | 344-368 (`_detect_reactive`) | Add close-through-level checks |
| `backend/v9/systems/five_min/five_min_system.py` | 383-423 (`_detect_initiative`) | Add close-through-level checks |
| `backend/v9/systems/five_min/five_min_system.py` | 563 (family mapping) | Replace tuple check with `==` |
| `tests/atomic/test_five_min_patterns.py` | extend | Add 6 new negative tests |

**Files CC MUST NOT touch (anti-regression · per CLAUDE.md):**

- `backend/v9/systems/five_min/adaptive_stop.py` (Pkg 1 deliverable · locked)
- `backend/v9/systems/five_min/five_min_system.py` lines 1-15 (docstring · post-Pkg 1)
- `backend/v9/systems/five_min/five_min_system.py` lines 205-207 (chronic `chart_5min` comment · deferred to Pkg 2a-companion later · **NOT** this Pkg 2a)
- `backend/v9/systems/five_min/five_min_system.py` lines 558-580 (adaptive_stop integration block · only line 563 may change)
- `sc_study/`, `backend/main.py`, `backend/v9/app.py`, all other test files
- `docs/decisions/` (already locked)

🛑 **Lines 205-207 must remain byte-identical to HEAD.** Same forbid as Pkg 1.

---

## 3 · Concrete edits CC must make

### Edit 1 · `_detect_reactive` (line 344-368 currently)

**Before (current code):**
```python
        # Reactive LONG
        b1_sellers = b1["c"] < b1["o"] and b1_vol > 0
        b2_drop = b2_vol <= b1_vol * 0.10 if b1_vol > 0 else False
        b3_buyers = b3["c"] > b3["o"]
        b3_belly = belly is not False
        b4_confirm = b4["c"] > b4["o"]
        cot_above_amt = cur_cot > cur_amt
        poc_rising = self._poc_vol_rising(bars_5m[-3:])

        if b1_sellers and b2_drop and b3_buyers and b3_belly and b4_confirm and cot_above_amt:
            return ("LONG", 0.80 if poc_rising else 0.75,
                    {"kind": "REACTIVE", "stage": 4, "belly": belly, "poc_rising": poc_rising})

        # Reactive SHORT (mirror)
        b1_buyers = b1["c"] > b1["o"] and b1_vol > 0
        b3_sellers = b3["c"] < b3["o"]
        b4_confirm_s = b4["c"] < b4["o"]
        cot_below_amt = cur_cot < cur_amt
        poc_falling = self._poc_vol_falling(bars_5m[-3:])

        if b1_buyers and b2_drop and b3_sellers and b3_belly and b4_confirm_s and cot_below_amt:
            return ("SHORT", 0.80 if poc_falling else 0.75,
                    {"kind": "REACTIVE", "stage": 4, "belly": belly, "poc_falling": poc_falling})

        return (None, 0, {})
```

**After (with close-through-level entry signal · per Master Summary Sheet 2):**
```python
        # Reactive LONG
        b1_sellers = b1["c"] < b1["o"] and b1_vol > 0
        b2_drop = b2_vol <= b1_vol * 0.10 if b1_vol > 0 else False
        b3_buyers = b3["c"] > b3["o"]
        b3_belly = belly is not False
        b4_confirm = b4["c"] > b4["o"]
        b4_close_above_b3_high = b4["c"] > b3["h"]  # Entry signal per Master Summary Sheet 2
        cot_above_amt = cur_cot > cur_amt
        poc_rising = self._poc_vol_rising(bars_5m[-3:])

        if (b1_sellers and b2_drop and b3_buyers and b3_belly
                and b4_confirm and b4_close_above_b3_high and cot_above_amt):
            return ("LONG", 0.80 if poc_rising else 0.75,
                    {"kind": "REACTIVE", "stage": 4, "belly": belly, "poc_rising": poc_rising})

        # Reactive SHORT (mirror)
        b1_buyers = b1["c"] > b1["o"] and b1_vol > 0
        b3_sellers = b3["c"] < b3["o"]
        b4_confirm_s = b4["c"] < b4["o"]
        b4_close_below_b3_low = b4["c"] < b3["l"]  # Entry signal per Master Summary Sheet 2
        cot_below_amt = cur_cot < cur_amt
        poc_falling = self._poc_vol_falling(bars_5m[-3:])

        if (b1_buyers and b2_drop and b3_sellers and b3_belly
                and b4_confirm_s and b4_close_below_b3_low and cot_below_amt):
            return ("SHORT", 0.80 if poc_falling else 0.75,
                    {"kind": "REACTIVE", "stage": 4, "belly": belly, "poc_falling": poc_falling})

        return (None, 0, {})
```

### Edit 2 · `_detect_initiative` (line 383-423 currently)

**Before:**
```python
        if b1_bull and b1_expansion and b2_test and b3_joining and b4_test and cot_below_amt:
            return ("LONG", 0.80, {"kind": "INITIATIVE", "stage": 4,
                                   "b2_alt": "poc_return" if b2_poc_return else "higher_low"})

        # Initiative SHORT (mirror)
        b1_bear = b1["c"] < b1["o"]
        b2_lower_high = b2["h"] < b1["h"]
        b2_poc_return_s = b2_poc is not None and abs(b2["c"] - b2_poc) <= 0.5
        b2_test_s = b2_lower_high or b2_poc_return_s
        b4_test_s = b4["h"] <= b2["h"]
        cot_above_amt = cur_cot > cur_amt

        if b1_bear and b1_expansion and b2_test_s and b3_joining and b4_test_s and cot_above_amt:
            return ("SHORT", 0.80, {"kind": "INITIATIVE", "stage": 4,
                                    "b2_alt": "poc_return" if b2_poc_return_s else "lower_high"})

        return (None, 0, {})
```

**After (with close-above-bar-0-high entry signal · per Master Summary Sheet 2 row 5/6):**
```python
        b4_close_above_b1_high = b4["c"] > b1["h"]  # Entry signal per Master Summary Sheet 2

        if (b1_bull and b1_expansion and b2_test and b3_joining and b4_test
                and b4_close_above_b1_high and cot_below_amt):
            return ("LONG", 0.80, {"kind": "INITIATIVE", "stage": 4,
                                   "b2_alt": "poc_return" if b2_poc_return else "higher_low"})

        # Initiative SHORT (mirror)
        b1_bear = b1["c"] < b1["o"]
        b2_lower_high = b2["h"] < b1["h"]
        b2_poc_return_s = b2_poc is not None and abs(b2["c"] - b2_poc) <= 0.5
        b2_test_s = b2_lower_high or b2_poc_return_s
        b4_test_s = b4["h"] <= b2["h"]
        b4_close_below_b1_low = b4["c"] < b1["l"]  # Entry signal per Master Summary Sheet 2
        cot_above_amt = cur_cot > cur_amt

        if (b1_bear and b1_expansion and b2_test_s and b3_joining and b4_test_s
                and b4_close_below_b1_low and cot_above_amt):
            return ("SHORT", 0.80, {"kind": "INITIATIVE", "stage": 4,
                                    "b2_alt": "poc_return" if b2_poc_return_s else "lower_high"})

        return (None, 0, {})
```

### Edit 3 · Family mapping fix (line 563 currently)

**Before:**
```python
            family = "Reactive" if kind in ("REACTIVE_LONG", "REACTIVE_SHORT") else "OFA"  # Initiative → OFA
```

**After:**
```python
            # Map detector `kind` ("REACTIVE" / "INITIATIVE") to D-091 family taxonomy.
            family = "Reactive" if kind == "REACTIVE" else "OFA"  # INITIATIVE → OFA family (D-091)
```

**Rationale:** `_detect_reactive` returns `kind="REACTIVE"` (line 355, 366). `_detect_initiative` returns `kind="INITIATIVE"` (line 408, 420). The tuple `("REACTIVE_LONG", "REACTIVE_SHORT")` never matches → all trades got `family="OFA"` → all stops used `1.5× today_typical` instead of `1.0×` for Reactive. Fix: simple `==` check.

---

## 4 · Tests CC must add (extend `tests/atomic/test_five_min_patterns.py`)

CC must extend the existing test classes with **6 new negative tests**. These verify that the close-through-level check actually gates fires:

| # | Test name | Setup | Expected |
|---|-----------|-------|----------|
| 1 | `test_reactive_long_rejected_when_b4_close_below_b3_high` | All current `test_reactive_long` inputs · but `b4.close = 5248.75` (= b3 high · NOT above it) | `direction is None` (no fire) |
| 2 | `test_reactive_short_rejected_when_b4_close_above_b3_low` | All current `test_reactive_short` inputs · but `b4.close = 5247.25` (= b3 low · NOT below it) | `direction is None` |
| 3 | `test_initiative_long_rejected_when_b4_close_below_b1_high` | All current `test_initiative_long` inputs · but `b4.close = 5248.50` (= b1 high · NOT above it) | `direction is None` |
| 4 | `test_initiative_short_rejected_when_b4_close_above_b1_low` | Mirror of #3 for SHORT | `direction is None` |
| 5 | `test_reactive_long_fires_when_b4_close_above_b3_high` | Existing positive test (regression confirmation) | `direction == "LONG"` |
| 6 | `test_initiative_long_fires_when_b4_close_above_b1_high` | Existing positive test (regression confirmation) | `direction == "LONG"` |

**Family mapping unit test (separate · new class):**

```python
class TestFamilyMapping:
    """Pkg 2a · family mapping fix for adaptive_stop integration."""

    def test_reactive_kind_maps_to_reactive_family(self):
        """REACTIVE detector → 'Reactive' family (multiplier 1.0)."""
        kind = "REACTIVE"
        family = "Reactive" if kind == "REACTIVE" else "OFA"
        assert family == "Reactive"

    def test_initiative_kind_maps_to_ofa_family(self):
        """INITIATIVE detector → 'OFA' family (multiplier 1.5)."""
        kind = "INITIATIVE"
        family = "Reactive" if kind == "REACTIVE" else "OFA"
        assert family == "OFA"

    def test_unknown_kind_falls_back_to_ofa(self):
        """Defensive: unknown kind → 'OFA' (wider stop, safer)."""
        kind = "UNKNOWN_FUTURE"
        family = "Reactive" if kind == "REACTIVE" else "OFA"
        assert family == "OFA"
```

**Integration test (verifies the fix reaches adaptive_stop):**

```python
class TestFamilyIntegratesWithAdaptiveStop:
    """Pkg 2a × Pkg 1 · Reactive trade gets correct multiplier downstream."""

    def test_reactive_family_yields_correct_multiplier(self):
        from backend.v9.systems.five_min.adaptive_stop import ATR_MULTIPLIERS
        assert ATR_MULTIPLIERS["Reactive"] == 1.0  # D-091 Master Sheet 4

    def test_ofa_family_yields_correct_multiplier(self):
        from backend.v9.systems.five_min.adaptive_stop import ATR_MULTIPLIERS
        assert ATR_MULTIPLIERS["OFA"] == 1.5
```

---

## 5 · Golden fixture arithmetic (CC must verify)

### Existing positive tests · MUST still pass after Pkg 2a edits

| Test | Critical close comparison | Result |
|------|---------------------------|--------|
| `test_reactive_long` | `b4.close=5249.75 > b3.high=5249` | TRUE · still fires ✅ |
| `test_reactive_short` | `b4.close=5246.50 < b3.low=5247` | TRUE · still fires ✅ |
| `test_initiative_long` | `b4.close=5249 > b1.high=5248.75` | TRUE · still fires ✅ |

If any existing positive test starts failing → STOP and report (numeric mismatch · spec violation).

### New negative tests · CC must construct fixtures

| Test | Required arithmetic | Why |
|------|---------------------|-----|
| `#1 reactive_long_rejected` | `b4.close == b3.high` (e.g. both = 5249) | edge case · close equal to prior high should NOT fire |
| `#2 reactive_short_rejected` | `b4.close == b3.low` | mirror |
| `#3 initiative_long_rejected` | `b4.close == b1.high` | edge case for Initiative |
| `#4 initiative_short_rejected` | `b4.close == b1.low` | mirror |

**Note on edge semantics:** The spec says "close ABOVE bar high" (strict `>`), so `b4.close == b3.high` → fire rejected. Use strict `>` everywhere · no `>=`.

---

## 6 · API contract — no public-API changes

Pkg 2a does NOT change any public method signature:
- `_detect_reactive(bars_5m: List[Dict]) -> tuple` (unchanged)
- `_detect_initiative(bars_5m: List[Dict]) -> tuple` (unchanged)
- All return shapes preserved.

No new exports. No new modules. No new dependencies.

---

## 7 · Acceptance criteria (G4 UAT)

CC must self-verify:

- ✅ `pytest tests/atomic/test_five_min_patterns.py -q` exit 0 · all 8+ tests pass (4 existing + 4+ new negative + family mapping class)
- ✅ `pytest tests/v9/systems/test_five_min/ -q` exit 0 (Pkg 1 adaptive_stop tests still green)
- ✅ `pytest backend/v9/tests/ -q` exit 0 (no regression on other tests)
- ✅ `BRIDGE_TOKEN=dummy python3 -c "from backend.v9.systems.five_min.five_min_system import FiveMinSystem; FiveMinSystem()"` succeeds
- ✅ ReadLints clean (1 file modified · 1 file extended)
- 🛑 **Lines 205-207 byte-identical to HEAD** · `git diff HEAD -- backend/v9/systems/five_min/five_min_system.py | grep -E "^[+-].*(chronic|toxicity)"` returns 0 hits
- ✅ All 3 edits applied (no partial · no skipped)
- ✅ No new dependencies
- ✅ App boot smoke · 5 systems still register

---

## 8 · Constraints (must not violate)

- **No silent excepts** — same Pkg 1 rule
- **No hardcoded magic numbers** — use named locals (`b4_close_above_b3_high`)
- **No `>=` instead of `>`** — spec is strict
- **Maintain Path A canonical** — no imports from deleted `chart_5min/`
- 🛑 **Do NOT touch lines 205-207 of `five_min_system.py`** — same Pkg 1 forbid
- **Do NOT modify any other files in `five_min/`** beyond what's specified in §2
- 🛑 **Do NOT change the structural anchor used by `adaptive_stop.compute_stop()` in line 559** — that change is deferred to a later package. Pkg 2a leaves `structural_anchor = bar.get("l", entry_price)` (LONG) unchanged. Only line 563 (family mapping) is touched in the adaptive_stop block.
- 🛑 **Spec is authority. If existing positive tests break after edits, STOP and report** — do not adjust fixtures to make tests pass (that would be hiding spec violations).

---

## 9 · Stop signal triggers

CC must STOP and report (NOT guess) if:

- Existing positive tests (`test_reactive_long`, `test_reactive_short`, `test_initiative_long`) start failing — STOP, report fixture numerics, do NOT adjust fixtures.
- Line 563 family mapping after fix yields any test failure that requires more than the `==` change to fix.
- `_detect_reactive` or `_detect_initiative` signature has shifted from HEAD · STOP and report new line numbers.
- Lines 205-207 were modified by accident — STOP, `git checkout HEAD -- backend/v9/systems/five_min/five_min_system.py`, re-apply edits surgically, retry.
- Master Summary Sheet 2 spec contradicts Constitution V3 §T1 in a way that affects the entry signal definition — STOP and report (Sheet 2 wins per D-091 §Source quality, but the conflict needs Michael's review).

Output format on STOP: `"STOP — <reason> · need Michael decision on <specific question>"`

---

## 10 · Deliverable format CC must produce

1. **Files modified** (full paths · M):
   - `backend/v9/systems/five_min/five_min_system.py` (lines 344-368, 383-423, 563)
   - `tests/atomic/test_five_min_patterns.py` (extended)
2. **Commit message:** `feat(s2): OFA entry signal close-through-level + family mapping fix per Master Sheet 2`
3. **pytest output tail** (last 30 lines · including new test names + counts)
4. **Boot smoke** output: 5 systems still register
5. **Self-report:**
   - All 3 edits applied? (yes/no per edit)
   - Any spec ambiguity encountered? (list)
   - Any forbidden constraint accidentally violated? (own up)
6. **ReadLints output** (paste verbatim)
7. **Sample diff verification:**
   - Show `git diff HEAD -- backend/v9/systems/five_min/five_min_system.py` chronic/toxicity grep returns 0 hits
   - Show lines 205-207 are byte-identical to HEAD

---

## 11 · Desktop's deliverable

Desktop, please produce a single MEGA prompt for CC following `docs/templates/MEGA_PROMPT_TEMPLATE.md`.

Use this handoff as the spec authority. Inline:
- `backend/v9/systems/five_min/five_min_system.py` lines 316-423 (the two detector methods · for CC's context)
- `backend/v9/systems/five_min/five_min_system.py` lines 555-580 (the adaptive_stop integration · for the line 563 fix)
- `tests/atomic/test_five_min_patterns.py` lines 1-90 (existing tests · for CC to extend)
- `docs/decisions/D-091_S2_LIVE_SCOPE.md` §Adaptive Stop Engine (for ATR_MULTIPLIERS reference)
- This handoff as the directive

**Length expectation:** ~400-500 lines (less than Pkg 1 since 3 small edits not a new module).

**Quality bar:** same as Pkg 1 — "TESTS ARE AUTHORITY · spec is illustrative · if conflict, tests win" applies, but here the SPEC is unambiguous (Master Summary Sheet 2 is verbatim) so tests should pass without ambiguity.

---

*End of handoff · Cursor agent · 2026-05-23 19:35 IL*
