# Dalton Context Simulation — 08-10..08-21 (10 sessions, 6 contracts)

**Ruling:** Michael 23.08 — "לפני התיקונים — להריץ סימולציה"
**Script:** `scripts/replay_dalton_context.py`
**Data:** `v9_bars_5min_woodies` RTH bars, `v9_trades` books

## Summary Table — Per Session

| Date | Day Type | IB | Transitions | BOOKS | L1-FIXES | L2-DALTON | ORACLE |
|------|----------|-----|-------------|-------|----------|-----------|--------|
| 08-10 | Normal | 20.2 | 3 | -$63.75 | -$597.00 | -$301.50 | +$1,474.50 |
| 08-11 | Normal_Variation | 20.8 | 2 | $0.00 | -$82.50 | **+$310.50** | +$1,294.50 |
| 08-12 | Normal | 30.5 | 2 | +$73.75 | -$594.00 | -$301.50 | +$1,242.00 |
| 08-13 | Normal | 51.8 | 1 | +$68.75 | -$396.00 | **+$103.50** | +$2,344.50 |
| 08-14 | Normal_Variation | 17.0 | 2 | -$135.00 | +$12.00 | **+$207.00** | +$1,054.50 |
| 08-17 | Trend_Normal | 20.2 | 2 | +$103.75 | -$189.00 | +$3.00 | +$1,099.50 |
| 08-18 | Normal_Variation | 18.8 | 2 | $0.00 | -$490.50 | -$97.50 | +$987.00 |
| 08-19 | Normal_Variation | 25.5 | 2 | -$51.25 | -$1,093.50 | -$195.00 | +$1,617.00 |
| 08-20 | Normal_Variation | 24.8 | 4 | $0.00 | -$1,297.50 | -$502.50 | +$1,684.50 |
| 08-21 | Normal_Variation | 19.8 | 2 | -$107.50 | +$21.00 | -$94.50 | +$1,362.00 |

## Totals

| Layer | Week 08-17..21 | Week 08-10..14 | ALL 10 sessions |
|-------|----------------|----------------|-----------------|
| **BOOKS** | -$55.00 | -$56.25 | **-$111.25** |
| **L1-FIXES** | -$3,049.50 | -$1,657.50 | **-$4,707.00** |
| **L2-DALTON** | -$886.50 | +$18.00 | **-$868.50** |
| **ORACLE** | +$6,750.00 | +$7,410.00 | **+$14,160.00** |

## Key Finding: Dalton Filter Value

The Dalton context layer **reduces losses by 82%** (L1: -$4,707 → L2: -$868.50).  It does
this by filtering out trades in the wrong location/state:
- Balance + wrong location (mid-value) → skip
- Discovery + against direction → skip

But L2 is still **net negative** over these 10 sessions.  The filter removes bad trades
better than it selects good ones.

## Dalton Dynamic — Transition Log

Average **2.2 transitions/session** (range: 1-4).  Transitions:
- `ib_lock` → BALANCE (every day at bar 12)
- `break_up/down` → DISCOVERY (8/10 days had at least one IB break)
- `dual_break` → back to BALANCE (2/10 days: 08-10, 08-20)
- `range_expansion` → DISCOVERY (1/10: 08-20)

**Problem: IB break ≠ DISCOVERY.**  The state machine calls every IB break "DISCOVERY",
but 7/8 break days were classified post-hoc as Normal_Variation — an extension within
a broader balance, not true price discovery.  True Dalton DISCOVERY requires:
- **Acceptance** beyond the IB (multiple closes with volume, not just a poke)
- **Value migration** (the developing value area shifts, not just the range)
- **No return** to the IB range within a few bars

## Convergence Test

| Date | Post-hoc | Dalton Dynamic | Match |
|------|----------|----------------|-------|
| 08-10 | Normal | BALANCE (Variation) | broad ✓ |
| 08-11 | Normal_Variation | DISCOVERY (Trend_Normal) | ✗ |
| 08-12 | Normal | DISCOVERY (Trend_Normal) | ✗ |
| 08-13 | Normal | BALANCE (Normal) | ✓ |
| 08-14 | Normal_Variation | DISCOVERY (Trend_Normal) | ✗ |
| 08-17 | Trend_Normal | DISCOVERY (Trend_Normal) | ✓ |
| 08-18 | Normal_Variation | DISCOVERY (Trend_Normal) | ✗ |
| 08-19 | Normal_Variation | DISCOVERY (Trend_Normal) | ✗ |
| 08-20 | Normal_Variation | DISCOVERY (Trend_Normal) | ✗ |
| 08-21 | Normal_Variation | DISCOVERY (Trend_Normal) | ✗ |

**Convergence: 30% (3/10).**  Michael: "if it doesn't converge, your definition is wrong."
The definition IS wrong: IB-break → DISCOVERY is too aggressive.  A Variation day breaks
the IB on one side but never establishes acceptance — it's still in balance, just with a
wider range.  Fix: require **acceptance** (2+ consecutive closes beyond the break level)
before declaring DISCOVERY.

## Limitations (Honesty Disclosure)

- **Fill simulation:** bar close, not intra-bar. Biased optimistic for entries.
- **Slot competition:** sim allows unlimited trades; live has 1 slot. Biased optimistic.
- **Slippage:** 1 tick/side uniform. Real slippage varies.
- **Value area:** IB used as proxy (no live TPO VAH/VAL in historical replay).
- **No TREND_STEP shadow:** not modeled in L1 (would reduce its losses).
- **L1 is a naive trigger-only sim**, not the actual Monday bundle with all gates.

## Conclusion

1. **Dalton filter is valuable** — cuts losses 82% vs raw triggers.
2. **But the state machine definition is wrong** — 30% convergence.
3. **The fix:** replace IB-break → DISCOVERY with acceptance-based transitions.
   This is exactly what `S1_STRUCTURAL_BINARY_V1` (map §B) does.
4. **The Dalton layer should be built ON TOP of the binary classifier**, not separately.
   The classifier already computes acceptance, sides, value migration — exactly the
   inputs the Dalton state machine needs.

*Generated 2026-08-24 by cc-macbook. Script: `scripts/replay_dalton_context.py`*
