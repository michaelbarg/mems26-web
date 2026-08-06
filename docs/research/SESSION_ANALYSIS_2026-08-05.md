 # Session Analysis -- 2026-08-05

Generated: 2026-08-05  
Database: `postgresql://localhost/mems26`  
All timestamps shown in IL (UTC+3) unless noted.

---

## 1. All Trades on 2026-08-05

10 trades fired (2 live, 8 shadow). All SHORT except one LONG. Day type: Variation (most of session), briefly Trend\_DD.

| ID  | Mode   | Dir   | Entry    | Stop     | T1      | T2      | T3      | PnL USD  | Outcome | Exit Reason | System |
|-----|--------|-------|----------|----------|---------|---------|---------|----------|---------|-------------|--------|
| 626 | shadow | SHORT | 7791.25  | 7791.00  | 7786.00 | 7783.75 | 7759.00 | +28.75   | WIN     | STOP\_HIT (trail) | S2 |
| 627 | **live** | SHORT | 7791.25 | 7791.00 | 7785.50 | 7779.75 | 7774.25 | +171.25  | WIN     | T3\_HIT     | S2 |
| 628 | shadow | SHORT | 7792.00  | 7791.75  | 7785.50 | 7774.50 | 7762.00 | +35.00   | WIN     | STOP\_HIT (trail) | S2 |
| 629 | shadow | SHORT | 7784.50  | 7784.50  | 7774.25 | 7769.25 | 7766.75 | +216.25  | WIN     | T3\_HIT     | S4 |
| 630 | shadow | SHORT | 7783.00  | 7783.00  | 7774.25 | 7769.25 | 7756.00 | +43.75   | WIN     | STOP\_HIT (trail) | S4 |
| 631 | shadow | SHORT | 7782.25  | 7782.25  | 7773.75 | 7759.50 | 7756.75 | +283.75  | WIN     | T3\_HIT     | S4 |
| 632 | shadow | SHORT | 7774.50  | 7773.25  | 7759.50 | 7752.25 | 7747.25 | +192.50  | WIN     | STOP\_HIT (trail) | S2 |
| 633 | **live** | SHORT | 7774.50 | 7773.25 | 7759.50 | 7757.25 | 7743.00 | +75.00   | WIN     | STOP\_HIT (trail) | S2 |
| 634 | shadow | SHORT | 7768.75  | 7768.75  | 7759.50 | 7752.25 | 7747.25 | +128.75  | WIN     | STOP\_HIT (trail) | S4 |
| 635 | shadow | LONG  | 7772.25  | 7767.75  | 7810.88 | 7800.25 | 7814.25 | -67.50   | LOSS    | STOP\_HIT   | S2 |

### Day P&L Summary

| Segment | Trades | P&L      |
|---------|--------|----------|
| Live    | 2      | +$246.25 |
| Shadow  | 8      | +$861.25 |
| **Total** | **10** | **+$1,107.50** |

Win rate: 9/10 (90%). Only loss was trade #635 (shadow LONG counter-trend).

---

## 2. Trade #633 -- Wrong T2/T3 Impact

### Facts

- Entry: 7774.50 SHORT at 18:25:06 IL, 3 contracts (INITIATIVE\_SHORT, S2)
- Sierra bracket IDs: C1 target=10002, C2 target=10005, C3 target=10008
- **Original t2 sent to Sierra: 7656.00** (stale/placeholder -- 118 pts below entry)
- Corrected t2 via TARGET\_REALISM at 18:56:26: **7656.00 -> 7757.25**

### Management Log Timeline

| Time (IL)  | Action           | Detail                                          |
|------------|------------------|-------------------------------------------------|
| 18:25:06   | ENTRY            | SHORT at 7774.50, stop 7785.00                  |
| 18:49:44   | TARGET\_REALISM  | t1: 7757.75 -> 7758.75                          |
| 18:50:49   | TARGET\_REALISM  | t1: 7758.75 -> 7759.50                          |
| 18:56:24   | T1\_HIT          | C1 exits at 7759.50                             |
| 18:56:24   | SMART\_BE        | Stop: 7785.00 -> 7782.50                        |
| 18:56:26   | TARGET\_REALISM  | **t2: 7656.00 -> 7757.25** (correction applied) |
| 19:00:04   | STRUCT\_TRAIL    | Stop: 7782.50 -> 7781.00                        |
| 19:10:02   | STRUCT\_TRAIL    | Stop: 7781.00 -> 7778.50                        |
| 19:15:04   | STRUCT\_TRAIL    | Stop: 7778.50 -> 7778.25                        |
| 19:20:05   | STRUCT\_TRAIL    | Stop: 7778.25 -> 7775.75                        |
| 19:25:04   | STRUCT\_TRAIL    | Stop: 7775.75 -> 7773.25                        |
| 21:06:03   | STOP\_HIT        | Trail stop 7773.25, fill 7774.50                |

### Did price reach t2 = 7757.25?

**Yes.** Multiple 5-min bars broke below 7757.25 after the correction:

| Bar (IL) | Low      | Below 7757.25? |
|----------|----------|----------------|
| 18:55    | 7754.50  | YES            |
| 19:00    | 7752.25  | YES            |
| 19:05    | 7750.50  | YES (session low) |
| 19:10    | 7750.75  | YES            |
| 19:15    | 7753.75  | YES            |

**But `t2_hit_ts` is NULL in the database.** This confirms the Sierra bracket was not properly updated after TARGET\_REALISM corrected the value. The C2 contract never filled its target order and was instead caught by the trailing stop.

### Cost of Wrong Targets

| Contract | Actual Exit        | Actual PnL  | Correct Exit       | Correct PnL |
|----------|--------------------|-----------  |--------------------| ------------|
| C1       | T1 at 7759.50      | +$75.00     | T1 at 7759.50      | +$75.00     |
| C2       | Trail stop 7774.50 | $0.00       | T2 at 7757.25      | +$86.25     |
| C3       | Trail stop 7774.50 | $0.00       | Trail stop ~7774.50| $0.00       |
| **Total**|                    | **+$75.00** |                    | **+$161.25**|

**Cost of wrong targets: $86.25** (C2 profit left on table).

T3 at 7743.00 was never reached (session low was 7750.50), so t3 error had no additional cost.

### Root Cause

The initial t2 value sent to Sierra was **7656.00** -- likely a stale or uninitialized value. The TARGET\_REALISM corrector identified and fixed it to 7757.25, but the correction either:
1. Did not propagate to the Sierra bracket order (C2 target ID 10005), or
2. Propagated but Sierra did not re-process the modified order in time.

**Action needed**: Verify that TARGET\_REALISM corrections are actually sent to Sierra via order modify. Check if `c2_target_id` (10005) was updated.

---

## 3. Leg Reversal Before T1

### Trade #635 -- LONG counter-trend loss (only candidate)

Trade #635 is the only loss and the only trade where T1 was never hit.

- Entry: 19:30:03 IL, LONG at 7772.25
- Stop: 7767.75 (hit at 19:35 IL, 5 minutes later)
- T1: 7810.875 (38.6 pts above entry -- never reached)
- Day type at entry: **Trend\_DD**

**Day-type direction at entry time:**

| Time (UTC) | Time (IL) | Day Type  | Direction              | Conf |
|------------|-----------|-----------|------------------------|------|
| 16:05      | 19:05     | Trend\_DD | with\_extension(DOWN)  | 0.62 |
| 16:20      | 19:20     | Trend\_DD | with\_extension(DOWN)  | 0.50 |
| 16:25      | 19:25     | Trend\_DD | with\_extension         | 0.25 |
| 16:30      | 19:30     | Variation | with\_extension         | 0.00 |

The trade was **LONG into a DOWN-extending day**. The prevailing leg was DOWN throughout. The day-type writer even downgraded confidence to 0.0 at the exact moment of entry, and the classification flipped from Trend\_DD to Variation -- a sign of structural uncertainty, not a reversal.

**S6 Rule Applicability**: This trade is a textbook case for the proposed rule _"exit (or do not enter) when the leg opposes the trade direction before T1"_. The leg was DOWN and the trade was LONG. Had this rule existed, the $67.50 loss would have been avoided.

### Other trades -- no leg reversal cases

All other 9 trades were SHORT (with-trend in a down-extension day) and all hit T1. No opposing-leg scenarios before T1 existed for any of them. The day was a clean one-directional SHORT session with no leg reversals until the final bar.

---

## 4. Day-Type Writer Gap at 11:45 IL

### Gap Details

The `v9_day_type_state` timestamps are stored without timezone and appear to be **UTC**.

| Entry | Timestamp (UTC) | Equiv ET | Equiv IL | Stage | Day Type     |
|-------|-----------------|----------|----------|-------|--------------|
| 11270 | 11:45:00        | 08:45    | 14:45    | A2    | UNKNOWN      |
| 11271 | 14:00:31        | 11:00    | 17:00    | A3    | Trend\_Normal |

**Gap: 2 hours 15 minutes** (08:45 to 11:00 ET).

This gap covers:
- RTH session open (09:30 ET)
- The **entire Initial Balance formation period** (09:30-10:30 ET)
- 30 minutes of post-IB trading

The writer went from stage A2 (pre-IB) directly to A3 (post-IB) with Trend\_Normal classification, meaning the IB was computed retroactively without any intermediate state updates.

### Comparison with 08-04

On 2026-08-04, the gap was from 06:44 to 13:15 UTC (03:44 to 10:15 ET) -- overnight/pre-market hours where no updates are expected. This is normal.

On 2026-08-05, the gap at 08:45-11:00 ET is **abnormal** -- it covers the most critical classification window of the session.

### Likely Cause

The day-type writer process crashed or hung at 08:45 ET (pre-open warmup entry) and did not recover until 11:00 ET. Possible causes:
- Process crash during bar ingestion at session open
- Connection pool exhaustion
- Unhandled exception in IB calculation path

### Impact

- IB width class was set to EXTREME retroactively (correct given price action)
- Opening type OPEN\_DRIVE was set retroactively
- No real-time day-type signals were available from 08:45 to 11:00 ET
- First trade (#626) fired at 14:40 ET, well after the gap ended, so no direct trading impact

**Action needed**: Add heartbeat/watchdog to day-type writer. If no state update for >5 minutes during RTH, trigger alert and auto-restart.

---

## 5. S7\_SHADOW\_LOG / TSF\_SHADOW\_LOG Tables

### Status: DO NOT EXIST

Checked for any tables matching patterns `%s7%`, `%tsf%`, `%shadow_log%`:

- `v9_s7_shadow_log` -- **does not exist**
- `v9_tsf_shadow_log` -- **does not exist**

The only shadow-related table is `v9_day_type_shadow_transitions` which tracks day-type classification changes, not S7/TSF shadow trade decisions.

### `v9_day_type_shadow_transitions` schema (for reference)

```
id, ts, session_date, session_min, from_type, to_type, trigger,
e_up, e_dn, r_total, ib_w, ib_h, ib_l, vah, val, poc, cvd, price, created_at
```

### M5 Task Required

Create the following tables:
- **`v9_s7_shadow_log`** -- Log S7 (System 7) shadow decisions: signal evaluation, entry/skip reasons, hypothetical PnL
- **`v9_tsf_shadow_log`** -- Log TSF (Trend/Structure/Flow) shadow evaluations and outcomes

These are needed for offline analysis of S7 and TSF signal quality before promoting to live trading.

---

## Summary of Findings

| Topic | Key Finding | Action |
|-------|-------------|--------|
| Day P&L | +$1,107.50 total, +$246.25 live, 90% win rate | None -- strong day |
| Trade #633 targets | Wrong t2 (7656.0) cost $86.25 in missed C2 profit | Fix TARGET\_REALISM -> Sierra propagation |
| Leg reversal / S6 | Trade #635 LONG into DOWN leg = only loss ($67.50) | Implement S6 rule: block/exit on opposing leg before T1 |
| Day-type writer gap | 2h15m gap covering IB formation (08:45-11:00 ET) | Add heartbeat watchdog + auto-restart |
| Shadow log tables | v9\_s7\_shadow\_log and v9\_tsf\_shadow\_log missing | M5 task: create both tables |
