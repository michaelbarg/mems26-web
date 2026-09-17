# Gap Analysis Report
Generated: 2026-09-17 11:42
Sessions analyzed: 75

## By Day Type

| Day Type | N | Avg Range | Avg Captured (pts) | Captured/Range | Move Status Distribution |
|----------|---|-----------|--------------------|---------------|-------------------------|
| Nontrend | 1 | 72.0 | 0.0 | 0.0% | FIRED_SHADOW_ONLY:1, NO_SETUP:2 |
| Normal | 9 | 65.2 | -11.6 | -17.8% | FIRED_LIVE:1, FIRED_SHADOW_ONLY:1, NO_SETUP:25 |
| Trend_Normal | 7 | 77.1 | -10.1 | -13.2% | FIRED_LIVE:3, FIRED_SHADOW_ONLY:1, NO_SETUP:17 |
| UNKNOWN | 42 | 70.1 | -15.1 | -21.6% | FIRED_LIVE:7, FIRED_SHADOW_ONLY:27, NO_SETUP:89 |
| Variation | 15 | 60.1 | -14.6 | -24.2% | FIRED_LIVE:5, FIRED_SHADOW_ONLY:2, NO_SETUP:38 |

## 20 Largest Missed Moves

| # | Session | Dir | Pts | Time | Status | Day Type |
|---|---------|-----|-----|------|--------|----------|
| 1 | 2026-06-10 | DOWN | 175.0 | 22:40-23:00 | NO_SETUP | None |
| 2 | 2026-06-10 | UP | 143.2 | 20:40-21:25 | NO_SETUP | None |
| 3 | 2026-07-29 | DOWN | 134.5 | 21:40-22:00 | NO_SETUP | None |
| 4 | 2026-06-10 | DOWN | 103.8 | 18:45-18:50 | NO_SETUP | None |
| 5 | 2026-06-11 | UP | 99.5 | 20:20-20:30 | NO_SETUP | UNKNOWN |
| 6 | 2026-06-05 | DOWN | 93.5 | 18:35-21:45 | NO_SETUP | Variation |
| 7 | 2026-06-09 | DOWN | 91.8 | 17:20-17:40 | NO_SETUP | UNKNOWN |
| 8 | 2026-07-29 | DOWN | 88.0 | 16:30-19:15 | NO_SETUP | None |
| 9 | 2026-07-29 | UP | 84.8 | 22:10-22:25 | NO_SETUP | None |
| 10 | 2026-06-11 | DOWN | 82.5 | 16:50-17:00 | NO_SETUP | UNKNOWN |
| 11 | 2026-06-17 | DOWN | 79.2 | 22:10-22:35 | NO_SETUP | None |
| 12 | 2026-06-17 | DOWN | 76.2 | 20:55-21:05 | NO_SETUP | None |
| 13 | 2026-06-09 | DOWN | 66.5 | 17:40-17:50 | NO_SETUP | UNKNOWN |
| 14 | 2026-06-25 | DOWN | 66.5 | 16:35-16:45 | NO_SETUP | Normal |
| 15 | 2026-06-09 | DOWN | 62.5 | 18:20-18:30 | NO_SETUP | UNKNOWN |
| 16 | 2026-06-26 | DOWN | 62.5 | 22:45-22:55 | NO_SETUP | Variation |
| 17 | 2026-06-25 | UP | 62.2 | 17:00-17:10 | NO_SETUP | Normal |
| 18 | 2026-06-12 | UP | 57.0 | 17:50-18:00 | NO_SETUP | UNKNOWN |
| 19 | 2026-07-28 | UP | 55.8 | 17:20-17:25 | NO_SETUP | None |
| 20 | 2026-07-24 | UP | 54.5 | 17:35-17:40 | NO_SETUP | UNKNOWN |

## Candidate Branches

Groups of missed moves + losses by (day_type, phase, zone, extension, dir_vs_move), N >= 15.

| Group Key | N | Missed Pts | Loss $ | Proposed Branch |
|-----------|---|------------|--------|----------------|
| UNKNOWN / DOWN / NO_SETUP | 47 | 1874.5 | $0 | expr: UNKNOWN.DOWN.filter |
| UNKNOWN / UP / NO_SETUP | 42 | 1459.0 | $0 | expr: UNKNOWN.UP.filter |
| Variation / UP / NO_SETUP | 22 | 608.0 | $0 | expr: Variation.UP.filter |
| UNKNOWN / DOWN / FIRED_SHADOW_ONLY | 18 | 520.5 | $0 | expr: UNKNOWN.DOWN.filter |
| Variation / DOWN / NO_SETUP | 16 | 475.2 | $0 | expr: Variation.DOWN.filter |
| Variation / SHORT / LOSS:zone=?,ext=? | 16 | 0.0 | $1165 | expr: Variation.SHORT.filter |

## TREND_STEP and RE_ACCEPTANCE Analysis

- Trend/Normal days: 16 sessions
- Missed moves with shadow setups: 2
- Total model $ (shadow, fixed eval): $88.75

## Summary

- Total sessions: 74
- Total range (sum): 5044.8 pts
- Total captured (live, fixed model): -1030.0 pts
- Overall captured/range: -20.4%
- Total missed moves (top 3 per session): 203
