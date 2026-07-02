# CC Research Handoff — INITIATIVE (S2): Optimal Construction (Geometry · CVD · Distances/Sizes · Stop)

**Date:** 2026-06-30 · **Owner:** Michael · **Prepared by:** Cowork
**Contract:** `docs/handoff/CC_HANDOFF_CONTRACT.md` — anti-tautological, **paste command + raw output (Rule 5)**, mandatory NOT-DONE.
**Type:** **RESEARCH (data study → report). NO code change, NO new detection, NO flag enable.** Output = a findings report + a recommended-parameter table + a worked example that will feed a *later* implementation handoff.
**Read first:** `docs/spec_authority/PATTERN_PAGE.html`, `docs/spec_authority/REACTIVE_SPEC_DRAFT.md`, `docs/spec_authority/PATTERN_ACCESS_MAP.md`, `docs/SOURCE_OF_TRUTH.md`, `docs/FLAG_INDEX.md`; code: `backend/v9/systems/five_min/five_min_system.py::_detect_initiative`, `daytype_position_gate.py`, `structural_targets.py`, `config/stop_anchors.yaml`, `services/trade_context.py`.

---

## 0 · Why — and what we ALREADY found (start grounded; do NOT re-explore blind)
INITIATIVE is S2's trend-continuation pattern (the pair to REACTIVE). This session's live-data + worked-example analysis already surfaced the hypotheses — your job is to **quantify and confirm/refute them on the full sample**, not rediscover them.

Findings to build on (from `v9_trades` firing_system=2 + the two worked examples):
- **23 live INITIATIVE trades** (18 SHORT, 5 LONG). The losses concentrate in **Variation SHORT: −$529 raw (n=13)** → but **de-duplicated to one fire per setup it is only −$79 (n=6)**. **≈$450 of the loss was duplicate/clustered fires** (06-29: 4 fires in 9 min, 2 in the same minute; 06-19: 2 same minute). Dedup (Stage 3) is the single biggest lever.
- After dedup: **Trend_Normal SHORT 2/2 win (+0.85R, +$89)**, **Variation LONG +1.95R (incl. +4.89R on 06-24)**, **Variation SHORT still weak (−0.23R)**.
- **Winner — 06-24 LONG**, entry **7481**: at the **value-area edge** (VAL 7478 / VAH 7489.5), CVD **positive & rising** (+6.4k→+12.3k = buyers), single fire; tight initial stop (~2.4 pt) **trailed up to exit 7492.75 = +4.89R**.
- **Loser — 06-29 SHORT cluster**, entry ~**7415-7425**: **~80 pt BELOW VAL (7495.5)** = chasing the extreme; CVD negative **but with ABSORPTION/divergence** (17:05 −6.2k → 17:10 −2.8k while price made a *lower low* = failing drive); 4 clustered fires; violent **snap-back to 7491 = −1R each**.

**The 4 candidate levers to quantify:** (1) **location vs value-area** + a **max-distance-from-value cap** (anti-chase); (2) **CVD absorption/divergence veto** — the current `_detect_initiative` only checks net-flow **sign** (`net_delta<0`), which the loser PASSED; (3) **stop** = keep tight + structural trail (validate the prior "tight wins +11%, n=5188" in the new trend-only context); (4) **dedup** (Stage 3, separate).

---

## 1 · Data sources (canonical — verify freshness/coverage first, Rule 2)
| Need | Source | Note |
|------|--------|------|
| Bars + Value Area | `v9_bars_5min` (OHLC, volume, `poc_vol`, `vah`, `val`, `cumulative_delta`) | 41 days, 2026-04-16→06-30, RTH |
| **Live CVD stream** | `v9_bars_cumulative_delta` | per SOURCE_OF_TRUTH (live). Reconcile vs `v9_bars_5min.cumulative_delta`; **state which you use per analysis and why** |
| TPO / value migration | `v9_tpo_sessions` (POC/VAH/VAL over session) | for distance-from-value + value-migration-direction |
| Day-type (S1) | `classify_replay` / `v9_day_type_state` (7-type) | segment EVERYTHING by this; note confidence/lock_state |
| Trend / LSMA / CCI (S4 context) | `v9_bars_5min_woodies` | LSMA side + CCI for with-trend context |
| Live INITIATIVE outcomes | `v9_trades` (firing_system=2, classification `INITIATIVE%`) | 23 rows; `day_type_at_entry`, `pnl_r`, `outcome`, entry/stop/t1-t3, `*_hit_ts` |

⚠️ `day_type_at_entry` on pre-fix rows is contaminated by the pre-IB-lock fallback (the 06-29 "Variation" label). Cross-check against the resolved/`classify_replay` type. **S2⟂S3: footprint COT/AMT is muted — do NOT use it as a requirement.**

---

## 2 · Research questions (quantify EACH with raw output, segmented by day-type)
**R1 — Geometry.** Sweep and measure expectancy (avg R) + win-rate per choice, on **Trend/Variation days only**:
- B1 expansion floor/ceiling — absolute vs ATR-relative (`get_expansion_range`, `S2_ATR_RELATIVE`, `vol_adaptive`). What size IS the impulse on winners vs losers?
- B2 test type: generic Higher-Low vs POC-return vs **VAH/VAL-edge retest** (does anchoring B2 to the value edge beat the generic test?).
- B3 joining factor; B4 breakout-confirm (`close>B1.high`) vs alternatives.
- Output: the geometry combo with the best expectancy + the measured lift of the VA-retest anchor.

**R2 — CVD / cumulative (entry confirmation).** Compare rules for separating winners/losers at entry:
(a) net-flow **sign** [current], (b) **slope** `cvd[B4]−cvd[B1]`, (c) **entry-bar** per-bar delta, (d) **absorption/divergence veto** (price lower-low while CVD higher-low → drive failing → block). Quantify the **marginal lift of the absorption veto** (does it kill the 06-29 class without killing winners?). Use the **live CVD stream**.

**R3 — Distances + sizes.** Measure vs outcome:
- `|entry − nearest VA edge|` and `|entry − POC|` → find the optimal **max-distance-from-value cap** (the winner ≈0, the loser ≈80 pt). Is there a distance beyond which INITIATIVE is −EV (chasing)?
- Bar **sizes**: B1 range, range/ATR, IB width, and the entry's position within the day's developing range. Is there a size/volatility regime where it fails?
- Value-**migration** direction (is value migrating WITH the trade?) vs outcome.

**R4 — Stop.** On the trend-only + VA-retest sample, compare initial-stop placements by **expectancy AND max-adverse-excursion**: tight `breakout_bar` (current, 12 pt cap) vs **B2 step-low** vs ATR×k vs below-test-low. **Does the prior "tight wins +11% (n=5188)" hold in the new context?** Then evaluate the **trailing** rule (`DYNAMIC_STRUCT_TRAIL` re-anchor on each new consolidation) — which consolidation/step definition captures the most runner R (the winner trailed +11.75 pt = 4.89R from ~2.4 pt risk)?

**R5 — Cross-system lift (use EVERYTHING the stack has).** Quantify the **marginal** expectancy lift of each contextual filter, then find the **minimal set** that captures most of the edge: S1 day-type (trend/Variation, confidence≥?), opening-type (mode-1 pre-lock), LSMA-with-trend (S4), value-migration direction (TPO), single-fire (dedup), with-flow CVD, distance-cap. Rank by lift.

**R6 — Worked example.** Pick 2-3 real setups (must include 06-24 winner + 06-29 loser) and show the **recommended** rule firing/blocking correctly — annotate geometry, CVD, distance-from-value, and stop. Include a small table of the bar-by-bar values used.

---

## 3 · Method / discipline
- Replay over the 41 days: detect candidate INITIATIVE setups, simulate (entry next-bar-open, the chosen stop, structural/trailed exit), segment by day-type. **n is small — report confidence honestly and triangulate with the 23 live trades.**
- **Rule 2:** verify each source's last row is recent/covering before trusting it. **Rule 5:** paste the command + raw output for every number. Anti-tautological: report where each lever does NOT help, not only where it does.

## 4 · Deliverable
`docs/reports/INITIATIVE_RESEARCH_2026-06-30.md` containing: (a) a **recommended-parameter table** — geometry, CVD rule, distance cap, size filters, initial stop, trail rule — each with its measured expectancy + raw evidence; (b) the **ranked cross-system filter list** (marginal lift); (c) the **worked example**. Then update the INITIATIVE block in `PATTERN_PAGE.html` with the research verdict. This report feeds a **separate, later implementation handoff** — do not implement here.

## 5 · NOT-DONE (explicit)
- ❌ No code changes, no edits to `_detect_initiative`/gates/`stop_anchors.yaml`, no new flag, no flag enable.
- ❌ Do not touch REACTIVE, S4 patterns, or the live system.
- ❌ Do not re-enable S3/footprint (COT/AMT stays muted).
- ❌ Do not implement the levers — this handoff only produces the data-backed report + example that the implementation spec will be built from.
