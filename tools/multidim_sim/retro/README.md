# Retro-Runner — Historical Outcome Backfill

Computes exact trade outcomes for historical setup_attempts by walking
Sierra Chart .scid tick data sequentially. Solves the temporal ordering
problem that made MFE/MAE heuristics unreliable (12% vs 43% WR).

## How It Works

1. Reads setup_attempts from PG (entry_price, stop_price, c1_target, direction)
2. For each setup, binary-searches the .scid file for the entry timestamp
3. Walks ticks forward from entry: first to hit stop or C1 wins
4. Records exact outcome, MAE, MFE, duration, and closed_ts
5. Saves results as Parquet for MDS consumption

## Usage

```bash
# Validate against Worker's known outcomes
python3 -m tools.multidim_sim retro-validate

# Test mode (10 setups)
python3 -m tools.multidim_sim retro-test

# Full run (all setups)
python3 -m tools.multidim_sim retro
```

## Resolution Difference vs Worker (Important)

This Retro-Runner uses **tick-level resolution** from Sierra .scid files.
The original Worker used **3-minute bar OHLC** data.

### Asymmetric mismatch found:

- Of setups Worker labeled HIT_STOP: ~60% retro labels HIT_C1
- Reason: within a 3-min bar, price briefly touched T1 then reversed to Stop
- Worker (bar-level): can't see intra-bar order, conservatively says STOP
- Retro (tick-level): sees actual sequence, correctly says T1 hit first

### Why Retro is correct for our purposes:

- LIVE broker fills T1 limit order on first tick that touches the price
- Stop order is CANCELED automatically when T1 fills
- Reality is tick-level, not bar-level
- Worker's STOP labels were "approximation in pessimistic direction"

### Impact on V1 baseline:

- V1 was reported -$46,914 net loss (using Worker outcomes)
- Real V1 (tick-corrected) likely -$20,000 to -$30,000
- V1 still loses money, but Worker over-counted losses

### Acceptance for production:

- For LIVE-realistic V2 optimization → use Retro outcomes
- For comparison with old reports → use Worker outcomes (deprecated)

## Requirements

- Sierra Chart .scid file: `/Users/michael/SierraChart2/Data/MESM26_FUT_CME.scid`
- DATABASE_URL environment variable
- Python: polars, psycopg2-binary, tqdm

## Output

Results saved to `tools/multidim_sim/cache/retro_outcomes_<timestamp>.parquet`
