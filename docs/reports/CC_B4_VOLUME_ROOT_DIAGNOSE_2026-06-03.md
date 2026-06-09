# CC Report — B4 Volume Artifact Root Diagnosis | 2026-06-03

## Summary

**Root cause: RTH chart (`5min.json`) overwrites continuous-chart bars with cumulative session volume during settlement.**

Two independent sources write to the same `v9_bars_5min` table via INSERT OR REPLACE. After RTH close, the RTH chart exports bars with **session-cumulative volume** (up to 1M) that overwrite the continuous chart's correct per-bar volume (1-2K).

---

## Step-by-step evidence

### Step 1 — Inflated bars identified

19 bars with volume >100K. Two patterns:

| Pattern | Time window (ET) | Volume | OHLC |
|---------|-----------------|--------|------|
| **Settlement** | June 2, 16:00-16:40 ET | 126K–1,000,000 | Real prices (~7623-7629) |
| **Overnight flat** | June 3, 03:05-03:55 ET | 163K–531K | O=H=L=C=7628.25 (stale) |

### Step 2 — Cross-reference with Sierra SoT

**DB bar at 20:05 UTC (16:05 ET):**
```
vol=1,000,000  o=7627.5  h=7629.75  l=7627.5  c=7627.75
```

**Sierra `5min_continuous.json` at same ts (1780430700):**
```
vol=1,244      o=7621.5  h=7622.75  l=7620.0  c=7621.5
```

**Sierra `5min.json` (RTH chart):** No bar at this timestamp (post-RTH).

**Neither OHLC nor volume match.** The DB bar was NOT written by the continuous stream.

### Step 3 — Who wrote the inflated bars?

The DB bar at 20:00 UTC has `open=7623.5, high=7627.5` — **identical** to the 19:00 UTC bar (15:00 ET = settlement start):

```
19:00 UTC: o=7623.5 h=7627.5 l=7623.25 c=7627.5  vol=6,337   ← legitimate
20:00 UTC: o=7623.5 h=7627.5 l=7623.5  c=7627.25 vol=990,000  ← inflated
```

**The inflated bar's OHLC matches the session open/high — this is a session-level summary bar, not a 5-minute bar.**

### Step 4 — Root cause mechanism

```
RTH chart (5min.json)             Continuous chart (5min_continuous.json)
─────────────────────             ──────────────────────────────────────
Source: Chart #1/4 (RTH only)     Source: Chart #5 (24h Globex)
Bridge: bars_5min_stream          Bridge: bars_5min_continuous_stream
API:    POST /api/v9/bars/5min    API:    POST /api/v9/bars/5min_continuous
Table:  v9_bars_5min              Table:  v9_bars_5min (SAME TABLE!)
SQL:    INSERT OR REPLACE         SQL:    INSERT OR REPLACE
```

**After 16:00 ET (RTH close):**
1. Sierra's RTH chart continues to update its last bars during settlement with **cumulative session volume** (entire day's volume rolled into the bar)
2. The DLL exports this to `5min.json` every 3 seconds
3. The bridge reads it and POSTs to `/api/v9/bars/5min`
4. INSERT OR REPLACE **overwrites** the continuous chart's correct per-bar data with the RTH chart's session-cumulative bar
5. The inflated bar carries OHLC from the session open (not the 5-minute window), confirming it's a session-level bar

**For overnight flat bars:**
Same mechanism — the RTH chart exports stale bars at last-traded-price with cumulative volume. These overwrite the continuous chart's legitimate overnight bars.

### Step 5 — Confirmed root cause

**(ב) ingestion overwrites — RTH chart's session-cumulative bars replace continuous chart's per-bar data via INSERT OR REPLACE race.**

The DLL/Sierra exports are technically correct (the RTH chart IS showing cumulative session data). The bug is that **two sources write to the same table and the RTH source writes AFTER the continuous source**, replacing correct data with cumulative data.

---

## Fix proposals (NOT IMPLEMENTED — strategic stop)

| Option | Description | Risk |
|--------|-------------|------|
| **A. Source separation** | Stop `bars_5min_stream` from writing to `v9_bars_5min` after RTH close (time-gate). Continuous stream owns post-RTH. | Low — bridge-only change, reversible |
| **B. Table separation** | Give RTH chart its own table (`v9_bars_5min_rth`). Continuous chart keeps `v9_bars_5min`. Chart endpoint merges both. | Medium — schema change, but clean |
| **C. Volume cap** | In `post_bars_5min`, reject bars with vol > N×rolling_avg (e.g. >5× or >100K). | Lowest — 1 line guard, but heuristic |
| **D. Settlement window guard** | Skip bridge pushes from RTH chart during 16:00-18:00 ET window (settlement+close). | Low — bridge-side, covers the exact problem |

**Recommended: D (immediate guard) + A (structural).** Option D is a 5-line bridge change that eliminates the symptom. Option A prevents the root cause.

**Existing inflated bars:** Mark with `is_synthetic=1` or delete rows where `volume > 100000` and `ts` is in settlement/overnight window. Reversible via the existing `is_synthetic` column.

---

## Decision for Michael

- **Root is at the ingestion layer** — Sierra exports are doing what they should (RTH chart shows session bars). The bug is that both charts write to the same DB table and the RTH chart wins the race after close.
- **S2/B1/VSA impact:** rolling_avg is inflated by these bars → legitimate setups may be suppressed (volume looks small relative to inflated bars).
- **Fix is safe and reversible** — no DLL change needed, bridge-side time guard + data cleanup.
