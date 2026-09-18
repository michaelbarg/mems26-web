# Oracle Validation Report
Generated: 2026-09-18 12:06
Config: K=12, target=1.5x ATR, stop=1.0x ATR

## Summary Table

| Condition | N | good% [CI] | lift-disc | lift-val | $/trade | plateau | Recommendation |
|-----------|---|------------|-----------|----------|---------|---------|----------------|
| break_dn | 430 | 38.4 [34.2-42.8] | -4.2 | -0.0 | $-7.54 | - | discard |
| break_dn+delta+vol>=1.3 | 56 | 46.9 [35.7-58.5] | +5.4 | +6.8 | $5.97 | - | discard |
| break_dn+delta<=-2 | 83 | 41.8 [32.4-51.8] | -4.8 | +3.4 | $-1.88 | - | discard |
| break_from_va_long | 547 | 37.8 [34.1-41.6] | +5.7 | +5.0 | $-4.51 | - | tree |
| break_from_va_short | 488 | 41.5 [37.6-45.6] | -2.0 | +2.7 | $-4.87 | - | discard |
| break_up | 414 | 36.9 [32.7-41.4] | +4.5 | +4.2 | $-1.72 | - | tree |
| break_up+delta+vol>=1.3 | 50 | 36.4 [25.5-48.8] | +1.9 | +5.0 | $-2.65 | - | discard |
| break_up+delta>=2 | 74 | 36.5 [27.3-46.8] | +13.6 | +0.1 | $-4.33 | - | discard |
| cup_handle_long | 575 | 37.4 [33.7-41.3] | +8.8 | +1.1 | $0.57 | - | tree |
| double_bottom | 24 | 52.4 [35.2-69.0] | +12.4 | +30.8 | $37.28 | - | small_N |
| double_top | 22 | 38.9 [22.7-58.0] | -10.1 | +9.4 | $-10.85 | - | small_N |
| head_shoulders_long | 139 | 41.2 [33.9-48.9] | +18.6 | +3.0 | $2.21 | - | tree |
| head_shoulders_short | 156 | 40.2 [33.4-47.3] | -3.2 | +2.7 | $-4.43 | - | discard |
| pullback_in_trend_long | 5 | 50.0 [18.2-81.8] | +16.2 | +18.3 | $-4.62 | - | small_N |
| pullback_in_trend_short | 13 | 54.5 [31.5-75.8] | +17.0 | +9.4 | $5.73 | - | small_N |
| pullback_long_classic | 80 | 41.0 [31.2-51.5] | +11.9 | +2.9 | $-0.51 | - | discard |
| pullback_short_classic | 107 | 36.8 [29.2-45.2] | -5.6 | -0.0 | $-12.61 | - | discard |

## Step 1: Threshold Sweep

Conditions where lift flips sign across K/ratio configs:

- break_dn
- break_dn+delta+vol+cp<=0.3
- break_dn+delta<=-2
- break_dn_fresh_low_mo>=3atr
- break_up+delta>=2
- double_top
- head_shoulders_short
- pullback_in_trend_short

## Step 2: OOS Split

| Condition | lift-disc | lift-val | pass |
|-----------|-----------|----------|------|
| break_dn | -4.2 | -0.0 | N |
| break_dn+delta+vol>=1.3 | +5.4 | +6.8 | Y |
| break_dn+delta<=-2 | -4.8 | +3.4 | N |
| break_from_va_long | +5.7 | +5.0 | Y |
| break_from_va_short | -2.0 | +2.7 | N |
| break_up | +4.5 | +4.2 | Y |
| break_up+delta+vol>=1.3 | +1.9 | +5.0 | Y |
| break_up+delta>=2 | +13.6 | +0.1 | Y |
| cup_handle_long | +8.8 | +1.1 | Y |
| double_bottom | +12.4 | +30.8 | Y |
| double_top | -10.1 | +9.4 | N |
| head_shoulders_long | +18.6 | +3.0 | Y |
| head_shoulders_short | -3.2 | +2.7 | N |
| pullback_in_trend_long | +16.2 | +18.3 | Y |
| pullback_in_trend_short | +17.0 | +9.4 | Y |
| pullback_long_classic | +11.9 | +2.9 | Y |
| pullback_short_classic | -5.6 | -0.0 | N |

## Step 3: Wilson 90% CI

| Condition | good% | CI [lo-hi] | base | pass |
|-----------|-------|------------|------|------|
| break_dn | 38.4 | [34.2-42.8] | 40.3 | N |
| break_dn+delta+vol>=1.3 | 46.9 | [35.7-58.5] | 40.3 | N |
| break_dn+delta<=-2 | 41.8 | [32.4-51.8] | 40.3 | N |
| break_from_va_long | 37.8 | [34.1-41.6] | 32.7 | Y |
| break_from_va_short | 41.5 | [37.6-45.6] | 40.3 | N |
| break_up | 36.9 | [32.7-41.4] | 32.7 | Y |
| break_up+delta+vol>=1.3 | 36.4 | [25.5-48.8] | 32.7 | N |
| break_up+delta>=2 | 36.5 | [27.3-46.8] | 32.7 | N |
| cup_handle_long | 37.4 | [33.7-41.3] | 32.7 | Y |
| double_bottom | 52.4 | [35.2-69.0] | 32.7 | Y |
| double_top | 38.9 | [22.7-58.0] | 40.3 | N |
| head_shoulders_long | 41.2 | [33.9-48.9] | 32.7 | Y |
| head_shoulders_short | 40.2 | [33.4-47.3] | 40.3 | N |
| pullback_in_trend_long | 50.0 | [18.2-81.8] | 32.7 | N |
| pullback_in_trend_short | 54.5 | [31.5-75.8] | 40.3 | N |
| pullback_long_classic | 41.0 | [31.2-51.5] | 32.7 | N |
| pullback_short_classic | 36.8 | [29.2-45.2] | 40.3 | N |

## Step 4: Realistic $/trade

| Condition | $/trade | n_trades |
|-----------|---------|----------|
| break_dn | $-7.54 | 428 |
| break_dn+delta+vol+bsl>=2 | $4.52 | 28 |
| break_dn+delta+vol+cp<=0.3 | $-3.51 | 40 |
| break_dn+delta+vol>=1.3 | $5.97 | 56 |
| break_dn+delta<=-2 | $-1.88 | 83 |
| break_dn_fresh_low_mo>=3atr | $-13.67 | 83 |
| break_from_va_long | $-4.51 | 546 |
| break_from_va_short | $-4.87 | 488 |
| break_up | $-1.72 | 411 |
| break_up+delta+vol+bsh>=2 | $16.83 | 30 |
| break_up+delta+vol>=1.3 | $-2.65 | 50 |
| break_up+delta>=2 | $-4.33 | 74 |
| break_up_fresh_high_mo>=3atr | $2.69 | 99 |
| cup_handle_long | $0.57 | 569 |
| double_bottom | $37.28 | 24 |
| double_top | $-10.85 | 22 |
| head_shoulders_long | $2.21 | 139 |
| head_shoulders_short | $-4.43 | 154 |
| pullback_in_trend_long | $-4.62 | 5 |
| pullback_in_trend_short | $5.73 | 13 |
| pullback_long_classic | $-0.51 | 80 |
| pullback_short_classic | $-12.61 | 106 |

## Step 5: Parameter Grid

Break short grid (window, delta_mult, vol_threshold):

- (3, 1.5, 1.0): good%=43.7, plateau=True
- (3, 1.5, 1.3): good%=44.9, plateau=True
- (3, 1.5, 1.6): good%=42.0, plateau=True
- (3, 2.0, 1.0): good%=45.2, plateau=True
- (3, 2.0, 1.3): good%=47.1, plateau=True
- (3, 2.0, 1.6): good%=43.6, plateau=True
- (3, 3.0, 1.0): good%=40.0, plateau=True
- (3, 3.0, 1.3): good%=40.0, plateau=True
- (3, 3.0, 1.6): good%=33.3, plateau=True
- (5, 1.5, 1.0): good%=44.3, plateau=True
- (5, 1.5, 1.3): good%=46.2, plateau=True
- (5, 1.5, 1.6): good%=41.7, plateau=True
- (5, 2.0, 1.0): good%=44.8, plateau=True
- (5, 2.0, 1.3): good%=46.9, plateau=True
- (5, 2.0, 1.6): good%=42.1, plateau=True
- (5, 3.0, 1.0): good%=39.3, plateau=True
- (5, 3.0, 1.3): good%=40.0, plateau=True
- (5, 3.0, 1.6): good%=33.3, plateau=True
- (8, 1.5, 1.0): good%=47.1, plateau=True
- (8, 1.5, 1.3): good%=48.3, plateau=True
- (8, 1.5, 1.6): good%=43.5, plateau=True
- (8, 2.0, 1.0): good%=48.1, plateau=True
- (8, 2.0, 1.3): good%=48.9, plateau=True
- (8, 2.0, 1.6): good%=43.2, plateau=True
- (8, 3.0, 1.0): good%=40.7, plateau=True
- (8, 3.0, 1.3): good%=40.0, plateau=True
- (8, 3.0, 1.6): good%=33.3, plateau=True

## Step 6: Component Decomposition

### break_dn+delta+vol

| Component | N | good% | lift |
|-----------|---|-------|------|
| break_dn | 430 | 38.4 | -1.9 |
| delta<=-2 | 146 | 43.2 | +2.9 |
| vol>=1.3 | 915 | 43.4 | +3.0 |
| break_dn+delta | 83 | 41.8 | +1.5 |
| break_dn+delta+vol | 56 | 46.9 | +6.6 |

### break_up+delta+vol

| Component | N | good% | lift |
|-----------|---|-------|------|
| break_up | 414 | 36.9 | +4.3 |
| delta>=2 | 138 | 37.6 | +5.0 |
| vol>=1.3 | 915 | 32.0 | -0.7 |
| break_up+delta | 74 | 36.5 | +3.9 |
| break_up+delta+vol | 50 | 36.4 | +3.7 |

## Step 7: Producers vs Oracle

Skipped: skip_producers flag set

## Step 8: Data Quality

Total sessions: 76
Clean sessions (excl. EXC/ROLL, >=40 bars): 60
Duplicate delta timestamps: 604
Partial sessions (<70 bars): 9
  - 2026-06-01: 8 bars
  - 2026-06-05: 38 bars
  - 2026-06-08: 53 bars
  - 2026-06-19: 43 bars
  - 2026-07-03: 42 bars
  - 2026-07-16: 65 bars
  - 2026-07-22: 57 bars
  - 2026-08-04: 41 bars
  - 2026-09-07: 42 bars
Low delta coverage sessions: 12
Sessions with TS gaps (>10 min): 4
  - 2026-06-01: max gap 360.0 min
  - 2026-06-05: max gap 100.0 min
  - 2026-07-22: max gap 65.0 min
  - 2026-06-08: max gap 30.0 min

## Step 9: Walk-Forward Simulation

Top conditions: double_bottom, pullback_in_trend_long, break_up+delta+vol+bsh>=2, pullback_in_trend_short, head_shoulders_long
Total trades: 52
Final equity: $-234.20
Max drawdown: $733.93
Trades/day: 0.87
% days >= $200: 3.3%

## Step 10: Condition x Phase x Day-type Cells

Only cells with N >= 10 shown.

| Condition | Phase | Day type | N | good% [CI] | disc% | val% | $/trade | pass |
|-----------|-------|----------|---|------------|-------|------|---------|------|
| head_shoulders_long | C | Variation | 13 | 46.2 [26.1-67.5] | 50.0 | 42.9 | $23.41 | N |
| head_shoulders_long | C | Trend | 38 | 50.0 [37.1-62.9] | 56.0 | 38.5 | $37.01 | Y |
| head_shoulders_long | D | UNRESOLVED | 20 | 30.0 [16.4-48.4] | 50.0 | 27.8 | $-16.25 | N |
| head_shoulders_long | D | Trend | 13 | 38.5 [20.2-60.7] | 100.0 | 20.0 | $-14.02 | N |

## Winner Profile Combinations

Combos screened (wr>60%, N>=15): 43

| Features | N | wr% | CI [lo-hi] | disc-wr | val-wr | $/trade | plateau | Rec |
|----------|---|-----|------------|---------|--------|---------|---------|-----|
| at_extreme & vol_trig & stop_le_1atr | 22 | 86.4 | [70.3-94.4] | 72.7 | 100.0 | $67.84 | N | monitor |
| chase & vol_trig & stop_le_1atr | 17 | 82.4 | [63.1-92.7] | 75.0 | 88.9 | $55.22 | N | monitor |
| at_extreme & trigger_ok & vol_trig | 15 | 80.0 | [59.1-91.7] | 85.7 | 75.0 | $34.75 | N | monitor |
| at_extreme & shape & trigger_ok | 15 | 73.3 | [52.1-87.4] | 85.7 | 62.5 | $15.40 | N | monitor |
| chase & shape & trigger_ok | 15 | 73.3 | [52.1-87.4] | 85.7 | 62.5 | $15.40 | N | monitor |
| with_day & at_extreme & vol_trig | 29 | 72.4 | [57.3-83.7] | 78.6 | 66.7 | $32.80 | N | monitor |
| with_ext & at_extreme & vol_trig | 29 | 72.4 | [57.3-83.7] | 78.6 | 66.7 | $32.80 | N | monitor |
| with_ext & vol_trig & stop_le_1atr | 29 | 72.4 | [57.3-83.7] | 57.1 | 86.7 | $50.22 | N | monitor |
| chase & body_ge_50 & vol_trig | 18 | 72.2 | [52.9-85.8] | 77.8 | 66.7 | $16.18 | N | monitor |
| at_extreme & trigger_ok & stop_le_1atr | 31 | 71.0 | [56.3-82.3] | 80.0 | 62.5 | $45.23 | N | monitor |
