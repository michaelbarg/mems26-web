# CC Handoff — ZLR Spec v2 (Michael's source characterization) 2026-06-24

_Author: Cowork · contract: `docs/handoff/CC_HANDOFF_CONTRACT.md`. CC develops; Cowork verifies. Same shape as `TLB_SPEC_V2`._

## Why
`backend/v9/systems/woodies/patterns/zlr.py` fires on **CCI-14 geometry ALONE** (extreme→pullback→bounce). It ignores every Woodies confirmation Michael's spec requires → it fires low-quality setups (shadow: **35 fires, −$268**). All the needed study fields **already exist on `WoodiesBar`** (`cci_6_tcci`, `ema_34`, `swi_value`, `czi_value`, `trend_state`) — the detector just doesn't read them.

## Michael's source spec — ZLR (Zero Line Reject), continuation
The pattern joins a not-too-deep correction at the moment the trend renews. 3 stages (LONG / uptrend shown; SHORT mirrors):

**Stage 1 — "trend":**
1. CCI stayed **≥ 6 bars above the 0 line** (i.e. blue).
2. CCI reached **above 100** for ≥ 1 bar.
3. **SWI yellow** for ≥ 1 bar.
4. **last 3 bars above EMA-34** (price chart).
5. Preferably CCI did not exceed 200 (NOT mandatory).

**Stage 2 — "correction" (not too deep):**
1. CCI turns **down**.
2. CCI **drops below 100**.
3. CCI does **NOT drop below −100**.

**Stage 3 — "return to trend" (entry):**
1. Reversal preferably happens **hugging EMA-34 and above it** (price chart).
2. CCI turns **back up sharply** with the Stage-1 trend.
3. **≥ 15–20 CCI units** difference between the entry bar and the previous bar.
4. At the reversal, **±200 line (SWI/SI) is yellow or green** (normal/strong momentum).
5. **±100 line (CZI) light-blue/cyan for ≥ the last 3 bars**.
6. Preferably **TCCI (fast oscillator) leads** at the reversal.
7. At the entry bar close, **CCI value ≤ 120**.
8. If the first bar of this stage lacks momentum (**SWI red**), enter on the **2nd bar** once the same conditions hold.

## Current code vs spec (the gaps to close)
| Stage | Spec condition | In code today? |
|---|---|---|
| 1.1 | CCI ≥6 bars above 0 (blue) | ❌ |
| 1.2 | CCI >100 ≥1 bar | ✅ (`cci_history[i] >= 100`) |
| 1.3 | SWI yellow ≥1 bar | ❌ |
| 1.4 | last 3 bars above EMA-34 | ❌ |
| 2.* | pullback <100, not <−100 | ✅ |
| 3.3 | ≥15–20 CCI diff entry vs prev | ❌ (code: any `current>prev`) |
| 3.7 | entry CCI ≤120 | ❌ (code allows `<200`) |
| 3.4 | ±200 SWI yellow/green | ❌ |
| 3.5 | ±100 CZI cyan ≥3 bars | ❌ |
| 3.6 | TCCI leads | ❌ |
| 3.1 | reversal hugging/above EMA-34 | ❌ |
| 3.8 | 2nd-bar entry if SWI red | ❌ |

## Fix — flag `ZLR_SPEC_V2` (default OFF; `.env=1`)
When ON, gate the ZLR fire on the spec conditions above, using the `WoodiesBar` fields:
- `trend_state` (blue) + a 6-bar look for 1.1; `b.cci_14` for 1.2/2.*/3.2/3.3/3.7; `b.ema_34` vs `b.close` for 1.4/3.1; `b.swi_value` for 1.3/3.4/3.8; `b.czi_value` for 3.5; `b.cci_6_tcci` for 3.6.
- **Tighten 3.7 to ≤120** and **add the ≥15–20 CCI sharpness (3.3)** — these two alone remove most of the bad fires.
- When OFF → today's CCI-only behavior (no change). Mandatory conditions = hard gates; "preferably" (1.5, 3.1, 3.6) = soft/confidence, not vetoes.
- **SWI/CZI color sub-task:** the spec uses COLORS (SWI yellow/green/red, CZI cyan) but the bar carries numeric `swi_value`/`czi_value`. Determine the value→color mapping from the Sierra Woodies study (there are `swi_state`/`czi_state` columns in `v9_woodies_signals` and color logic in the frontend `woodiesDesignerSpec` — reuse, don't invent). Document the mapping.

## Backtest + test + verify (Rule 5)
1. Backtest `ZLR_SPEC_V2` ON vs OFF across the shadow history: report fires kept/dropped + P&L delta (today 35 fires/−$268; expect the ≤120 + 15–20 + SWI/CZI gates drop the losers).
2. `pytest tests/v9/regression/test_zlr_spec_v2.py` — anti-tautological: OFF fires today's set; ON drops a no-SWI / CCI-140-entry / 5-unit-bounce case; ON fires a full-spec case.
3. `gen_flag_index.py --check`=0 (document the flag). NOT-DONE section (esp. the color-mapping if unresolved).

_Source spec preserved here verbatim from Michael's ZLR sheet (3 stages + the LONG condition list). SHORT mirrors (downtrend, CCI ≤−100, SWI/CZI mirror)._
