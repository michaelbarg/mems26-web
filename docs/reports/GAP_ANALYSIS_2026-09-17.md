# Gap Analysis Report
Generated: 2026-09-17 14:45
Sessions analyzed: 76

## SUSPECT Sessions (excluded from summaries)

| Session | Suspect Bars | Range | Day Type |
|---------|-------------|-------|----------|
| 2026-06-09 | 1 | 306.8 | Variation |
| 2026-06-11 | 1 | 156.8 | Trend |
| 2026-06-12 | 1 | 95.8 | UNRESOLVED |
| 2026-06-17 | 1 | 132.0 | Trend |
| 2026-06-26 | 1 | 99.2 | Variation |
| 2026-07-10 | 1 | 75.0 | Trend |
| 2026-07-24 | 1 | 65.2 | Trend |
| 2026-07-28 | 1 | 68.8 | UNRESOLVED |
| 2026-07-29 | 1 | 139.0 | Trend |

## By Day Type

| Day Type | N | Avg Range | Avg Captured (pts) | Captured/Range | Move Status Distribution |
|----------|---|-----------|--------------------|---------------|-------------------------|
| Normal | 11 | 44.8 | -5.6 | -12.5% | FIRED_SHADOW_ONLY:5, NO_SETUP:27 |
| Trend | 28 | 73.8 | -9.6 | -13.1% | FIRED_LIVE:10, FIRED_SHADOW_ONLY:10, NO_SETUP:64 |
| UNRESOLVED | 15 | 53.7 | -34.2 | -63.7% | FIRED_LIVE:3, FIRED_SHADOW_ONLY:7, NO_SETUP:35 |
| Variation | 12 | 55.4 | -18.1 | -32.6% | FIRED_LIVE:2, FIRED_SHADOW_ONLY:10, NO_SETUP:22 |

## 20 Largest Missed Moves

| # | Session | Dir | Pts | Time | Status | Day Type |
|---|---------|-----|-----|------|--------|----------|
| 1 | 2026-06-10 | DOWN | 175.0 | 22:40-23:00 | NO_SETUP | Trend |
| 2 | 2026-06-10 | UP | 143.2 | 20:40-21:25 | NO_SETUP | Trend |
| 3 | 2026-06-10 | DOWN | 103.8 | 18:45-18:50 | NO_SETUP | Trend |
| 4 | 2026-06-05 | DOWN | 93.5 | 18:35-21:45 | NO_SETUP | Trend |
| 5 | 2026-06-25 | DOWN | 66.5 | 16:35-16:45 | NO_SETUP | Normal |
| 6 | 2026-06-25 | UP | 62.2 | 17:00-17:10 | NO_SETUP | Normal |
| 7 | 2026-06-25 | DOWN | 54.0 | 16:45-16:55 | NO_SETUP | Normal |
| 8 | 2026-09-16 | DOWN | 52.2 | 21:40-21:50 | NO_SETUP | UNRESOLVED |
| 9 | 2026-06-01 | UP | 47.0 | 16:30-22:30 | NO_SETUP | Normal |
| 10 | 2026-06-29 | DOWN | 45.5 | 16:55-17:05 | NO_SETUP | Trend |
| 11 | 2026-06-18 | DOWN | 44.8 | 16:30-16:40 | FIRED_SHADOW_ONLY | Normal |
| 12 | 2026-06-29 | UP | 44.2 | 17:20-17:30 | NO_SETUP | Trend |
| 13 | 2026-07-31 | DOWN | 44.2 | 16:35-16:45 | FIRED_SHADOW_ONLY | Trend |
| 14 | 2026-09-03 | UP | 43.2 | 17:55-18:10 | NO_SETUP | Trend |
| 15 | 2026-09-16 | DOWN | 42.5 | 22:00-22:10 | FIRED_SHADOW_ONLY | UNRESOLVED |
| 16 | 2026-09-16 | UP | 42.2 | 21:35-21:40 | NO_SETUP | UNRESOLVED |
| 17 | 2026-06-29 | DOWN | 41.8 | 17:05-17:15 | NO_SETUP | Trend |
| 18 | 2026-07-23 | UP | 41.8 | 16:30-16:40 | NO_SETUP | UNRESOLVED |
| 19 | 2026-06-24 | UP | 40.2 | 22:50-23:00 | NO_SETUP | UNRESOLVED |
| 20 | 2026-06-30 | UP | 39.8 | 18:00-20:00 | NO_SETUP | Trend |

## Candidate Branches

Groups of missed moves + losses by (day_type, phase, zone, extension, dir_vs_move), N >= 15.

| Group Key | N | Missed Pts | Loss $ | Proposed Branch |
|-----------|---|------------|--------|----------------|
| Trend / DOWN / NO_SETUP | 33 | 1112.8 | $0 | expr: Trend.DOWN.filter |
| Trend / UP / NO_SETUP | 31 | 948.8 | $0 | expr: Trend.UP.filter |
| UNRESOLVED / UP / NO_SETUP | 18 | 539.8 | $0 | expr: UNRESOLVED.UP.filter |
| UNRESOLVED / DOWN / NO_SETUP | 17 | 450.5 | $0 | expr: UNRESOLVED.DOWN.filter |
| Variation / SHORT / LOSS:zone=?,ext=? | 16 | 0.0 | $1165 | expr: Variation.SHORT.filter |
| Normal / UP / NO_SETUP | 15 | 419.8 | $0 | expr: Normal.UP.filter |

## TREND_STEP and RE_ACCEPTANCE Analysis

- Trend/Normal days: 39 sessions
- Missed moves with shadow setups: 15
- Total model $ (shadow, fixed eval): $594.50

## Summary

- Total sessions: 66
- Total range (sum): 4030.0 pts
- Total captured (live, fixed model): -1062.0 pts
- Overall captured/range: -26.4%
- Total missed moves (top 3 per session): 180

## Model vs Broker Gap Explanation

- **(a) Full ladder (5 contracts):** 35 trades
- **(a) Partial size (<5 contracts):** 3 trades
- **(b) Live losses (MAE_SCRATCH/BE/STRUCTURE):** 58
- **(b) Model full-stop events:** 43
- **(c) No matching bar (Globex entries):** 148
- **pts_total:** 164.9
- **pts_per_contract:** 0.90
