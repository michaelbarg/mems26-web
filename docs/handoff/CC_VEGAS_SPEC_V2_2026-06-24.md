# CC Handoff — VEGAS Spec v2: REWRITE to cup-and-handle (Michael's source) 2026-06-24

_Author: Cowork · contract: `docs/handoff/CC_HANDOFF_CONTRACT.md`. CC develops; Cowork verifies. This is a REWRITE, not a gate — the current code is a different pattern._

## The mismatch (severe)
`backend/v9/systems/woodies/patterns/vegas.py` implements **price/CCI DIVERGENCE** (price HH + CCI LH → SHORT; price LL + CCI HL → LONG). Michael's VEGAS is a **cup-and-handle ("ספל וידית") on the CCI** — an entirely different pattern. The code implements NONE of the spec structure. (Result: VEGAS fired once ever, +$54 — it's detecting divergence, not the real pattern.)

## Michael's source spec — VEGAS (reversal, STRATEGIC)
> "A cup-and-handle on the oscillator indicates at least the END of a trend, and a HIGH chance for the start of a NEW trend in the OPPOSITE direction." Note: it's **strategic, not tactical** — it marks an old-trend end (like HTLB). Identify the structure precisely.

**LONG (reverses a downtrend → up):**
1. CCI crosses **below −200** (deep extreme = the cup bottom).
2. CCI **reverses toward 0 (ZL) and reaches at least −100** → forms the "cup" (U-shape: <−200 up to ≥−100).
3. CCI **reverses again and makes a HIGHER LOW, or stays horizontal for ≥3 bars** → the "handle" (a shallow pullback that holds above the cup bottom).
4. **Entry = break of the HIGH between the cup and the handle** (the "rim"/neckline — the peak CCI reached at the end of step 2, before the handle dip).

**SHORT (mirror, reverses an uptrend → down):**
1. CCI crosses **above +200**.
2. CCI reverses toward 0 and reaches **at least +100** (the inverted cup).
3. CCI makes a **LOWER HIGH or horizontal for ≥3 bars** (the handle).
4. **Entry = break of the LOW between cup and handle** (the rim).

## Fix — flag `VEGAS_SPEC_V2` (default OFF; `.env=1`)
- When ON: replace the divergence logic with the cup-and-handle detector above (pure CCI structure on `b.cci_14`; the bars carry it). Detect, in the lookback window: (a) a bar < −200 [LONG] / > +200 [SHORT]; (b) recovery crossing −100 / +100 forming a local peak/trough = the rim; (c) a handle = a higher-low / lower-high or a ≥3-bar flat that holds; (d) fire on the bar that breaks the rim. Entry = that bar's close; direction = the reversal side.
- When OFF: keep today's divergence logic (no change) — so this is reversible and A/B-testable.
- Keep the existing AP8/AP3 anti-patterns + the ATR/stop-anchor stop machinery (only the detection structure changes).
- **Strategic note:** like HTLB, VEGAS marks trend-END. Consider whether a confirmed VEGAS should set/feed a directional bias (it already groups REVERSAL); at minimum it must fire only the cup-and-handle, not divergence.

## Backtest + test + verify (Rule 5)
1. Backtest `VEGAS_SPEC_V2` ON vs OFF across the shadow history: today's divergence VEGAS = 1 fire/+$54; report what the cup-and-handle detector fires instead (likely a different, rarer set) + P&L.
2. `pytest tests/v9/regression/test_vegas_spec_v2.py` — anti-tautological: ON fires a crafted −200→−100→higher-low→rim-break LONG; ON does NOT fire a plain HH/LH divergence (the old trigger); OFF still fires the divergence (proves the flag swaps the logic).
3. `gen_flag_index.py --check`=0 (document the flag). NOT-DONE.
4. ⚠️ Run the FULL suite with all flags ON before declaring done (flag-interaction check — this has bitten 3×).

_Source spec preserved verbatim from Michael's VEGAS sheet (cup-and-handle, LONG + SHORT condition lists)._
