# CC Fix Report — DLL Frozen-Tail Bug · 2026-05-29

## §1 · Option chosen

**Option A** — clamp-detection in `mapIdx` lambda.

Michael confirmed `WoodiesChartNumber` (Input #18 / In:19) = **12** — a different
chart from the host. Option B (set to 0) was rejected because Michael wants to
keep chart 12 as the Woodies data source.

The fix detects when `GetContainingIndexForDateTimeIndex` returns the same index
for consecutive bars (clamped) and falls back to `dll_bar_idx`, allowing the
existing `sv == 0` fallback to produce live Python-computed values.

## §2 · Build result

```
=== Monolith Generator v9.2.0 ===
Source: /Users/michael/Downloads/mems26_web_git/sc_study
OK:     2641 lines, SCDLLName@line7, 1x sierrachart.h, 11x v9.2
DEPLOYED to /Users/michael/SierraChart/ACS_Source/MES_AI_DataExport.cpp
DEPLOYED to /Users/michael/SierraChart2/ACS_Source/MES_AI_DataExport.cpp
DEPLOYED to /Users/michael/SierraChart/SierraChartInstance_2/ACS_Source/MES_AI_DataExport.cpp
=== Done ===

Sierra Remote Build: SUCCESS
Writing file to: Y:\SierraChart\Data\MES_AI_DataExport_64.dll
-- End of Build -- 08:47:56
```

Version in live export: `v9.4.3-p31.1`

## §3 · UAT 4 axes (raw output)

```
=== AXIS 1: Quality ===
PASS: no consecutive identical (cci_14, swi_value) pairs in 50 bars

=== AXIS 2: Recency ===
export age: 2.6s  (expect < 5)
current_bar.cci_14 = 2.37
history[-1].cci_14 = 2.37
current_bar.swi_value = -51.51
history[-1].swi_value = -51.51

=== AXIS 3: Cardinality ===
total bars: 60  history: 50  expect >=50

=== AXIS 4: Latency ===
HTTP 200  time=0.012683s
```

All 4 axes PASS.

## §4 · Backend patch

The `current_bar` routing override was already applied in commit `99671e4`
(2026-05-28 pre-live batch). No additional change needed.

```python
# bars.py:852-870 — already in place:
if payload.current_bar:
    _cb = payload.current_bar
    _cb_ohlc = _cb.get("ohlc", {}) or {}
    last_flat = {
        "ts": _cb.get("ts"),
        "open":   _cb_ohlc.get("o", ...),
        # ... all study fields from current_bar
    }
```

## §5 · Regression tests

```
$ pytest tests/v9/dll/test_woodies_mapidx_clamp.py -v
4 passed in 0.05s

$ pytest tests/v9/api/test_bars_woodies_routing.py -v
2 passed in 0.45s
```

## §6 · Remaining watch items

1. **DLL frozen-tail during RTH** — need to verify during next RTH session
   (the fix was applied off-hours; the clamp may only manifest during active RTH
   when the Woodies chart is computing bars)
2. **`woodies_chart_routes.py` hardcoded +5h** — replaced with DST-aware
   `_chicago_to_utc()` in commit `99671e4` (resolved)
3. **S2 `current_day_type=None`** — fixed in P31-F (hydrate before overnight
   early-return, commit `c79029d`)
