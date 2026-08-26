# FAILED_BREAK §D — 33 Sessions (Variation+Normal+Neutral) · 2026-08-26

## Verdict: **Variant A (VA edges) POSITIVE — +$118.20, 56% win rate**

## Three Variants Compared

| Variant | Edge | Total | Median/day | Days+ | Win% | Cands |
|---------|------|-------|-----------|-------|------|-------|
| **A (VA)** | VAH/VAL | **+$118.20** | **$0.00** | **16/33** | **56%** | **48** |
| B (Session) | Session hi/lo | $0.00 | $0.00 | 0/33 | 0% | 0 |
| C (IB) | IB edges | +$48.75 | -$37.50 | 12/33 | 49% | 35 |

**Variant B produced 0 candidates** — by definition, the session extreme IS the probe;
there's no "bar that probed BEYOND the session extreme" because that bar sets the new
extreme.

## Variant A — Per Day

| Date | Day Type | P&L | Trades |
|------|----------|-----|--------|
| 07-07 | Normal_Variation | +$258.75 | S +$157(T1) · L +$101(T1) |
| 07-14 | Normal_Variation | +$213.75 | S +$43(T1) · L +$170(T1) |
| 07-15 | Normal_Variation | +$292.50 | L +$123(T1) · S +$168(T1) |
| 08-13 | Normal | +$363.75 | S +$180(T1) · L +$183(T1) |
| 08-21 | Normal_Variation | +$253.20 | L +$146(T1) · S +$106(T1) |
| **08-25** | Normal_Variation | **+$166.80** | **L +$95(T1) · S +$71(T1)** |
| ... | | | (16 positive, 13 negative days) |

**25.08 anchor: PASSES** — 2 failed-break trades, both win at T1.

## Why This Works When VA_FADE Didn't

VA_FADE entered on the **first probe** — the bar touching the edge. Failed-break
enters on the **bar AFTER the failed attempt** — the confirmation that the break
didn't work. This is the one-bar delay that the extreme detection audit identified
as the missing piece (83-88% reversal, but entry too early).

The three-step sequence (attempt → failure → return) is exactly the confirmation
step that REACTIVE provides for its patterns, applied to edge fading.

## Variant C (IB edges) — Viable But Weaker

+$48.75, 49% win, 35 candidates. IB edges are less dynamic than VA — they're
fixed at 10:30 ET while VA shifts with the developing profile. But it's still
positive and could complement VA when TPO data is unavailable.

## Recommendation

**Variant A (VA edges) to shadow.** Flag `FAILED_BREAK_VA_V1`, OFF until
§D is verified by cowork. The entry mechanics (3-step failed break) are
sound and the edge source (live TPO VAH/VAL) is the same proven path.

*cc-macbook · 2026-08-26. Script: `backend/v9/systems/failed_break.py`*
