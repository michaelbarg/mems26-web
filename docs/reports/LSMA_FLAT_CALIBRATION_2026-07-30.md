# lsma_flat Gate Calibration Study (P3, 2026-07-30)

## Data

60 blocks across 4 days (07-23, 07-24, 07-28, 07-29). Current threshold: |slope| < 0.25 pts/bar.

## Results

| Verdict | Count | % |
|---|---|---|
| SAVED (would have stopped out) | 49 | 82% |
| COST (would have reached +1R) | 11 | 18% |
| UNDECIDED | 0 | 0% |

**Net: gate is right 82% of the time. Saved 38 more trades than it cost.**

## Key Observations

1. **07-28 dominates** — 42/60 blocks (70%) from a single day, all SAVED, all at entry=7600 (boot-replay phantom signals at @06:23). These aren't real trading decisions — they're phantom fires from the ts-skew bug that the gate coincidentally blocked. **Excluding 07-28 phantoms: 7 SAVED / 11 COST = 39% — the gate COSTS more than it saves on real signals.**

2. **The 07-29 miss** — ZLR LONG blocked at slope 0.2133 (threshold 0.25), market rose 29pt in 10 min. This is the case Michael cited. At slope 0.21, the LSMA is nearly trending — the threshold is too aggressive.

3. **Slope distribution of COST cases:**
   - slope 0.21 (1 case) — near threshold, real winner
   - slope -0.14 to -0.17 (4 cases) — counter-slope signals blocked, some would have worked
   - slope 0.04-0.11 (4 cases) — genuinely flat, but the trades would have worked
   - slope -0.15 (2 cases at 7600 phantom entry) — phantom, not real

## Recommendations (data-backed, Michael decides)

**Option A — Lower threshold to 0.15:** Would have released the 07-29 ZLR (slope 0.21 > 0.15). Still blocks the genuinely flat (< 0.15). Risk: also releases some of the 0.16-0.17 range losers.

**Option B — Scope reduction from ALL to S4-only:** The gate currently blocks ALL patterns on flat LSMA. S2 patterns (REACTIVE, HNS) are already direction-gated by the playbook — the LSMA gate is a redundant second check. Reducing scope to S4 (ZLR, GB100, GHOST, etc.) removes the redundancy without weakening S4's direction discipline.

**Option C — Keep as-is (0.25, ALL):** On real signals excluding phantoms, the gate costs more than it saves (7 saved vs 11 cost = 39%). But some of those "costs" occurred on 07-24 at entry=7600 which is another phantom class. The true data set is too small (15 real decisions) for a confident threshold change.

**Option D — Turn off entirely:** 0-saved/2-cost today. But on 07-23 it saved 4 genuine losers. Too early to kill.

## Raw Evidence (Rule-5)

```
$ grep lsma_flat gateway_decisions.jsonl | wc -l
60

SAVED:     49 (42 phantoms from 07-28 boot-replay)
COST:      11
Real signal net: 7 saved / 11 cost = 39% (gate costs more on real signals)
Assumption: 12pt fixed risk, 24-bar window. Stated, not hidden.
```
