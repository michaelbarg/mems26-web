# DESKTOP_PHASE_A_CONSOLIDATION_STALE_FIXTURES_HANDOFF · Cursor → Claude Desktop → CC

**Date:** 2026-05-25 14:55 IL · **Owner draft:** Cursor · **Reviewer:** Michael Barg
**Package:** Phase A Consolidation · **Stale-fixture test repair** (6 failures · deferred from B2 25/5 13:35)
**Branch:** `stabilize/mems26-local-truth-2026-05-16` · HEAD `e7094d3`
**Phase A status:** 14/15 done · this is the **15th and FINAL** package before Phase A → Phase B
**Estimated CC time:** ~30-45 min (tests-only · zero production-code changes)

---

## 0 · Cursor verify-first audit (25/5 14:50 IL)

CC must trust these locks · they are verified against live code/tests.

| # | Lock | Evidence |
|---|---|---|
| 1 | Root cause **confirmed**: production detectors require 7 bars (4 pattern + 3 lookback) but the 3 test files supply only 4 bars | `backend/v9/systems/five_min/five_min_system.py:30` defines `MIN_BARS_REQUIRED: int = 7` · lines 407, 484 short-circuit detectors when `len(bars_5m) < 7` |
| 2 | The 3 lookback bars (`bars_5m[-7:-4]`) must satisfy: (a) `b.get("v", 0) > 0` for all 3, (b) `max(lookback.volume) < b1.volume * LOOKBACK_MAX_VOL_RATIO=0.6` | `five_min_system.py:31-32` + lines 433-437 (`_detect_reactive`) + lines 511-515 (`_detect_initiative`) |
| 3 | This is a **tests-only fix**. Production code (`five_min_system.py` + `setup_emitter.py` + detectors) is correct — the fixtures are stale (pre-Pkg 2bc · before lookback was added) | git history: `MIN_BARS_REQUIRED=7` introduced in Pkg 2bc (commit `dfdf91f` · 23/5 20:46) · these tests predate that change |
| 4 | Zero functional change to production code. Zero new tests · just extending existing fixtures by 3 bars each | scope §3 below |
| 5 | Pkg 6 G3 baseline (HEAD `e7094d3`): `30 failed / 1562 passed` in `tests/v9/ --ignore=api`. The 6 failures here are NOT in that sweep — they live in `backend/v9/systems/five_min/tests/` (different test root) | `pytest backend/v9/systems/five_min/tests/test_e2e_t1.py test_poc_return_alt.py test_process_bar_emission.py -q` → `6 failed / 12 passed` at HEAD |

---

## 1 · Exact 6 failing tests (verbatim · paste into `pytest -v` to verify)

```
backend/v9/systems/five_min/tests/test_e2e_t1.py::TestE2EScenarios::test_reactive_long_full_pipeline
backend/v9/systems/five_min/tests/test_e2e_t1.py::TestE2EScenarios::test_reactive_short_mirror
backend/v9/systems/five_min/tests/test_e2e_t1.py::TestE2EScenarios::test_initiative_long_fires
backend/v9/systems/five_min/tests/test_e2e_t1.py::TestE2EScenarios::test_initiative_long_poc_return_alt
backend/v9/systems/five_min/tests/test_poc_return_alt.py::TestPocReturnAlt::test_initiative_long_poc_return
backend/v9/systems/five_min/tests/test_process_bar_emission.py::test_process_bar_emits_setup_on_pattern_match
```

All 6 fail because `_detect_reactive(bars)` or `_detect_initiative(bars)` is called with `len(bars)==4` → detector returns `(None, 0, {})` at line 407/484 due to `len < MIN_BARS_REQUIRED=7`.

---

## 2 · Production code (READ-ONLY · do NOT modify)

### 2.1 · `backend/v9/systems/five_min/five_min_system.py` (lookback contract · lines 30-32 + 407-437 + 484-515)

```python
MIN_BARS_REQUIRED: int = 7                     # 4 pattern + 3 lookback (Pkg 2bc)
LOOKBACK_BARS: int = 3                         # bars before bar 1 to check "normal" volume
LOOKBACK_MAX_VOL_RATIO: float = 0.6            # max(lookback_3bars.volume) / bar1.volume < this
```

Both `_detect_reactive(bars_5m)` and `_detect_initiative(bars_5m)` enforce:
- `if len(bars_5m) < MIN_BARS_REQUIRED: return (None, 0, {})`
- `lookback = bars_5m[-MIN_BARS_REQUIRED:-(MIN_BARS_REQUIRED - LOOKBACK_BARS)]` → 3 bars (indices -7, -6, -5)
- `all(b.get("v", 0) > 0 for b in lookback)` — all 3 lookback bars must have positive volume
- `max(lookback.volume) < b1_vol * LOOKBACK_MAX_VOL_RATIO` — lookback "quiet" relative to b1

**CC MUST NOT touch any production file under `backend/v9/systems/five_min/` outside the `tests/` subdir.**

---

## 3 · SCOPE — exactly these 3 files

CC modifies ONLY the 3 test files. Zero production code. Zero new files.

### MODIFY · `backend/v9/systems/five_min/tests/test_e2e_t1.py`

Three fixtures + one inline bar list need 3 "quiet" lookback bars prepended:

| Fixture / inline | Location | Current b1.volume | Required lookback `v` per bar |
|---|---|---|---|
| `_bars_reactive_long()` | lines 24-30 | `v=1000` (line 26) | `v=300` per bar (300 < 0.6×1000=600) |
| inline `bars` in `test_reactive_short_mirror` | lines 81-86 | `v=1000` (line 82) | `v=300` per bar |
| `_bars_initiative_long()` | lines 33-39 | `v=600` (line 35) | `v=200` per bar (200 < 0.6×600=360) |
| inline `bars` in `test_initiative_long_poc_return_alt` | lines 104-109 | `v=600` (line 105) | `v=200` per bar |

**OHLC for lookback bars:** use plausible flat candles below the pattern's b1.open to avoid disturbing other pattern checks (b1_sellers vs b1_buyers semantic). Recommended pattern: 3 bars with `o=h=l=c=<price 1-2pt below b1.open>` (zero-range "doji" with the chosen volume). Example for Reactive LONG where b1.open=5250:
```python
{"o": 5249, "h": 5249, "l": 5249, "c": 5249, "v": 300},
{"o": 5249, "h": 5249, "l": 5249, "c": 5249, "v": 300},
{"o": 5249, "h": 5249, "l": 5249, "c": 5249, "v": 300},
```

### MODIFY · `backend/v9/systems/five_min/tests/test_poc_return_alt.py`

| Fixture / inline | Location | Current b1.volume | Required lookback |
|---|---|---|---|
| inline `bars` in `test_initiative_long_poc_return` | lines 21-27 | `v=600` (line 22) | 3 bars with `v=200` |

Note: the OTHER test in this file (`test_initiative_long_no_hl_no_poc_fails` lines 34-44) **must also be extended** with 3 lookback bars · otherwise the assertion `direction is None` will pass for the WRONG reason (length-gate instead of pattern-fail). The test currently passes accidentally · CC must extend it too so the test actually verifies the pattern-fail path.

### MODIFY · `backend/v9/systems/five_min/tests/test_process_bar_emission.py`

| Fixture / inline | Location | Current b1.volume | Required lookback |
|---|---|---|---|
| `_reactive_long_bars()` | lines 8-15 | `v=1000` (line 11) | 3 bars with `v=300` prepended |

Both tests that pre-load via `sys._bar_buffer = _reactive_long_bars()[:-1]` (`test_process_bar_emits_setup_on_pattern_match` line 38 and `test_process_bar_handles_emitter_exception` line 59) will automatically benefit — once the fixture returns 7 bars, `[:-1]` is 6 bars in buffer, `process_bar(bars[-1])` brings buffer to 7 → detector fires.

### FORBIDDEN — do NOT touch

```text
backend/v9/systems/five_min/five_min_system.py        # Production detectors
backend/v9/systems/five_min/setup_emitter.py          # Emitter logic
backend/v9/systems/five_min/quality_tier.py           # Pkg 8 (Quality V2)
backend/v9/systems/five_min/auth_table_v1.py          # Pkg 8 Auth Table
backend/v9/systems/five_min/patterns/                 # Pattern detectors
backend/v9/systems/day_type/                          # S1 Day Type system
backend/v9/services/                                  # All services (incl. Pkg 6 rules + TrailEngine)
backend/v9/systems/woodies/                           # Pipeline 2
backend/v9/systems/footprint/                         # Pipeline 4
frontend/ sc_study/ bridge/                           # Out of scope
backend/v9/db/                                        # No schema changes
tests/v9/                                             # Different test root (Pkg 6 + Pkg 8 lives there)
```

---

## 4 · Acceptance criteria

| # | Criterion | Verify |
|---|---|---|
| 1 | All 6 originally-failing tests PASS | `pytest backend/v9/systems/five_min/tests/test_e2e_t1.py backend/v9/systems/five_min/tests/test_poc_return_alt.py backend/v9/systems/five_min/tests/test_process_bar_emission.py -v` → 18 passed / 0 failed |
| 2 | No new regressions in same dir | `pytest backend/v9/systems/five_min/tests/ -q` → no NEW failures vs HEAD `e7094d3` baseline (`6 failed / 12 passed` in those 3 files at HEAD) |
| 3 | No new regressions in broader v9 sweep | `pytest tests/v9/ --ignore=tests/v9/api -q` → exactly `30 failed / 1562 passed` (same as Pkg 6 G3 baseline) |
| 4 | No production-code changes | `git diff --stat e7094d3..HEAD backend/v9/ -- ':!backend/v9/systems/five_min/tests/'` → empty (0 production files touched) |
| 5 | Only 3 test files modified | `git diff --name-only e7094d3..HEAD` → exactly the 3 files in §3 (+ optionally STATUS_BOARD if CC chose to add an entry) |
| 6 | ReadLints clean on the 3 modified test files | paste output |
| 7 | Pattern semantics preserved · the lookback bars don't disturb b1_sellers/b1_buyers/b2_drop checks · just satisfy length + volume invariants | inspect new fixtures · 3 bars are zero-range "doji" with low volume · don't introduce new patterns |

---

## 5 · Constraints (must not violate · pre-LIVE protocol)

- **Tests-only fix.** Zero production code changes. If you find a real bug in production code, STOP and report — do not "fix while here" (pre-LIVE protocol Rule 5).
- **Preserve test intent.** The 4 pattern bars in each fixture stay verbatim — they encode the exact reactive/initiative pattern recipe. Only PREPEND 3 lookback bars.
- **Lookback `volume` MUST be `< b1.volume * 0.6`** (verify each: `v=300` for `b1.v=1000`, `v=200` for `b1.v=600`).
- **Lookback `volume` MUST be `> 0`** (the `all(b.get("v", 0) > 0)` check rejects zero-volume bars).
- **OHLC of lookback bars** should be neutral (zero range or tiny range · doesn't trigger any pattern hint). Recommended: `{"o": X, "h": X, "l": X, "c": X, "v": <vol>}` where X is 1-2pt below b1.open.
- **No imports added** to the 3 test files. Use existing imports.
- **No `assert` modifications** in any of the 6 fixed tests · the existing assertions must continue to pass once detector receives 7 bars.
- **No new helper functions** unless absolutely required (e.g., a single `_lookback_bars(b1_vol, base_price)` helper is OK if used in 3+ places — but inlining is simpler for 3-4 files).
- **Commit message MUST include:** `Phase A Consolidation · stale-fixture repair · tests-only · zero production diff`.

---

## 6 · Allowed imports (whitelist)

The 3 test files already import everything they need. **CC must NOT add any new import** unless writing the optional `_lookback_bars()` helper (which doesn't need new imports anyway).

If touching `test_e2e_t1.py`: current imports at top (pytest · datetime · zoneinfo · unittest.mock · FiveMinSystem · emit_t1_setup · sr_proximity · q0_dispatcher · first_hour_buffer · first_hour_matrix · choppiness · confluence · pre_fire_validator) — keep verbatim.

---

## 7 · Deliverable format (CC self-report)

After completion, CC outputs:

1. **Files changed:**
   - M · `backend/v9/systems/five_min/tests/test_e2e_t1.py` (~12 LOC added · 3 fixtures + 1 inline list extended)
   - M · `backend/v9/systems/five_min/tests/test_poc_return_alt.py` (~6 LOC added · 2 inline lists extended)
   - M · `backend/v9/systems/five_min/tests/test_process_bar_emission.py` (~3 LOC added · 1 fixture extended)

2. **Commit message** (verbatim):
   ```
   fix(test): Phase A Consolidation · stale-fixture repair · prepend 3 lookback bars to 6 stale fixtures (post-Pkg-2bc 7-bar contract) · tests-only · zero production diff
   ```

3. **Self-report:**
   - Confirm zero production-code touched: `git diff --name-only` shows only 3 test files
   - LOC added (total across 3 files)
   - Any TODOs left in code? (must be empty)
   - Any spec ambiguity encountered? (list explicitly · STOP signal if blocked)
   - Optional: did you extract a `_lookback_bars()` helper? If yes, where?

4. **ReadLints output** (paste verbatim · 3 modified files)

5. **pytest outputs** (paste verbatim · tail 20 lines):
   - `pytest backend/v9/systems/five_min/tests/test_e2e_t1.py backend/v9/systems/five_min/tests/test_poc_return_alt.py backend/v9/systems/five_min/tests/test_process_bar_emission.py -v`
   - `pytest backend/v9/systems/five_min/tests/ -q` (broader subdir sweep)
   - `pytest tests/v9/ --ignore=tests/v9/api -q` (must show same `30 failed / 1562 passed` as Pkg 6 G3 baseline)

---

## 8 · Stop signal

IF any condition met, STOP and output `STOP — <reason> · need Michael decision on <specific question>`:

- Any FORBIDDEN file (§3) appears in your edit list · STOP
- A test you fix starts failing for a DIFFERENT reason (not stale fixture) · STOP and report (could be real regression hidden by length-gate)
- `pytest tests/v9/ --ignore=tests/v9/api -q` count drifts from `30 failed / 1562 passed` · STOP (introduced regression)
- The lookback `v` value you chose makes `lookback_quiet` False even though it satisfies the volume ratio · STOP and inspect `_detect_reactive`/`_detect_initiative` source
- Pattern OHLC checks (b1_sellers · b2_drop · b3_buyers · b4_confirm) start failing AFTER prepending lookback · STOP (lookback bars contaminated the b1_vol calculation somehow)
- `test_initiative_long_no_hl_no_poc_fails` (in `test_poc_return_alt.py`) starts passing for the WRONG reason after extension · STOP and verify it now exercises the pattern-fail path, not the length-gate

**DO NOT guess. DO NOT add a comment "TODO: ask Michael".**

---

## 9 · Phase A completion outlook

After this Pkg G3 PASS:

- **Phase A: 15/15 done** (13 GREEN + 2 deferred per D-095)
- All Phase A test failures cleaned up → clean baseline for SHADOW gate
- Next steps: G4 UAT (Pkg 6 + Pkg 8 · `/cockpit/systems-snapshot` during RTH) · then Phase A → Phase B transition decision

Cursor will write G3 report `docs/reports/PHASE_A_CONSOLIDATION_G3_PASS_2026-05-25.md` after CC delivers.

---

## 10 · Authority & references

- **Pkg 2bc · 7-bar contract origin:** commit `dfdf91f` (23/5 20:46) — introduced `MIN_BARS_REQUIRED=7` + lookback
- **B2 test cleanup decision:** STATUS_BOARD amendment 25/5 13:35 (deferred 6 stale-fixture failures to "Phase A Consolidation Pkg")
- **Pkg 6 G3 baseline reference:** `docs/reports/PKG6_G3_PASS_2026-05-25.md` + STATUS_BOARD amendment 25/5 14:35
- **Pre-LIVE protocol:** `.cursor/rules/mems26-pre-live-protocol.mdc` (verify-first · smallest correct change · no while-I'm-here refactors)

---

*End of handoff · ready for Claude Desktop to convert into final CC mega-prompt · 2026-05-25 14:55 IL Cursor*
