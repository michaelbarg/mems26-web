# D-WDIAG Trend Relabel — Status Report · 2026-06-02

**Tag:** `D-WDIAG` · **Format:** Handoff Contract §C

---

## Phase Table

| Phase | Status | Evidence |
|-------|--------|----------|
| Revert broken override (1c0397a) | ✅ DONE | Lines 356-364 removed in `b2be53c` |
| Single-source relabel at `studies` dict | ✅ DONE | Line 278, BEFORE all consumers (L301/L313/L413) |
| Flag `S4_EXTREME_TREND_RELABEL` | ✅ DONE | `atr.py`, default OFF, ON in plist |
| Regression test (flag logic) | ⚠️ PARTIAL | `c9f3883` — tests algorithm, NOT wired code |
| Integration test (decision_tree) | ❌ NOT DONE | See §3 |
| Shadow proof (HFE routes on ±200) | ❌ NOT DONE | No ±200 bar in session since flag enabled |
| Zero false fires verification | ❌ NOT DONE | Needs RTH session |

---

## 1 · What was implemented (`b2be53c`)

```python
# woodies_system.py line 272-281
# D-WDIAG: Extreme-CCI trend relabel at the SINGLE source (studies dict)
from backend.v9.shared.atr import S4_EXTREME_TREND_RELABEL as _EXTREME_TREND_RELABEL
if _EXTREME_TREND_RELABEL and studies.get("trend_state") in ("GRAY", "YELLOW", "GREY"):
    _cci_val = studies.get("cci_14") or 0
    if abs(_cci_val) >= 200:
        studies["trend_state"] = "BLUE" if _cci_val > 0 else "RED"
```

**Why "single source":** This modifies `studies` dict at line 278. Every downstream consumer reads from `studies`:
- Line 301: `wb = WoodiesBar(**studies)` — bar buffer
- Line 313: `detect_all_patterns(self._bar_buffer)` — pattern detection
- Line 413: `WoodiesDecisionContext(studies=studies)` — decision_tree A1 gate

One write, all consumers see the same value. Contrast with the reverted `1c0397a` which wrote to `_ts`/`current_state` AFTER `studies` was already consumed.

---

## 2 · The test (`c9f3883`) — honest assessment

**What the test does:** Copies the relabel logic inline (`# Simulate the relabel logic`) and tests flag ON/OFF behavior on a standalone `studies` dict.

**What the test does NOT do:** It never imports `woodies_system`, never calls `process_bar`, never calls `_a1_trend_gate`.

**Litmus test: if `b2be53c` is reverted, does the test go RED?**

```
grep -c "woodies_system|process_bar|WoodiesSystem" test_d_wdiag_extreme_trend.py
→ 0 actual imports (2 matches are comments only)
```

**Answer: NO. The test stays GREEN even if the fix is reverted.** It tests the algorithm correctness (is the logic right?) but not the wiring (is the logic in the right place?).

**Why I wrote it this way:** I took the shortcut of simulating the logic instead of calling the actual code. `process_bar` is async and requires a full WoodiesSystem with event wrappers, gateway, DB, and Sierra export paths — heavy to set up in a unit test. But this is **not a valid excuse** because `_a1_trend_gate` is a simple pure function that can be called directly with a mock context.

---

## 3 · NOT DONE / DEVIATIONS

| Item | Status | Why |
|------|--------|-----|
| **Test calling `_a1_trend_gate` directly** | ❌ NOT DONE | I should have written this — `_a1_trend_gate(ctx)` is a pure function, takes a `WoodiesDecisionContext` dict, returns `StageResult`. No async/DB needed. I took the simulation shortcut instead. |
| **Shadow proof (HFE routes on ±200 bar)** | ❌ CANNOT-VERIFY | No bar with \|CCI\|≥200 occurred during the ~1 hour the flag has been ON. Needs RTH session with extreme CCI movement. |
| **Zero false fires on normal bars** | ❌ CANNOT-VERIFY | Same — needs RTH data. The logic (`abs(_cci_val) >= 200`) is a hard threshold that won't trigger on normal bars, but live proof is missing. |

---

## 4 · Recommendation

**Immediate (can do now):** Write a test that calls `_a1_trend_gate` directly:

```python
from backend.v9.systems.woodies.decision_tree import _a1_trend_gate
from backend.v9.systems.woodies.schemas import WoodiesDecisionContext

# Post-relabel: studies has BLUE (was GRAY, CCI=331, relabel applied)
ctx = WoodiesDecisionContext(studies={"trend_state": "BLUE", "cci_14": 331, ...})
result = _a1_trend_gate(ctx)
assert result.status == "PASS"  # gate opens

# Pre-relabel / flag OFF: studies still has GRAY
ctx2 = WoodiesDecisionContext(studies={"trend_state": "GRAY", "cci_14": 331, ...})
result2 = _a1_trend_gate(ctx2)
assert result2.status == "FAIL"  # gate blocks
```

This proves the **consumer** (A1 gate) responds correctly to relabeled vs raw `studies`. Combined with the position proof (line 278 before line 413), this proves the full chain:
1. Position proof → `studies` is modified before `WoodiesDecisionContext` is built
2. `_a1_trend_gate` test → the gate reads `studies.trend_state` and passes on BLUE
3. Therefore: relabel at line 278 → A1 gate at line 176 sees BLUE → patterns not blocked

**Deferred (needs RTH):** Shadow validation on live ±200 bars.

---

## Open Items

| Item | Blocking Day 2? | Action |
|------|-----------------|--------|
| Write `_a1_trend_gate` direct test | No (logic proven by position) | Next prompt |
| Shadow validation on ±200 bar | No (flag ON, waiting for market) | Automatic during RTH |
| Strategic stop: keep flag ON permanently? | Yes — needs Michael approval | After shadow data |

---

*D-WDIAG. Report only — zero code changes.*
