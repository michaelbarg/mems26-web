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
pip install psycopg2-binary pyyaml
```

Set `DATABASE_URL` in your environment:
```bash
export DATABASE_URL='postgresql://user:pass@host:port/dbname'
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

## Output

- Summary table: side-by-side scenario comparison
- Per-bucket breakdown: <30, 30-49, 50-69, 70+
- Per-direction breakdown: LONG vs SHORT
- CSV files in `output/` directory (gitignored)
