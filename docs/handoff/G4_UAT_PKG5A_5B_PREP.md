# G4 UAT prep · Pkg 5a (Inv H&S + H&S Top) + Pkg 5b (Double Bottom/Top)

**Date drafted:** 2026-05-24 20:20 IL · **Owner:** Cursor (prep) → Michael (execute)
**Predecessor:** Pkg 5a `7ffab50` (G3 PASS 24/5 17:45) + Pkg 5b `2c001a2` (G3 PASS 24/5 18:50)
**Status:** ⬜ G4 pending Michael smoke trade
**Estimated execution time:** ~45 min (4 smoke scenarios × ~10 min each + verification)

---

## §0 · TL;DR

Pkg 5a + 5b are **emit-only chart pattern detectors** (Pkg 6 will enforce
trail logic later). G4 UAT validates that the detectors produce
end-to-end correct payloads through the chain:

`FiveMinSystem.process_bar(breakout_bar)` → detector fires →
`compute_stop` builds family-aware stop → setup_emitter builds T1Setup
(with day-type-aware T3 logic OFF for these patterns · trail per Pkg 6)
→ `V9FiveMinSetup` row written → Gateway records the trade.

**The four UAT axes (mandatory · all 4 must be green):**

| Axis | What we verify | Threshold |
|------|----------------|-----------|
| **Quality** | Each pattern detects correctly on a known shape · false positives rejected | 4/4 positive fixtures fire + 4/4 negative fixtures reject |
| **Recency** | Pattern fires on the same bar as the breakout close (no lag) | T1Setup `ts` == breakout bar `ts` (± 0 ms) |
| **Cardinality** | One T1Setup per pattern instance · no double-emit on follow-up bars | exactly 1 row in `v9_five_min_setups` per shape |
| **Latency** | `process_bar` with all 6 pattern detectors in chain completes under budget | p95 < 50ms · p99 < 80ms over 100 calls |

---

## §1 · What's in scope

### Pkg 5a (commit `7ffab50`)
- `detect_inverse_hns(bars)` → LONG · returns `(direction, conf, info)`
- `detect_hns_top(bars)` → SHORT · symmetric mirror
- Targets: T1 = entry ± 0.50 × pattern_measure · T2 = ± 0.74 × pm · T3 = None (trail)
- Stop family: `HnS` (3-layer adaptive · structural_anchor = shoulder pivot ± 1T)
- Day-type gate: NeuE / NeuC / Norm / NV

### Pkg 5b (commit `2c001a2`)
- `detect_double_bottom_ee(bars)` → LONG · Eve&Eve (wide troughs)
- `detect_double_top_aa(bars)` → SHORT · Adam&Adam (sharp peaks)
- Targets:
  - Double Bottom EE: T1 = +0.50 × pm · T2 = +0.66 × pm (haircut) · T3 = None
  - Double Top AA: T1 = -0.50 × pm · T2 = -0.74 × pm (haircut) · T3 = None
- Stop family: `Double_BT` (2.0× ATR cap)
- Day-type gate: same 4 day types as 5a

### NOT in scope (deferred)
- Pkg 5c Flags G4 — separate report
- Trail enforcement (Pkg 6 territory)
- SHADOW soak metrics (G5 — runs after G4 green)

---

## §2 · Four UAT axes — concrete scenarios

### §2.1 · Quality (4/4 positive + 4/4 negative · 8 scenarios)

**Positive fixtures** (must fire):

| # | Pattern | Fixture | Expected direction | Expected conf | Expected pm |
|---|---------|---------|---------------------|---------------|-------------|
| Q1 | Inv H&S | `_build_inverse_hns_bars(ls_low=4500, head_low=4490, rs_low=4500)` | LONG | ≥ 0.7 | ≈ 20.0 |
| Q2 | H&S Top | `_build_hns_top_bars(ls_high=4500, head_high=4510, rs_high=4500)` | SHORT | ≥ 0.7 | ≈ 20.0 |
| Q3 | Double Bottom EE | `_build_double_bottom_bars(...)` from `test_double_bt.py` (use the "classic" fixture) | LONG | ≥ 0.7 | per fixture |
| Q4 | Double Top AA | `_build_double_top_bars(...)` from `test_double_bt.py` (use the "classic" fixture) | SHORT | ≥ 0.7 | per fixture |

**Negative fixtures** (must reject · return `(None, 0, {})`):

| # | Pattern | Fixture | Expected |
|---|---------|---------|----------|
| Q5 | Inv H&S | Asymmetric shoulders (`ls_low=4500, head_low=4490, rs_low=4505` · 10% diff > 5%) | None |
| Q6 | H&S Top | Head not extending beyond shoulders (`head_high=4502` only +2T) | None |
| Q7 | Double Bottom EE | Adam variant (V-shaped trough · width=1 bar) | None |
| Q8 | Double Top AA | Eve variant (rounded peak · width=4 bars) | None |

**Execution:** existing 16+16 golden tests already cover Q1–Q8. **For G4 we
re-run them with `-v` to confirm zero regressions post-merge:**

```bash
pytest tests/v9/systems/test_five_min/test_head_shoulders.py -v
pytest tests/v9/systems/test_five_min/test_double_bt.py -v
```

Expected output: 16 + 16 = **32 tests · all green**. Capture `stdout` to
`docs/reports/G4_UAT_PKG5A_5B_AXIS1_QUALITY.txt`.

### §2.2 · Recency (4 scenarios · breakout bar `ts` propagation)

Verify that `T1Setup.ts` (the emitted setup timestamp) equals the
breakout-bar timestamp · NOT the timestamp of detection runtime.

```python
# Pseudo-test for each pattern · run via pytest or one-shot script
import time
from backend.v9.systems.five_min.five_min_system import FiveMinSystem
from backend.v9.systems.five_min.five_min_system import FiveMinMode

fm = FiveMinSystem()
fm.mode = FiveMinMode.DAY_TYPE_MODE
fm.current_day_type = "Variation"  # tradable for chart patterns

bars = _build_inverse_hns_bars(ls_low=4500, head_low=4490, rs_low=4500)
# Pre-seed buffer with all bars except the last (breakout)
fm._bar_buffer = bars[:-1]
breakout_bar = bars[-1]
breakout_bar["ts"] = 1748208900  # specific known epoch · 2026-05-25 17:35 UTC

# Inject NOW timestamp delay to prove ts comes from bar · not clock
time.sleep(2.0)  # 2 sec delay before process_bar call
asyncio.run(fm.process_bar(breakout_bar))

# Query DB for the just-written V9FiveMinSetup row
setup = db.query(V9FiveMinSetup).order_by(V9FiveMinSetup.id.desc()).first()

# AXIS: setup.ts must equal breakout_bar["ts"] · NOT 2 sec later
assert int(setup.ts.timestamp()) == 1748208900, (
    f"RECENCY FAIL: setup.ts={setup.ts.timestamp()} != bar.ts=1748208900 "
    f"(delta={setup.ts.timestamp() - 1748208900:.1f}s)"
)
```

Run this for all 4 patterns: Inv H&S · H&S Top · Double Bottom EE · Double
Top AA. Expected: all 4 deltas == 0.0 seconds (or < 1ms float jitter).

**⚠️ KNOWN GAP:** `five_min_system.py:771` currently uses
`datetime.now(timezone.utc)` for `setup.ts`. If this UAT fails, that line
must change to use `bar["ts"]` — file a Pkg 5a/5b hotfix before G4 green.

### §2.3 · Cardinality (no double-emit · 4 scenarios)

For each of the 4 patterns: after the breakout bar fires and one
`V9FiveMinSetup` row is written, simulate 3 follow-up bars (no new
pattern emerges). Confirm:

1. Only 1 row in `v9_five_min_setups` for this pattern instance
2. `last_pattern` on the FiveMinSystem stays `<pattern>_<direction>`
3. Subsequent `process_bar` calls do NOT re-fire the same pattern

```python
# Pre-seed + breakout
fm._bar_buffer = bars[:-1]
asyncio.run(fm.process_bar(bars[-1]))  # FIRE bar
count_after_fire = db.query(V9FiveMinSetup).filter_by(
    pattern=f"{kind}_{direction}").count()
assert count_after_fire == 1

# 3 follow-up bars (price continuing in direction · no new pattern)
follow_ups = [
    {"o": 4515, "h": 4516, "l": 4514, "c": 4515.5, "v": 1000, "ts": ...},
    {"o": 4515.5, "h": 4517, "l": 4515, "c": 4516.5, "v": 1100, "ts": ...},
    {"o": 4516.5, "h": 4518, "l": 4516, "c": 4517.5, "v": 1000, "ts": ...},
]
for fb in follow_ups:
    asyncio.run(fm.process_bar(fb))

count_after_follow = db.query(V9FiveMinSetup).filter_by(
    pattern=f"{kind}_{direction}").count()
assert count_after_follow == 1, (
    f"CARDINALITY FAIL: {kind}_{direction} double-emitted "
    f"(expected 1 row · got {count_after_follow})"
)
```

**⚠️ POTENTIAL GAP:** there is no explicit per-pattern dedup at the
FiveMinSystem level. The natural dedup is geometric: the detector won't
re-fire because the breakout pivot is now stale. If this UAT fails (any
of the 4 patterns double-emits), Pkg 5a/5b need an `_last_fired_pattern_ts`
guard like S4 WoodiesSystem has (`_last_fired_bar_ts`).

### §2.4 · Latency (p95 < 50ms · 100 iterations)

The chain runs in `process_bar` at Stage 3 · with 6 detectors potentially
called per bar (initiative · reactive · inv_hns · hns_top · db_ee · dt_aa
· bull_flag · bear_flag). Measure end-to-end:

```python
import time
import statistics

fm = FiveMinSystem()
fm.mode = FiveMinMode.DAY_TYPE_MODE
fm.current_day_type = "Variation"

# Seed buffer with bars that will NOT fire (random walk · no pattern)
fm._bar_buffer = _random_walk_bars(30, seed=42)
plain_bar = {"o": 4500, "h": 4501, "l": 4499, "c": 4500.5, "v": 1000, "ts": 1748208900}

latencies = []
for _ in range(100):
    start = time.perf_counter()
    asyncio.run(fm.process_bar(plain_bar))
    latencies.append((time.perf_counter() - start) * 1000)  # ms

p50 = statistics.median(latencies)
p95 = statistics.quantiles(latencies, n=20)[18]  # 95th percentile
p99 = max(latencies)  # only 100 samples · p99 ≈ max

print(f"process_bar latency: p50={p50:.2f}ms · p95={p95:.2f}ms · p99={p99:.2f}ms")
assert p95 < 50.0, f"LATENCY FAIL: p95={p95:.2f}ms exceeds 50ms budget"
assert p99 < 80.0, f"LATENCY FAIL: p99={p99:.2f}ms exceeds 80ms hard cap"
```

If p95 > 50ms: identify the slowest detector via per-call profiling
(`cProfile` on `process_bar`) before promoting.

---

## §3 · Smoke trade scenarios (1 per pattern · 4 total)

### §3.1 · Smoke S1 · Inverse H&S → LONG

**Setup:**
1. Set `FiveMinSystem.current_day_type = "Variation"` (gate passes)
2. Set `FiveMinSystem.mode = FiveMinMode.DAY_TYPE_MODE`
3. Pre-seed `_bar_buffer` with 13 bars from `_build_inverse_hns_bars()`
4. Call `process_bar(bars[13])` (breakout bar)

**Expected outcomes (verify each):**

| Check | Expected | How to verify |
|---|---|---|
| Detector fires | `direction="LONG"` `conf>=0.7` `kind="INVERSE_HNS"` | log line `[FiveMin] FIRE: INVERSE_HNS LONG (conf=...)` |
| Stop family | `HnS` | log line from `compute_stop` family=HnS |
| Structural anchor | `4500 - 0.25 = 4499.75` (LS pivot - 1T) | inspect `info["structural_anchor"]` |
| Stop ≤ structural_anchor (LONG) | True | `setup.stop_price <= 4499.75` |
| T1 price | `entry + 0.50 × 20 = entry + 10` | `setup.t1_price` |
| T2 price | `entry + 0.74 × 20 = entry + 14.8` | `setup.t2_price` |
| T3 price | `None` (trail per Pkg 6) | `setup.t3_price is None` |
| DB row | 1 row in `v9_five_min_setups` with `pattern="INVERSE_HNS_LONG"` | `SELECT * FROM v9_five_min_setups WHERE pattern = 'INVERSE_HNS_LONG' ORDER BY id DESC LIMIT 1;` |
| Gateway record | trade enters SHADOW mode | check `cockpit/systems-snapshot` shows FiveMin pattern=`INVERSE_HNS_LONG` |

### §3.2 · Smoke S2 · H&S Top → SHORT

Same as S1 but with `_build_hns_top_bars(ls_high=4500, head_high=4510, rs_high=4500)`.

Expected: `direction="SHORT"`, `kind="HNS_TOP"`, `structural_anchor=4500.25` (RS + 1T), T2 = entry - 14.8.

### §3.3 · Smoke S3 · Double Bottom EE → LONG

Use the "classic" fixture from `test_double_bt.py` (TestClassicDetection).
Expected: `direction="LONG"`, `kind="DOUBLE_BOTTOM_EE"`, T2 with **0.66×**
haircut (not 0.74×).

### §3.4 · Smoke S4 · Double Top AA → SHORT

Use the "classic" Adam&Adam fixture. Expected: `direction="SHORT"`,
`kind="DOUBLE_TOP_AA"`, T2 with **0.74×** haircut (different from S3 — this
verifies asymmetric haircut survives).

---

## §4 · Execution script (single shell · all 4 smokes)

```bash
# From repo root
cd /Users/michael/Downloads/mems26_web_git

# Axis 1 (Quality) · re-run golden tests
pytest tests/v9/systems/test_five_min/test_head_shoulders.py \
       tests/v9/systems/test_five_min/test_double_bt.py -v \
       > /tmp/g4_axis1_quality.log 2>&1

# Axis 4 (Latency) · custom one-shot script
python -m scripts.g4_pkg5_latency_probe > /tmp/g4_axis4_latency.log 2>&1
# (script to be created · see §6)

# Smoke S1-S4 via integration test runner
pytest tests/v9/systems/test_five_min/test_five_min_day_type_wiring.py -v \
       -k "test_chart_pattern_inverse_hns or test_chart_pattern_hns_top or test_chart_pattern_double_bottom or test_chart_pattern_double_top" \
       > /tmp/g4_smokes.log 2>&1

# Inspect outputs
for f in /tmp/g4_axis*.log /tmp/g4_smokes.log; do
  echo "=== $f ==="
  tail -20 "$f"
done

# Axis 2 (Recency) + Axis 3 (Cardinality) verified inside the integration tests above
```

If the integration tests for chart patterns don't exist yet, CC must add
them as part of G4 prep (see §6).

---

## §5 · Acceptance criteria (G4 green)

All of the following MUST be true · zero exceptions:

- [ ] **Axis 1 (Quality):** 32/32 golden tests pass (no skips · no xfails)
- [ ] **Axis 2 (Recency):** for each of the 4 patterns, `setup.ts` == `breakout_bar.ts` (no clock-time leak). If this fails, hotfix `five_min_system.py:771` to use `bar.get("ts")` then re-run UAT.
- [ ] **Axis 3 (Cardinality):** after 3 follow-up bars, exactly 1 row in `v9_five_min_setups` per fire (no double-emit). If this fails, add `_last_fired_pattern_ts` dedup like S4.
- [ ] **Axis 4 (Latency):** p95 < 50ms · p99 < 80ms over 100 calls
- [ ] **Smoke S1–S4:** each smoke verifies the 9 outcomes in §3.1 table
- [ ] **DB integrity:** all 4 smoke setups visible in `v9_five_min_setups` with non-null `entry_price`, `stop_price`, `confidence`, `setup_kind` (one of INVERSE_HNS / HNS_TOP / DOUBLE_BOTTOM_EE / DOUBLE_TOP_AA)
- [ ] **Gateway recording:** SHADOW gateway sees all 4 trades · cockpit snapshot reflects the most recent fire
- [ ] **No regressions:** `pytest tests/v9/ -q` total count == count from G3 PASS (24/5 18:50) ± 0 new failures
- [ ] **Forbidden zones unchanged:** `git diff backend/v9/services/layer4/ sc_study/ bridge/ frontend/` is empty

---

## §6 · Required test scaffolding (CC task · prerequisite to G4)

Two things may be missing or incomplete · CC must create them BEFORE Michael runs G4:

### §6.1 · 4 chart-pattern integration tests in `test_five_min_day_type_wiring.py`

Add 4 async tests:
- `test_chart_pattern_inverse_hns_fires_t1setup`
- `test_chart_pattern_hns_top_fires_t1setup`
- `test_chart_pattern_double_bottom_ee_fires_t1setup`
- `test_chart_pattern_double_top_aa_fires_t1setup`

Each: pre-seed buffer · trigger `process_bar` · assert T1Setup payload
matches the §3 expected outcomes table.

### §6.2 · Latency probe script `scripts/g4_pkg5_latency_probe.py`

100-call latency measurement per §2.4. Outputs p50/p95/p99 to stdout.
Exits 1 if p95 ≥ 50ms (so CI can gate).

These two are part of the G4 prep. After CC produces them and they pass
locally, Michael runs the §4 execution script and reports back the 8
checkbox results from §5.

---

## §7 · If G4 fails — escalation paths

| Failure mode | Likely cause | Fix path |
|---|---|---|
| Axis 2 (Recency) fails | `setup.ts` uses `datetime.now()` not `bar["ts"]` | Hotfix `five_min_system.py:771` · re-run UAT |
| Axis 3 (Cardinality) fails | No per-pattern dedup at FiveMin level | Add `_last_fired_pattern_ts: Dict[str, float]` mirror of S4 · re-run UAT |
| Axis 4 (Latency) fails | One of the chart-pattern detectors > 10ms/call | Profile with `cProfile` · identify slow detector · consider early-return when `len(bars) < MIN_BARS_REQUIRED` |
| Quality fails on negative fixture | Detector too permissive | Tighten relevant constant (SHOULDER_SYM_PCT or TROUGH_SYM_PCT) · re-validate full golden suite |
| Smoke S1–S4 fail on Gateway | Gateway not receiving SHADOW · or NT gate blocking | Check `current_day_type` set to a tradable value · verify Gateway init log |
| DB row missing | DB session error · check logs | `tail /tmp/v9.err.log` for `[FiveMin] DB persist error:` |

---

## §8 · Reference index

- D-091 LOCKED: `docs/decisions/D-091_S2_LIVE_SCOPE.md` §5+§6 (H&S) · §7+§8 (Double BT)
- Pkg 5a code: `backend/v9/systems/five_min/patterns/head_shoulders.py`
- Pkg 5b code: `backend/v9/systems/five_min/patterns/double_bt.py`
- Integration entry: `backend/v9/systems/five_min/five_min_system.py:680–815`
- Existing tests:
  - `tests/v9/systems/test_five_min/test_head_shoulders.py` (16 tests)
  - `tests/v9/systems/test_five_min/test_double_bt.py` (16 tests)
  - `tests/v9/systems/test_five_min/test_five_min_day_type_wiring.py` (integration · needs 4 new tests per §6.1)
- Pkg 5a G3 PASS: `docs/reports/PKG5A_G3_PASS_2026-05-24.md` (if exists)
- Pkg 5b G3 PASS: `docs/reports/PKG5B_G3_PASS_2026-05-24.md` (if exists)
- Status board entry: `docs/plans/STATUS_BOARD.md` rows 5a + 5b

End of G4 UAT prep · Pkg 5a + Pkg 5b.
