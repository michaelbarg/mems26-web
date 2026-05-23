# P31-STRAT-S3 UAT Report — 2026-05-22

## Backend restart
- Old PID 10845 (start: 10:48 IL) — graceful kill via `pkill -f uvicorn`
- New PID 39826 (start: 11:35:26 IL) — health=200, bars flowing

## Footprint state — before vs after restart

| Field | Pre-fix (PID 10845) | Post-fix (PID 39826) | Status |
|---|---|---|---|
| cot | 46.0 | 44,081.0 (session-scoped) | IMPROVED — no longer −144K cross-session |
| amt | 0.0 | 0.0 | FAIL — see Bug below |
| bars_processed_today | 4 | 585→591 (growing) | PASS |
| hydrated | true | true | PASS |
| running | true | true | PASS |

## 4 UAT axes

- **Quality: PARTIAL PASS**
  - COT: PASS — value 44K is session-scoped (current Globex session since 18:00 ET yesterday). No longer accumulating across days (was −144K). Session reset logic (dcae75d) confirmed working.
  - AMT: **FAIL** — still 0.0 despite 585+ bars processed with volume. Root cause identified below.

- **Recency: PASS** — bars_processed_today growing continuously (585→587→591 in 15s). Bridge pushing tick_reversal bars, backend ingesting.

- **Cardinality: PASS** — buffer_size=30, bars_processed_today=591 and growing.

- **Latency: PASS** — API response 26ms (well under 1s threshold).

## AMT=0 Root Cause (NEW BUG — not fixed by dcae75d)

The commit (dcae75d) correctly changed AMT from instant to 90-min rolling average. However, the **field name extraction is wrong**:

```python
# footprint_system.py:275 (current code)
total_vol = float(bar.get("v") or bar.get("volume") or 0)
```

Footprint system subscribes to `tick_reversal_15` + `tick_reversal_12`. Tick reversal bars use field `"vol"` (not `"v"` or `"volume"`):

```json
{"idx":65, "o":7490.25, "h":7491.5, "l":7488.0, "c":7490.0,
 "vol":2132.0, "ask_vol":1043.0, "bid_vol":1089.0, "delta":-46.0, ...}
```

Since `bar.get("v")` and `bar.get("volume")` are both None, `total_vol = 0` always. Therefore `per_bar_amt = 0 / 1 = 0`, and the rolling average of zeros = 0.

**Fix needed (1 line):**
```python
total_vol = float(bar.get("vol") or bar.get("v") or bar.get("volume") or 0)
```

Similarly, `trade_count` falls back to 1 because tick_reversal bars don't have `"trade_count"`, `"ticks_count"`, or `"n"`. This may be intentional (tick reversal bars = fixed tick count), but worth verifying the expected AMT semantic: vol/trade_count or just vol?

## S2 fire (RTH check)

Current time ~08:50 ET — pre-RTH. S2 state: `OVERNIGHT_MODE`, running, hydrated, buffer_size=192. S2 firing deferred to RTH UAT (09:30+ ET = 16:30+ IL).

## Issues found + fixed

1. **AMT field-name mismatch** (P31-STRAT-S3 #3 incomplete) — `"vol"` key not checked in `_update_flow()`.
   - **Root cause:** tick_reversal bars use `"vol"`, code checked `"v"` and `"volume"`.
   - **Fix:** 63934f7 — added `"vol"` as first lookup in fallback chain.
   - **Test:** `test_amt_reads_sierra_vol_field` added (9/9 pass).
   - **Status:** committed, awaiting backend restart to verify live AMT > 0.

## Next step recommendation

- Restart backend to pick up 63934f7
- Verify AMT > 0 during active trading (expect 50-300 range)
- After AMT confirmed, wait for RTH (16:30 IL) to verify S2 can fire with corrected COT+AMT inputs
