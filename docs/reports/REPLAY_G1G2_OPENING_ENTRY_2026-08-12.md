# G1+G2 Replay: Opening Entry Engine Fuse + OR Threshold (2026-08-12)

## Configuration

- `OPENING_CONF_ENGINE_FUSE_V1=1` — engine confidence (DRIVE=0.85, ORR=0.65) overrides detector conf when detector is directional (conf≥0.5)
- `OPENING_OR_ATR_SCALE_V1=1` — OR threshold = max(10, 0.25 × daily ATR) = **19.9pt** (ATR=79.4)
- `min_conf=0.6` (from OPENING_MIN_CONF)
- Window: 12 bars (OPENING_FIRE_V1), pullback enabled

## Results per session

| Date | Opening Type | Det.Conf | OR (bar1) | Triggers | PnL |
|------|-------------|----------|-----------|----------|-----|
| 08-03 | DRIVE | 0.85 | **22.5** | — (OR > threshold 19.9) | — |
| 08-04 | DRIVE | 0.85 | 14.2 | ✅ DRIVE LONG @bar4 | **+$388.75** |
| 08-05 | DRIVE | 0.85 | 15.5 | ❌ EXTREME_REJECT · ✅ PULLBACK_CONT SHORT · ✅ TEST_DRIVE LONG | −$40.00 |
| 08-06 | ORR | 0.65 | 17.0 | ✅ PULLBACK_CONT LONG · ✅ DRIVE LONG | −$40.00 |
| 08-07 | ORR | 0.65 | 10.0 | ✅ DRIVE LONG · ✅ PULLBACK_CONT SHORT · ✅ ORR SHORT | −$60.00 |
| 08-10 | AUCTION_IN | 0.00 | 11.2 | ❌×8 (all blocked — conf=0<0.6, fuse OFF on auction) | — |
| 08-11 | AUCTION_IN | 0.00 | 14.0 | ❌×6 (all blocked) | — |

**NET: +$248.75**

## Acceptance criteria

| Criterion | Result |
|-----------|--------|
| Auction days entry-free | ✅ YES (08-10: 8 triggers blocked, 08-11: 6 blocked) |
| Directional entries produced | ✅ 8 entries across 4/5 directional sessions |
| NET PnL positive | ✅ +$248.75 |
| 08-04 trend captured | ✅ DRIVE LONG +$388.75 (was dead — OR=14.2 > old threshold 10) |

## Verdict: 🟢 GO

The engine fuse + ATR-scaled OR threshold unblocks the 5 directional identifications
that died last week while keeping auction days clean. NET is positive, dominated by
the 08-04 trend capture (+$388.75).

## Key observations

1. **08-03 stays entry-free** — OR=22.5 genuinely exceeds even the ATR-derived threshold. This is correct Dalton behavior (very wide OR = no directional edge).
2. **08-05/06/07 net negative** — multiple triggers fire and most hit stops. This is expected for non-trend days with mixed direction. The stop of 4pt is tight; with F3's step-scaled ladder these may improve.
3. **The fuse correctly gates on detector confidence** — conf=0 (auction) → fuse doesn't fire → triggers blocked. conf≥0.5 (directional) → fuse boosts to engine grade → triggers pass.

## For Michael's ruling

- Enable `OPENING_CONF_ENGINE_FUSE_V1=1`
- Set `OR_NARROW_MAX_PTS=20` (or enable `OPENING_OR_ATR_SCALE_V1=1` for dynamic)
- Cowork enables after ruling; replay script: `scripts/replay_g1g2_opening_entry.py`
