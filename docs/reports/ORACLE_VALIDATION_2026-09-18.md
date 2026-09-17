# Oracle Validation Report
Generated: 2026-09-17 18:44
Config: K=12, target=1.5x ATR, stop=1.0x ATR

## Summary Table

| Condition | N | good% [CI] | lift-disc | lift-val | $/trade | plateau | Recommendation |
|-----------|---|------------|-----------|----------|---------|---------|----------------|
| break_dn | 449 | 36.5 [32.4-40.8] | -5.8 | -0.9 | $-4.03 | - | discard |
| break_dn+delta+vol>=1.3 | 58 | 43.4 [32.8-54.6] | -0.9 | +5.1 | $16.08 | - | discard |
| break_dn+delta<=-2 | 89 | 36.5 [27.9-46.0] | -10.8 | -0.3 | $8.74 | - | discard |
| break_from_va_long | 610 | 36.0 [32.6-39.6] | +3.1 | +5.1 | $-3.35 | - | discard |
| break_from_va_short | 559 | 40.7 [37.0-44.6] | +1.2 | +0.9 | $0.67 | - | discard |
| break_up | 427 | 36.5 [32.3-40.9] | +4.1 | +5.2 | $0.54 | - | tree |
| break_up+delta+vol>=1.3 | 49 | 34.1 [23.6-46.5] | -4.4 | +5.8 | $3.90 | - | discard |
| break_up+delta>=2 | 78 | 34.3 [25.6-44.3] | +6.2 | +1.0 | $-1.84 | - | discard |
| cup_handle_long | 601 | 36.3 [32.7-40.0] | +7.7 | +1.4 | $0.11 | - | tree |
| double_bottom | 21 | 50.0 [31.9-68.1] | +3.4 | +40.6 | $38.67 | - | small_N |
| double_top | 20 | 41.2 [24.1-60.7] | +0.6 | +3.0 | $9.75 | - | small_N |
| head_shoulders_long | 156 | 36.0 [29.3-43.3] | +3.0 | +5.2 | $-9.55 | - | discard |
| head_shoulders_short | 150 | 40.0 [33.1-47.3] | -2.5 | +2.7 | $-3.79 | - | discard |
| pullback_in_trend_long | 4 | 66.7 [25.4-92.2] | +67.0 | +19.2 | $25.38 | - | small_N |
| pullback_in_trend_short | 18 | 36.4 [17.5-60.6] | -10.8 | +10.1 | $-13.72 | - | small_N |
| pullback_long_classic | 84 | 39.1 [29.7-49.3] | +9.1 | +3.8 | $-4.17 | - | discard |
| pullback_short_classic | 112 | 32.2 [24.7-40.7] | -11.6 | -1.0 | $-17.76 | - | discard |

## Step 1: Threshold Sweep

Conditions where lift flips sign across K/ratio configs:

- break_dn
- break_dn+delta+vol+bsl>=2
- break_dn+delta+vol>=1.3
- break_dn+delta<=-2
- break_dn_fresh_low_mo>=3atr
- break_from_va_long
- break_from_va_short
- break_up+delta+vol>=1.3
- break_up+delta>=2
- double_top
- head_shoulders_short
- pullback_in_trend_short

## Step 2: OOS Split

| Condition | lift-disc | lift-val | pass |
|-----------|-----------|----------|------|
| break_dn | -5.8 | -0.9 | N |
| break_dn+delta+vol>=1.3 | -0.9 | +5.1 | N |
| break_dn+delta<=-2 | -10.8 | -0.3 | N |
| break_from_va_long | +3.1 | +5.1 | Y |
| break_from_va_short | +1.2 | +0.9 | Y |
| break_up | +4.1 | +5.2 | Y |
| break_up+delta+vol>=1.3 | -4.4 | +5.8 | N |
| break_up+delta>=2 | +6.2 | +1.0 | Y |
| cup_handle_long | +7.7 | +1.4 | Y |
| double_bottom | +3.4 | +40.6 | Y |
| double_top | +0.6 | +3.0 | Y |
| head_shoulders_long | +3.0 | +5.2 | Y |
| head_shoulders_short | -2.5 | +2.7 | N |
| pullback_in_trend_long | +67.0 | +19.2 | Y |
| pullback_in_trend_short | -10.8 | +10.1 | N |
| pullback_long_classic | +9.1 | +3.8 | Y |
| pullback_short_classic | -11.6 | -1.0 | N |

## Step 3: Wilson 90% CI

| Condition | good% | CI [lo-hi] | base | pass |
|-----------|-------|------------|------|------|
| break_dn | 36.5 | [32.4-40.8] | 39.6 | N |
| break_dn+delta+vol>=1.3 | 43.4 | [32.8-54.6] | 39.6 | N |
| break_dn+delta<=-2 | 36.5 | [27.9-46.0] | 39.6 | N |
| break_from_va_long | 36.0 | [32.6-39.6] | 31.9 | Y |
| break_from_va_short | 40.7 | [37.0-44.6] | 39.6 | N |
| break_up | 36.5 | [32.3-40.9] | 31.9 | Y |
| break_up+delta+vol>=1.3 | 34.1 | [23.6-46.5] | 31.9 | N |
| break_up+delta>=2 | 34.3 | [25.6-44.3] | 31.9 | N |
| cup_handle_long | 36.3 | [32.7-40.0] | 31.9 | Y |
| double_bottom | 50.0 | [31.9-68.1] | 31.9 | Y |
| double_top | 41.2 | [24.1-60.7] | 39.6 | N |
| head_shoulders_long | 36.0 | [29.3-43.3] | 31.9 | N |
| head_shoulders_short | 40.0 | [33.1-47.3] | 39.6 | N |
| pullback_in_trend_long | 66.7 | [25.4-92.2] | 31.9 | N |
| pullback_in_trend_short | 36.4 | [17.5-60.6] | 39.6 | N |
| pullback_long_classic | 39.1 | [29.7-49.3] | 31.9 | N |
| pullback_short_classic | 32.2 | [24.7-40.7] | 39.6 | N |

## Step 4: Realistic $/trade

| Condition | $/trade | n_trades |
|-----------|---------|----------|
| break_dn | $-4.03 | 446 |
| break_dn+delta+vol+bsl>=2 | $23.78 | 30 |
| break_dn+delta+vol+cp<=0.3 | $11.94 | 42 |
| break_dn+delta+vol>=1.3 | $16.08 | 58 |
| break_dn+delta<=-2 | $8.74 | 89 |
| break_dn_fresh_low_mo>=3atr | $-9.12 | 83 |
| break_from_va_long | $-3.35 | 609 |
| break_from_va_short | $0.67 | 559 |
| break_up | $0.54 | 424 |
| break_up+delta+vol+bsh>=2 | $23.12 | 30 |
| break_up+delta+vol>=1.3 | $3.90 | 49 |
| break_up+delta>=2 | $-1.84 | 78 |
| break_up_fresh_high_mo>=3atr | $3.41 | 100 |
| cup_handle_long | $0.11 | 594 |
| double_bottom | $38.67 | 21 |
| double_top | $9.75 | 20 |
| head_shoulders_long | $-9.55 | 156 |
| head_shoulders_short | $-3.79 | 148 |
| pullback_in_trend_long | $25.38 | 4 |
| pullback_in_trend_short | $-13.72 | 18 |
| pullback_long_classic | $-4.17 | 84 |
| pullback_short_classic | $-17.76 | 111 |

## Step 5: Parameter Grid

Break short grid (window, delta_mult, vol_threshold):

- (3, 1.5, 1.0): good%=41.0, plateau=True
- (3, 1.5, 1.3): good%=41.2, plateau=True
- (3, 1.5, 1.6): good%=40.4, plateau=True
- (3, 2.0, 1.0): good%=41.3, plateau=True
- (3, 2.0, 1.3): good%=43.4, plateau=True
- (3, 2.0, 1.6): good%=39.5, plateau=True
- (3, 3.0, 1.0): good%=31.2, plateau=True
- (3, 3.0, 1.3): good%=32.1, plateau=True
- (3, 3.0, 1.6): good%=33.3, plateau=True
- (5, 1.5, 1.0): good%=41.0, plateau=True
- (5, 1.5, 1.3): good%=41.2, plateau=True
- (5, 1.5, 1.6): good%=40.4, plateau=True
- (5, 2.0, 1.0): good%=41.3, plateau=True
- (5, 2.0, 1.3): good%=43.4, plateau=True
- (5, 2.0, 1.6): good%=39.5, plateau=True
- (5, 3.0, 1.0): good%=31.2, plateau=True
- (5, 3.0, 1.3): good%=32.1, plateau=True
- (5, 3.0, 1.6): good%=33.3, plateau=True
- (8, 1.5, 1.0): good%=41.0, plateau=True
- (8, 1.5, 1.3): good%=41.2, plateau=True
- (8, 1.5, 1.6): good%=40.4, plateau=True
- (8, 2.0, 1.0): good%=41.3, plateau=True
- (8, 2.0, 1.3): good%=43.4, plateau=True
- (8, 2.0, 1.6): good%=39.5, plateau=True
- (8, 3.0, 1.0): good%=31.2, plateau=True
- (8, 3.0, 1.3): good%=32.1, plateau=True
- (8, 3.0, 1.6): good%=33.3, plateau=True

## Step 6: Component Decomposition

### break_dn+delta+vol

| Component | N | good% | lift |
|-----------|---|-------|------|
| break_dn | 449 | 36.5 | -3.1 |
| delta<=-2 | 192 | 37.4 | -2.2 |
| vol>=1.3 | 1013 | 42.8 | +3.1 |
| break_dn+delta | 89 | 36.5 | -3.2 |
| break_dn+delta+vol | 58 | 43.4 | +3.8 |

### break_up+delta+vol

| Component | N | good% | lift |
|-----------|---|-------|------|
| break_up | 427 | 36.5 | +4.6 |
| delta>=2 | 158 | 38.1 | +6.2 |
| vol>=1.3 | 1013 | 31.0 | -0.9 |
| break_up+delta | 78 | 34.3 | +2.5 |
| break_up+delta+vol | 49 | 34.1 | +2.2 |

## Step 7: Producers vs Oracle

Base rate short: 39.6%
Base rate long: 31.9%
Producer gap: 1893 / 2218 GOOD bars not selected (85.3%)

| Producer | Total | Matched | Good(S) | Good(L) | Bad(S) | Bad(L) |
|----------|-------|---------|---------|---------|--------|--------|
| 2 | 724 | 283 | 50 | 35 | 67 | 73 |
| 4 | 871 | 460 | 60 | 45 | 117 | 146 |

## Step 8: Data Quality

Total sessions: 0
Duplicate delta timestamps: 604
Partial sessions (<70 bars): 0
Low delta coverage sessions: 0
Sessions with TS gaps (>10 min): 4

## Step 9: Walk-Forward Simulation

Top conditions: pullback_in_trend_long, double_bottom, break_up+delta+vol+bsh>=2, pullback_long_classic, break_dn+delta+vol+bsl>=2
Total trades: 36
Final equity: $320.18
Max drawdown: $675.17
Trades/day: 0.60
% days >= $200: 0.0%
