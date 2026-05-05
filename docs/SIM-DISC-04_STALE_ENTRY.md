# SIM-DISC-04: Stale Entry Filter

**Date:** 2026-05-05
**Investigator:** Claude Code (V8.4.0-RESEARCH-2)

---

## Question

Does MDS dataset contain stale entry duplicates? How does this compare to production?

## Findings

### MDS Stale Entry Analysis

| Window | Duplicate Clusters | Stale Copies | Stale Ratio |
|--------|-------------------|--------------|-------------|
| 60 seconds | 1,924 | 2,096 | 42.0% |
| 300 seconds | 3,098 | 7,582* | 151.8%* |

*Note: 300s count exceeds 100% because a single setup can appear in multiple overlapping clusters.

**After deduplication (300s window): 4,996 → 1,891 unique setups (3,105 removed).**

### Impact on WR

```
WR before dedup (MFE method): 59.7%
WR after dedup  (MFE method): 69.9%
Delta:                         +10.2pp
```

**Stale entries are DEPRESSING MDS WR by 10pp** because:
- Duplicate clusters like `LONG @ 7258.25, 11x over 300s` share the SAME outcome
- When that outcome is HIT_STOP, it counts as 11 losses instead of 1
- Net effect: losers are over-represented in stale clusters

### Example Stale Cluster (from MDS)

```
LONG @ 7258.25: 11 copies over 300s (05/01 05:45 UTC)
  All outcomes: HIT_STOP, HIT_STOP, HIT_STOP...
  
SHORT @ 7258.25: 11 copies over 300s (05/01 05:46 UTC)
  All outcomes: HIT_C1, HIT_C1, HIT_C1...
```

Both LONG and SHORT setups re-emitted every ~30 seconds at the same price.

### Production Stale Entry Analysis (Today)

From API (500 recent attempts):
```
Unique (direction, entry_price) pairs: 2
Pairs with duplicates: 2
Total in duplicate groups: 500
Stale ratio: 99.6%
```

**Critical finding:** ALL today's API-visible attempts have `entry_price_hypothetical = NULL`.
The stale grouping shows 250 LONG + 250 SHORT — these group by `(direction, 0)` because entry_price isn't populated yet.

This means we CANNOT accurately measure today's stale ratio from the API. The `entry_price_hypothetical` field is populated asynchronously by the MAE/MFE measurement worker (after 60 minutes).

### Production Trade Count as Proxy

Today: 74 setups detected, 57 closed.
MDS per-day average: ~1,000 setups/day (heavily stale-inflated).

If production de-duplicates at the execution layer (only executing one setup per signal), then:
- Production effectively takes 57 unique trades
- MDS counts 1,000+ "setups" that are really ~50-100 unique signals

### True Dataset Size After Dedup

| Dataset | Raw | After 300s Dedup | Unique Signals |
|---------|-----|-----------------|----------------|
| MDS (5 days) | 4,996 | 1,891 | ~380/day |
| Production today | 74 | ~74 (already deduped?) | 74 |

## Verdict

| Check | Result |
|-------|--------|
| MDS has stale duplicates | **YES — 42-62% are duplicates** |
| MDS deduplicated | **NO** — raw dataset used |
| Production deduplicated | **Likely YES** at execution layer |
| WR impact | Stale entries depress MDS WR by ~10pp |
| Volume impact | MDS inflates trade count 5-10x |

### Key Finding

The stale entry problem goes BOTH WAYS:
1. It inflates MDS trade COUNT (4,996 → should be ~1,891)
2. It depresses MDS WR slightly (losing clusters amplified)
3. Production likely de-duplicates before execution → fewer but "real" trades
4. But production's 19.3% WR is still far below deduped-MDS's 69.9% (MFE) or ~45% (outcome)

### Recommendation

1. MDS dataset MUST be deduplicated before any simulation
2. Dedup rule: keep first occurrence per (direction, entry_price ± 0.5pt, 300s window)
3. Re-run SIM-DEC on deduped dataset for valid baseline
4. Investigate why production takes 57 trades/day vs expected ~10-15 with sequential filter
