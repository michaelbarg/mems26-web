# MDS — Multi-Dimensional Simulator V1.0.0

Research-grade simulator for MEMS26 Quality Score V2 optimization.
Sweeps multi-dimensional parameter space against historical setups
to find optimal scoring weights + filtering parameters.

**Status:** Foundation (Commit 1/5)
**Architecture:** Option C — Hybrid Outcome Sourcing
**Isolation:** Does NOT touch production code (backend/frontend/bridge).

## Quickstart

```bash
# Set DATABASE_URL (Render PostgreSQL)
export DATABASE_URL="postgresql://..."

# 1. Fetch + cache dataset
python3 -m tools.multidim_sim load

# 2. Run V1 baseline simulation
python3 -m tools.multidim_sim simulate --config v1_production

# 3. Run sanity test suite (GATE for Commit 2)
python3 -m tools.multidim_sim sanity
```

## Requirements

```bash
pip3 install polars pyyaml psycopg2-binary pytest
```

## Architectural Decisions

### Option C — Hybrid Outcome Sourcing

MDS-V1.0 uses DB outcome directly (not bar-by-bar simulation).

This means:
- **Fully optimizable:** Quality Score V2 (weights, threshold, filters)
- **Fully optimizable:** Duration management (max_duration, EOD flatten)
- **Uses V1 defaults:** Trade management (stop type, T2 cap, C3 mode)
  — deferred to Phase 3.5 bar-by-bar sim

**Why:** The MFE/MAE heuristic cannot reconstruct temporal order
(12% sim WR vs 43% DB WR). The anti-correlation problem is in
*scoring*, not trade management. Solving scoring first delivers
the V2 spec faster.

### Data Source

Uses `setup_attempts` table (hypothetical forward performance).
This is a different population from the `setups` table used by
`/analytics/by_score_bucket`. Counts may differ by ~10-15%.

## Critical Findings from MDS-V1.0 Sanity Diagnostics (May 2, 2026)

### Finding 1: Score Anti-Correlation by Day Type

TREND_DAY data (88 setups):
- Score 30-50 bucket: **90.2% WR** (n=41)
- Score 70+ bucket: **11.4% WR** (n=44)
- V1 production threshold=50 misses the profitable bucket entirely.
- This is concrete proof of the anti-correlation problem and validates
  the threshold_lower hypothesis from the master spec.

### Finding 2: VWAP Overextension Hypothesis Confirmed (96.3%)

For setups with vwap_side data (n=4,379 of 5,499 = limited subset):
- Score 90+: **96.3% overextended** (price moved against VWAP direction)
- Score 70-89: 72.4% overextended
- Score 50-69: 35.8% overextended
- Score 30-49: 22.2% overextended

This is the mechanism behind Score 100 = 100% loss rate — the system
gives highest scores when price is most overextended (mean reversion
imminent).

Coverage limitation: vwap_side populated only ~3.4% of recent dataset.
Other 96.6% have NULL vwap_side. V1.0 includes optional skip_overextended
config, but it only filters the populated subset.

### Finding 3: Duration Data Limitation

setup_attempts uses a fixed 60-minute forward measurement window.
All rows have duration_minutes = 60. The duration_max_minutes parameter
is implemented but inert in V1.0 (no variation in source data).

For real variable duration, V1.1 should JOIN with setups table
(first_detected_ts, closed_ts).

## Status

- ✅ MDS-V1.0.0 (Commit 1): Foundation — data_loader + simulator_core + sanity
- ⏳ MDS-V1.0.1 (Commit 2): Phase 1 Grid + Composite Score
- ⏳ MDS-V1.0.2 (Commit 3): Phase 2 Optuna + Phase 3 WFO
- ⏳ MDS-V1.0.3 (Commit 4): Visualizations
- ⏳ MDS-V1.0.4 (Commit 5): Golden Table + V2 Spec Output

## Spec Reference

Full design: `~/Downloads/cc_prompts/MEMS26_MDS_V1.0.0_SPEC.md`

## Architecture

```
data_loader.py      PG → filtered Polars DataFrame → Parquet cache
simulator_core.py   Vectorized trade evaluation (Option C: DB outcome)
cli.py              Entry point: load | simulate | sanity
tests/              Sanity gate (must pass to unlock Commit 2)
```

Built for MEMS26 Phase 3.3 by Michael Barg + Claude.
