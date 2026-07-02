# CC — Build the Structural Profit-Target Resolver (per verified research)

**Date:** 2026-07-01 · **Owner:** Michael · **Prepared by:** Cowork
**Contract:** `docs/handoff/CC_HANDOFF_CONTRACT.md` — command + raw output (Rule 5), anti-tautological tests, NOT-DONE.
**Spec:** the external research result (pasted 2026-07-01) — the full AMT/Dalton + Williams-fractal + IB-extension + POC + chandelier spec. Brief that produced it: `docs/spec_authority/RESEARCH_STRUCTURAL_TARGET_RESOLVER_TOOLCONSTRAINED_2026-07-01.md`.
**Why:** today's targets are broken — ZLR **+4.75/+9.5** (too close), HTLB/REACTIVE SHORT **−92/−140** (unreachable), 267 = "no target." Replace the R-multiple + pattern-height logic with a structural resolver.

## Cowork verification (Rule 2 — real data, use these, not the research priors)
- **ATR₅ₘ(14, Wilder) = 7.07 pts** (research prior ~6 → confirmed; the "20–40" is a units error, ignore).
- **24h daily range avg (14d) = 100.2 pts** — this is 24h; **measure RTH-only daily ATR live** for the cap (prior ~55 is likely low for us; expect ~60–80).
- **VA width today (VAH−VAL) = 38 pts** (research assumed IBw~20 → ours is wider; extensions/caps scale up).
- Levels available + verified live: VAH/VAL/POC (`v9_tpo_history`), IB (day_type), swings (computable from bars), CVD, ATR.

## Build order (research recommendation, endorsed)
### Step 1 · Swing-completion T1 (highest-leverage, pure geometry) — flag `STRUCTURAL_TARGETS_V2` (default OFF, SHADOW)
- **T1 = first confirmed NEW swing** in the trade direction after entry: Williams 5-bar fractal, **K=2** (high[i] > high[i±1..2] for long / low[i] < low[i±1..2] for short), **close-confirmed** (reject wick-only sweeps).
- **Noise floor:** skip a swing whose leg < `0.5 × ATR₅ₘ` (≈3.5 pts for us) → go to the next swing. *(Kills the +4.75 tiny T1.)*
- **Cap:** `T1 ≤ min(2 × ATR₅ₘ, 0.30 × dATR_RTH)` ≈ **14 pts** for us; if the first swing is farther, place T1 **at the cap**. *(Kills the +92 far T1.)*

### Step 2 · Day-type target table for C2/C3 (route EVERY pattern through this — not the pattern's own measured move)
| Day-type | C1 | C2 | C3 + trail |
|---|---|---|---|
| Trend_Normal | first-swing | 1× IB-ext (or nearer VA/PDH first) | hold-to-close, swing/chandelier trail |
| Trend_DD | first-swing | 2nd-distribution POC (else 1× IB-ext) | trail behind structure |
| Variation | ½ IB-ext (or first-swing if nearer) | 1× IB-ext | 2× IB-ext, trailed |
| Normal | IB-center | opposite VA edge | opposite IB edge, no runner |
| Neutral_Extreme | POC | opposite VA edge | winning extreme, light trail |
| Neutral_Center | POC | opposite IB edge | none (flatten C2) |
| Nontrend | POC | none | skip / scalp |
- **Precedence for "nearest structure":** among lines beyond the current target, in-direction, within cap → pick **nearest** ("first structure wins"); tie-band ~0.25×ATR₅ₘ broken by weight VA/POC > IB > prior-day > overnight > IB-ext fallback.
- **Michael's C2/C3 split (2026-07-01 — overrides the research where C2 was the VA edge):** **C2 = the nearest structure that is CLOSER than the VA edge** (POC · IB-center · IB-edge · intermediate swing / IB-½ext) — bank the middle contract at a high-probability nearer level. **C3 = the VA edge (VAH long / VAL short) as the runner's target, trailed** — give the last contract the room to reach the value edge. So across day-types the VA edge shifts from C2 to **C3**; C2 takes the nearest inner structure (POC/IB-center/next-swing). Reversal patterns: C2 = nearest structure toward the mean, C3 = POC/opposite VA edge (still capped).
- **Reversal patterns (REACTIVE, GHOST, VEGAS, FAMIR, HTLB, Doubles, HnS): DELETE pattern-height measured-moves.** Target nearest-opposing-structure / mean-reversion: first-swing → POC → opposite VA edge, each capped.

### Step 3 · Hard-cap post-processor (on any computed target)
- `T1_cap = min(2×ATR₅ₘ, 0.30×dATR)` · `runner_cap = min(1.5×dATR, 3×IBw)` · `nonrunner_C2_cap = 1.0×dATR` · reversal ≤ opposite VA edge.
- If `target_distance > cap` → **snap to the nearest structural line inside the cap.** *(This alone would have fixed HTLB −92 → nearest structure.)*

### Step 4 · Calibrate [K] on our bars (order)
(a) measure ATR₅ₘ (≈7) + RTH dATR live; (b) tune K + swing_min_leg for T1 hit-rate; (c) tune runner_cap + chandelier m/lookback for trend capture; (d) per-day-type scale fractions.

## Tests (anti-tautological)
- Fractal: on a synthetic 4-swing series, T1 = the first confirmed swing (K=2), not the entry-bar extreme.
- Cap: any pattern with a raw target > cap → snapped to the nearest structural line ≤ cap. **Feed today's HTLB (−92) → result ≤ opposite VA edge.**
- Noise floor: a <3.5pt first swing is skipped to the next.
- Per-day-type: Normal LONG → C1=IB-center, C2=VAH, C3=IB-high; Trend_Normal → C1=first-swing, C3=trailed (not fixed).
- Flag OFF → current R-based/structural behavior byte-identical.

## Verification (Rule 5, SHADOW)
Replay today's fires: ZLR (was +4.75/+9.5) → first-swing T1 + structural C2/C3; HTLB SHORT (was −92/−140) → capped to nearest structure. Paste the before/after targets. Then a live SHADOW day: no target exceeds its cap; T1 = first swing on every fire.

## NOT-DONE
- ❌ Do NOT enable live without SHADOW validation + Michael sign-off.
- ❌ Do NOT keep pattern-height measured-moves for reversals.
- ❌ Do NOT trust the research point-priors over our measured ATR (7.07) — calibrate to our feed.
- ❌ CVD = divergence/exhaustion confirmation for the runner only, never a target generator.
- ❌ Pre-IB-lock (day-type not stable): use the conservative location-day template until movement-day criteria confirm.
