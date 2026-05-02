# MEMS26 Backtest Framework V1

Development tool for testing alternative scoring scenarios against historical setup data.

## Usage

```bash
cd tools/backtest

# Run all 8 scenarios (last 7 days)
python3 run_scenarios.py --scenarios scenarios.yaml

# Run specific scenarios
python3 run_scenarios.py --only baseline,design_b_aggressive

# Custom lookback period
python3 run_scenarios.py --days 14

# Skip CSV export
python3 run_scenarios.py --no-csv
```

## Requirements

```bash
pip install pyyaml
```

Uses the mems26-web API (no DATABASE_URL needed):
```bash
# Default: https://mems26-web.onrender.com
python3 run_scenarios.py

# Custom API URL:
python3 run_scenarios.py --api-url http://localhost:8000
```

## Scenarios (V8.3.0)

| Scenario | Description |
|----------|-------------|
| baseline | Current production scoring (NORMAL weights) |
| vegas_reduced | Vegas 30→15, Footprint 20→35 |
| footprint_veto | Reject if footprint delta opposes direction |
| threshold_lower | Execution threshold 50→35 |
| structural_stop | Use shadow structural stop instead of fixed 5pt |
| combined_v2 | Vegas reduced + footprint veto + lower threshold + structural |
| design_b_score_binary | Score >=30 is binary qualifier; real filters do the work |
| design_b_aggressive | Design B + structural stop + skip score 90+ death trap |

## Design B Hypothesis

Score above 30 is NOISE, not SIGNAL:
- Score 30-49: WR 46.8% (best bucket)
- Score 50-69: WR 31.1%
- Score 70+: WR 34.6%
- Score 100: WR 0% (6/6 LONG losses)

Design B treats score as a binary qualifier (pass/fail at 30) and uses
footprint veto, day type filtering, and direction sizing for real signal.

## IMPORTANT CAVEATS

**This backtest is APPROXIMATION ONLY.**

1. **Day 0 data limitations:**
   - 100% NORMAL day_type (off-hours classifier issue)
   - 100% FVG setup type (only FVG triggers off-hours)
   - 100% OFF_HOURS (Bridge weekend pause)
   - Only ~50-150 setups with MAE/MFE data
   - Component scores estimated, not always present

2. **PnL calculation is rough:**
   - Assumes C1 hit if MFE >= stop_pts (1:1 R:R)
   - Assumes stop hit if MAE >= stop_pts
   - Timeout PnL = (MFE - MAE) * 0.5 (conservative)
   - No slippage, no commissions
   - MES = $5/pt

3. **Use for HYPOTHESIS GENERATION, not execution.**
   Real validation = Day 1-3 fresh data with live market hours.

## Sample Run Results (2026-05-02, 5499 attempts)

```
  Scenario                  Total   Exec  W/Data    WR%    PnL($)   Avg/tr
  ──────────────────────────────────────────────────────────────────────────
  baseline                   5499   3558    3175  59.2% $25421.12 $   8.01
  vegas_reduced              5499   3753    3371  59.8% $28017.40 $   8.31
  footprint_veto             5499   1501    1233  62.7% $11529.31 $   9.35
  threshold_lower            5499   4897    4459  60.0% $38428.68 $   8.62
  structural_stop            5499   3558    3175  59.2% $25421.12 $   8.01
  combined_v2                5499   1511    1242  62.9% $11704.31 $   9.42
  design_b_score_binary      5499   1062     799  73.5% $ 5327.19 $   6.67
  design_b_aggressive        5499    703     445  77.1% $ 3420.30 $   7.69
```

Best total PnL: **threshold_lower** (+$38K, +$13K vs baseline)
Best WR: **design_b_aggressive** (77.1%, +17.9% vs baseline)
Best avg/trade: **combined_v2** ($9.42/trade)

## Output

- Summary table: side-by-side scenario comparison
- Per-bucket breakdown: <30, 30-49, 50-69, 70+
- Per-direction breakdown: LONG vs SHORT
- CSV files in `output/` directory (gitignored)
