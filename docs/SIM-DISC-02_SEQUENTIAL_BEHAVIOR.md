# SIM-DISC-02: Sequential Filter Behavior

**Date:** 2026-05-05
**Investigator:** Claude Code (V8.4.0-RESEARCH-2)

---

## Question

When many setups arrive simultaneously, does MDS sequential filter pick the same ones as production?

## Findings

### MDS Sequential Filter Behavior

```
Before sequential filter: 4,996 trades eligible
After sequential filter:  46 trades taken
Blocked by overlap:       4,950 (99.1%)
```

The sequential filter (`apply_sequential_filter`) enforces one-trade-at-a-time with 60-minute hold assumption. Over 5 days of data, this means ~9-10 trades per day maximum.

### Sequential Filter WR (outcome-based)

```
All setups (no filter):     WR = 40.7% (outcome)
Sequential subset (46):     WR = 47.8% (outcome)
```

The sequential filter provides +7.1pp WR improvement by selecting from clusters.

### Cluster Analysis

Searching for 10+ setups arriving within 60 seconds: **0 clusters found**.

This is because setups are emitted every ~60 seconds (the re-emission cycle). They arrive in a steady stream, not bursts. However, within 300-second windows:

```
3,098 duplicate clusters (300s window)
Total stale copies: 7,582 (beyond first occurrence)
```

### How Sequential Filter Selects

The filter works by timestamp order:
1. Sort all setups by `ts`
2. Accept first setup
3. Reject all setups until previous trade's estimated close (ts + 3600s)
4. Accept next eligible setup
5. Repeat

**It always picks the FIRST setup in a cluster** — not the best-scored one.

### Production Behavior

Production today: 74 total setups detected, 57 closed trades.
This implies production is taking MORE trades per day (57 vs MDS sequential's ~10/day).

Key difference: **Production does NOT enforce strict one-at-a-time.**
It appears to allow new entries once prior trade hits C1 or stop, not after a fixed 60-min window.

### Production vs MDS Selection Example

Cannot do direct comparison because:
- Today's API data lacks `entry_price_hypothetical` (field is NULL for today's entries)
- MDS dataset ends at May 3, no overlap with today

### Impact Assessment

| Factor | Impact |
|--------|--------|
| MDS takes ~10 trades/day | vs production's ~57/day → MDS is much more selective |
| MDS always picks first in cluster | May miss better-scored later setups |
| Production allows concurrent entries? | Unclear — needs Phase 3.3 code review |

## Verdict

The sequential filter is not the primary gap source. It actually HELPS MDS (+7.1pp WR improvement).

The real difference is **trade volume**: production takes 5-6x more trades per day than MDS sequential would allow. Those extra trades appear to be lower quality (dragging WR down).

### Recommendation

Production's higher trade count (57/day vs MDS's 10/day) suggests either:
1. Production doesn't enforce sequential properly
2. Production uses shorter hold time assumptions
3. Multiple setups are being opened simultaneously

This needs investigation in Phase 3.3.
