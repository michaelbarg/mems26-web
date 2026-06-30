# CC Handoff — Stage 2: CVD Confirmation INSIDE S2 Geometry Detection

**Date:** 2026-06-30 · **Owner:** Michael · **Prepared by:** Cowork
**Contract:** `docs/handoff/CC_HANDOFF_CONTRACT.md` (anti-tautological tests + NOT-DONE + paste raw output, Rule 5).
**Flag:** `S2_CVD_DETECTION_V1` — **default OFF · SHADOW.** New flag.
**Read first:** `docs/spec_authority/PATTERN_PAGE.html` (stage tracker), `docs/spec_authority/REACTIVE_SPEC_DRAFT.md`, `docs/SOURCE_OF_TRUTH.md` (CVD source).

---

## Why
The S2 detectors are **CVD-blind** — verified: 0 references to cvd/cumulative_delta in `_detect_reactive`/`_detect_initiative` (they fire on raw bar volume + price geometry only; belly/COT are muted via S3). On **06-29** the REACTIVE-LONG reversal was missed even though CVD showed **+3,403 delta absorption at the 17:10 low** (buyers stepping in = the reversal). This session's investigation A (on live CVD) showed CVD **separates winners from losers direction-specifically**: REACTIVE-LONG winners had **+delta at the entry bar**; REACTIVE-SHORT winners had **net selling flow building over the 4-bar setup**.

Stage 0 already CVD-confirms the *opening type*. Stage 2 adds CVD confirmation to the *pattern geometry* itself.

> ⚠️ Distinct from Stage 0. Do NOT reuse the opening-window CVD; compute CVD over the **setup's own 4 bars (B1–B4)**.

## CVD source (CRITICAL — learned 06-29)
Use the **LIVE** CVD stream `v9_bars_cumulative_delta` (verified live) — **NOT** `v9_bars_5min.cumulative_delta` (RTH-only / stalls). Per-bar delta = diff of cumulative over the setup bars. **Freshness-guard:** if CVD is stale/unavailable for the setup window → **fail-OPEN** (skip the CVD requirement, fire on geometry as today) and log `S2_CVD: stale → geometry-only`. Never block all fires on missing CVD.

## Scope — behind `S2_CVD_DETECTION_V1` (default OFF)

### REACTIVE (reversal / fade) — `_detect_reactive` (final fire condition ~L672 LONG / ~L697 SHORT)
Add a CVD-confirmation term to the fire condition:
- **LONG:** confirm buyers at the reversal — `perbar_delta(B4) > 0` **OR** bullish divergence (price made a lower low across B1→B3 but CVD made a higher low = absorption, the 06-29 case).
- **SHORT:** mirror — `perbar_delta(B4) < 0` **OR** bearish divergence; **and/or** net selling slope over B1→B4 (`cvd[B4] − cvd[B1] < 0`), per investigation A (SHORT separated on the setup-window slope, LONG on the entry bar).
- Implement both signals; require (entry-bar term **OR** divergence) so a clean absorption qualifies.

### INITIATIVE (continuation / breakout) — `_detect_initiative` (~L787 LONG / ~L801 SHORT)
Confirm **with-flow**: LONG → net buying delta over the breakout (`cvd[B4] − cvd[B1] > 0`); SHORT → net selling. A breakout against the flow (e.g. delta absorption opposing the break) is suspect → do NOT confirm.

## Flag registry
Add `S2_CVD_DETECTION_V1` to `docs/FLAG_REGISTRY.yaml` (category s2; SHADOW/default-OFF), run `scripts/gen_flag_index.py`, commit `docs/FLAG_INDEX.md`.

## Tests (anti-tautological — both confirm & reject, realistic fixtures)
1. **REACTIVE_LONG + buyers** (`perbar_delta(B4)>0`) → confirmed (fires). 
2. **REACTIVE_LONG + sellers** (delta<0, no divergence) → CVD rejects (no fire).
3. **06-29 absorption regression:** REACTIVE_LONG geometry + price-LL/CVD-HL divergence (the +3,403 case) → confirmed.
4. **REACTIVE_SHORT + building sell-flow** (`cvd[B4]<cvd[B1]`) → confirmed; **+ buy-flow** → rejected.
5. **INITIATIVE_SHORT with-flow** (net selling) → confirmed; **against-flow** (absorption/buying) → rejected (would have suppressed a failing-drive short).
6. **Stale CVD → fail-open** (geometry-only fire, logged).
7. **Flag OFF → byte-identical** to current detection (all existing S2 detection tests pass).

## Verification (SHADOW · Rule 5)
- Enable in SHADOW; on the next REACTIVE/INITIATIVE setups, confirm via `S2_DETECTION_LOG` that CVD-confirmed fires pass and CVD-divergent ones are suppressed. Paste raw log lines.

## NOT-DONE (explicit)
- ❌ Do NOT touch the opening-type CVD (Stage 0) or the gateway gates (Stage 1/1b).
- ❌ Stage 3 (single-fire/DEDUP), Stage 4 (REACTIVE tweaks: B2 0.85 / 2T stop / HVN-POC targets / 2nd-test), Stage 5 (HnS/Double/TT calibration).
- ❌ Do NOT re-enable S3/footprint belly/COT (separate, deferred until after LIVE).
- ❌ Do NOT enable the flag live — SHADOW + Michael sign-off.
