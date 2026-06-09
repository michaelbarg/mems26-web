# CC Handoff · DLL Frozen-Tail Bug · Part 3 of 3: UAT + Backend Patch
**Date:** 2026-05-29  
**Owner:** Claude Code  
**Pre-condition:** Part 2 fix applied (Option A or B), Sierra study reloaded  
**Pre-condition:** `woodies_5min.json` showing no frozen runs (confirmed by Michael / T2 re-probe)

---

## UAT — 4 axes

### Axis 1 — Quality: frozen tail is gone

```bash
python3 - << 'PY'
import json, sys

path = "/Users/michael/SierraChart_Data/v9_export/woodies_5min.json"
d = json.load(open(path))
hist = d.get("history", [])

frozen = []
for i in range(1, len(hist)):
    if hist[i].get("cci_14") == hist[i-1].get("cci_14") and \
       hist[i].get("swi_value") == hist[i-1].get("swi_value"):
        frozen.append(i)

if frozen:
    print(f"FAIL: {len(frozen)} consecutive identical bars at indices {frozen[:10]}")
    sys.exit(1)
else:
    print(f"PASS: no consecutive identical (cci_14, swi_value) pairs in {len(hist)} bars")
PY
```

Expected: `PASS: no consecutive identical ...`

### Axis 2 — Recency: current_bar matches history tail

```bash
python3 - << 'PY'
import json, time

path = "/Users/michael/SierraChart_Data/v9_export/woodies_5min.json"
d = json.load(open(path))
cb = d.get("current_bar", {})
last = d.get("history", [{}])[-1]
age = time.time() - d.get("export_ts", 0)

print(f"export age: {age:.1f}s  (expect < 5)")
print(f"current_bar.cci_14 = {cb.get('cci_14')}")
print(f"history[-1].cci_14 = {last.get('cci_14')}")
print(f"current_bar.swi_value = {cb.get('swi_value')}")
print(f"history[-1].swi_value = {last.get('swi_value')}")
PY
```

Expected: `export age < 5s`; `current_bar` and `history[-1]` values should be close  
(they cover the same bar from two paths — minor diff OK; large diff means Option A  
took effect and `history[-1]` is now using local Python fallback).

### Axis 3 — Cardinality: all history bars present

```bash
python3 -c "
import json
d = json.load(open('/Users/michael/SierraChart_Data/v9_export/woodies_5min.json'))
print(f\"total bars: {d.get('total_bars')}  history: {len(d.get('history', []))}  expect >=50\")
"
```

### Axis 4 — Latency: backend endpoint responds within threshold

```bash
curl -s -o /dev/null -w "HTTP %{http_code}  time=%{time_total}s\n" \
  "http://localhost:8000/api/v9/woodies/chart?limit=20"
```

Expected: `HTTP 200  time < 0.2s`

---

## Backend patch: prefer `current_bar` over `history[-1]`

**File:** `backend/v9/api/v9/bars.py`  
**Context:** This is a separate bug (rank-2 from audit) — even after the DLL fix,  
the backend routes `history[-1]` (the last bar of the frozen tail) to S4 instead  
of `current_bar` (the live in-progress bar). After the DLL fix, `history[-1]` will  
be non-frozen, but `current_bar` is still the most live value.

**Read the file first.** Locate the block around line 799–852 where `payload.all_bars`  
is assembled — specifically where `last_flat` is set to `history[-1]`.

**Change:** When `current_bar` is present in the payload, use it as the last bar  
sent to S4 instead of `history[-1]`. `history[-1]` remains as fallback if `current_bar`  
is absent.

Paste the exact lines you read before making any change.

After the change, run:

```bash
python3 -m pytest tests/v9/api/test_bars_woodies_routing.py -v
```

If that file does not exist, add a minimal test:

```python
# tests/v9/api/test_bars_woodies_routing.py
"""Regression: woodies routing prefers current_bar over history[-1]."""
import pytest

def test_current_bar_preferred_over_history(monkeypatch):
    """When current_bar is present, it should be routed, not history[-1]."""
    from backend.v9.api.v9.bars import _build_woodies_flat_bar
    # Stub: history tail has cci_14=49.70 (frozen), current_bar has cci_14=67.96 (live)
    history_tail = {"ts": 1000, "cci_14": 49.70, "swi_value": -78.17}
    current_bar  = {"ts": 1003, "cci_14": 67.96, "swi_value": -55.20}
    result = _build_woodies_flat_bar(history_tail, current_bar)
    assert result["cci_14"] == 67.96, "current_bar cci_14 must override history[-1]"
    assert result["swi_value"] == -55.20
```

Adapt the test to match the actual function/method name you find in `bars.py`.

---

## Final report

Write `docs/reports/CC_FIX_DLL_FROZEN_TAIL_2026-05-29.md` with:

1. **Option chosen** (A or B) and why.
2. **Build result** — paste the last 5 lines of the Sierra Remote Build log or DLL mtime output.
3. **UAT 4 axes** — paste raw output of all 4 probes.
4. **Backend patch** — paste the before/after diff (exact lines).
5. **Regression tests** — paste `pytest` output.
6. **Remaining watch items:**
   - `woodies_chart_routes.py:43` hardcoded `+5h` (winter-time bomb — Item #2 in OPEN_ITEMS)
   - `S2 current_day_type=None` silent skip — Item #3 in OPEN_ITEMS

---

## Commit format

```
fix(dll+backend): frozen-tail UAT + backend current_bar routing

UAT Axis1 (Quality):   PASS — 0 frozen pairs in N bars
UAT Axis2 (Recency):   export_age=Xs current_bar.cci_14=Y history[-1].cci_14=Z
UAT Axis3 (Cardinality): total_bars=N history=N
UAT Axis4 (Latency):   HTTP 200 time=Xs

Backend: _build_woodies_flat_bar now prefers current_bar over history[-1]
Regression: tests/v9/api/test_bars_woodies_routing.py (N tests)
```
